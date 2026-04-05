# Development Project Progress

**Project:** lumen
**Status:** Phase 1 complete
**Last Updated:** 2026-04-07

## Current Status Overview

### Development Phase

- **Current Phase:** Phase 3 — Command Implementation
- **Phase Progress:** Phase 2 100% complete
- **Overall Project Progress:** ~30% complete

### Recent Accomplishments

- README written and refined — 2026-04-05
- Project structure and command surface designed — 2026-04-05
- specs/ scaffolded with planning, progress, and implementation docs — 2026-04-05
- Phase 1 complete: git repo, pyproject.toml, uv.lock, Typer app skeleton with all global
  flags (`--version`, `--verbose`, `--quiet`, `--no-color`, `--config`), config resolution
  layer (XDG paths, TOML file, env vars, CLI flag merging, 0600 credential write), all 11
  command stubs with full `--help` strings and argument signatures, `lumen init` (interactive
  Rich prompts, writes config), `lumen doctor` (async connectivity checks), full package
  skeleton (`clients/`, `core/`, `display/`, `zotero/`), test scaffold — 2026-04-05
- Phase 2 session 1: `core/models.py` tested (15 tests); `clients/arxiv.py` implemented
  (`_parse_entry`, `search`, `get_by_id`); arXiv Atom fixtures saved to `tests/fixtures/`;
  15 arXiv client tests covering search, get_by_id, parse, retry, circuit-break;
  30 tests total, ruff clean — 2026-04-06
- Phase 2 session 2: `clients/semantic_scholar.py` implemented (search, get_by_id,
  get_citations, get_recommendations, _parse_paper); `core/deduplication.py` implemented
  (DOI, arXiv ID, fuzzy title + author overlap, metadata merge); `core/ranking.py`
  implemented (relevance, citations, date, impact, combined criteria); `core/cache.py`
  implemented (SQLite TTL cache, schema versioning, get/set/clean/clear/stats);
  SS fixtures saved; 80 new tests (15 SS, 24 dedup, 22 ranking, 19 cache);
  110 tests total, ruff clean — 2026-04-07

### Active Work

- [x] Pydantic models (`Paper`, `Author`, `SearchResult`) — tested (15 tests)
- [x] arXiv client (Atom feed via feedparser) — implemented and tested (15 tests)
- [x] Semantic Scholar client (REST API) — implemented and tested (15 tests)
- [x] Deduplication (DOI, arXiv ID, fuzzy title + author overlap) — implemented and tested (24 tests)
- [x] Ranking (relevance, citations, date, impact, combined) — implemented and tested (22 tests)
- [x] SQLite cache with TTL tiers — implemented and tested (19 tests)

## Milestone Tracking

### Completed Milestones

- [x] ~~README and project design~~ — 2026-04-05
- [x] ~~Phase 1: repo scaffolded, Typer skeleton, config layer~~ — 2026-04-05
- [x] ~~Phase 2: Core data layer — all clients, dedup, ranking, cache~~ — 2026-04-07

### Upcoming Milestones

- [x] ~~Phase 1 complete: repo scaffolded, Typer skeleton, config layer~~ — 2026-04-05
- [x] Phase 2 complete: all three API clients + dedup/ranking/cache — 2026-04-07 (ahead of schedule)
- [ ] Phase 3 complete: all 11 commands implemented — target 2026-05-26
- [ ] Phase 4 complete: display layer polished, errors finalized — target 2026-06-09
- [ ] v0.1.0 release — target 2026-06-23

### At-Risk Milestones

_None identified yet._

## Build and Test Status

### Build Health

- **Last Successful Build:** 2026-04-07 (`uv run pytest` — 110 tests, ruff clean)
- **Build Warnings:** None

### Test Results

- **Unit Tests:** 110 passing (15 models, 15 arXiv, 15 SS, 24 dedup, 22 ranking, 19 cache)
- **Integration Tests:** N/A
- **Test Coverage:** N/A

### Open Defects

- **Critical:** 0
- **High:** 0
- **Medium:** 0
- **Low:** 0

## Feature Progress

### Completed Features

