#!/usr/bin/env python3
"""
AnalytIQ Knowledge Base Generator

Scans the workspace for documentation, code, and configuration files,
then organizes everything into structured Markdown documentation grouped by topic.

NOTE: This script processes workspace files only. Cursor chat history and
previous conversations are not stored in the workspace and cannot be accessed.
To include chat insights, you can manually export conversations to a file
and place it in docs/sources/ for inclusion in future runs.
"""

import os
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Configuration
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = WORKSPACE_ROOT / "docs" / "knowledge_base"
EXCLUDE_DIRS = {".venv", "venv", "node_modules", ".git", "__pycache__", "htmlcov", ".pytest_cache"}
EXCLUDE_FILES = {"generate_knowledge_base.py"}
MAX_FILE_SIZE = 500_000  # Skip files larger than 500KB

# Topic categorization rules: (pattern, category)
TOPIC_PATTERNS = [
    (r"auth|jwt|login|signup|signin|password|token", "01-Security-Authentication"),
    (r"security|csrf|cors|rate.?limit|bcrypt", "01-Security-Authentication"),
    (r"config|env|environment|\.env", "02-Configuration"),
    (r"deploy|render|procfile|gunicorn", "03-Deployment"),
    (r"database|postgres|psycopg|sql", "04-Database-Storage"),
    (r"supabase|redis|cache|storage", "04-Database-Storage"),
    (r"api|endpoint|route|swagger|openapi", "05-API-Endpoints"),
    (r"test|pytest|coverage|ci\.yml", "06-Testing-CICD"),
    (r"celery|task|async|background", "07-Background-Tasks"),
    (r"gemini|exercise.?gen|ai|pdf.?process", "08-AI-Exercise-Generation"),
    (r"sentry|error|monitor|logging", "09-Monitoring-Logging"),
    (r"class|chapter|module|enrollment", "10-Classes-Chapters"),
    (r"frontend|\.js|\.html|profile|dashboard", "11-Frontend-Pages"),
    (r"utils|helper|common", "12-Utilities"),
]

# File extensions and how to process them
DOC_EXTENSIONS = {".md", ".mdx", ".txt"}
CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}
CONFIG_EXTENSIONS = {".json", ".yaml", ".yml"}


def should_skip(path: Path) -> bool:
    """Check if path should be skipped."""
    if path.name in EXCLUDE_FILES:
        return True
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
    if path.suffix not in DOC_EXTENSIONS | CODE_EXTENSIONS | CONFIG_EXTENSIONS:
        return True
    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return True
    except OSError:
        return True
    return False


def categorize_file(rel_path: str, content: str) -> list[str]:
    """Determine which topic(s) a file belongs to."""
    text = f"{rel_path} {content[:2000]}".lower()
    categories = set()
    for pattern, category in TOPIC_PATTERNS:
        if re.search(pattern, text, re.I):
            categories.add(category)
    if not categories:
        categories.add("13-General")
    return sorted(categories)


def extract_python_docstrings(content: str) -> str:
    """Extract module/class/function docstrings from Python."""
    parts = []
    # Module docstring
    mod_match = re.search(r'^"""([^"]*(?:""[^"]*)*)"""', content, re.DOTALL)
    if mod_match:
        parts.append(mod_match.group(1).strip())
    # Class and function docstrings
    for match in re.finditer(
        r'(?:def|class)\s+\w+[^:]*:\s*"""([^"]*(?:""[^"]*)*)"""',
        content,
        re.DOTALL,
    ):
        parts.append(match.group(1).strip())
    return "\n\n---\n\n".join(parts) if parts else content[:3000]


def extract_js_comments(content: str) -> str:
    """Extract meaningful comments and structure from JS."""
    lines = []
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*"):
            lines.append(stripped)
        elif "//" in line and not line.strip().startswith("//"):
            idx = line.find("//")
            lines.append(line[idx:].strip())
    return "\n".join(lines[:100]) if lines else content[:2000]


