# Development Project Planning

**Project:** orbitr
**Status:** Planning
**Last Updated:** 2026-04-05

## Project Overview

### Software Description

- **Application Type:** CLI tool
- **Target Platform:** macOS and Linux (cross-platform)
- **Primary Language:** Python ≥ 3.10
- **Key Libraries/Frameworks:** Typer (CLI), Rich (terminal output), httpx (async HTTP), Pydantic (models), pyzotero (Zotero), feedparser (arXiv)

### Problem Statement

- Researchers, academics, and students lack a fast, composable, terminal-native way to search academic literature across multiple databases simultaneously.
- Existing tools either require a GUI (Zotero, Google Scholar), are locked to a single source (arXiv CLI tools), or are not designed for scripting and automation.
- `orbitr` fills this gap: a well-designed CLI that follows Unix conventions, supports piping and JSON output, and integrates directly with Zotero for reference management — all without leaving the terminal.

### Goals and Non-Goals

#### Goals

- [ ] Multi-source search (arXiv, Semantic Scholar) with intelligent deduplication and ranking
- [ ] Advanced field-specific queries (title, author, abstract, venue, date range) via a single `search` command
- [ ] Citation lookup, author search, and paper recommendations from seed titles
- [ ] Bibliography export to BibTeX, RIS, and CSL-JSON (from the terminal or piped results)
- [ ] Zotero library integration: add papers, create collections, list collections with automatic tagging
- [ ] Local result caching with TTL tiers for search, paper, and citation data
- [ ] Full Unix composability: stdout/stderr discipline, JSON output, pipe-friendly design
- [ ] Robust help system, informative errors with suggestions, and `orbitr doctor` diagnostics
- [ ] Shell completions for Zsh, Bash, and Fish
- [ ] `orbitr init` guided setup for credentials and defaults

#### Non-Goals

- No GUI or TUI — terminal output only
- No PDF download or full-text retrieval
- No built-in AI summarization or annotation (outside scope; handled upstream by calling tools)
- No support for databases beyond arXiv and Semantic Scholar in v1 (Google Scholar deferred to v1.1)
- No multi-user or server mode — single-user local tool only

## Architecture and Design

### High-Level Architecture

- **Pattern:** CLI pipeline — command tree dispatches to source clients, results flow through core processing (deduplication, ranking, caching), then to display layer
- **Data Flow:** User invokes command → config resolved → clients query source APIs concurrently → results deduplicated and ranked → rendered in requested format (table/list/detail/json)
- **Key Components:**
  - `cli.py` — Typer app, command registration, global flags
  - `commands/` — one module per command group (search, paper, cite, author, recommend, export, zotero, cache, init, doctor)
  - `clients/` — source-specific API clients (arXiv, Semantic Scholar; Google Scholar deferred to v1.1)
  - `core/` — models, deduplication, ranking, caching, export formatting
  - `zotero/` — Zotero Web API client and collection management
  - `display/` — Rich renderers for table, list, detail, and JSON output
  - `config.py` — layered config resolution (CLI flags > env vars > config file > defaults)

### External Dependencies

- **APIs and Services:** arXiv API (Atom feed), Semantic Scholar API (REST), Google Scholar (web scraping via BeautifulSoup), Zotero Web API
- **Data Sources:** Remote APIs only; local SQLite for cache
- **Build Tools:** `uv` for dependency management and packaging; `hatchling` build backend

### Technical Constraints

- Async HTTP throughout (`httpx`) to support concurrent multi-source queries
- Rate limiting respected per source: arXiv (3 req/s), Semantic Scholar (100 req/min with key), Google Scholar (conservative with delays)
- Retry with exponential backoff on 429/503; circuit-break per source so partial failures degrade gracefully
- `NO_COLOR` env var and `--no-color` flag honored throughout
- Config and cache follow XDG Base Directory spec (`~/.config/orbitr/`, `~/.cache/orbitr/`)
- Credentials file created with `0600` permissions

## Timeline and Milestones

### Phase 1: Architecture and Scaffolding (Weeks 1–2) — COMPLETE

- [x] Initialize repo with `pyproject.toml`, `flake.nix`, `.gitignore`
- [x] Set up Typer app skeleton with global flags (`--help`, `--version`, `--verbose`, `--quiet`, `--no-color`)
- [x] Implement config resolution layer (file, env vars, defaults)
- [x] Stub all command modules with `--help` strings and argument signatures
- [x] Write `orbitr init` and `orbitr doctor` skeletons

### Phase 2: Core Data Layer (Weeks 3–4) — COMPLETE

- [x] Define Pydantic models (`Paper`, `Author`, `SearchResult`)
- [x] Implement arXiv client (Atom feed parsing via feedparser)
- [x] Implement Semantic Scholar client (REST API, pagination)
- [—] ~~Google Scholar client~~ — deferred to v1.1
- [x] Implement deduplication (DOI, arXiv ID, fuzzy title matching)
- [x] Implement ranking (relevance, citations, date, combined, impact)
- [x] Implement SQLite cache with TTL tiers

