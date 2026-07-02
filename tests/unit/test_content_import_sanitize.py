"""
tests/unit/test_content_import_sanitize.py — imported-HTML sanitization (B3).

Imported external HTML is served same-origin; it must not carry script-executing
vectors. _parse_html drops <script>/<iframe> and neutralises javascript:/data:html
URLs; _wrap_html escapes the source URL.
"""
from blueprints.content_import import _parse_html, _is_safe_content_url, _wrap_html


class TestUrlSafety:
    def test_https_and_relative_allowed(self):
        assert _is_safe_content_url("https://x.com/a", "href") is True
        assert _is_safe_content_url("/rel/path", "href") is True
        assert _is_safe_content_url("#frag", "href") is True
        assert _is_safe_content_url("mailto:a@b.com", "href") is True

    def test_dangerous_schemes_rejected(self):
        assert _is_safe_content_url("javascript:alert(1)", "href") is False
        assert _is_safe_content_url("vbscript:msgbox(1)", "href") is False
        assert _is_safe_content_url("data:text/html,<script>", "src") is False

    def test_inline_image_allowed_for_src(self):
        assert _is_safe_content_url("data:image/png;base64,AAAA", "src") is True


class TestParseHtml:
    def test_javascript_href_is_stripped(self):
        html = b'<main><a href="javascript:alert(1)">x</a>' b'<a href="https://ok.com">ok</a></main>'
        _, _, body = _parse_html(html)
        assert "javascript:" not in body
        assert "https://ok.com" in body

    def test_script_tag_removed(self):
        _, _, body = _parse_html(b"<main><script>alert(1)</script><p>hi</p></main>")
        assert "<script" not in body.lower()

    def test_iframe_removed(self):
        _, _, body = _parse_html(b'<main><iframe src="evil"></iframe><p>hi</p></main>')
        assert "<iframe" not in body.lower()


class TestWrapHtml:
    def test_source_url_is_escaped(self):
        doc = _wrap_html("<p>body</p>", "Title", source_url='https://x"onmouseover="e()')
        assert 'onmouseover="e()' not in doc