def read_file_safe(path: Path) -> str:
    """Read file with encoding fallback."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def process_file(path: Path, rel_path: str) -> dict:
    """Process a single file and return extracted content."""
    content = read_file_safe(path)
    if not content.strip():
        return {"path": rel_path, "content": "", "summary": ""}

    if path.suffix == ".md" or path.suffix == ".mdx" or path.suffix == ".txt":
        extracted = content
    elif path.suffix == ".py":
        extracted = extract_python_docstrings(content)
        if len(extracted) < 100:
            extracted = content[:4000]  # Fallback to raw
    elif path.suffix in {".js", ".jsx", ".ts", ".tsx"}:
        extracted = extract_js_comments(content)
        if len(extracted) < 50:
            extracted = content[:2000]
    elif path.suffix in CONFIG_EXTENSIONS:
        extracted = content
    else:
        extracted = content[:3000]

    # Create short summary
    first_para = extracted.split("\n\n")[0][:200].strip()
    summary = first_para.replace("\n", " ") if first_para else path.name

    return {
        "path": rel_path,
        "content": extracted,
        "summary": summary,
        "full_content": content if path.suffix in DOC_EXTENSIONS else None,
    }


def gather_files() -> list[tuple[Path, str]]:
    """Gather all processable files."""
    files = []
    sources_dir = WORKSPACE_ROOT / "docs" / "knowledge_base" / "sources"
    for root, dirs, filenames in os.walk(WORKSPACE_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        root_path = Path(root)
        for name in filenames:
            path = root_path / name
            if should_skip(path):
                continue
            try:
                rel = path.relative_to(WORKSPACE_ROOT)
            except ValueError:
                continue
            if str(rel).startswith("docs/knowledge_base") and "sources" not in str(rel):
                continue  # Don't include our own output (but DO include sources/)
            files.append((path, str(rel)))
    return files


def build_category_content(files_by_category: dict[str, list]) -> dict[str, str]:
    """Build Markdown content for each category."""
    category_docs = {}

    category_titles = {
        "01-Security-Authentication": "Security & Authentication",
        "02-Configuration": "Configuration",
        "03-Deployment": "Deployment",
        "04-Database-Storage": "Database & Storage",
        "05-API-Endpoints": "API & Endpoints",
        "06-Testing-CICD": "Testing & CI/CD",
        "07-Background-Tasks": "Background Tasks",
        "08-AI-Exercise-Generation": "AI & Exercise Generation",
        "09-Monitoring-Logging": "Monitoring & Logging",
        "10-Classes-Chapters": "Classes & Chapters",
        "11-Frontend-Pages": "Frontend & Pages",
        "12-Utilities": "Utilities",
        "13-General": "General",
    }

    for category, items in sorted(files_by_category.items()):
        title = category_titles.get(category, category)
        sections = [
            f"# {title}\n",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
            "---\n",
            "## Overview\n",
            f"This document consolidates knowledge from **{len(items)}** file(s) related to {title.lower()}.\n",
            "---\n",
        ]

        for item in sorted(items, key=lambda x: x["path"]):
            path = item["path"]
            content = item["content"]
            summary = item["summary"]

            sections.append(f"## `{path}`\n\n")
            sections.append(f"**Summary:** {summary}\n\n")

            if content:
                sections.append("### Details\n\n")
                sections.append("```\n")
                sections.append(content[:8000])  # Limit per file
                if len(content) > 8000:
                    sections.append("\n\n... (truncated)")
                sections.append("\n```\n\n")

            sections.append("---\n\n")

        category_docs[category] = "".join(sections)

    return category_docs


def build_decisions_doc(files_by_category: dict) -> str:
    """Build a dedicated document for key decisions, workflows, and context."""
    # Find and include full content of key audit/checklist docs
    key_sources = []
    for path in [
        WORKSPACE_ROOT / "SECURITY_AUDIT_COMPLETE.md",
        WORKSPACE_ROOT / "RENDER_ENV_CHECKLIST.md",
    ]:
        if path.exists():
            key_sources.append((path.name, path.read_text(encoding="utf-8", errors="replace")))

    if not key_sources:
        return ""

    sections = [
        "# Key Decisions, Workflows & Context\n",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
        "---\n\n",
        "## Purpose\n\n",
        "This document consolidates important decisions, workflows, technical notes, ",
        "and context from project documentation. Use it as a quick reference for ",
        "how things were set up and why.\n\n",
        "---\n\n",
    ]

    for name, content in key_sources:
        sections.append(f"## From `{name}`\n\n")
        sections.append(content)
        sections.append("\n\n---\n\n")

    return "".join(sections)


def write_index(categories: list[str]) -> str:
    """Create index/README for the knowledge base."""
    category_links = {
        "01-Security-Authentication": "01-Security-Authentication.md",
        "02-Configuration": "02-Configuration.md",
        "03-Deployment": "03-Deployment.md",
        "04-Database-Storage": "04-Database-Storage.md",
        "05-API-Endpoints": "05-API-Endpoints.md",
        "06-Testing-CICD": "06-Testing-CICD.md",
        "07-Background-Tasks": "07-Background-Tasks.md",
        "08-AI-Exercise-Generation": "08-AI-Exercise-Generation.md",
        "09-Monitoring-Logging": "09-Monitoring-Logging.md",
        "10-Classes-Chapters": "10-Classes-Chapters.md",
        "11-Frontend-Pages": "11-Frontend-Pages.md",
        "12-Utilities": "12-Utilities.md",
        "13-General": "13-General.md",
    }

    lines = [
        "# AnalytIQ Knowledge Base\n",
        f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
        "---\n\n",
        "## About\n\n",
        "This knowledge base was auto-generated from workspace files. It organizes ",
        "documentation, code insights, configuration, and technical notes by topic.\n\n",
        "### Scope\n\n",
        "- **Included:** All Markdown docs, Python/JS source (docstrings & comments), ",
        "config files, and scripts in the workspace.\n",
        "- **Not included:** Cursor chat history is not stored in the workspace. ",
        "To add insights from past conversations, export them to `docs/sources/` ",
        "and re-run this script.\n\n",
        "---\n\n",
        "## Quick Navigation\n\n",
        "- [Key Decisions & Workflows](00-Key-Decisions-And-Workflows.md)\n",
    ]

    for cat in sorted(categories):
        fname = category_links.get(cat, f"{cat}.md")
        name = cat.replace("-", " ").replace("01 ", "").replace("02 ", "").replace("03 ", "")
        name = name.replace("04 ", "").replace("05 ", "").replace("06 ", "").replace("07 ", "")
        name = name.replace("08 ", "").replace("09 ", "").replace("10 ", "").replace("11 ", "")
        name = name.replace("12 ", "").replace("13 ", "")
        lines.append(f"- [{name}]({fname})\n")

    lines.extend([
        "\n---\n\n",
        "## Regenerating\n\n",
        "```bash\n",
        "python3 scripts/generate_knowledge_base.py\n",
        "```\n",
    ])

    return "".join(lines)


def main():
    print("AnalytIQ Knowledge Base Generator")
    print("=" * 50)
    print(f"Workspace: {WORKSPACE_ROOT}")
    print(f"Output:    {OUTPUT_DIR}\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "sources").mkdir(exist_ok=True)

    files = gather_files()
    print(f"Found {len(files)} files to process.\n")

    files_by_category = defaultdict(list)

    for path, rel_path in files:
        result = process_file(path, rel_path)
        if not result["content"] and not result["full_content"]:
            continue
        content_to_use = result["full_content"] or result["content"]
        categories = categorize_file(rel_path, content_to_use)
        entry = {
            "path": rel_path,
            "content": content_to_use[:12000],
            "summary": result["summary"],
        }
        for cat in categories:
            files_by_category[cat].append(entry)

    category_docs = build_category_content(dict(files_by_category))

    # Add Key Decisions & Workflows doc
    decisions_doc = build_decisions_doc(files_by_category)
    if decisions_doc:
        decisions_path = OUTPUT_DIR / "00-Key-Decisions-And-Workflows.md"
        decisions_path.write_text(decisions_doc, encoding="utf-8")
        print(f"  Wrote {decisions_path.name}")

    for category, doc_content in category_docs.items():
        out_path = OUTPUT_DIR / f"{category}.md"
        out_path.write_text(doc_content, encoding="utf-8")
        print(f"  Wrote {out_path.name}")

    index_content = write_index(list(files_by_category.keys()))
    (OUTPUT_DIR / "README.md").write_text(index_content, encoding="utf-8")
    print(f"  Wrote README.md")

    print("\nDone. Knowledge base is in docs/knowledge_base/")


if __name__ == "__main__":
    main()
