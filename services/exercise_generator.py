"""
Exercise Generation Service
Uses Google Gemini API to generate coding exercises from PDF content
"""

import hashlib
import logging
import re
import time
import json
from concurrent.futures import ThreadPoolExecutor

import config

logger = logging.getLogger(__name__)

# Bump this constant whenever the Gemini prompt changes so the flywheel can
# measure whether the change improved exercise quality.
PROMPT_TEMPLATE_VERSION = "v1.3"

# Use the model configured in config.py / GEMINI_MODEL env var.
# Defaults to gemini-flash-latest if not set (alias always tracks latest stable Flash).
_GEMINI_MODEL = config.GEMINI_MODEL or "gemini-flash-latest"
_GENERATION_PARAMS = {"temperature": 0.7, "maxOutputTokens": 8192}
_TRUNCATION_LIMIT = 10_000

# --- Chunked extraction (behind config.FEATURE_PDF_CHUNKING, default OFF) ---
# See reports/product-engineer/PDF_TRUNCATION_FIX_PLAN.md. When the flag is
# off, generate_exercises_from_pdf_content() is byte-for-byte identical to
# before this fix (single slice at _TRUNCATION_LIMIT, one Gemini call).
_CHUNK_BOUNDARY_LOOKBACK = 300  # chars to look back for a "\n\n" cut point
_CHUNK_CONCURRENCY = 4  # bounded concurrent Gemini calls per chapter
_DEDUPE_SIMILARITY_THRESHOLD = 0.6  # Jaccard word-overlap threshold for "duplicate"

# Adam's approved copy (2026-08-12) for when content still exceeds the chunk
# cap (config.PDF_MAX_CHUNKS) even after chunking. Wording is Adam's call —
# see reports/product-engineer/2026-08-13.md "Needs Adam" for variants.
CONTENT_WARNING_TITLE = "Large document — partial content used"
_CONTENT_WARNING_MESSAGE_TEMPLATE = (
    "This chapter is {total_chars:,} characters long. We generated exercises "
    "from the first {chars_processed:,} characters; the rest was not used. "
    "For full coverage, split this PDF into smaller chapters and upload each "
    "one separately."
)


class _ExerciseList(list):
    """A plain list of validated exercise dicts with one extra attribute,
    `content_warning` (None, or a dict — see part (b) of the fix plan).

    Subclassing list (rather than returning a tuple) keeps every existing
    caller that does `len(exercises)`, `exercises[0]["title"]`, or iterates
    the return value working completely unchanged — this is what keeps the
    chunking change backward-compatible for callers that don't yet read
    `content_warning` (workers/tasks.py, scripts/regenerate_exercises.py),
    which are out of scope for this fix per the approved plan's file list.
    """

    content_warning = None


def _extract_topics(title: str, description: str) -> list[str]:
    """
    Simple keyword extraction from exercise title + description for the flywheel.
    Splits on non-word characters, lowercases, and keeps tokens > 2 chars that
    are not common stop-words.  Does NOT make any AI call.
    """
    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "into",
        "your",
        "you",
        "are",
        "use",
        "using",
        "write",
        "create",
        "define",
        "return",
        "function",
        "method",
        "value",
        "values",
        "given",
        "one",
        "two",
        "all",
        "each",
        "its",
        "has",
        "can",
        "not",
        "new",
        "any",
        "how",
    }
    text = f"{title} {description}".lower()
    tokens = re.split(r"[^a-z0-9_]+", text)
    seen: set = set()
    topics: list = []
    for tok in tokens:
        if len(tok) > 2 and tok not in stop_words and tok not in seen:
            seen.add(tok)
            topics.append(tok)
            if len(topics) >= 10:
                break
    return topics


def _extract_partial_exercises(content):
    """
    Salvage complete exercise JSON objects from a truncated/malformed response.
    Scans for balanced {...} blocks and attempts to parse each one individually.
    Returns a list of successfully parsed exercise dicts (may be empty).
    """
    results = []
    depth = 0
    start = None
    for i, ch in enumerate(content):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                candidate = content[start : i + 1]
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict) and "title" in obj:
                        results.append(obj)
                except json.JSONDecodeError:
                    pass
                start = None
    if results:
        logger.warning(
            "_extract_partial_exercises: salvaged %d exercise(s) from malformed JSON", len(results)
        )
    return results


