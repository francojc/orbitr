# Development Implementation Details

**Project:** lumen
**Status:** Phase 2 complete
**Last Updated:** 2026-04-07

## Architecture

### System Design

- **Architecture Pattern:** CLI pipeline — layered command dispatch → concurrent API clients → core processing → display
- **Primary Language:** Python 3.10+
- **Framework:** Typer (CLI), Rich (terminal rendering)
- **Build System:** Hatchling via `uv`

### Component Overview

```
lumen/
├── pyproject.toml
├── flake.nix
├── .gitignore
├── .env.example
├── README.md
├── specs/               # Planning, progress, implementation docs
├── logs/                # Session and weekly review logs
├── src/
│   └── lumen/
│       ├── __init__.py
│       ├── cli.py           # Typer app root; global flags; command tree
│       ├── config.py        # Layered config: flags > env > file > defaults
│       ├── commands/
│       │   ├── search.py    # lumen search (keyword + field filters)
│       │   ├── paper.py     # lumen paper, lumen cite
│       │   ├── author.py    # lumen author
│       │   ├── recommend.py # lumen recommend
│       │   ├── query.py     # lumen query
│       │   ├── export.py    # lumen export
│       │   ├── zotero.py    # lumen zotero add / collections / new
│       │   ├── cache.py     # lumen cache stats / clean / clear
│       │   ├── init.py      # lumen init
│       │   └── doctor.py    # lumen doctor
│       ├── clients/
│       │   ├── base.py              # Abstract base client (retry, rate limit)
│       │   ├── arxiv.py             # arXiv Atom feed client
│       │   ├── semantic_scholar.py  # Semantic Scholar REST client
│       │   # google_scholar.py — deferred to v1.1
│       ├── core/
│       │   ├── models.py        # Paper, Author, SearchResult (Pydantic)
│       │   ├── deduplication.py # DOI, arXiv ID, fuzzy title dedup
│       │   ├── ranking.py       # Relevance, citations, date, impact scoring
│       │   ├── cache.py         # SQLite-backed TTL cache
│       │   └── export.py        # BibTeX, RIS, CSL-JSON formatters
│       ├── zotero/
│       │   └── client.py        # pyzotero wrapper; add, collections, new
│       └── display/
│           ├── table.py         # Rich Table renderer
│           ├── list.py          # Rich Panel/group renderer
│           ├── detail.py        # Full single-paper Rich layout
│           └── json_fmt.py      # JSON serializer (newline-delimited)
└── tests/
    ├── conftest.py
    ├── fixtures/                    # Recorded API responses for offline testing
    │   ├── arxiv_search.xml
    │   ├── arxiv_get_by_id.xml
    │   ├── ss_search.json
    │   ├── ss_get_by_id.json
    │   ├── ss_citations.json
    │   └── ss_recommendations.json
    ├── test_models.py               # Paper, Author, SearchResult (15 tests)
    ├── test_arxiv.py                # ArxivClient (15 tests)
    ├── test_semantic_scholar.py     # SemanticScholarClient (15 tests)
    ├── test_deduplication.py        # deduplicate, _merge, helpers (24 tests)
    ├── test_ranking.py              # rank, scoring functions (22 tests)
    └── test_cache.py                # Cache get/set/clean/clear/stats (19 tests)
```

### Key Modules

1. **`cli.py`**
   - **Purpose:** Root Typer app; registers all subcommand groups; handles `--version`, `--verbose`, `--quiet`, `--no-color`, `--config`; injects resolved config into Click context
   - **Public Interface:** `app` (Typer instance), `main()` entry point
   - **Dependencies:** `config.py`, all `commands/` modules

2. **`config.py`**
   - **Purpose:** Resolves settings from CLI flags, environment variables, TOML config file, and built-in defaults in priority order; manages credential storage
   - **Public Interface:** `Config` dataclass, `load_config(path=None) -> Config`
   - **Dependencies:** `tomllib` (stdlib 3.11+; `tomli` for 3.10), `python-dotenv`

3. **`clients/base.py`**
   - **Purpose:** Abstract base providing retry logic (exponential backoff on 429/503), per-source rate limiting, and circuit breaking; all source clients extend this
   - **Public Interface:** `BaseClient`, `async search(query, max_results) -> SearchResult`, `async get_by_id(id) -> Paper`
   - **Dependencies:** `httpx`, `asyncio`
   - **Retry policy:** 3 attempts; backoff 1 s, 2 s, 4 s on 429/503; circuit flag set after network failure

