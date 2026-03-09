# AI Exercise Generation in AnalytIQ

## Overview

AnalytIQ uses **Google Gemini 2.5 Flash** to automatically generate coding exercises from chapter content. A professor uploads a file or imports a web resource, the AI reads it, detects the programming language being taught, and produces 5–8 graded, sandboxed exercises — with no manual authoring required.

---

## How It Works: End-to-End

```
File Upload / Web Import → Text Extraction → Gemini Prompt → Exercises JSON → Stored in DB
                                                                                    ↓
                           Student Submission → Sandboxed Code Runner → Output Comparison → Score (0–100)
```

---

## Content Sources

### Uploaded Files

Professors can upload chapter files directly. The allowed extensions are:

| Format | Extension | How Text Is Extracted |
|--------|-----------|-----------------------|
| PDF | `.pdf` | PyPDF2 — reads all text layers |
| Word document | `.docx` | python-docx — paragraphs + table cells |
| Plain text | `.txt` | UTF-8 decode |
| Jupyter Notebook | `.ipynb` | All code and markdown cells, separated by `---` |
| CSV | `.csv` | Rows joined as comma-separated text |
| Spreadsheet | `.xlsx`, `.xls` | Accepted by upload but **not yet extracted** for exercise generation (no extractor implemented) |
| JSON | `.json` | Accepted by upload but **not yet extracted** for exercise generation |

**File size limit:** 50 MB per upload.

Extraction is handled by [python/content_extractor.py](../python/content_extractor.py). If extraction fails or the format is unsupported by the extractor, the chapter is still saved but exercise auto-generation is skipped.

> **Note:** PowerPoint (`.pptx`) and Apple Notes exports are not currently accepted. To use slides as course content, export them to PDF or copy the text into a `.txt` or `.docx` file first.

---

### Web Content Import

Instead of uploading a file, professors can import a chapter directly from the web. The app supports three open-content sources plus generic URLs:

| Source | What It Imports |
|--------|----------------|
| **OpenStax** | Any page from any OpenStax textbook, selected via a built-in book browser and table of contents |
| **LibreTexts** | Any page across 12 subject libraries (Biology, Chemistry, Math, Stats, Engineering, etc.) via keyword search |
| **OER Commons** | Open educational resources found via the OER Commons API |
| **Any URL** | Any publicly accessible web page — the app fetches the HTML, strips nav/footer/ads, and isolates the main content |
| **PyPI package** | Documentation page for any Python package by package name |

For web imports, the app:
1. Fetches the HTML (capped at 5 MB)
2. Strips `<script>`, `<style>`, `<nav>`, `<footer>`, `<aside>`, and similar noise
3. Isolates the `<main>`, `<article>`, or main content block
4. Wraps it in a clean HTML document stored as the chapter's "file"
5. Passes the plain-text version to Gemini for exercise generation (same pipeline as file uploads)

**Files:** [blueprints/content_import.py](../blueprints/content_import.py)

---

### 1. Text Extraction

All content paths — file upload or web import — converge on plain text before being sent to Gemini. The first 10,000 characters are used to stay within token limits.

**File:** [python/pdf_processor.py](../python/pdf_processor.py) (PDF), [python/content_extractor.py](../python/content_extractor.py) (all other formats)

---

### 2. Language Detection (Automatic)

The Gemini prompt instructs the model to **read the chapter content first** and identify the primary language or tool being taught before generating any exercises. The AI will never default to Python unless the content is clearly Python-based.

**Detected languages include:**

| Language   | Notes |
|------------|-------|
| Python     | Data science, scripting, OOP |
| R          | Statistics, data analysis |
| SQL        | Queries — uses SQLite for grading |
| JavaScript | Web / scripting |
| Java       | OOP, algorithms |
| Scala      | (generated but not yet graded) |
| MATLAB     | (generated but not yet graded) |

---

### 3. Prompt Engineering

The Gemini prompt enforces strict rules to produce **automatically gradable** exercises:

- **One concept per exercise** — no multi-step bundled problems
- **Named functions that return values** — not just `print()` calls
- **5–10 lines of solution code** — beginner-friendly, never complex one-liners
- **Every line commented** — using the language's native comment syntax
- **5–8 test cases per exercise** — including edge cases with higher weight (2×)
- **No hardcoded answers** — exercises must accept parameters and compute results
- **SQL exception** — SQL exercises use `SELECT` queries with DDL `setup` blocks instead of functions

**File:** [python/exercise_generator.py](../python/exercise_generator.py)

---

### 4. Grading: Output-Based, Not String-Similarity

Student code is executed in a **sandboxed subprocess** and graded by comparing the actual return value to the expected output. There is no Levenshtein distance, no partial string matching — the answer must be correct.

**Scoring (0–100):**

| Component | Points | Criteria |
|-----------|--------|----------|
| Correctness | 0–80 | `(weighted_tests_passed / total_weight) × 80` |
| Runs cleanly | 0–10 | Code compiles and executes without errors |
| No hardcoded answers | 0–5 | Not all lines are bare literal returns |
| Basic style | 0–5 | At least one meaningful variable assignment |

**File:** [python/code_runner.py](../python/code_runner.py)

---

### 5. Security Model (Sandboxing)

Each language has its own isolation strategy:

