"""
Content Import blueprint — import chapters from external web sources.

Routes:
  GET  /api/import/openstax/books                   List OpenStax textbooks
  GET  /api/import/openstax/books/<slug>/toc        Table of contents for one book
  GET  /api/import/libretexts/libraries             LibreTexts subject libraries
  GET  /api/import/libretexts/search                Search LibreTexts by keyword
  GET  /api/import/oer/search                       Search OER Commons
  POST /api/import/preview                          Preview content before importing
  POST /api/classes/<class_id>/chapters/import      Create chapter from external source
"""

import html as _html_mod
import ipaddress
import logging
import re
import socket
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from flask import Blueprint, g, jsonify, request

import repositories.chapter_repository as chapter_repo
import repositories.class_repository as class_repo
from core.audit import audit
from core.auth import require_auth, require_role
from core.database import get_db_connection
from core.extensions import csrf_exempt

logger = logging.getLogger(__name__)
bp = Blueprint("content_import", __name__)

_HTTP_TIMEOUT = 15  # seconds
_MAX_CONTENT_BYTES = 5 * 1024 * 1024  # 5 MB cap on external fetches
_MAX_REDIRECTS = 5
_OPENSTAX_CMS = "https://openstax.org/apps/cms/api/v2/pages"


# ---------------------------------------------------------------------------
# SSRF guard
# ---------------------------------------------------------------------------


def _is_public_host(host: str) -> bool:
    """Return True only if every IP *host* resolves to is a public address.

    Blocks private, loopback, link-local (incl. 169.254.169.254 cloud metadata),
    multicast, reserved, and unspecified ranges. Returns False on resolution
    failure (fail closed).
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False
    if not infos:
        return False
    for info in infos:
        ip_str = info[4][0]
        # Strip IPv6 scope id if present (e.g. "fe80::1%eth0")
        ip_str = ip_str.split("%", 1)[0]
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_multicast
            or addr.is_reserved
            or addr.is_unspecified
        ):
            return False
    return True


def _assert_public_url(url: str) -> None:
    """Raise ValueError if *url* is not an http(s) URL whose host is public."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http/https URLs are allowed")
    host = parsed.hostname
    if not host:
        raise ValueError("URL has no host")
    if not _is_public_host(host):
        raise ValueError("URL resolves to a non-public/internal address")


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------


def _fetch_bytes(url: str) -> bytes:
    """GET a URL with an SSRF guard, manual redirect validation, and a size cap.

    Redirects are followed manually so each hop's destination is re-validated
    against the SSRF allowlist (a server that 302s to http://169.254.169.254/
    or http://10.0.0.1/ is rejected).
    """
    headers = {"User-Agent": "AnalytIQ/1.0 (+https://myanalytiq.org)"}
    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        _assert_public_url(current)
        resp = requests.get(
            current,
            timeout=_HTTP_TIMEOUT,
            stream=True,
            headers=headers,
            allow_redirects=False,
        )
        if resp.is_redirect or resp.is_permanent_redirect:
            location = resp.headers.get("Location")
            resp.close()
            if not location:
                raise ValueError("Redirect without Location header")
            current = urljoin(current, location)
            continue
        resp.raise_for_status()
        chunks = []
        total = 0
        for chunk in resp.iter_content(65536):
            chunks.append(chunk)
            total += len(chunk)
            if total > _MAX_CONTENT_BYTES:
                break
        return b"".join(chunks)
    raise ValueError("Too many redirects")


