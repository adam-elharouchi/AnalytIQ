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
        list: Array of exercise dictionaries with title, description, difficulty, solution_code
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
    prompt = f"""You are a coding tutor creating beginner-friendly Python exercises for a university data science course.

Analyze the chapter below and generate 5 to 8 short, focused coding exercises.

Chapter Title: {chapter_title}
Chapter Content:
{truncated_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT RULES — follow every one of these exactly:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ONE CONCEPT PER EXERCISE
  • Each exercise teaches exactly one thing (e.g. "compute the mean", NOT "compute the mean, std, and percentage above average").
  • If a topic naturally has three sub-steps, make three separate exercises.

SOLUTION CODE SIZE
  • 5 to 10 lines of actual code (import lines do not count toward the limit).
  • If you need more lines, the exercise covers too much — split it.

COMMENT EVERY LINE
  • Every single line of code must have an inline comment explaining what it does.
  • Example: `mean_age = df["age"].mean()  # compute the average age`

PRINT THE RESULT
  • The last line of every exercise must print the result with a label.
  • Example: `print("Mean age:", mean_age)`

NO COMPLEX PYTHON
  • No list comprehensions — use a plain for loop instead.
  • No nested conditionals (if inside if) — use guard clauses or separate exercises.
  • No method chaining longer than one dot — store each intermediate result in a named variable.
  • No lambda functions.
  • No classes or object-oriented patterns.

NAMED INTERMEDIATE VARIABLES
  • Never compute and use a value in the same expression.
  • Bad:  `print(df["age"].mean())`
  • Good: `mean_age = df["age"].mean()` then `print("Mean age:", mean_age)`

IMPORTS
  • Include only the imports actually used in that exercise.
  • Always use standard aliases: `import pandas as pd`, `import matplotlib.pyplot as plt`, `import numpy as np`.

DATA
  • Use synthetic/sample data defined inside the exercise (e.g. a small list or dict), OR reference a standard public dataset (e.g. seaborn's "tips", "iris", sklearn's "load_iris()").
  • Do NOT reference files that may not exist on the student's machine.
  • If loading from seaborn: `import seaborn as sns` then `df = sns.load_dataset("tips")  # load the tips dataset`.

DIFFICULTY
  • First 2–3 exercises: "easy" (single operation, one library call).
  • Remaining exercises: "medium" (combine two concepts, still one idea per exercise).
  • Never use "hard".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GOOD EXAMPLE (follow this style exactly):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Title: Compute the mean of a column
Description: Use the .mean() method to find the average value of the "total_bill" column in the tips dataset.
Difficulty: easy
Solution code:
import pandas as pd        # import pandas for data manipulation
import seaborn as sns      # import seaborn to load sample datasets

df = sns.load_dataset("tips")           # load the tips dataset into a DataFrame
total_bill_mean = df["total_bill"].mean()  # compute the average of the total_bill column
print("Mean total bill:", total_bill_mean) # print the result with a clear label

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BAD EXAMPLE (never do this):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Title: Analyze tips data
Solution code:
import pandas as pd
import seaborn as sns
df = sns.load_dataset("tips")
stats = df.groupby("sex")["total_bill"].agg(["mean","std","count"]).reset_index()
above_avg = df[df["total_bill"] > df["total_bill"].mean()]
pct = len(above_avg) / len(df) * 100
print(stats, pct)
# BAD: multiple concepts, no comments, chaining, no named variables

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return your response as a JSON array with ONLY this structure — no markdown, no code fences, no extra text:
[
  {{
    "title": "Exercise title",
    "description": "One or two sentences telling the student exactly what to do, naming the function/method to use.",
    "difficulty": "easy|medium",
    "solution_code": "Python code — every line commented, print at end, 5-10 lines max"
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

            validated_exercise = {
                "title": exercise.get("title", "Untitled Exercise"),
                "description": exercise.get("description", ""),
                "difficulty": exercise.get("difficulty", "medium").lower(),
                "solution_code": exercise.get("solution_code", ""),
            }

            # Validate difficulty
            if validated_exercise["difficulty"] not in ["easy", "medium", "hard"]:
                validated_exercise["difficulty"] = "medium"

            validated_exercises.append(validated_exercise)

        return validated_exercises

    except json.JSONDecodeError as e:
        snippet = content[:500] + "..." if len(content) > 500 else content
        logger.error("Failed to parse Gemini JSON response: %s. Content snippet: %s", e, snippet)
        raise Exception("Failed to parse the exercise response from AI. Please try again.")
    except Exception as e:
        logger.error("Error generating exercises: %s", e)
        raise