- [x] `pyproject.toml` with Hatchling backend, all runtime and dev dependencies
- [x] `flake.nix` dev shell (Python 3.12, uv, ruff, pyright, git)
- [x] `src/lumen/` package skeleton: all modules and subpackages
- [x] `lumen.cli` — Typer app, global flags, command registration, entry point
- [x] `lumen.config` — layered config (XDG, TOML, env vars, CLI flags), `write_config` (0600)
- [x] `lumen.exceptions` — `LumenError` hierarchy with exit codes
- [x] `lumen._async` — `run()` utility for per-command async execution
- [x] `lumen.core.models` — `Paper`, `Author`, `SearchResult` Pydantic models
- [x] All 11 command stubs with full `--help` text and argument/option signatures
- [x] `lumen init` — interactive Rich prompts, writes config.toml
- [x] `lumen doctor` — async connectivity checks for arXiv, Semantic Scholar, Zotero
- [x] `clients/base.py` — abstract client with retry, backoff, circuit breaker skeleton
- [x] Stub skeletons for `clients/`, `core/`, `display/`, `zotero/`
- [x] `tests/conftest.py` with basic fixtures
- [x] ruff lint + format passing clean
- [x] `clients/arxiv.py` — Atom feed search + get_by_id, feedparser field mapping, ID normalisation
- [x] `clients/semantic_scholar.py` — REST search, get_by_id, citations, recommendations, API key support
- [x] `core/deduplication.py` — DOI/arXiv ID exact match + rapidfuzz fuzzy title + author overlap + metadata merge
- [x] `core/ranking.py` — relevance, citations, date, impact, combined criteria; TF-IDF relevance scorer
- [x] `core/cache.py` — SQLite TTL cache, 3 tiers, schema versioning, get/set/clean/clear/stats
- [x] `tests/fixtures/` — recorded arXiv XML and Semantic Scholar JSON responses for offline testing
- [x] 110 tests total (15 models, 15 arXiv, 15 SS, 24 dedup, 22 ranking, 19 cache), ruff clean

### In Progress

_None — beginning Phase 3._

### Planned

- [ ] `lumen search` — Phase 3
- [ ] `lumen paper` — Phase 3
- [ ] `lumen cite` — Phase 3
- [ ] `lumen author` — Phase 3
- [ ] `lumen recommend` — Phase 3
- [ ] `lumen export` — Phase 3
- [ ] `lumen query` — Phase 3
- [ ] `lumen zotero add/collections/new` — Phase 3
- [ ] `lumen cache stats/clean/clear` — Phase 3
- [ ] `lumen init` — Phase 3
- [ ] `lumen doctor` — Phase 3
- [ ] Rich display layer (table, list, detail, JSON) — Phase 4
- [ ] Shell completions (Zsh, Bash, Fish) — Phase 4

### Deferred or Cut

_Nothing deferred yet._

## Technical Debt

### Known Debt

- `test_cache.py` imports `_TTL` and `CacheStats` that are unused (ruff auto-fixed); no functional debt
- SS `get_recommendations` fixture returned 0 results (API behaviour without key); test only asserts type, not content
- No test coverage measurement yet — `pytest-cov` not yet run against Phase 2 modules

## Dependency Status

### External Dependencies

| Package | Version | Status |
|---|---|---|
| `typer` | latest stable | ✓ installed |
| `rich` | latest stable | ✓ installed |
| `httpx` | latest stable | ✓ installed |
| `pydantic` | ≥ 2.0 | ✓ installed |
| `feedparser` | latest stable | ✓ installed |
| `rapidfuzz` | latest stable | ✓ installed |
| `pyzotero` | latest stable | ✓ installed (unused until Phase 3) |
| `python-dateutil` | latest stable | ✓ installed |
| `beautifulsoup4` | latest stable | ✓ installed (unused until Phase 3) |
| `python-dotenv` | latest stable | ✓ installed |

## Challenges and Blockers

### Current Blockers

_None._

### Resolved Challenges

_None yet._

### Lessons Learned

- Google Scholar client should be designed as best-effort from the start to avoid over-engineering a fragile scraper

## Next Steps

### Immediate Actions (Next 2 Weeks)

- [ ] Implement `lumen search` — wire arXiv + SS clients, dedup, rank, cache, display
- [ ] Implement `lumen paper` — fetch by arXiv/SS ID
- [ ] Implement `lumen cite` — SS citations endpoint
- [ ] Implement `lumen cache stats/clean/clear` — thin wrappers over `core/cache.py`
- [ ] Add CLI integration tests (Typer `CliRunner`) for each implemented command

### Medium-term Goals (Next Month)

- [ ] All 11 commands implemented and passing integration tests
- [ ] `lumen search` end-to-end with multi-source dedup + ranking verified
- [ ] `lumen export` producing valid BibTeX and RIS output
- [ ] `lumen zotero add` functional with real credentials

### Decisions Needed

- ~~**Async strategy in Typer:**~~ resolved — Option A (`asyncio.run()` per command, `asyncio.gather()` across sources inside async impl); see implementation.md decision log
- ~~**Google Scholar inclusion in v1:**~~ resolved — deferred to v1.1

## Release Planning

### Next Release

- **Version:** 0.1.0
- **Target Date:** 2026-06-23
- **Included Features:** All 11 commands, three sources, Zotero integration, caching, shell completions, `lumen init`, `lumen doctor`
- **Release Blockers:** Everything — not yet started

### Release History

| Version | Date | Key Changes |
|---|---|---|
| — | — | — |