def _parse_html(raw: bytes, source_url: str = "") -> tuple:
    """
    Return (title, description, clean_body_html) from raw HTML bytes.
    Strips nav/footer/scripts; attempts to isolate main content.
    """
    soup = BeautifulSoup(raw, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else source_url
    meta = soup.find("meta", attrs={"name": "description"})
    description = (meta.get("content") or "") if meta else ""

    for tag in soup(
        ["script", "style", "nav", "header", "footer", "aside", "form", "iframe", "noscript"]
    ):
        tag.decompose()

    main = (
        soup.find("main")
        or soup.find(attrs={"role": "main"})
        or soup.find("article")
        or soup.find(id=re.compile(r"content|main|article", re.I))
        or soup.find(class_=re.compile(r"content|main|article|post|body", re.I))
        or soup.body
    )
    if not main:
        return title, description, f"<p>{_html_mod.escape(soup.get_text()[:5000])}</p>"

    # Strip inline styles / class bloat, keep semantic attrs only, and neutralise
    # dangerous URL schemes (javascript:, vbscript:, non-image data:) in href/src.
    # Combined with the script/iframe/style removal above and the sandboxing CSP
    # applied when the stored HTML is served, this prevents stored XSS.
    for tag in main.find_all(True):
        attrs = {k: v for k, v in tag.attrs.items() if k in ("href", "src", "alt", "title")}
        for url_attr in ("href", "src"):
            val = attrs.get(url_attr)
            if isinstance(val, str) and not _is_safe_content_url(val, url_attr):
                attrs.pop(url_attr, None)
        tag.attrs = attrs

    return title, description, str(main)


# Allow only http(s), mailto, fragment, and relative URLs (plus inline images for src).
_SAFE_URL_RE = re.compile(r"^(https?:|mailto:|/|#|\.)", re.I)


def _is_safe_content_url(value: str, attr: str) -> bool:
    """Return True if *value* is a safe URL for imported content href/src."""
    v = value.strip()
    if not v:
        return False
    if attr == "src" and v.lower().startswith("data:image/"):
        return True  # inline images are safe to keep
    return bool(_SAFE_URL_RE.match(v))


def _wrap_html(body: str, title: str, source_url: str = "") -> str:
    """Wrap an HTML body in a clean standalone document."""
    _safe_source = _html_mod.escape(source_url, quote=True) if source_url else ""
    source_line = (
        f'<p style="font-size:0.8em;color:#888">Source: '
        f'<a href="{_safe_source}">{_safe_source}</a></p>'
        if source_url
        else ""
    )
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_html_mod.escape(title)}</title>"
        "<style>"
        "body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;"
        "padding:1rem 1.5rem;color:#1e293b;line-height:1.7}"
        "h1,h2,h3{color:#0f172a;margin-top:1.5em}"
        "pre,code{background:#f1f5f9;padding:0.2em 0.4em;border-radius:3px;font-size:0.9em}"
        "pre{padding:1em;overflow-x:auto}"
        "img{max-width:100%;height:auto}"
        "table{border-collapse:collapse;width:100%}"
        "td,th{border:1px solid #e2e8f0;padding:0.5em}"
        "a{color:#6366f1}"
        "</style></head><body>"
        f"{source_line}{body}"
        "</body></html>"
    )


def _md_to_html(md_text: str) -> str:
    """Convert Markdown to HTML; fall back to <pre> if markdown package absent."""
    try:
        import markdown

        return markdown.markdown(md_text, extensions=["fenced_code", "tables"])
    except Exception:
        return f"<pre>{_html_mod.escape(md_text)}</pre>"


def _auto_exercises(conn, text: str, chapter_id: str, title: str, class_id: str) -> int:
    """Delegate to chapters blueprint's private exercise generator."""
    try:
        from blueprints.chapters import _auto_generate_exercises

        return _auto_generate_exercises(conn, text, chapter_id, title, class_id)
    except Exception as exc:
        logger.warning("Auto-exercise generation skipped: %s", exc)
        return 0


# ---------------------------------------------------------------------------
# Internal content fetchers (return dict with html_doc / text / error)
# ---------------------------------------------------------------------------


