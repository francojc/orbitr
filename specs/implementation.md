# Development Implementation Details

**Project:** lumen
**Status:** Phase 3 complete — Phase 4 starting
**Last Updated:** 2026-04-06

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
│       │   ├── query.py         # field:value parsing, per-source query builders, cache key
│       │   └── export.py        # BibTeX, RIS, CSL-JSON formatters (Phase 3)
│       ├── zotero/
│       │   └── client.py        # pyzotero wrapper; add, collections, new (Phase 3)
│       └── display/
│           ├── __init__.py      # render() dispatcher — table/list/detail/json
│           ├── table.py         # Rich Table renderer (Phase 3 — functional)
│           ├── list.py          # Rich Panel/group renderer (Phase 3 — functional)
│           ├── detail.py        # Full single-paper Rich layout (Phase 4 — stub)
│           └── json_fmt.py      # ndjson serialiser (Phase 3 — complete)
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
    ├── test_cache.py                # Cache get/set/clean/clear/stats (19 tests)
    ├── test_search.py               # lumen search CLI integration (25 tests)
    ├── test_cache_cmd.py            # lumen cache CLI integration (15 tests)
    ├── test_paper.py                # lumen paper unit + CLI integration
    ├── test_recommend.py            # lumen recommend CLI integration (9 tests)
    ├── test_author.py               # lumen author CLI integration (9 tests)
    ├── test_export.py               # core/export unit (25) + lumen export CLI (8)
    ├── test_init.py                 # lumen init CLI integration (8 tests)
    ├── test_doctor.py               # lumen doctor CLI integration (13 tests)
    ├── test_query.py                # lumen query unit + CLI integration (16 tests)
    └── test_zotero.py               # lumen zotero CLI integration (18 tests)
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

8. **`core/query.py`** *(Phase 3 — complete)*
   - **Purpose:** Translates user-facing query strings and CLI flags into per-source API query strings; computes stable cache keys
   - **Public Interface:** `parse_query(raw) -> (base, filters)`, `build_arxiv_query(...)`, `build_ss_query(...)`, `ss_year_param(from, to)`, `in_year_range(year, from, to)`, `cache_key(source, query, limit, sort, year_from, year_to)`
   - **Field syntax:** `field:value` or `field:"quoted value"` for `title`, `author`, `venue`, `abstract`; parsed by `_FIELD_RE` regex
   - **arXiv translation:** `title:` → `ti:`, `author:` → `au:`, `abstract:` → `abs:`, `venue:` → `jr:`; joined with ` AND `
   - **SS translation:** all fields folded into plain keyword string (SS API has no structured field queries)
   - **Cache key:** SHA-256 hex digest of `source|query|limit|sort|year_from|year_to`, prefixed `search:{source}:`
   - **Dependencies:** `hashlib`, `re` (stdlib only)

9. **`display/__init__.py`** *(Phase 3 — complete)*
   - **Purpose:** Unified `render()` dispatcher; routes to the appropriate renderer based on the format string
   - **Public Interface:** `render(papers, fmt, *, console, file)` where `fmt` is `"table"`, `"list"`, `"detail"`, or `"json"`
   - **Note:** `"detail"` falls back to `render_list` until Phase 4

10. **`display/table.py`** *(Phase 3 — functional)*
    - **Purpose:** Renders a `list[Paper]` as a Rich Table with truncated fields
    - **Columns:** `#` (3 chars, dim), `Title` (max 52 chars + `…`), `Authors` (first surname + et al. count), `Year`, `Source` (arXiv / Sem. Scholar labels), `Cites`
    - **Public Interface:** `render_table(papers, console=None) -> None`

11. **`display/list.py`** *(Phase 3 — functional)*
    - **Purpose:** Renders a `list[Paper]` as one Rich Panel per paper
    - **Panel content:** meta line (authors · venue · year · source · cites) + abstract snippet (≤ 200 chars) + URL
    - **Public Interface:** `render_list(papers, console=None) -> None`

12. **`display/json_fmt.py`** *(Phase 3 — complete)*
    - **Purpose:** Writes papers as newline-delimited JSON (ndjson) for piping to `jq` or `lumen export`
    - **Serialisation:** `Paper.model_dump_json()` — one JSON object per line, no wrapper array
    - **Public Interface:** `render_json(papers, file=None) -> None`

13. **`commands/search.py`** *(Phase 3 — complete)*
    - **Purpose:** Implements `lumen search`; orchestrates the full query pipeline
    - **Typer command:** `search(ctx, query, sources, limit, title, author, venue, year_from, year_to, sort, fmt, no_cache)`
    - **Async inner function:** `_search_async(...)` called via `_async.run()`; `_fetch_source(...)` handles per-source cache + client call
    - **Pipeline:** `parse_query` → `build_*_query` per source → `asyncio.gather(_fetch_source(...))` → year post-filter → `deduplicate` → `rank` → `render`
    - **Degradation:** per-source `SourceError` is caught and logged; re-raises only if *all* sources fail
    - **Exit codes:** 0 success, 1 source error, 2 usage/validation error, 4 no results
    - **Dependencies:** all clients, `core/query.py`, `core/cache.py`, `core/deduplication.py`, `core/ranking.py`, `display/`

13. **`commands/cache.py`** *(Phase 3 — complete)*
    - **Purpose:** Implements `lumen cache stats/clean/clear` as Typer subcommands
    - **`stats`:** renders a Rich Table of entries per tier, total count, db path, and file size
    - **`clean`:** removes expired entries; accepts optional `--tier` filter; reports count removed
    - **`clear`:** removes all entries with `--yes` bypass or interactive confirmation prompt; tier-specific or full
    - **Validation:** invalid tier name → `UsageError` → exit 2
    - **Dependencies:** `core/cache.py`

