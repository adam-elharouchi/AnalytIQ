"""B14: validate_config() is called at startup and is fatal in production only.

The function was defined, documented in five places as a fail-fast startup check,
and never called by application code. These tests pin both halves of the wiring:
production refuses to boot on a config error, and every other environment logs and
carries on — because FEATURE_AI_EXERCISES defaults True, so a missing
GEMINI_API_KEY is an error in CI and on a developer's first run.
"""

import pytest

import config
from core import factory


class _App:
    """Minimal stand-in for the Flask app configure_app() mutates."""

    def __init__(self):
        self.config = {}


def test_production_refuses_to_start_on_config_error(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ENV", "production")
    monkeypatch.setattr(config, "validate_config", lambda: ["DATABASE_URL environment variable is required"])
    monkeypatch.setattr(config, "UPLOAD_FOLDER", str(tmp_path))

    with pytest.raises(RuntimeError, match="Refusing to start"):
        factory.configure_app(_App())


def test_non_production_logs_and_continues(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(config, "ENV", "testing")
    monkeypatch.setattr(config, "validate_config", lambda: ["GEMINI_API_KEY required when FEATURE_AI_EXERCISES is enabled"])
    monkeypatch.setattr(config, "UPLOAD_FOLDER", str(tmp_path))

    with caplog.at_level("ERROR"):
        factory.configure_app(_App())   # must not raise

    assert "GEMINI_API_KEY" in caplog.text


def test_clean_config_starts_anywhere(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ENV", "production")
    monkeypatch.setattr(config, "validate_config", lambda: [])
    monkeypatch.setattr(config, "UPLOAD_FOLDER", str(tmp_path))

    factory.configure_app(_App())   # must not raise
