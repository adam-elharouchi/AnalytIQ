"""
Exercise Generation Service
Uses Google Gemini API to generate coding exercises from PDF content
"""

import logging
import os
import json

logger = logging.getLogger(__name__)


def generate_exercises_from_pdf_content(pdf_text, chapter_title, api_key=None):
    """
    Generate coding exercises from PDF text using Gemini API

    Args:
        pdf_text: Extracted text from PDF
        chapter_title: Title of the chapter
        api_key: Google Gemini API key (optional, can use env var)

    Returns:
        list: Array of exercise dicts with title, description, difficulty,
              function_name, solution_code, and test_cases
    """
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables")
        raise Exception(
            "Configuration Error: GEMINI_API_KEY is missing. Please set this environment variable in Render."
        )

    # Limit PDF text to avoid token limits (first 10000 characters)
    truncated_text = pdf_text[:10000] if len(pdf_text) > 10000 else pdf_text

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return your response as a JSON array with ONLY this structure — no markdown, no code fences, no extra text:
[
  {{
    "language": "The detected language name, e.g. Python, R, SQL, JavaScript",
    "title": "Exercise title",
    "description": "One or two sentences telling the student exactly what to do. Name the function they must define and what it must return.",
    "difficulty": "easy|medium",
    "solution_code": "Code in the detected language — every line commented, result output at end, 5-10 lines max"
  }}
]"""

    try:
        import requests

        # Call Gemini API
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 8192,
                    "responseMimeType": "application/json",
                },
            },
            timeout=60,
        )

        if not response.ok:
            error_data = response.json() if response.content else {}
            error_message = error_data.get("error", {}).get(
                "message", "Failed to generate exercises"
            )
            raise Exception(f"Gemini API error: {error_message}")

        data = response.json()

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
                    validated_cases.append({
                        "description":     tc.get("description", ""),
                        "input":           tc["input"],
                        "expected_output": tc["expected_output"],
                        "weight":          int(tc.get("weight", 1)),
                    })

            validated_exercise = {
                "language": exercise.get("language", "Unknown"),
                "title": exercise.get("title", "Untitled Exercise"),
                "description": exercise.get("description", ""),
                "difficulty": difficulty,
                "solution_code": exercise.get("solution_code", ""),
                "test_cases":    validated_cases,
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