def _fetch_pypi(data: dict) -> dict:
    package = (data.get("package") or "").strip().lower()
    if not package or not re.match(r"^[a-z0-9_\-\.]+$", package):
        return {"error": "Invalid package name"}

    resp = requests.get(f"https://pypi.org/pypi/{package}/json", timeout=_HTTP_TIMEOUT)
    if resp.status_code == 404:
        return {"error": f"Package '{package}' not found on PyPI"}
    resp.raise_for_status()

    info = resp.json().get("info", {})
    raw_desc = info.get("description") or info.get("summary") or "No description available."
    content_type = info.get("description_content_type") or "text/markdown"

    html_body = (
        _md_to_html(raw_desc)
        if "markdown" in content_type.lower()
        else f"<pre>{_html_mod.escape(raw_desc)}</pre>"
    )

    meta_block = (
        f"<h1>{_html_mod.escape(info.get('name', package))}</h1>"
        f"<table style='margin-bottom:1rem'>"
        f"<tr><th>Version</th><td>{_html_mod.escape(info.get('version',''))}</td></tr>"
        f"<tr><th>Author</th><td>{_html_mod.escape(info.get('author',''))}</td></tr>"
        f"<tr><th>License</th><td>{_html_mod.escape(info.get('license',''))}</td></tr>"
        f"<tr><th>Summary</th><td>{_html_mod.escape(info.get('summary',''))}</td></tr>"
        f"</table><hr>{html_body}"
    )

    return {
        "title": f"{info.get('name', package)} Documentation",
        "description": info.get("summary", ""),
        "text": raw_desc,
        "html_doc": _wrap_html(meta_block, f"{info.get('name', package)} Docs"),
    }


def _fetch_url(data: dict) -> dict:
    url = (data.get("url") or "").strip()
    if not url or not url.startswith(("http://", "https://")):
        return {"error": "A valid http/https URL is required"}

    try:
        raw = _fetch_bytes(url)
    except Exception as exc:
        logger.warning("Fetch failed %s: %s", url, exc)
        return {"error": "Could not fetch the URL. Check that it is publicly accessible."}

    title, description, body = _parse_html(raw, url)
    plain_text = BeautifulSoup(body, "html.parser").get_text(separator=" ", strip=True)

    return {
        "title": title,
        "description": description,
        "text": plain_text,
        "html_doc": _wrap_html(body, title, source_url=url),
    }


def _route_fetch(data: dict) -> dict:
    """Dispatch to the correct fetcher based on 'source' field."""
    source = data.get("source", "")
    if source == "pypi":
        return _fetch_pypi(data)
    if source in ("url", "openstax", "libretexts", "oer"):
        return _fetch_url(data)
    return {"error": "Unknown import source"}


# ---------------------------------------------------------------------------
# OpenStax routes
# ---------------------------------------------------------------------------