| Language | Sandbox |
|----------|---------|
| Python | Subprocess + blocked dangerous imports (`subprocess`, `socket`, `os`, etc.) + `RLIMIT_AS/NPROC/FSIZE` on Linux + read-only `open()` |
| JavaScript | Node.js subprocess + `--disallow-code-generation-from-strings` |
| R | Rscript subprocess + per-test timeout |
| SQL | SQLite **in-process** (`:memory:`) + SIGALRM timeout — no subprocess needed |
| Java | `javac` + `java` subprocess + timeout |

All runners enforce a **5-second per-test timeout** and a **50 KB code size limit**.

---

## Supported Exercise Types by Language

### Python
- Descriptive statistics (mean, median, std)
- DataFrame operations (pandas)
- List comprehensions, sorting, filtering
- String manipulation
- File I/O concepts (conceptual, not file-system dependent)
- OOP basics (class methods)

### R
- Vector operations (`sum`, `mean`, `sd`)
- Data frame manipulation (`dplyr`, `tidyr`)
- Statistical tests
- Plot generation (described, not rendered)
- `apply` family functions

### SQL
- `SELECT` with `WHERE`, `GROUP BY`, `ORDER BY`
- `JOIN` operations
- Aggregation functions (`COUNT`, `SUM`, `AVG`)
- Subqueries
- Each exercise includes its own DDL + `INSERT` setup — no external DB required

### JavaScript
- Array methods (`map`, `filter`, `reduce`)
- String manipulation
- Object traversal
- Basic algorithm implementation

### Java
- Static methods on the `Solution` class
- String processing
- Math operations
- Basic data structure manipulation

---

## What the AI Generates (Per Exercise)

```json
{
  "language": "Python",
  "title": "Calculate the Mean of a List",
  "description": "Define a function calculate_mean(numbers) that computes and returns the arithmetic mean of a list of numbers.",
  "difficulty": "easy",
  "function_name": "calculate_mean",
  "solution_code": "def calculate_mean(numbers):\n    total = sum(numbers)  # add all values\n    count = len(numbers)  # count elements\n    mean = total / count  # compute average\n    print('Mean:', mean)  # display for student\n    return mean           # return for grading",
  "test_cases": [
    {
      "description": "basic case — small list",
      "input": { "numbers": [1, 2, 3, 4, 5] },
      "expected_output": 3.0,
      "weight": 1
    },
    {
      "description": "edge case — single element",
      "input": { "numbers": [42] },
      "expected_output": 42.0,
      "weight": 2
    }
  ]
}
```

---

## Could AnalytIQ Work for Computer Science?

**Short answer: Yes, with caveats.**

The exercise engine is already largely language-agnostic. The same pipeline — PDF → language detection → function-based exercises → sandboxed grading — applies to CS content. Here is where it fits well and where gaps exist:

### Strengths for CS

| CS Topic | Fit | Notes |
|----------|-----|-------|
| Algorithms (sorting, searching) | Excellent | Python/Java/JS all supported and sandboxed |
| Data structures (lists, trees, graphs) | Good | Works for returning computed values (e.g., tree height, list reversal) |
| Recursion | Good | Clean test-case model; function returns match well |
| Database / SQL | Excellent | Full in-process SQLite grading already exists |
| OOP basics | Moderate | Java `Solution` class pattern works; Python classes work |
| Web fundamentals (JS) | Good | Node.js runner handles DOM-agnostic logic |
| Discrete math / logic | Good | Exercises can return boolean or integer answers |

### Current Limitations for CS

| CS Topic | Gap | Workaround Needed |
|----------|-----|-------------------|
| Data structures (linked lists, trees) | No pointer/reference support in grading harness | Would need object serialisation layer |
| Concurrency / threading | Blocked — Python sandbox blocks `threading`, `asyncio` | Not supported by design (security) |
| Systems programming (C, C++) | No C/C++ runner | Would need `gcc`/`clang` subprocess + strict sandboxing |
| Assembly / low-level | Not supported | Out of scope |
| GUI / web rendering | Subprocess runners are headless | UI testing not supported |
| Large-scale project structure | Each exercise is a single function | Multi-file projects not supported |

### Recommendation

AnalytIQ is a strong fit for **introductory and intermediate CS courses** where exercises map naturally to "write a function that does X and returns Y". It would cover:

- CS1 / CS2 courses (Python or Java)
- Data structures and algorithms (function-level problems)
- Databases (SQL is already first-class)
- Scripting and automation
- Web programming fundamentals (JavaScript)

For advanced topics like OS, compilers, systems programming, or projects requiring multiple files, the current single-function exercise model would need to be extended. The most impactful addition would be a **C/C++ runner** and a **multi-file submission mode**.

---

## Key Files

| File | Purpose |
|------|---------|
| [python/exercise_generator.py](../python/exercise_generator.py) | Gemini API call, prompt engineering, JSON validation |
| [python/code_runner.py](../python/code_runner.py) | Sandboxed multi-language execution and grading |
| [python/pdf_processor.py](../python/pdf_processor.py) | PDF text extraction |
| [blueprints/exercises.py](../blueprints/exercises.py) | REST API routes (`/api/exercises/*`) |
| [repositories/exercise_repository.py](../repositories/exercise_repository.py) | DB read/write for exercises and progress |
| [tasks.py](../tasks.py) | Celery async task that triggers generation after PDF upload |