def _split_into_chunks_with_offsets(
    text, chunk_size, overlap, boundary_lookback=_CHUNK_BOUNDARY_LOOKBACK
):
    """Split `text` into overlapping (start, end) offset pairs covering all of it.

    - No chunk exceeds `chunk_size` characters.
    - Consecutive chunks overlap by up to `overlap` characters so content
      straddling a boundary isn't lost from both sides.
    - Boundary snapping: instead of cutting at the raw chunk_size offset, look
      back up to `boundary_lookback` characters for the nearest paragraph
      break ("\\n\\n") and cut there; fall back to the raw cut point if none
      is found nearby.
    - Does NOT enforce config.PDF_MAX_CHUNKS — callers apply that cap and
      compute the content_warning from however many offsets they keep.

    Returns [] for empty/falsy text, [(0, len(text))] if text already fits in
    one chunk.
    """
    if not text:
        return []
    n = len(text)
    if n <= chunk_size:
        return [(0, n)]

    offsets = []
    start = 0
    while start < n:
        raw_end = min(start + chunk_size, n)
        end = raw_end
        if raw_end < n:
            lookback_start = max(start, raw_end - boundary_lookback)
            snap_idx = text.rfind("\n\n", lookback_start, raw_end)
            if snap_idx > start:
                end = snap_idx
        offsets.append((start, end))
        if end >= n:
            break
        next_start = end - overlap
        if next_start <= start:  # guard against zero/negative forward progress
            next_start = end
        start = next_start
    return offsets


def _split_into_chunks(text, chunk_size, overlap):
    """Pure function: split `text` into a list of overlapping chunk strings.

    See _split_into_chunks_with_offsets for the exact splitting rules. This
    is the function named in reports/product-engineer/PDF_TRUNCATION_FIX_PLAN.md
    part (d); generate_exercises_from_pdf_content() uses the offset-returning
    variant internally so it can compute chars_processed for the content
    warning without re-scanning the text.
    """
    return [text[s:e] for s, e in _split_into_chunks_with_offsets(text, chunk_size, overlap)]


def _jaccard_similarity(text_a, text_b):
    """Word-overlap similarity in [0, 1]. No LLM call — simple and deterministic."""
    words_a = set(re.findall(r"[a-z0-9]+", text_a.lower()))
    words_b = set(re.findall(r"[a-z0-9]+", text_b.lower()))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def _dedupe_exercises(exercises, threshold=_DEDUPE_SIMILARITY_THRESHOLD):
    """Drop near-duplicate exercises generated from overlapping chunks.

    Compares `title + description` of each exercise via Jaccard word-overlap
    similarity against every exercise already kept. Pairs at/above `threshold`
    are treated as duplicates; the earlier one (lower index — earlier chunk,
    since callers pass exercises in chunk order) is kept and the later one is
    dropped. Preserves input order for everything kept.
    """
    kept = []
    kept_texts = []
    for ex in exercises:
        text = f"{ex.get('title', '')} {ex.get('description', '')}"
        if any(_jaccard_similarity(text, kept_text) >= threshold for kept_text in kept_texts):
            continue
        kept.append(ex)
        kept_texts.append(text)
    return kept