@bp.route("/api/import/openstax/books", methods=["GET"])
@require_auth
@require_role("professor", "superadmin")
def openstax_books():
    """List all OpenStax textbooks via the public CMS API."""
    try:
        resp = requests.get(
            _OPENSTAX_CMS,
            params={
                "type": "books.Book",
                "fields": "title,slug,cover_url,description",
                "limit": 250,
                "offset": 0,
            },
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        books = [
            {
                "slug": item.get("meta", {}).get("slug") or item.get("slug", ""),
                "title": item.get("title", ""),
                "description": (item.get("description") or "")[:200],
                "cover_url": item.get("cover_url", ""),
            }
            for item in resp.json().get("items", [])
        ]
        return jsonify({"books": books}), 200
    except Exception as exc:
        logger.error("OpenStax book list failed: %s", exc)
        return jsonify({"error": "Could not fetch OpenStax catalog"}), 502


@bp.route("/api/import/openstax/books/<book_slug>/toc", methods=["GET"])
@require_auth
@require_role("professor", "superadmin")
def openstax_toc(book_slug: str):
    """Scrape the table of contents for one OpenStax book."""
    if not re.match(r"^[a-z0-9\-]+$", book_slug):
        return jsonify({"error": "Invalid book slug"}), 400
    try:
        raw = _fetch_bytes(f"https://openstax.org/details/books/{book_slug}")
        soup = BeautifulSoup(raw, "html.parser")
        pattern = re.compile(rf"/books/{re.escape(book_slug)}/pages/", re.I)
        seen, toc = set(), []
        for a in soup.find_all("a", href=pattern):
            m = re.search(r"/pages/(.+)$", a.get("href", ""))
            if not m:
                continue
            page_slug = m.group(1).strip("/")
            if page_slug in seen:
                continue
            seen.add(page_slug)
            toc.append(
                {
                    "slug": page_slug,
                    "title": a.get_text(strip=True) or page_slug,
                    "url": f"https://openstax.org/books/{book_slug}/pages/{page_slug}",
                }
            )
        return jsonify({"book_slug": book_slug, "toc": toc}), 200
    except Exception as exc:
        logger.error("OpenStax TOC failed for %s: %s", book_slug, exc)
        return jsonify({"error": "Could not fetch book contents"}), 502


# ---------------------------------------------------------------------------
# LibreTexts routes
# ---------------------------------------------------------------------------

_LIBRETEXTS_LIBS = [
    {"id": "biology", "name": "Biology", "domain": "bio.libretexts.org"},
    {"id": "business", "name": "Business", "domain": "biz.libretexts.org"},
    {"id": "chemistry", "name": "Chemistry", "domain": "chem.libretexts.org"},
    {"id": "engineering", "name": "Engineering", "domain": "eng.libretexts.org"},
    {"id": "geosciences", "name": "Geosciences", "domain": "geo.libretexts.org"},
    {"id": "humanities", "name": "Humanities", "domain": "human.libretexts.org"},
    {"id": "mathematics", "name": "Mathematics", "domain": "math.libretexts.org"},
    {"id": "medicine", "name": "Medicine", "domain": "med.libretexts.org"},
    {"id": "physics", "name": "Physics", "domain": "phys.libretexts.org"},
    {"id": "social-sciences", "name": "Social Sciences", "domain": "socialsci.libretexts.org"},
    {"id": "statistics", "name": "Statistics", "domain": "stats.libretexts.org"},
    {"id": "workforce", "name": "Workforce", "domain": "workforce.libretexts.org"},
]


@bp.route("/api/import/libretexts/libraries", methods=["GET"])
@require_auth
@require_role("professor", "superadmin")
def libretexts_libraries():
    """Return the list of LibreTexts subject libraries."""
    return jsonify({"libraries": _LIBRETEXTS_LIBS}), 200


@bp.route("/api/import/libretexts/search", methods=["GET"])
@require_auth
@require_role("professor", "superadmin")
def libretexts_search():
    """Search a LibreTexts library and return matching page links."""
    query = request.args.get("q", "").strip()
    library_id = request.args.get("library", "")
    if not query:
        return jsonify({"error": "Query is required"}), 400

    domain = next(
        (lib["domain"] for lib in _LIBRETEXTS_LIBS if lib["id"] == library_id),
        "libretexts.org",
    )
    search_url = f"https://{domain}/search?q={requests.utils.quote(query)}"

    results = []
    try:
        raw = _fetch_bytes(search_url)
        soup = BeautifulSoup(raw, "html.parser")
        seen_urls = set()
        for a in soup.find_all("a", href=re.compile(rf"https?://{re.escape(domain)}/")):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if text and len(text) > 5 and href not in seen_urls and href != search_url:
                seen_urls.add(href)
                results.append({"title": text, "url": href})
                if len(results) >= 20:
                    break
    except Exception as exc:
        logger.warning("LibreTexts search scrape failed: %s", exc)

    return jsonify({"results": results, "search_url": search_url, "library": library_id}), 200


# ---------------------------------------------------------------------------
# OER Commons route
# ---------------------------------------------------------------------------


@bp.route("/api/import/oer/search", methods=["GET"])
@require_auth
@require_role("professor", "superadmin")
def oer_search():
    """Search OER Commons for open educational resources."""
    query = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 10, type=int), 20)
    if not query:
        return jsonify({"error": "Query is required"}), 400

    fallback = {
        "results": [],
        "total": 0,
        "page": page,
        "search_url": f"https://www.oercommons.org/search?q={requests.utils.quote(query)}",
    }
    try:
        resp = requests.get(
            "https://www.oercommons.org/api/v1/materials/",
            params={
                "search": query,
                "limit": limit,
                "offset": (page - 1) * limit,
                "format": "json",
            },
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        results = [
            {
                "id": item.get("id"),
                "title": item.get("title", ""),
                "url": item.get("url") or f"https://www.oercommons.org/courses/{item.get('id')}",
                "description": (item.get("description") or "")[:400],
                "license": item.get("license_name", ""),
            }
            for item in data.get("results", [])
        ]
        return jsonify({"results": results, "total": data.get("count", 0), "page": page}), 200
    except Exception as exc:
        logger.warning("OER Commons search failed: %s", exc)
        return jsonify(fallback), 200


# ---------------------------------------------------------------------------
# Preview route
# ---------------------------------------------------------------------------


@bp.route("/api/import/preview", methods=["POST"])
@csrf_exempt
@require_auth
@require_role("professor", "superadmin")
def import_preview():
    """Return title, description and a short text snippet — no chapter saved."""
    data = request.json or {}
    try:
        result = _route_fetch(data)
        if "error" in result:
            return jsonify(result), 400
        return (
            jsonify(
                {
                    "title": result.get("title", ""),
                    "description": result.get("description", ""),
                    "content_preview": (result.get("text") or "")[:600],
                    "source": data.get("source", ""),
                }
            ),
            200,
        )
    except Exception as exc:
        logger.error("Import preview failed: %s", exc)
        return jsonify({"error": "Preview failed"}), 500


# ---------------------------------------------------------------------------
# Import-as-chapter route
# ---------------------------------------------------------------------------


@bp.route("/api/classes/<class_id>/chapters/import", methods=["POST"])
@csrf_exempt
@require_auth
def import_as_chapter(class_id: str):
    """Fetch external content and persist it as a new chapter."""
    try:
        data = request.json or {}
        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()
        exercise_mode = data.get("exercise_mode", "auto")

        conn = get_db_connection()

        owner_id = class_repo.get_class_owner(conn, class_id)
        if owner_id != g.user_id:
            return jsonify({"error": "Not authorized"}), 403

        result = _route_fetch(data)
        if "error" in result:
            return jsonify(result), 400

        if not title:
            title = result.get("title") or "Imported Chapter"
        if not description:
            description = result.get("description", "")

        file_bytes = result["html_doc"].encode("utf-8")
        safe_name = re.sub(r"[^\w\-]", "_", title)[:50]
        pdf_filename = f"{safe_name}.html"

        chapter_number = chapter_repo.get_next_chapter_number(conn, class_id)
        chapter_id = f"{class_id}_{int(time.time() * 1000)}"
        pdf_url = f"/api/chapters/{chapter_id}/pdf"

        chapter_repo.insert_chapter(
            conn,
            chapter_id,
            class_id,
            title,
            description,
            chapter_number,
            pdf_url,
            pdf_filename,
            file_bytes,
        )

        audit(
            conn,
            "IMPORT_CHAPTER",
            resource_type="chapter",
            resource_id=chapter_id,
            details={"source": data.get("source", ""), "class_id": class_id},
        )

        exercises_generated = 0
        plain_text = result.get("text", "")
        if exercise_mode == "auto" and plain_text:
            exercises_generated = _auto_exercises(conn, plain_text, chapter_id, title, class_id)

        conn.commit()

        try:
            from core import cache

            cache.invalidate_cache(f"chapters:*:class_id={class_id}")
        except Exception:
            pass

        return (
            jsonify(
                {
                    "chapter_id": chapter_id,
                    "title": title,
                    "description": description,
                    "chapter_number": chapter_number,
                    "pdf_url": pdf_url,
                    "source": data.get("source", ""),
                    "exercises_generated": exercises_generated,
                    "success": True,
                }
            ),
            201,
        )

    except Exception as exc:
        logger.error("Chapter import failed: %s", exc)
        return jsonify({"error": "Import failed"}), 500