4. **`clients/arxiv.py`** *(Phase 2 — complete)*
   - **Purpose:** Fetches arXiv Atom feed via `feedparser`; parses entries into `Paper` models
   - **Public Interface:** `ArxivClient.search(query, max_results) -> SearchResult`, `get_by_id(paper_id) -> Paper`
   - **Field mapping:** `entry.id` → `arxiv_id` (URL stripped, version stripped); `entry.authors` → `Author` list; `entry.tags[].term` → `categories`; PDF link via `links[type=application/pdf]`
   - **ID parsing:** `_parse_arxiv_id()` handles bare IDs, `abs/` prefix, full HTTPS URLs, and versioned suffixes
   - **Dependencies:** `feedparser`, `clients/base.py`

5. **`clients/semantic_scholar.py`** *(Phase 2 — complete)*
   - **Purpose:** Queries the Semantic Scholar Graph API v1 (REST/JSON)
   - **Public Interface:** `search`, `get_by_id`, `get_citations`, `get_recommendations`, `_parse_paper`
   - **Field mapping:** `externalIds.ArXiv` → `arxiv_id`; `externalIds.DOI` → `doi`; `openAccessPdf.url` → `pdf_url`; `publicationDate` (ISO string) → `published_date`; falls back to `year` (int) when `publicationDate` is absent
   - **Auth:** `x-api-key` header injected when `api_key` is set
   - **Citations endpoint:** `/paper/{id}/citations` — wraps `citingPaper` key from each result item
   - **Recommendations endpoint:** `/recommendations/v1/papers/forpaper/{id}`
   - **Dependencies:** `httpx`, `clients/base.py`

6. **`core/deduplication.py`** *(Phase 2 — complete)*
   - **Purpose:** Merges result sets from multiple sources using a three-stage matching pipeline
   - **Public Interface:** `deduplicate(papers, threshold=0.85) -> list[Paper]`
   - **Match priority:** (1) exact DOI → (2) exact arXiv ID → (3) fuzzy title (`rapidfuzz.fuzz.token_sort_ratio` ≥ 85%) + author surname overlap
   - **Author overlap:** surname-set intersection; falls back to `True` (assume match) when either paper has no authors
   - **Merge policy:** richer author list wins; `None` fields filled from duplicate; citation counts take the maximum; categories merged without duplication
   - **Dependencies:** `core/models.py`; `rapidfuzz` (optional — Jaccard fallback if absent)

7. **`core/ranking.py`** *(Phase 2 — complete)*
   - **Purpose:** Sorts papers by a named criterion
   - **Public Interface:** `rank(papers, criterion, query=None) -> list[Paper]`
   - **Criteria:** `relevance` (TF-IDF term frequency; title weighted 3×, abstract 1×); `citations` (`math.log1p` of count); `date` (normalised recency since 1990-01-01); `impact` (citations × date); `combined` (relevance 40%, citations 35%, date 25%)
   - **Fallback:** `relevance` without a query degrades to `date`
   - **Dependencies:** `core/models.py`, `math`, `datetime`

8. **`core/cache.py`** *(Phase 2 — complete)*
   - **Purpose:** SQLite-backed TTL key-value store with three independent tiers
   - **Public Interface:** `Cache(db_path)`, `get(key, tier)`, `set(key, value, tier)`, `clean(tier)`, `clear(tier)`, `stats() -> CacheStats`
   - **Tiers and TTLs:** `search` 3600 s · `paper` 86400 s · `citations` 21600 s
   - **Schema versioning:** `meta` table stores `schema_version`; mismatch triggers silent wipe and rebuild
   - **Storage:** values serialised with `json.dumps`; `expires_at` stored as Unix float
   - **Location:** `~/.cache/lumen/cache.db` (XDG); overridable via `db_path` constructor arg
   - **Dependencies:** `sqlite3` (stdlib), `json`, `time`

7. **`display/`**
   - **Purpose:** Renders `list[Paper]` or `Paper` into Rich output or JSON; auto-detects TTY for format and pager; respects `NO_COLOR`
   - **Public Interface:** `render(papers, format: Literal["table","list","detail","json"], pager=True)`
   - **Dependencies:** `rich`

### Data Model

```python
class Author(BaseModel):
    name: str
    affiliation: str | None = None
    author_id: str | None = None

class Paper(BaseModel):
    id: str
    title: str
    authors: list[Author]
    abstract: str | None = None
    published_date: datetime | None = None
    updated_date: datetime | None = None
    url: str
    pdf_url: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    venue: str | None = None
    categories: list[str] = []
    citation_count: int | None = None
    source: str

class SearchResult(BaseModel):
    papers: list[Paper]
    total_count: int
    query: str
    sources: list[str]
```