### Phase 3: Command Implementation (Weeks 5–8) — COMPLETE

- [x] `orbitr search` — keyword + field filters, multi-source, dedup, rank
- [x] `orbitr paper` — fetch by ID from arXiv or Semantic Scholar
- [x] `orbitr cite` — citing papers via Semantic Scholar
- [x] `orbitr author` — author search across sources
- [x] `orbitr recommend` — content, citation, and hybrid methods via SS
- [x] `orbitr export` — BibTeX, RIS, CSL-JSON; stdin ndjson + `--query` paths
- [x] `orbitr query` — natural language to query syntax helper; `--run` flag
- [x] `orbitr zotero add/collections/new` — full Zotero integration
- [x] `orbitr cache stats/clean/clear` — thin wrappers over `core/cache.py`
- [x] `orbitr init` — full interactive credential setup (fixed + tested)
- [x] `orbitr doctor` — connectivity and config health checks (fixed + tested)

### Phase 4: Display and Polish (Weeks 9–10) — COMPLETE

- [x] Rich table renderer (truncated fields, color-coded) — complete in Phase 3
- [x] Rich list renderer (labeled blocks per paper) — complete in Phase 3
- [x] JSON serializer (newline-delimited, pipe-friendly) — complete in Phase 3
- [x] Detail renderer (full single-paper view, wrapped abstract) — complete in Phase 4
- [x] TTY auto-detection for default format switching (`effective_format()`) — complete in Phase 4
- [x] Pager integration (`$PAGER` via `console.pager(styles=True)`, `LUMEN_NO_PAGER`) — complete in Phase 4
- [x] Error message polish: dim suggestions, `LumenError` catch-alls, consistent "Unknown format" — complete in Phase 4

### Phase 5: Testing and Documentation (Weeks 11–12) — COMPLETE

- [x] Unit tests for core (deduplication, ranking, cache, export) — 343 tests total
- [x] Integration tests with mocked API responses
- [x] Shell completion generation documented (`--install-completion`, env-var fallback)
- [x] README finalized and `.env.example` verified
- [x] Smoke test script (`tests/smoke_test.sh`) for pre-release live-API validation
- [x] GitHub Actions CI pipeline (lint, typecheck, test 3.10–3.12, coverage, build, publish)

### Phase 6: Release (Week 13) — COMPLETE

- [x] `uv build` — wheel and sdist produced
- [x] Wheel install verified (`orbitr --version` returns `0.1.0`)
- [x] `CHANGELOG.md` written
- [x] Tag v0.1.0

## Resources and Requirements

### Development Environment

- Python 3.10+ via Nix flake or system install
- `uv` for dependency management (`uv sync`, `uv tool install .`)
- Nix flake for reproducible dev shell
- No local services required (SQLite cache is file-based)

### Infrastructure

- No hosting required — local CLI tool
- GitHub for version control and releases
- GitHub Actions for CI (lint, test, build)
- PyPI for distribution (optional; `uv tool install` from git is sufficient)

### Collaboration

- Solo project; no formal review process required
- Conventional commits for changelog generation

## Risk Assessment

### Technical Risks

- **Google Scholar scraping fragility** — deferred to v1.1; structure changes frequently and a brittle scraper raises maintenance burden disproportionate to value at launch
- **Rate limiting from Semantic Scholar without an API key** — mitigate with conservative defaults, cache, and clear error messages pointing to `orbitr init`
- **Async complexity in Typer** — Typer runs synchronously; mitigate by wrapping async client calls in `asyncio.run()` per command, or using a thin async runner utility

### Scope Risks

- Recommendation algorithm quality may invite scope creep (ML models, embeddings, etc.) — keep v1 to keyword/citation-based methods only
- Zotero integration covers the common cases; edge cases (group libraries, linked attachments) deferred to v2
- Google Scholar is intentionally best-effort and documented as such

## Success Metrics

### Functional Criteria

- [ ] All 11 commands implemented and passing integration tests
- [ ] Multi-source search returns deduplicated, ranked results
- [ ] Pipe chain `orbitr search ... --format json | orbitr export` works end-to-end
- [ ] Zotero add/collections/new functional with valid credentials

### Quality Criteria

- [ ] Unit test coverage ≥ 80% for `core/` modules
- [ ] All commands have `--help` text with usage example
- [ ] `orbitr doctor` catches missing credentials and unreachable services
- [ ] No unhandled exceptions surface to the user — all errors caught and formatted

### Adoption Criteria

- [ ] Installable with a single `uv tool install` command
- [ ] `orbitr init` completes setup in under 2 minutes for a new user
- [ ] Shell completions installable for Zsh, Bash, and Fish
