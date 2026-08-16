"""
Regression test: dense PDFs must not be silently truncated before exercise
generation.

Fixture: static/course-content/Chapter 2 - Types of Analytics.pdf — a real
course chapter already shipped in this repo. It extracts to ~17,700
characters across 10 pages, which is well past the current hard
_TRUNCATION_LIMIT of 10,000 characters in services/exercise_generator.py.
That means the last ~4 pages of this exact chapter are silently dropped
from the prompt sent to Gemini today, with no warning surfaced anywhere.

The chunked-extraction fix (services/exercise_generator.py, see
reports/product-engineer/PDF_TRUNCATION_FIX_PLAN.md) landed on 2026-08-13
behind config.FEATURE_PDF_CHUNKING, which DEFAULTS TO OFF. So:
  - test_last_page_content_reaches_the_gemini_prompt explicitly turns the
    flag on for the duration of the test (matching how this fixture would
    behave once Adam flips the flag in production) and is no longer xfail —
    it is the fix's real, green regression signal.
  - test_flag_off_still_truncates_today documents that the default
    (flag-off) production behavior is UNCHANGED by this fix: merging this
    code cannot alter live behavior on its own.
"""
import os
from unittest.mock import patch

import pytest

import config

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

    @staticmethod
    def _last_page_snippet(pdf_bytes):
        """A snippet unique to the last *content-bearing* page of the source
        PDF (not just the extracted-text slice) — this is the content that
        must not be lost. Some trailing pages (e.g. a blank back page) may
        extract no text, so walk backwards to the last page that has any.
        """
        import pypdf
        import io

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        last_page_text = ""
        for page in reversed(reader.pages):
            candidate = (page.extract_text() or "").strip()
            if candidate:
                last_page_text = candidate
                break
        assert last_page_text, "No page in the fixture extracted any text — pick another fixture."
        return last_page_text[:40]

    @staticmethod
    def _capture_prompts_and_generate(text, **kwargs):
        """Call generate_exercises_from_pdf_content with requests.post mocked,
        returning (result, list_of_captured_prompt_texts)."""
        from unittest.mock import MagicMock
        from services.exercise_generator import generate_exercises_from_pdf_content

        mock_response = {"candidates": [{"content": {"parts": [{"text": "[]"}]}}]}
        captured_prompts = []

        def _fake_post(url, headers=None, json=None, timeout=None):
            captured_prompts.append(json["contents"][0]["parts"][0]["text"])
            resp = MagicMock()
            resp.ok = True
            resp.json.return_value = mock_response
            return resp

        with patch("requests.post", side_effect=_fake_post):
            result = generate_exercises_from_pdf_content(text, "Types of Analytics", **kwargs)

        return result, captured_prompts

    def test_last_page_content_reaches_the_gemini_prompt(self):
        """With config.FEATURE_PDF_CHUNKING on, the whole chapter — including
        the last page — must reach the model.

        Before the fix, services/exercise_generator.py sliced pdf_text to the
        first _TRUNCATION_LIMIT (10,000) characters with no chunking and no
        warning. For this fixture, that slice ends partway through the
        document, so a snippet unique to the last page never reached the
        prompt sent to Gemini. Chunked extraction (with overlap) sends every
        chunk — including the one containing the last page — to Gemini, so
        the last-page snippet must appear somewhere across all chunk calls.

        This test explicitly flips config.FEATURE_PDF_CHUNKING on for its
        duration (the flag defaults OFF in production — see
        test_flag_off_still_truncates_today below for the unchanged default
        behavior) and is intentionally NOT marked xfail: it is the fix's
        real, green pass/fail signal now that the fix has landed.
        """
        with open(FIXTURE_PATH, "rb") as f:
            pdf_bytes = f.read()
        text = _load_fixture_text()
        last_page_snippet = self._last_page_snippet(pdf_bytes)

        # Fail fast with a clear message if the snippet isn't even present in
        # the full extracted text (would indicate a fixture/extraction problem
        # unrelated to truncation).
        assert last_page_snippet in text

        with patch.object(config, "FEATURE_PDF_CHUNKING", True):
            result, captured_prompts = self._capture_prompts_and_generate(
                text, api_key="test_key"
            )

        assert captured_prompts, "generate_exercises_from_pdf_content never called Gemini"
        full_prompt_text = "\n".join(captured_prompts)

        assert last_page_snippet in full_prompt_text, (
            "Content unique to the last page of a real, dense course chapter "
            "never reached the Gemini prompt. This is the silent-truncation "
            "bug described in reports/product-engineer/PDF_TRUNCATION_FIX_PLAN.md "
            "— it should be fixed now that chunking is on."
        )

        # This fixture (17,677 chars) needs only 2 chunks at the plan's
        # defaults (10,000 chunk size / 500 overlap), comfortably under the
        # 6-chunk cap — so it must be fully processed with NO warning.
        assert result.content_warning is None, (
            "This fixture should fit well under the PDF_MAX_CHUNKS cap and "
            f"needs no content_warning, but got: {result.content_warning}"
        )
        assert len(captured_prompts) == 2, (
            f"Expected exactly 2 Gemini calls (2 chunks) for this fixture at "
            f"the default chunk size/overlap, got {len(captured_prompts)}."
        )

    def test_flag_off_still_truncates_today(self):
        """Documents that the default (config.FEATURE_PDF_CHUNKING = False)
        production behavior is UNCHANGED by the chunking fix — merging the
        chunked-extraction code cannot alter live behavior until Adam
        explicitly flips the flag in a specific, approved deploy.
        """
        with open(FIXTURE_PATH, "rb") as f:
            pdf_bytes = f.read()
        text = _load_fixture_text()
        last_page_snippet = self._last_page_snippet(pdf_bytes)
        assert last_page_snippet in text

        assert config.FEATURE_PDF_CHUNKING is False, (
            "config.FEATURE_PDF_CHUNKING must default to False — flipping the "
            "default would change production behavior on merge, which the "
            "approved fix plan explicitly rules out."
        )

        result, captured_prompts = self._capture_prompts_and_generate(text, api_key="test_key")

        assert len(captured_prompts) == 1, "Flag off must still be a single Gemini call."
        assert last_page_snippet not in captured_prompts[0], (
            "Flag-off behavior changed — the last page now reaches the prompt "
            "even with chunking off. That is a behavior change on merge, which "
            "must not happen (flag must default off)."
        )
        assert result.content_warning is None