def _build_exercise_prompt(chapter_title, content_text):
    """Build the exercise-generation prompt for one chunk (or the whole chapter
    when chunking is off). Identical template to the pre-chunking implementation
    so a single-chunk chapter produces a byte-identical prompt to before this fix.
    """
    return f"""You are a coding tutor creating beginner-friendly exercises for a university course.

Analyze the chapter below and generate 5 to 8 short, focused coding exercises.

Chapter Title: {chapter_title}
Chapter Content:
{content_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — DETECT THE LANGUAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read the chapter content carefully and identify the primary programming language or tool being taught (e.g. Python, R, SQL, JavaScript, Java, Scala, MATLAB, etc.).
Use ONLY that language for all exercises. Do NOT default to Python unless the content is clearly Python-based.
If the content covers multiple languages, pick the dominant one.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT RULES — follow every one of these exactly:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ONE CONCEPT PER EXERCISE
  • Each exercise teaches exactly one thing (e.g. "compute the mean", NOT "compute the mean, std, and percentage above average").
  • If a topic naturally has three sub-steps, make three separate exercises.

SELF-CONTAINED (CRITICAL)
  • Every exercise MUST work completely on its own — define all data inline.
  • NEVER reference another exercise: no "using the DataFrame from exercise 1", no "continuing from the previous task", no "building on what you created above".
  • A student must be able to do exercise 3 without having done exercises 1 or 2.

FUNCTION STRUCTURE (critical for automated grading)
  • Every exercise solution MUST define a named function that:
      – accepts named parameters (not hardcoded data)
      – returns the result (not just prints it)
      – also prints the result with a label for human readability
  • The function name must be short, descriptive, and in snake_case for Python/R
    or camelCase for JavaScript/Java.
  • You MUST include this function name as the "function_name" field in the JSON output.
  • Example (Python):
      def calculate_mean(numbers):
          mean = sum(numbers) / len(numbers)  # compute the average
          print("Mean:", mean)                 # display for student
          return mean                          # return for automated testing

SOLUTION CODE SIZE
  • 5 to 10 lines of actual code (import/library lines do not count toward the limit).
  • If you need more lines, the exercise covers too much — split it.
  • Do NOT add a standalone function call below the definition (e.g. no `calculate_mean([1,2,3])` at the bottom). The print statement inside the function is sufficient — there is no need for an extra call line.

COMMENT EVERY LINE
  • Every single line of code must have an inline comment explaining what it does.
  • Use the comment style native to the detected language (e.g. # for Python/R, -- for SQL, // for JavaScript/Java).

OUTPUT THE RESULT
  • The last statement of every exercise must output/print the result with a label using the idiom of the detected language.
  • Python: `print("Mean age:", mean_age)`
  • R: `cat("Mean age:", mean_age, "\\n")`
  • SQL: the SELECT result is the output — end with a meaningful SELECT.
  • JavaScript: `console.log("Mean age:", meanAge)`

KEEP IT BEGINNER-FRIENDLY
  • No deeply nested logic — use guard clauses or split into separate exercises.
  • No complex one-liners — store each intermediate result in a named variable.
  • Use only the standard/idiomatic features of the detected language.

NAMED INTERMEDIATE VARIABLES
  • Never compute and use a value in the same expression.
  • Bad (Python):  `print(df["age"].mean())`
  • Good (Python): `mean_age = df["age"].mean()` then `print("Mean age:", mean_age)`

IMPORTS / DEPENDENCIES
  • Include only the imports or library calls actually used in that exercise.
  • Use standard aliases/conventions for the detected language and ecosystem.

DATA
  • PRIORITY: If the chapter shows a specific dataset, table, or list of values, USE THOSE EXACT VALUES in the exercise. This makes the exercise feel grounded in the lesson.
  • If no specific values exist, use small synthetic data defined inline (5–10 values max).
  • Reference well-known public datasets (seaborn "tips"/"iris", R built-ins, SQL inline inserts) only as a last resort.
  • Do NOT reference external files that may not exist on the student's machine.
  • Always include the inline data in the description so the student knows what to work with.

DIFFICULTY
  • First 2–3 exercises: "easy" (single operation, one function/method call).
  • Next 2–3 exercises: "medium" (combine two concepts, still one idea per exercise).
  • Remaining exercises (if any): "hard" (multi-step logic, conditional branching, or real-world data wrangling — still one idea per exercise).

TEST CASES (critical for automated grading)
  • Generate 5–8 test cases per exercise.
  • Each test case calls the function with a specific input and checks its output.
  • "input" must be a JSON-serialisable value (string, number, list, dict, or null).
    For functions that take no arguments, use null.
  • "expected_output" must be the exact string that the function returns (as a string),
    or the string representation of its return value.
  • Keep inputs small and self-contained — no file I/O, no external state.
  • If the exercise uses pandas/numpy/etc., use small inline data (3–5 elements max).
  • Include at least one edge case (e.g. empty list, zero, negative number) where appropriate.
  • "weight" is 1 for all test cases.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return your response as a JSON array with ONLY this structure — no markdown, no code fences, no extra text:
[
  {{
    "language": "The detected language name, e.g. Python, R, SQL, JavaScript",
    "title": "Short action-oriented title describing the exact goal, e.g. 'Calculate the Mean of Test Scores'",
    "description": "EXACTLY 2 sentences — no more. Sentence 1: state the specific data the student will work with (include the actual values from the chapter, e.g. 'You have the following test scores: [10, 15, 12, 14, 17, 17, 20, 8, 5, 13].'). Sentence 2: state exactly what the student must do and what function to write, e.g. 'Write a function called calculate_mean(scores) that computes and returns the mean of a list of numbers.' CRITICAL RULES: (a) NEVER reference another exercise — every exercise is standalone; (b) NEVER say 'using the DataFrame/list/variable from the previous exercise' — define the data fresh in every description; (c) keep both sentences concise and specific.",
    "difficulty": "easy|medium|hard",
    "function_name": "snake_case function name the student must define",
    "solution_code": "Code in the detected language — every line commented, result output at end, 5-10 lines max",
    "test_cases": [
      {{
        "description": "Short label for this test",
        "input": "JSON-serialisable value",
        "expected_output": "Exact expected return value as a string",
        "weight": 1
      }}
    ]
  }}
]"""


