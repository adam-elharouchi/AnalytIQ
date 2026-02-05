"""
Exercise Generation Service
Uses Google Gemini API to generate coding exercises from PDF content
"""

import os
import json


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
        print("Error: GEMINI_API_KEY not found in environment variables.")
        raise Exception(
            "Configuration Error: GEMINI_API_KEY is missing. Please set this environment variable in Render."
        )

    # Limit PDF text to avoid token limits (first 10000 characters)
    truncated_text = pdf_text[:10000] if len(pdf_text) > 10000 else pdf_text

    # Build prompt
    prompt = f"""Analyze the following chapter content and create 3-5 beginner-friendly coding practice exercises.
    
Chapter Title: {chapter_title}
Chapter Content: {truncated_text}

The user wants exercises that feel like a "Jupyter Notebook" tutorial (step-by-step, clear, using standard libraries like pandas/matplotlib).

For each exercise:
1. **Title**: Simple and descriptive (e.g., "Load the dataset", "Visualize the distribution").
2. **Description**: Clear instructions on what to do. Mention specific library functions if helpful (e.g., "Use pd.read_csv()").
3. **Difficulty**: Default to "easy" or "medium". Avoid "hard" unless necessary.
4. **Solution Code**: Provide complete, runnable Python code that could be pasted into a notebook cell. 
   - Use standard imports (import pandas as pd, import matplotlib.pyplot as plt).
   - Add comments explaining each step.
   - Keep it simple and procedural (avoid complex classes or advanced functional patterns).

Focus on practical tasks:
- Loading data (CSV, standard datasets).
- basic DataFrame operations (head(), describe(), selecting columns).
- Simple visualizations (histograms, scatter plots).
- Basic modeling (LinearRegression) if the text covers it.

Return your response as a JSON array with this structure:
[
  {{
    "title": "Exercise Title",
    "description": "Exercise description",
    "difficulty": "easy|medium",
    "solution_code": "Python code here"
  }}
]

Return ONLY valid JSON, no additional text before or after."""

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
        # Include snippet of content in error for debugging
        snippet = content[:500] + "..." if len(content) > 500 else content
        print(f"FAILED CONTENT: {content}")  # Print to server logs
        raise Exception(f"Failed to parse JSON response: {str(e)}. Raw content snippet: {snippet}")
    except Exception as e:
        raise Exception(f"Error generating exercises: {str(e)}")
