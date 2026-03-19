"""
Exercise Generation Service
Uses Google Gemini API to generate coding exercises from PDF content
"""

import hashlib
import logging
import os
import re
import time
import json

logger = logging.getLogger(__name__)

# Bump this constant whenever the Gemini prompt changes so the flywheel can
# measure whether the change improved exercise quality.
PROMPT_TEMPLATE_VERSION = "v1.1"

_GEMINI_MODEL = "gemini-2.5-flash"
_GENERATION_PARAMS = {"temperature": 0.7, "maxOutputTokens": 8192}
_TRUNCATION_LIMIT = 10_000


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
        list: Array of exercise dicts with title, description, difficulty,
              function_name, solution_code, test_cases, and _gen_meta (flywheel metadata).
              Callers that do not need _gen_meta can ignore it.
    """
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables")
        raise Exception(
            "Configuration Error: GEMINI_API_KEY is missing. Please set this environment variable in Render."
        )

    # --- Flywheel: capture input metadata before truncation ----------------
    original_len = len(pdf_text) if pdf_text else 0
    source_content_hash = hashlib.sha256(
        (pdf_text or "").encode("utf-8", errors="replace")
    ).hexdigest()
    was_truncated = original_len > _TRUNCATION_LIMIT

    # Limit PDF text to avoid token limits (first 10000 characters)
    truncated_text = pdf_text[:_TRUNCATION_LIMIT] if was_truncated else pdf_text

    # Build prompt
    prompt = f"""You are a coding tutor creating beginner-friendly exercises for a university course.

Analyze the chapter below and generate 5 to 8 short, focused coding exercises.

Chapter Title: {chapter_title}
Chapter Content:
{truncated_text}

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
  • Use small synthetic data defined inline, OR reference a well-known public dataset appropriate for the language (e.g. seaborn "tips"/"iris" for Python, built-in datasets for R, a simple CREATE TABLE + INSERT for SQL).
  • Do NOT reference external files that may not exist on the student's machine.

DIFFICULTY
  • First 2–3 exercises: "easy" (single operation, one function/method call).
  • Remaining exercises: "medium" (combine two concepts, still one idea per exercise).
  • Never use "hard".

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
    "title": "Exercise title",
    "description": "One or two sentences telling the student exactly what to do. Name the function they must define and what it must return.",
    "difficulty": "easy|medium",
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

    try:
        import requests

        # Call Gemini API
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{_GEMINI_MODEL}:generateContent?key={api_key}"

        _t0 = time.monotonic()
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": _GENERATION_PARAMS["temperature"],
                    "maxOutputTokens": _GENERATION_PARAMS["maxOutputTokens"],
                    "responseMimeType": "application/json",
                },
            },
            timeout=60,
        )
        generation_time_ms = int((time.monotonic() - _t0) * 1000)

        if not response.ok:
            error_data = response.json() if response.content else {}
            error_message = error_data.get("error", {}).get(
                "message", "Failed to generate exercises"
            )
            raise Exception(f"Gemini API error: {error_message}")

        data = response.json()

        # --- Flywheel: extract token counts from Gemini usageMetadata -------
        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount")
        completion_tokens = usage.get("candidatesTokenCount")

        # Extract text from response
        if "candidates" not in data or len(data["candidates"]) == 0:
            raise Exception("No response from Gemini API")

        content = data["candidates"][0]["content"]["parts"][0]["text"]

        # Extract JSON from response (handle markdown code blocks)
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

        # Parse JSON
        exercises = json.loads(content)

        # Validate structure
        if not isinstance(exercises, list):
            raise Exception("Invalid response format: expected array")

        # Validate each exercise
        validated_exercises = []
        for exercise in exercises:
            if not isinstance(exercise, dict):
                continue

            difficulty = exercise.get("difficulty", "medium").lower()
            if difficulty not in ["easy", "medium", "hard"]:
                difficulty = "medium"

            # Validate test_cases structure
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

            ex_language = exercise.get("language", "Unknown")
            ex_title = exercise.get("title", "Untitled Exercise")
            ex_description = exercise.get("description", "")
            ex_solution = exercise.get("solution_code", "")

            validated_exercise = {
                "language": ex_language,
                "title": ex_title,
                "description": ex_description,
                "difficulty": difficulty,
                "function_name": exercise.get("function_name", "solution"),
                "solution_code": ex_solution,
                "test_cases": validated_cases,
                # Flywheel metadata — callers that don't need this can ignore it.
                "_gen_meta": {
                    "source_content_hash": source_content_hash,
                    "source_content_type": source_content_type,
                    "source_char_count": len(truncated_text),
                    "was_truncated": was_truncated,
                    "detected_language": ex_language,
                    "detected_topics": _extract_topics(ex_title, ex_description),
                    "gemini_model": _GEMINI_MODEL,
                    "prompt_template_version": PROMPT_TEMPLATE_VERSION,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "generation_params": _GENERATION_PARAMS,
                    "difficulty_generated": difficulty,
                    "exercise_type": "generated",
                    "exercise_structure": {
                        "has_starter_code": False,
                        "num_test_cases": len(validated_cases),
                        "instruction_length_chars": len(ex_description),
                        "has_solution": bool(ex_solution),
                    },
                    "num_test_cases": len(validated_cases),
                    "generation_time_ms": generation_time_ms,
                },
            }

            validated_exercises.append(validated_exercise)

        return validated_exercises

    except json.JSONDecodeError as e:
        snippet = content[:500] + "..." if len(content) > 500 else content
        logger.error("Failed to parse Gemini JSON response: %s. Content snippet: %s", e, snippet)
        raise Exception("Failed to parse the exercise response from AI. Please try again.")
    except Exception as e:
        logger.error("Error generating exercises: %s", e)
        raise


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
        api_key = os.getenv("GEMINI_API_KEY")
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
        _t0 = time.monotonic()
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 2048,
                    "responseMimeType": "application/json",
                },
            },
            timeout=45,
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