def _call_gemini_generate(prompt, api_key):
    """Make one Gemini generateContent call for one prompt (one chunk, or the
    whole chapter when chunking is off) and return validated exercises + usage.

    Returns {"exercises": [...raw validated dicts, no _gen_meta...],
    "prompt_tokens": int|None, "completion_tokens": int|None,
    "generation_time_ms": int}.

    Raises the same Exception types/messages as the pre-chunking implementation
    (same request shape, same parsing/validation/salvage logic) so callers and
    tests that assert on those messages are unaffected by this refactor.
    """
    import requests

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{_GEMINI_MODEL}:generateContent?key={api_key}"

    # Disable thinking mode on thinking-capable models (e.g. gemini-2.5-*).
    # Without this, the model's internal reasoning tokens can corrupt the
    # structured JSON output, causing JSONDecodeError mid-response.
    gen_config = {
        "temperature": _GENERATION_PARAMS["temperature"],
        "maxOutputTokens": _GENERATION_PARAMS["maxOutputTokens"],
        "responseMimeType": "application/json",
    }
    if "2.5" in _GEMINI_MODEL or "3." in _GEMINI_MODEL:
        gen_config["thinkingConfig"] = {"thinkingBudget": 0}

    content = None
    try:
        _t0 = time.monotonic()
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": gen_config,
            },
            timeout=config.GEMINI_TIMEOUT,
        )
        generation_time_ms = int((time.monotonic() - _t0) * 1000)

        if not response.ok:
            error_data = response.json() if response.content else {}
            error_message = error_data.get("error", {}).get(
                "message", "Failed to generate exercises"
            )
            raise Exception(f"Gemini API error: {error_message}")

        data = response.json()

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount")
        completion_tokens = usage.get("candidatesTokenCount")

        if "candidates" not in data or len(data["candidates"]) == 0:
            raise Exception("No response from Gemini API")

        content = data["candidates"][0]["content"]["parts"][0]["text"]
        content = content.strip()

        # Robust extraction: Find the first [ and last ]
        start_index = content.find("[")
        end_index = content.rfind("]")

        if start_index != -1 and end_index != -1 and end_index > start_index:
            content = content[start_index : end_index + 1]
        elif "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        try:
            exercises_raw = json.loads(content)
        except json.JSONDecodeError:
            exercises_raw = _extract_partial_exercises(content)
            if not exercises_raw:
                raise

        if not isinstance(exercises_raw, list):
            raise Exception("Invalid response format: expected array")

        validated_exercises = []
        for exercise in exercises_raw:
            if not isinstance(exercise, dict):
                continue

            difficulty = exercise.get("difficulty", "medium").lower()
            if difficulty not in ("easy", "medium", "hard"):
                difficulty = "medium"

            raw_cases = exercise.get("test_cases", [])
            validated_cases = []
            if isinstance(raw_cases, list):
                for tc in raw_cases:
                    if not isinstance(tc, dict):
                        continue
                    if "input" not in tc or "expected_output" not in tc:
                        continue
                    validated_cases.append(
                        {
                            "description": tc.get("description", ""),
                            "input": tc["input"],
                            "expected_output": tc["expected_output"],
                            "weight": int(tc.get("weight", 1)),
                        }
                    )

            validated_exercises.append(
                {
                    "language": exercise.get("language", "Unknown"),
                    "title": exercise.get("title", "Untitled Exercise"),
                    "description": exercise.get("description", ""),
                    "difficulty": difficulty,
                    "function_name": exercise.get("function_name", "solution"),
                    "solution_code": exercise.get("solution_code", ""),
                    "test_cases": validated_cases,
                }
            )

        return {
            "exercises": validated_exercises,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "generation_time_ms": generation_time_ms,
        }

    except json.JSONDecodeError as e:
        snippet = (content[:500] + "...") if content and len(content) > 500 else (content or "")
        logger.error("Failed to parse Gemini JSON response: %s. Content snippet: %s", e, snippet)
        raise Exception("Failed to parse the exercise response from AI. Please try again.")