- **Persistence:** SQLite at `~/.cache/lumen/cache.db`
- **Serialization:** Pydantic `.model_dump_json()` for cache storage; custom formatters in `core/export.py` for bibliography output
- **Migration:** Cache schema versioned; on version mismatch, cache is wiped and rebuilt transparently

## Development Environment

### Setup

The project uses a **Nix flake** (`flake.nix` + `flake.lock`) to pin the development
environment and **direnv** to activate it automatically. A **justfile** wraps all
common tasks.

```bash
# Clone and enter the project
git clone <repo-url> lumen && cd lumen

# direnv activates the flake shell automatically (Python 3.12, uv, ruff, pyright)
# If direnv is not installed, enter manually:
nix develop

# Install all dependencies into .venv and register as an editable tool
just setup

# Verify
lumen --version
```

The `.envrc` contains `use flake .` — this ensures `uv sync` always runs against the
flake-pinned Python, not whatever Python happens to be on `$PATH`.

### Build and Run

```bash
just run -- --help        # uv run lumen --help
just install              # uv tool install . (production-style)
just install-dev          # uv tool install --editable . (changes take effect immediately)
just build                # uv build — produces dist/ wheel + sdist
```

### Code Standards

- **Formatting:** `ruff format` (line length 88)
- **Linting:** `ruff check` with rules `E, F, UP, B, SIM, I`
- **Type Checking:** `pyright` in basic mode; all public interfaces annotated
- **Naming Conventions:** `snake_case` for functions and variables; `PascalCase` for classes; `UPPER_SNAKE` for constants
- **Docstrings:** Google style; required on all public classes and functions

## Testing Strategy

### Test Levels

- **Unit Tests:** `pytest`; located in `tests/`; named `test_<module>.py`; cover `core/` in full
- **Integration Tests:** `pytest` with recorded API fixtures (no live network calls in CI); test full command execution via Typer's `CliRunner`
- **Smoke Tests:** Small script hitting live APIs; run manually before release, not in CI

### Running Tests

```bash
just test                               # full suite
just test-unit                          # unit tests only (-m "not integration")
just cov                                # with coverage report
just test-mod core/test_deduplication   # single module
just test-v                             # verbose output
```

### Coverage Targets

- **Overall:** ≥ 75%
- **`core/` modules:** ≥ 90% (deduplication, ranking, cache, export are critical)
- **`commands/`:** ≥ 60% via CLI runner tests
- **`clients/`:** covered by fixtures; live tests excluded from coverage target

### Test Data

- **Fixtures:** `tests/fixtures/` contains recorded JSON responses for arXiv, Semantic Scholar, and Zotero; generated once with `httpx` mock recording
- **Mocks:** `respx` for async httpx mocking in client tests
- **Cache:** each test gets an isolated in-memory SQLite instance via `conftest.py` fixture

## Deployment

### Target Environment

- **Platform:** Local user install; distributed via PyPI and/or `uv tool install` from git
- **Runtime:** Python 3.10+ on macOS and Linux
- **Configuration:** `~/.config/lumen/config.toml` and environment variables; no server-side config

### CI/CD Pipeline

- **Platform:** GitHub Actions
- **Triggers:** On push to `main`; on pull request; on version tag
- **Stages:**
  1. `lint` — `just check` (`ruff format --check` + `ruff check`)
  2. `typecheck` — `just types` (`pyright src/`)
  3. `test` — `just test` with fixture-based mocks (no live API calls)
  4. `build` — `just build` (`uv build`); upload wheel as artifact
  5. `publish` (tag only) — `uv publish` to PyPI

### Release Process

- **Versioning:** SemVer (`MAJOR.MINOR.PATCH`); managed via `pyproject.toml`
- **Changelog:** `CHANGELOG.md` maintained manually; conventional commit messages used as input
- **Release Steps:**
  1. Update version in `pyproject.toml`
  2. Update `CHANGELOG.md`
  3. Commit: `chore(release): v0.x.0`
  4. Tag: `git tag v0.x.0`
  5. Push tag; CI publishes to PyPI automatically
- **Rollback:** Yank release on PyPI; tag previous version as latest in GitHub Releases

## Error Handling

### Error Hierarchy

```python
class LumenError(Exception): ...            # base
class ConfigError(LumenError): ...          # exit code 3
class UsageError(LumenError): ...           # exit code 2
class SourceError(LumenError): ...          # exit code 1 (network, API)
class NoResultsError(LumenError): ...       # exit code 4
```

