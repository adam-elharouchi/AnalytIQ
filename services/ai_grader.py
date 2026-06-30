"""
AI-based code grader using Google Gemini.

Grades student code by evaluating whether the logic and actual output fulfil
the exercise description — not by comparing against pre-generated test cases.
Every student can write the solution in their own style; what matters is
whether the result makes sense for the task.

Scoring (0–100)
───────────────
Correctness  0–70   Does the code produce output / behaviour that solves the task?
Quality      0–30   Is the code readable, structured, and conceptually sound?
Total        0–100
"""

import json
import logging
import time

import config

logger = logging.getLogger(__name__)

_GEMINI_MODEL = config.GEMINI_MODEL or "gemini-flash-latest"


def grade_with_ai(
    title: str,
    description: str,
    language: str,
    student_code: str,
    actual_output: str,
    api_key: str = None,
) -> dict:
    """
    Grade student code using Gemini against the exercise description.

    Parameters
    ----------
    title         : exercise title
    description   : what the student was asked to do
    language      : Python / R / SQL / …
    student_code  : source code submitted by the student
    actual_output : combined stdout + stderr from running the code
    api_key       : Gemini API key (falls back to GEMINI_API_KEY env var)

    Returns
    -------
    {
      correctness_score : int   0-70
      quality_score     : int   0-30
      total_score       : int   0-100
      feedback          : str   2-3 sentences of actionable feedback
      passed            : bool  total_score >= 50
      graded_by         : "ai"
    }
    """
    if not api_key:
        api_key = config.GEMINI_API_KEY
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    output_block = (
        f"```\n{actual_output[:3000]}\n```"
        if actual_output.strip()
        else "(the code produced no output)"
    )

    prompt = f"""You are an expert coding instructor grading a student submission for a data analytics course.

Exercise: {title}
Task: {description}
Language: {language}

Student's code:
```{language.lower()}
{student_code[:4000]}
```

Actual output when the code was run:
{output_block}

Grade this submission on two dimensions:

1. Correctness (0–70): Does the code logically solve the described task?
   Does the output match what you would expect for this exercise?
   Award partial credit generously — a student with the right idea but a minor bug should score 45–60, not 0.
   A complete, correct solution with matching output earns 60–70.

2. Code quality (0–30): Is the code readable and well-structured?
   Does it use meaningful variable names, appropriate constructs for the language,
   and demonstrate understanding of the concept rather than hardcoding answers?

Important: Focus on logic and intent, not on a specific coding style.
Different valid approaches (function vs script, explicit vs concise) should all
receive full marks if they correctly solve the task.

Respond with ONLY this JSON (no markdown fences):
{{
  "correctness_score": <integer 0-70>,
  "quality_score": <integer 0-30>,
  "total_score": <integer equal to correctness_score + quality_score>,
  "feedback": "<2-3 sentences: acknowledge one thing done well, then give one concrete actionable suggestion>",
  "passed": <true if total_score >= 50>
}}"""

    try:
        import requests

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{_GEMINI_MODEL}:generateContent?key={api_key}"
        )
        gen_config = {
            "temperature": 0.2,
            "maxOutputTokens": 512,
            "responseMimeType": "application/json",
        }
        if "2.5" in _GEMINI_MODEL or "3." in _GEMINI_MODEL:
            gen_config["thinkingConfig"] = {"thinkingBudget": 0}

        _t0 = time.monotonic()
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": gen_config,
            },
            timeout=config.GEMINI_TIMEOUT,
        )
        grading_time_ms = int((time.monotonic() - _t0) * 1000)

        if not resp.ok:
            error_msg = resp.json().get("error", {}).get("message", "Gemini API error")
            raise RuntimeError(f"Gemini API error: {error_msg}")

        data = resp.json()
        if "candidates" not in data or not data["candidates"]:
            raise RuntimeError("No response from Gemini API.")

        content = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        # Strip markdown fences if present despite responseMimeType
        if content.startswith("```"):
            content = content[3:]
            if content.startswith("json"):
                content = content[4:]
            content = content.split("```")[0].strip()

        parsed = json.loads(content)
        correctness = min(70, max(0, int(parsed.get("correctness_score", 0))))
        quality = min(30, max(0, int(parsed.get("quality_score", 0))))
        total = min(100, correctness + quality)
        feedback = str(parsed.get("feedback", "")).strip()

        logger.info(
            "AI graded exercise: total=%s correctness=%s quality=%s time=%sms",
            total,
            correctness,
            quality,
            grading_time_ms,
        )

        return {
            "correctness_score": correctness,
            "quality_score": quality,
            "total_score": total,
            "feedback": feedback,
            "passed": total >= 50,
            "graded_by": "ai",
        }

    except json.JSONDecodeError as exc:
        logger.error("AI grader returned invalid JSON: %s", exc)
        raise RuntimeError(f"AI grader returned invalid JSON: {exc}")
    except Exception as exc:
        logger.error("AI grader error: %s", exc)
        raise