def _build_gen_meta(
    exercise,
    source_content_hash,
    source_content_type,
    source_char_count,
    was_truncated,
    call_result,
    chunk_index=None,
    total_chunks=None,
):
    """Assemble the flywheel `_gen_meta` block for one validated exercise dict."""
    meta = {
        "source_content_hash": source_content_hash,
        "source_content_type": source_content_type,
        "source_char_count": source_char_count,
        "was_truncated": was_truncated,
        "detected_language": exercise["language"],
        "detected_topics": _extract_topics(exercise["title"], exercise["description"]),
        "gemini_model": _GEMINI_MODEL,
        "prompt_template_version": PROMPT_TEMPLATE_VERSION,
        "prompt_tokens": call_result["prompt_tokens"],
        "completion_tokens": call_result["completion_tokens"],
        "generation_params": _GENERATION_PARAMS,
        "difficulty_generated": exercise["difficulty"],
        "exercise_type": "generated",
        "exercise_structure": {
            "has_starter_code": False,
            "num_test_cases": len(exercise["test_cases"]),
            "instruction_length_chars": len(exercise["description"]),
            "has_solution": bool(exercise["solution_code"]),
        },
        "num_test_cases": len(exercise["test_cases"]),
        "generation_time_ms": call_result["generation_time_ms"],
    }
    if chunk_index is not None:
        meta["chunk_index"] = chunk_index
        meta["total_chunks"] = total_chunks
    return meta


