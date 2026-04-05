# Development Implementation Details

**Project:** lumen
**Status:** Planning
**Last Updated:** 2026-04-05

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
    ├── fixtures/            # Recorded API responses for mocking
    ├── test_search.py
    ├── test_paper.py
    ├── test_deduplication.py
    ├── test_ranking.py
    ├── test_cache.py
    ├── test_export.py
    └── test_zotero.py
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

4. **`core/deduplication.py`**
   - **Purpose:** Merges result sets from multiple sources; removes duplicates by exact DOI, exact arXiv ID, then fuzzy title + author overlap (≥ 85% similarity threshold)
   - **Public Interface:** `deduplicate(papers: list[Paper], threshold=0.85) -> list[Paper]`
   - **Dependencies:** `core/models.py`; optional `rapidfuzz` for fast string similarity

5. **`core/ranking.py`**
   - **Purpose:** Scores and sorts papers by one of: `relevance` (TF-IDF query match), `citations` (log-scaled count), `date` (recency), `impact` (citations × recency), `combined` (weighted composite)
   - **Public Interface:** `rank(papers, criterion, query=None) -> list[Paper]`
   - **Dependencies:** `core/models.py`

6. **`core/cache.py`**
   - **Purpose:** SQLite-backed TTL cache with three independent tiers (search: 1 h, paper: 24 h, citations: 6 h); keyed by normalized query + source hash
   - **Public Interface:** `Cache`, `get(key) -> T | None`, `set(key, value, tier)`, `stats() -> CacheStats`, `clean()`, `clear()`
   - **Dependencies:** `sqlite3` (stdlib)

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
