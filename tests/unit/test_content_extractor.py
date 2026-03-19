"""
tests/test_content_extractor.py — Unit tests for services/content_extractor.py
"""
import json
import sys
import os
import pytest

import services.content_extractor as content_extractor


class TestExtractTxt:
    def test_basic_utf8_text(self):
        raw = b"Hello, world!\nLine two."
        result = content_extractor.extract_text(raw, "notes.txt")
        assert "Hello, world!" in result
        assert "Line two." in result

    def test_non_utf8_bytes_replaced(self):
        raw = b"Good \xff\xfe text"
        result = content_extractor.extract_text(raw, "notes.txt")
        assert "Good" in result
        assert "text" in result

    def test_empty_file(self):
        result = content_extractor.extract_text(b"", "notes.txt", max_size_mb=1)
        assert result == ""


class TestExtractCsv:
    def test_csv_includes_headers_and_values(self):
        raw = b"name,age,city\nAlice,30,Boston\nBob,25,NYC\n"
        result = content_extractor.extract_text(raw, "data.csv")
        assert "name" in result
        assert "age" in result
        assert "Alice" in result
        assert "Boston" in result
        assert "Bob" in result

    def test_csv_rows_separated_by_newlines(self):
        raw = b"a,b\n1,2\n3,4\n"
        result = content_extractor.extract_text(raw, "data.csv")
        lines = result.strip().splitlines()
        assert len(lines) == 3  # header + 2 data rows


class TestExtractIpynb:
    @staticmethod
    def _make_notebook(cells):
        return json.dumps({"nbformat": 4, "nbformat_minor": 5, "cells": cells}).encode()

    def test_code_cell_extracted(self):
        nb = self._make_notebook([
            {"cell_type": "code", "source": ["print('hello')\n", "x = 1"]}
        ])
        result = content_extractor.extract_text(nb, "notebook.ipynb")
        assert "print('hello')" in result
        assert "x = 1" in result

    def test_markdown_cell_extracted(self):
        nb = self._make_notebook([
            {"cell_type": "markdown", "source": ["# Title\n", "Some explanation."]}
        ])
        result = content_extractor.extract_text(nb, "notebook.ipynb")
        assert "# Title" in result
        assert "Some explanation." in result

    def test_cells_separated_by_dashes(self):
        nb = self._make_notebook([
            {"cell_type": "code", "source": ["x = 1"]},
            {"cell_type": "markdown", "source": ["## Section"]},
        ])
        result = content_extractor.extract_text(nb, "notebook.ipynb")
        assert "---" in result

    def test_raw_cells_skipped(self):
        nb = self._make_notebook([
            {"cell_type": "raw", "source": ["should be ignored"]},
            {"cell_type": "code", "source": ["x = 1"]},
        ])
        result = content_extractor.extract_text(nb, "notebook.ipynb")
        assert "should be ignored" not in result
        assert "x = 1" in result

    def test_invalid_json_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid .ipynb"):
            content_extractor.extract_text(b"not json {{", "notebook.ipynb")

    def test_empty_cells_list(self):
        nb = self._make_notebook([])
        result = content_extractor.extract_text(nb, "notebook.ipynb")
        assert result == ""


class TestSizeLimit:
    def test_oversized_file_raises_value_error(self):
        with pytest.raises(ValueError, match="exceeds"):
            content_extractor.extract_text(b"ab", "notes.txt", max_size_mb=0.000001)

    def test_exactly_at_limit_does_not_raise(self):
        raw = b"hello"
        max_mb = len(raw) / (1024 * 1024)
        result = content_extractor.extract_text(raw, "notes.txt", max_size_mb=max_mb)
        assert "hello" in result


class TestUnsupportedExtension:
    def test_unknown_extension_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported file extension"):
            content_extractor.extract_text(b"data", "file.xyz")

    def test_no_extension_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported file extension"):
            content_extractor.extract_text(b"data", "filewithnoext")