def generate_exercises_from_pdf_content(
    pdf_text, chapter_title, api_key=None, source_content_type=None
):
    """
    Generate coding exercises from PDF text using Gemini API.

    Args:
        pdf_text: Extracted text from PDF
        chapter_title: Title of the chapter
        api_key: Google Gemini API key (optional, can use env var)
        source_content_type: File extension of the source (e.g. "pdf", "ipynb") for flywheel

    Returns:
        _ExerciseList (behaves as a plain list): exercise dicts with title,
        description, difficulty, function_name, solution_code, test_cases,
        and _gen_meta (flywheel metadata). Callers that do not need _gen_meta
        can ignore it. The returned object also has a `.content_warning`
        attribute — None unless config.FEATURE_PDF_CHUNKING is on AND the
        chapter still exceeded config.PDF_MAX_CHUNKS after chunking (see
        reports/product-engineer/PDF_TRUNCATION_FIX_PLAN.md part (b)).

    When config.FEATURE_PDF_CHUNKING is False (the default), this function's
    behavior is unchanged from before the chunking fix: a single Gemini call
    on the first _TRUNCATION_LIMIT (10,000) characters, content_warning
    always None. This preserves exact backward compatibility for the
    default/production path until Adam explicitly flips the flag.
    """
    if not api_key:
        api_key = config.GEMINI_API_KEY

    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables")
        raise Exception(
            "Configuration Error: GEMINI_API_KEY is missing. Please set this environment variable in Render."
        )

    original_len = len(pdf_text) if pdf_text else 0
    source_content_hash = hashlib.sha256(
        (pdf_text or "").encode("utf-8", errors="replace")
    ).hexdigest()

    if not config.FEATURE_PDF_CHUNKING:
        # --- Pre-chunking behavior, byte-for-byte unchanged -----------------
        was_truncated = original_len > _TRUNCATION_LIMIT
        truncated_text = pdf_text[:_TRUNCATION_LIMIT] if was_truncated else pdf_text
        prompt = _build_exercise_prompt(chapter_title, truncated_text)

        try:
            call_result = _call_gemini_generate(prompt, api_key)
        except Exception as e:
            logger.error("Error generating exercises: %s", e)
            raise

        validated_exercises = _ExerciseList()
        for exercise in call_result["exercises"]:
            validated_exercises.append(
                {
                    **exercise,
                    "_gen_meta": _build_gen_meta(
                        exercise,
                        source_content_hash,
                        source_content_type,
                        len(truncated_text),
                        was_truncated,
                        call_result,
                    ),
                }
            )
        validated_exercises.content_warning = None
        return validated_exercises

    # --- Chunked extraction path (config.FEATURE_PDF_CHUNKING = True) -------
    offsets = _split_into_chunks_with_offsets(
        pdf_text or "", config.PDF_CHUNK_SIZE, config.PDF_CHUNK_OVERLAP
    )
    capped = len(offsets) > config.PDF_MAX_CHUNKS
    used_offsets = offsets[: config.PDF_MAX_CHUNKS] if capped else offsets
    total_chunks = len(used_offsets)
    chars_processed = used_offsets[-1][1] if used_offsets else 0
    chars_total = original_len

    if total_chunks == 0:
        result = _ExerciseList()
        result.content_warning = None
        return result

    chunk_jobs = [
        (idx, pdf_text[s:e], _build_exercise_prompt(chapter_title, pdf_text[s:e]))
        for idx, (s, e) in enumerate(used_offsets)
    ]

    def _run_chunk(job):
        idx, _chunk_text, prompt = job
        try:
            return idx, _call_gemini_generate(prompt, api_key), None
        except Exception as e:
            logger.warning(
                "PDF chunk %d/%d exercise generation failed, continuing with remaining chunks: %s",
                idx + 1,
                total_chunks,
                e,
            )
            return idx, None, e

    # Bounded concurrency: run up to _CHUNK_CONCURRENCY chunks at a time so a
    # multi-chunk chapter's total latency stays close to a single call's
    # latency instead of growing linearly with chunk count (demo's <60s budget).
    chunk_results = [None] * total_chunks
    with ThreadPoolExecutor(max_workers=min(_CHUNK_CONCURRENCY, total_chunks)) as executor:
        for idx, call_result, err in executor.map(_run_chunk, chunk_jobs):
            chunk_results[idx] = (call_result, err)

    merged = []
    any_success = False
    for idx, (call_result, err) in enumerate(chunk_results):
        if call_result is None:
            continue
        any_success = True
        for exercise in call_result["exercises"]:
            merged.append(
                {
                    **exercise,
                    "_gen_meta": _build_gen_meta(
                        exercise,
                        source_content_hash,
                        source_content_type,
                        chars_processed,
                        capped,
                        call_result,
                        chunk_index=idx,
                        total_chunks=total_chunks,
                    ),
                }
            )

    if not any_success:
        # Today's behavior — raise — is preserved only when EVERY chunk fails.
        first_err = next((err for _, err in chunk_results if err), None)
        logger.error("Error generating exercises: all %d chunk(s) failed", total_chunks)
        raise first_err or Exception("Failed to generate exercises for any chunk.")

    deduped = _dedupe_exercises(merged)

    content_warning = None
    if capped:
        content_warning = {
            "truncated": True,
            "title": CONTENT_WARNING_TITLE,
            "message": _CONTENT_WARNING_MESSAGE_TEMPLATE.format(
                total_chars=chars_total, chars_processed=chars_processed
            ),
            "chars_processed": chars_processed,
            "chars_total": chars_total,
        }

    result = _ExerciseList(deduped)
    result.content_warning = content_warning
    return result


