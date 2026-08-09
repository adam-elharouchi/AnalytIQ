"""
Regression test: dense PDFs must not be silently truncated before exercise
generation.

Fixture: static/course-content/Chapter 2 - Types of Analytics.pdf — a real
course chapter already shipped in this repo. It extracts to ~17,700
characters across 10 pages, which is well past the current hard
_TRUNCATION_LIMIT of 10,000 characters in services/exercise_generator.py.
That means the last ~4 pages of this exact chapter are silently dropped
from the prompt sent to Gemini today, with no warning surfaced anywhere.

This test is EXPECTED TO FAIL until the chunked-extraction fix
(see reports/product-engineer/PDF_TRUNCATION_FIX_PLAN.md) lands. It exists
now so the fix has a concrete, reproducible pass/fail signal instead of a
manual demo-day discovery.
"""
import os
from unittest.mock import patch

import pytest

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "static",
    "course-content",
    "Chapter 2 - Types of Analytics.pdf",
)


def _load_fixture_text():
    from services.content_extractor import extract_text_from_pdf_bytes

    with open(FIXTURE_PATH, "rb") as f:
        pdf_bytes = f.read()
    return extract_text_from_pdf_bytes(pdf_bytes)


class TestDensePdfNotSilentlyTruncated:
    def test_fixture_exceeds_current_truncation_limit(self):
        """Sanity check: confirms the fixture is dense enough to trigger truncation.

        If this ever fails, the fixture PDF changed and no longer exercises
        the bug — swap in a denser chapter from static/course-content/.
        """
        from services.exercise_generator import _TRUNCATION_LIMIT

        text = _load_fixture_text()
        assert text is not None
        assert len(text) > _TRUNCATION_LIMIT, (
            f"Fixture only extracted {len(text)} chars, which no longer exceeds "
            f"the {_TRUNCATION_LIMIT}-char limit. Pick a denser fixture PDF."
        )

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Known bug: services/exercise_generator.py hard-truncates at 10,000 chars. "
            "Fix pending Adam's approval of reports/product-engineer/PDF_TRUNCATION_FIX_PLAN.md "
            "(due 2026-08-12). strict=True means this test FAILS once the fix lands — "
            "that is the signal to delete this marker."
        ),
    )
    def test_last_page_content_reaches_the_gemini_prompt(self):
        """The whole chapter — including the last page — must reach the model.

        Today, services/exercise_generator.py:147 slices pdf_text to the first
        _TRUNCATION_LIMIT (10,000) characters with no chunking and no warning.
        For this fixture, that slice ends partway through the document, so a
        snippet unique to the last page never reaches the prompt sent to
        Gemini. Once chunked extraction (with overlap) ships, every chunk's
        content — including the last page — must appear somewhere in what
        gets sent to the model across all chunk calls.
        """
        from services.exercise_generator import generate_exercises_from_pdf_content
        import pypdf
        import io

        with open(FIXTURE_PATH, "rb") as f:
            pdf_bytes = f.read()
        text = _load_fixture_text()

        # A snippet unique to the last *content-bearing* page of the source
        # PDF (not just the extracted-text slice) — this is the content that
        # must not be lost. Some trailing pages (e.g. a blank back page) may
        # extract no text, so walk backwards to the last page that has any.
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        last_page_text = ""
        for page in reversed(reader.pages):
            candidate = (page.extract_text() or "").strip()
            if candidate:
                last_page_text = candidate
                break
        assert last_page_text, "No page in the fixture extracted any text — pick another fixture."
        last_page_snippet = last_page_text[:40]

        # Fail fast with a clear message if the snippet isn't even present in
        # the full extracted text (would indicate a fixture/extraction problem
        # unrelated to truncation).
        assert last_page_snippet in text

        mock_response = {
            "candidates": [{"content": {"parts": [{"text": "[]"}]}}],
        }

        captured_prompts = []

        def _fake_post(url, headers=None, json=None, timeout=None):
            captured_prompts.append(json["contents"][0]["parts"][0]["text"])
            from unittest.mock import MagicMock

            resp = MagicMock()
            resp.ok = True
            resp.json.return_value = mock_response
            return resp

        with patch("requests.post", side_effect=_fake_post):
            generate_exercises_from_pdf_content(
                text, "Types of Analytics", api_key="test_key"
            )

        assert captured_prompts, "generate_exercises_from_pdf_content never called Gemini"
        full_prompt_text = "\n".join(captured_prompts)

        assert last_page_snippet in full_prompt_text, (
            "Content unique to the last page of a real, dense course chapter "
            "never reached the Gemini prompt, and no warning was raised. "
            "This is the silent-truncation bug described in "
            "reports/product-engineer/PDF_TRUNCATION_FIX_PLAN.md."
        )