### User-Facing Errors

All exceptions are caught at the command boundary in `cli.py`. Error output:
1. A one-line summary of what failed (to stderr, in red if color enabled)
2. A cause sentence where inferable
3. A concrete fix suggestion (command to run, flag to check, URL to visit)
4. Exit with the appropriate code

Example pattern:
```python
except SourceError as e:
    console.print(f"[red]Error:[/red] {e.message}", err=True)
    console.print(f"{e.suggestion}", err=True)
    raise SystemExit(1)
```

### Automatic Retry

`BaseClient` retries on 429 and 503 with exponential backoff (1 s, 2 s, 4 s; max 3 attempts). After exhausting retries, raises `SourceError` with a message indicating the source name and a suggestion to try `--sources` with an alternative.

## Security Considerations

### Secret Management

- Credentials stored in `~/.config/lumen/config.toml` under `[credentials]`; file created with `0600` permissions via `lumen init`
- Credentials read at startup and injected into clients; never logged, never included in JSON output or error messages
- `LUMEN_` env vars are an alternative to the config file; take precedence

### Input Validation

- All CLI arguments validated by Typer/Pydantic before reaching client code
- Search queries are passed to APIs as-is (no shell injection risk since we use structured HTTP requests, not shell commands)
- File paths for `--output` are resolved and parent directories checked before writing

### Dependency Security

- `uv lock` pins all transitive dependencies for reproducible builds
- Dependabot or manual audit for CVE scanning before each release
- Google Scholar client deferred to v1.1; no scraping concerns in v1

## Decision Log

| Date | Decision | Rationale | Alternatives Considered |
|---|---|---|---|
| 2026-04-05 | Typer as CLI framework | Excellent `--help` generation, native Pydantic integration, shell completion support built-in | Click (lower-level, more boilerplate), argparse (stdlib but verbose) |
| 2026-04-05 | Rich for terminal output | Best-in-class tables, panels, progress bars, and color; integrates with Typer | Textual (overkill for CLI), termcolor (too limited) |
| 2026-04-05 | SQLite for cache | Zero-dependency local persistence; supports concurrent reads; easy to inspect and wipe | shelve (not queryable), Redis (external service), plain JSON files (no TTL) |
| 2026-04-05 | `asyncio.run()` per command | Keeps Typer's sync model simple; avoids running a persistent event loop; acceptable for CLI latency | Single shared event loop (complex lifecycle), trio (different ecosystem) |
| 2026-04-05 | Async strategy: `asyncio.run()` per command (Option A) | Typer is sync; wrapping async impl functions with `asyncio.run()` is explicit, testable, and zero-cost for a CLI. Event loop created and torn down per invocation. `httpx.AsyncClient` scoped inside each async impl via context manager. Enables `asyncio.gather()` for concurrent multi-source queries. | anyio + Typer async (experimental), sync client wrappers hiding async (prevents concurrent queries) |
| 2026-04-05 | Defer Google Scholar to v1.1 | Web scraping is inherently fragile and raises maintenance burden disproportionate to value at launch; arXiv + Semantic Scholar cover the core use case | Include as best-effort (sets wrong expectations), include fully (too brittle) |
| 2026-04-06 | Use `rapidfuzz` for fuzzy title matching | 10–20× faster than pure-Python Jaccard; `token_sort_ratio` handles word-order variation across sources (e.g. "Attention Is All You Need" vs. "Attention is All you Need") | `difflib.SequenceMatcher` (slower, no token sorting), exact match only (too brittle) |
| 2026-04-06 | Dedup match priority: DOI → arXiv ID → fuzzy+author | Exact identifiers are zero false-positive; fuzzy is a last resort gated by author overlap to prevent cross-paper collisions | Fuzzy-only (false positives on similarly-titled papers), ID-only (misses cross-source matches without shared IDs) |
| 2026-04-06 | Merge keeps richer author list, not winner-by-source | arXiv entries often have full author lists; SS may truncate; source-agnostic richness heuristic is more robust than a fixed source preference | Always prefer arXiv, always prefer SS |
| 2026-04-06 | Ranking `combined` weights: relevance 40%, citations 35%, date 25% | Balances recency and impact without letting high-citation classic papers dominate fresh results; weights tunable in a future config option | Equal weights (flattens signal), citation-only (biases to classics) |
| 2026-04-07 | Cache schema versioning via `meta` table | Single-table version check enables silent wipe on mismatch without user intervention; SQLite file stays self-describing | Version in filename (complicates path resolution), no versioning (silent corruption) |
