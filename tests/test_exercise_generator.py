"""
Comprehensive Tests for Exercise Generation Module
Target: Increase coverage from 6% to 80%+
"""
import pytest
from unittest.mock import patch, MagicMock
import json


class TestExerciseGeneration:
    """Test exercise generation from PDF content"""

    def test_generate_exercises_success(self):
        """Test successful exercise generation"""
        from python.exercise_generator import generate_exercises_from_pdf_content

        mock_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps([
                                    {
                                        "title": "Load Dataset",
                                        "description": "Load the CSV file using pandas",
                                        "difficulty": "easy",
                                        "solution_code": "import pandas as pd\ndf = pd.read_csv('data.csv')"
                                    }
                                ])
                            }
                        ]
                    }
                }
            ]
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.ok = True
            mock_post.return_value.json.return_value = mock_response

            exercises = generate_exercises_from_pdf_content(
                "Sample PDF text about data analysis",
                "Chapter 1: Introduction",
                api_key="test_key"
            )

            assert len(exercises) == 1
            assert exercises[0]["title"] == "Load Dataset"
            assert exercises[0]["difficulty"] == "easy"

    def test_generate_exercises_no_api_key(self):
        """Test error when API key is missing"""
        from python.exercise_generator import generate_exercises_from_pdf_content

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(Exception) as exc_info:
                generate_exercises_from_pdf_content(
                    "Sample text",
                    "Chapter 1"
                )
            assert "GEMINI_API_KEY" in str(exc_info.value)

    def test_generate_exercises_api_error(self):
        """Test handling of API errors"""
        from python.exercise_generator import generate_exercises_from_pdf_content

        with patch("requests.post") as mock_post:
            mock_post.return_value.ok = False
            mock_post.return_value.json.return_value = {
                "error": {"message": "API quota exceeded"}
            }

            with pytest.raises(Exception) as exc_info:
                generate_exercises_from_pdf_content(
                    "Sample text",
                    "Chapter 1",
                    api_key="test_key"
                )
            assert "Gemini API error" in str(exc_info.value)

    def test_generate_exercises_truncates_long_text(self):
        """Test that long PDF text is truncated"""
        from python.exercise_generator import generate_exercises_from_pdf_content

        long_text = "A" * 15000  # 15k characters

        mock_response = {
            "candidates": [{
                "content": {"parts": [{"text": "[]"}]}
            }]
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.ok = True
            mock_post.return_value.json.return_value = mock_response

            generate_exercises_from_pdf_content(
                long_text,
                "Chapter 1",
                api_key="test_key"
            )

            # Verify the content was truncated to 10000 chars (not all 15k)
            call_args = mock_post.call_args
            prompt = call_args[1]["json"]["contents"][0]["parts"][0]["text"]
            assert "A" * 10000 in prompt       # 10k consecutive A's present
            assert "A" * 15000 not in prompt   # But not all 15k

    def test_generate_exercises_handles_markdown_json(self):
        """Test extraction of JSON from markdown code blocks"""
        from python.exercise_generator import generate_exercises_from_pdf_content

        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": "```json\n[{\"title\": \"Test\", \"description\": \"Test\", \"difficulty\": \"easy\", \"solution_code\": \"print('test')\"}]\n```"
                    }]
                }
            }]
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.ok = True
            mock_post.return_value.json.return_value = mock_response

            exercises = generate_exercises_from_pdf_content(
                "Sample text",
                "Chapter 1",
                api_key="test_key"
            )

            assert len(exercises) == 1
            assert exercises[0]["title"] == "Test"

    def test_generate_exercises_validates_difficulty(self):
        """Test that invalid difficulty levels are corrected"""
        from python.exercise_generator import generate_exercises_from_pdf_content

        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps([
                            {
                                "title": "Test",
                                "description": "Test",
                                "difficulty": "super_hard",  # Invalid
                                "solution_code": "print('test')"
                            }
                        ])
                    }]
                }
            }]
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.ok = True
            mock_post.return_value.json.return_value = mock_response

            exercises = generate_exercises_from_pdf_content(
                "Sample text",
                "Chapter 1",
                api_key="test_key"
            )

            # Should default to "medium"
            assert exercises[0]["difficulty"] == "medium"

    def test_generate_exercises_empty_response(self):
        """Test handling of empty API response"""
        from python.exercise_generator import generate_exercises_from_pdf_content

        mock_response = {"candidates": []}

        with patch("requests.post") as mock_post:
            mock_post.return_value.ok = True
            mock_post.return_value.json.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                generate_exercises_from_pdf_content(
                    "Sample text",
                    "Chapter 1",
                    api_key="test_key"
                )
            assert "No response" in str(exc_info.value)

    def test_generate_exercises_invalid_json(self):
        """Test handling of invalid JSON response"""
        from python.exercise_generator import generate_exercises_from_pdf_content

        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": "This is not valid JSON at all!"
                    }]
                }
            }]
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.ok = True
            mock_post.return_value.json.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                generate_exercises_from_pdf_content(
                    "Sample text",
                    "Chapter 1",
                    api_key="test_key"
                )
            assert "Failed to parse the exercise response from AI" in str(exc_info.value)

    def test_generate_exercises_non_array_response(self):
        """Test handling when API returns object instead of array"""
        from python.exercise_generator import generate_exercises_from_pdf_content

        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({"error": "Not an array"})
                    }]
                }
            }]
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.ok = True
            mock_post.return_value.json.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                generate_exercises_from_pdf_content(
                    "Sample text",
                    "Chapter 1",
                    api_key="test_key"
                )
            assert "expected array" in str(exc_info.value)

    def test_generate_exercises_filters_invalid_exercises(self):
        """Test that invalid exercise objects are filtered out"""
        from python.exercise_generator import generate_exercises_from_pdf_content

        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps([
                            {
                                "title": "Valid Exercise",
                                "description": "Valid",
                                "difficulty": "easy",
                                "solution_code": "print('valid')"
                            },
                            "This is not a dict",  # Invalid
                            {
                                "title": "Another Valid",
                                "description": "Valid",
                                "difficulty": "medium",
                                "solution_code": "print('valid2')"
                            }
                        ])
                    }]
                }
            }]
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.ok = True
            mock_post.return_value.json.return_value = mock_response

            exercises = generate_exercises_from_pdf_content(
                "Sample text",
                "Chapter 1",
                api_key="test_key"
            )

            # Should only return the 2 valid exercises
            assert len(exercises) == 2
            assert exercises[0]["title"] == "Valid Exercise"
            assert exercises[1]["title"] == "Another Valid"

    def test_generate_exercises_uses_env_api_key(self):
        """Test that API key is read from environment"""
        from python.exercise_generator import generate_exercises_from_pdf_content

        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": "[]"
                    }]
                }
            }]
        }

        with patch.dict("os.environ", {"GEMINI_API_KEY": "env_key"}):
            with patch("requests.post") as mock_post:
                mock_post.return_value.ok = True
                mock_post.return_value.json.return_value = mock_response

                generate_exercises_from_pdf_content(
                    "Sample text",
                    "Chapter 1"
                    # No api_key parameter - should use env var
                )

                # Verify the env key was used in the URL
                call_args = mock_post.call_args
                assert "key=env_key" in call_args[0][0]