def generate_test_cases_for_exercise(title, description, solution_code, language, api_key=None):
    """
    Generate test cases for an existing exercise using its description and solution code.

    Args:
        title: Exercise title
        description: Exercise description (what the student must do)
        solution_code: Reference solution code
        language: Programming language (Python, R, SQL, etc.)
        api_key: Google Gemini API key (optional, falls back to env var)

    Returns:
        dict: {"function_name": str, "test_cases": [...]}
              test_cases shape: [{description, input, expected_output, weight}, ...]
    """
    if not api_key:
        api_key = config.GEMINI_API_KEY
    if not api_key:
        raise Exception("GEMINI_API_KEY is not configured.")

    prompt = f"""You are a coding tutor. Generate automated test cases for the exercise below.

Language: {language}
Title: {title}
Description: {description}

Reference solution:
```{language.lower()}
{solution_code}
```

Your job:
1. Identify the single function the student must write (look at the description and solution).
2. Generate 3–5 test cases that verify correct behaviour.

Rules:
- Each test case calls the function with specific inputs and checks the output.
- "input" must be a JSON-serialisable value (string, number, list, dict, or null).
  For no-argument functions use null.
- "expected_output" must be the exact string that the function PRINTS (not returns),
  or the string representation of what it returns if it prints nothing.
- Keep inputs small and self-contained (no file I/O, no external state).
- If the exercise uses pandas/numpy/etc., use small inline data (5 rows max).
- "weight" is 1 for every test case.

Return ONLY a JSON object (no markdown):
{{
  "function_name": "the_function_name",
  "test_cases": [
    {{
      "description": "short human-readable label",
      "input": <JSON value>,
      "expected_output": "exact expected string",
      "weight": 1
    }}
  ]
}}"""

    try:
        import requests

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{_GEMINI_MODEL}:generateContent?key={api_key}"
        gen_config_tc = {
            "temperature": 0.3,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
        }
        if "2.5" in _GEMINI_MODEL or "3." in _GEMINI_MODEL:
            gen_config_tc["thinkingConfig"] = {"thinkingBudget": 0}

        _t0 = time.monotonic()
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": gen_config_tc,
            },
            timeout=config.GEMINI_TIMEOUT,
        )
        _retroactive_gen_time_ms = int((time.monotonic() - _t0) * 1000)

        if not response.ok:
            error_msg = response.json().get("error", {}).get("message", "Gemini API error")
            raise Exception(f"Gemini API error: {error_msg}")

        data = response.json()
        if "candidates" not in data or not data["candidates"]:
            raise Exception("No response from Gemini API")

        content = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        _retroactive_usage = data.get("usageMetadata", {})

        # Strip markdown fences if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        parsed = json.loads(content)
        function_name = parsed.get("function_name", "solution")
        raw_cases = parsed.get("test_cases", [])

        validated = []
        for tc in raw_cases:
            if not isinstance(tc, dict):
                continue
            if "input" not in tc or "expected_output" not in tc:
                continue
            validated.append(
                {
                    "description": tc.get("description", ""),
                    "input": tc["input"],
                    "expected_output": str(tc["expected_output"]),
                    "weight": int(tc.get("weight", 1)),
                }
            )

        if not validated:
            raise Exception("Gemini returned no valid test cases.")

        return {
            "function_name": function_name,
            "test_cases": validated,
            # Flywheel metadata for retroactive instrumentation in the grading blueprint.
            "_gen_meta": {
                "gemini_model": _GEMINI_MODEL,
                "prompt_template_version": PROMPT_TEMPLATE_VERSION,
                "prompt_tokens": _retroactive_usage.get("promptTokenCount"),
                "completion_tokens": _retroactive_usage.get("candidatesTokenCount"),
                "generation_params": {"temperature": 0.3, "maxOutputTokens": 2048},
                "exercise_type": "retroactive_test_gen",
                "num_test_cases": len(validated),
                "generation_time_ms": _retroactive_gen_time_ms,
            },
        }

    except json.JSONDecodeError as e:
        logger.error("Failed to parse test-case JSON from Gemini: %s", e)
        raise Exception("Failed to parse test cases from AI. Please try again.")
    except Exception as e:
        logger.error("Error generating test cases: %s", e)
        raise