14. **`commands/paper.py`** *(Phase 3 — complete)*
    - **Purpose:** Implements `lumen paper <id>` — fetch a single paper by any recognized ID format
    - **`_detect_id_type(id)`:** classifies IDs as `arxiv` (bare, versioned, URL, `arXiv:` prefix), `doi` (bare, `doi.org` URL, `DOI:` prefix), `semantic_scholar` (40-char hex), or `unknown`
    - **`_normalize_for_ss(id, id_type)`:** builds SS-compatible `ARXIV:`, `DOI:`, or bare SS ID strings
    - **Routing:** arXiv IDs → `ArxivClient.get_by_id()`; all others → `SemanticScholarClient.get_by_id()`
    - **`fetch_paper(id, config, cache)`:** shared async helper (returns `Paper` without rendering); used by `lumen zotero add`
    - **Cache:** tier `paper`; key `paper:{source}:{id}`
    - **Dependencies:** both clients, `core/cache.py`, `display/`

15. **`commands/recommend.py`** *(Phase 3 — complete)*
    - **Purpose:** Implements `lumen recommend <id>` — content-based or citation-based recommendations
    - **`--method`:** `content`, `citation`, or `hybrid`; all currently route to SS `get_recommendations()` (method distinctions reserved for v1.1 with ML embeddings)
    - **ID handling:** reuses `_detect_id_type` / `_normalize_for_ss` from `commands/paper`
    - **Cache:** tier `search`; cache key incorporates method and limit
    - **Dependencies:** `clients/semantic_scholar.py`, `core/cache.py`, `display/`

16. **`commands/author.py`** *(Phase 3 — complete)*
    - **Purpose:** Implements `lumen author <name>` — find papers by an author
    - **Pipeline:** `SemanticScholarClient.search_authors(name, limit)` → rank → render
    - **Cache:** tier `search`; key `author:{name}:{limit}`
    - **Error handling:** same pattern as `lumen cite` (SourceError → exit 1, NoResultsError → exit 4)
    - **Dependencies:** `clients/semantic_scholar.py`, `core/ranking.py`, `core/cache.py`, `display/`

17. **`core/export.py`** *(Phase 3 — complete)*
    - **Purpose:** Bibliography formatters converting `list[Paper]` to BibTeX, RIS, and CSL-JSON strings
    - **`to_bibtex(papers)`:** `@article` entries; `_bibtex_key()` generates `SurnameYear` key; authors joined with ` and `; brace-escapes `{}` and backslashes
    - **`to_ris(papers)`:** `TY`, `TI`, `AU` (one per author), `PY`, `JO`, `DO`, `UR`, `AB`, `ER` records per paper
    - **`to_csl_json(papers)`:** JSON array; author objects with `given`/`family` split; `issued` with `date-parts`; `container-title` from venue; `DOI`, `URL`
    - **Dependencies:** `core/models.py`, `json` (stdlib)

18. **`commands/export.py`** *(Phase 3 — complete)*
    - **Purpose:** Implements `lumen export` — convert papers to bibliography format
    - **Stdin path:** reads ndjson lines from stdin (piped from `lumen search --format json`); parses with `Paper.model_validate_json()`
    - **`--query` path:** runs concurrent arXiv + SS search (same pipeline as `lumen search`), deduplicates, then formats
    - **`--output`:** writes to file; defaults to stdout
    - **Format dispatch:** `bibtex` → `to_bibtex`; `ris` → `to_ris`; `csl-json` → `to_csl_json`
    - **Exit codes:** 2 on invalid format or non-TTY stdin with no data; 4 on empty result set

19. **`commands/query.py`** *(Phase 3 — complete)*
    - **Purpose:** Implements `lumen query <natural-language>` — heuristic NL-to-query-syntax helper
    - **`_parse_natural(text)`:** extracts 4-digit year, author surname (capitalized token immediately before year, filtered against stop words), and remaining tokens as keyword terms (stop words removed)
    - **`_build_command(parsed)`:** renders a `lumen search ...` command string with flags for each extracted field
    - **`--run`:** invokes `search` command in-process via `ctx.invoke` with parsed kwargs; prints command first
    - **Dependencies:** `commands/search.py` (for `--run`), `re` (stdlib)

20. **`zotero/client.py`** *(Phase 3 — complete)*
    - **Purpose:** `pyzotero` wrapper for Zotero Web API operations
    - **`add_paper(paper, collection_key, tags)`:** builds a `journalArticle` item template; populates creators, tags, and optional collection; calls `zot.create_items()`; returns item key
    - **`list_collections()`:** returns all top-level and nested collections as list of `{key, name, parentKey}` dicts
    - **`create_collection(name, parent_key)`:** creates a new collection; returns new collection key
    - **`find_collection_key(name)`:** case-insensitive name lookup across all collections; returns key or `None`
    - **Auth:** `library_id`, `library_type`, `api_key` read from `Config.credentials`; `ConfigError` raised if absent
    - **Dependencies:** `pyzotero`, `core/models.py`

21. **`commands/zotero.py`** *(Phase 3 — complete)*
    - **Purpose:** Implements `lumen zotero add/collections/new` subcommands
    - **`add <id>`:** fetches paper via `fetch_paper()`, resolves optional `--collection` by name, builds tag list from categories + `--tags`, calls `ZoteroClient.add_paper()`; reports item key
    - **`collections`:** lists all Zotero collections as Rich table (`key`, `name`, `parent`) or json
    - **`new <name>`:** optional `--parent` (resolved by name via `find_collection_key`); calls `create_collection()`; reports new key
    - **ConfigError** (missing credentials) → exit 3 throughout
    - **Dependencies:** `zotero/client.py`, `commands/paper.py` (`fetch_paper`), `display/`

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
