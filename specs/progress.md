# Development Project Progress

**Project:** lumen
**Status:** v0.1.0 released
**Last Updated:** 2026-04-06

## Current Status Overview

### Development Phase

- **Current Phase:** Released — v0.1.0
- **Phase Progress:** All 6 phases complete
- **Overall Project Progress:** 100% (v0.1.0)

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
- Phase 3 session 1: `core/query.py` added (field-filter parsing, per-source query
  builders, year-range helpers, cache-key utility); `display/` layer implemented
  (`json_fmt.py` ndjson, `table.py` Rich Table, `list.py` Rich Panels, `__init__.py`
  unified `render()` dispatcher); `commands/search.py` fully wired — concurrent
  async gather across arXiv + SS, cache read/write, dedup, rank, display, full
  error handling; 25 new integration tests covering all branches;
  135 tests total, ruff clean — 2026-04-05
- Phase 3 session 2: `commands/cache.py` wired (`stats/clean/clear` as Typer
  subcommands with Rich Table output and confirmation prompt); `commands/paper.py`
  implemented (`_detect_id_type`, `_normalize_for_ss`, arXiv and SS path, cache
  tier `paper`, `fetch_paper` extracted as shared async helper); `commands/cite.py`
  implemented (SS `get_citations`, cache tier `citations`); 34 new tests (10 unit
  + 24 CLI integration); 184 tests total, ruff clean — 2026-04-05
- Phase 3 session 3: `clients/semantic_scholar.py` extended with
  `search_authors(name, limit)` (two-step: author search → author papers);
  `core/export.py` implemented (`to_bibtex`, `to_ris`, `to_csl_json`; 25 unit
  tests); `commands/recommend.py` wired (SS recommendations, cache tier `search`,
  `--method` validation; 9 tests); `commands/author.py` wired (author search via
  new SS method, same error/display pattern; 9 tests); `commands/export.py`
  implemented (stdin ndjson path + `--query` search path, `--output` file,
  BibTeX/RIS/CSL-JSON; 8 tests); `commands/init.py` and `commands/doctor.py`
  fixed (no longer re-call `load_config()`; now use `ctx.obj.config`) and
  fully tested (8 + 13 tests respectively); 70 new tests; 254 total, ruff clean — 2026-04-05
- Phase 3 session 4 (complete): `commands/query.py` implemented
  (`_parse_natural`, `_build_command`, `--run` via `ctx.invoke`; 16 tests);
  `zotero/client.py` fully implemented (`add_paper`, `list_collections`,
  `create_collection`, `find_collection_key`); `commands/zotero.py` wired
  (`add`, `collections`, `new` subcommands; collection name resolution,
  tag building, Rich table and json output; 18 tests); `commands/paper.py`
  refactored to expose `fetch_paper()` shared helper used by zotero add;
  34 new tests; 288 tests total, ruff clean — Phase 3 complete — 2026-04-05

### Active Work

- [x] Pydantic models (`Paper`, `Author`, `SearchResult`) — tested (15 tests)
- [x] arXiv client (Atom feed via feedparser) — implemented and tested (15 tests)
- [x] Semantic Scholar client (REST API) — implemented and tested (15 tests)
- [x] Deduplication (DOI, arXiv ID, fuzzy title + author overlap) — implemented and tested (24 tests)
- [x] Ranking (relevance, citations, date, impact, combined) — implemented and tested (22 tests)
- [x] SQLite cache with TTL tiers — implemented and tested (19 tests)
- [x] `core/query.py` — field-filter parsing, per-source query builders, cache key (phase 3)
- [x] `display/` layer — `json_fmt`, `table`, `list`, unified `render()` dispatcher (phase 3)
- [x] `lumen search` — full pipeline: concurrent fetch, cache, dedup, rank, display (phase 3)
- [x] `lumen paper` — `_detect_id_type`, `_normalize_for_ss`, cache tier `paper` (phase 3)
- [x] `lumen cite` — SS `get_citations`, cache tier `citations` (phase 3)
- [x] `lumen cache stats/clean/clear` — thin wrappers over `core/cache.py` (phase 3)
- [x] `lumen recommend` — SS recommendations, `--method` validation, cache (phase 3)
- [x] `lumen author` — SS `search_authors` two-step, cache (phase 3)
- [x] `core/export.py` — `to_bibtex`, `to_ris`, `to_csl_json` (phase 3)
- [x] `lumen export` — stdin ndjson + `--query` paths, `--output` file (phase 3)
- [x] `lumen init` — fixed + fully tested (phase 3)
- [x] `lumen doctor` — fixed + fully tested (phase 3)
- [x] `lumen query` — `_parse_natural`, `_build_command`, `--run` (phase 3)
- [x] `zotero/client.py` — `add_paper`, `list_collections`, `create_collection`, `find_collection_key` (phase 3)
- [x] `lumen zotero add/collections/new` — full Zotero integration (phase 3)

## Milestone Tracking

### Completed Milestones

- [x] ~~README and project design~~ — 2026-04-05
- [x] ~~Phase 1: repo scaffolded, Typer skeleton, config layer~~ — 2026-04-05
- [x] ~~Phase 2: Core data layer — all clients, dedup, ranking, cache~~ — 2026-04-07
- [x] ~~Phase 3 session 1: `lumen search` implemented~~ — 2026-04-05
- [x] ~~Phase 3 complete: all 11 commands implemented~~ — 2026-04-05

### Upcoming Milestones

- [x] ~~Phase 1 complete: repo scaffolded, Typer skeleton, config layer~~ — 2026-04-05
- [x] ~~Phase 2 complete: all three API clients + dedup/ranking/cache~~ — 2026-04-07
- [x] ~~Phase 3 complete: all 11 commands implemented~~ — 2026-04-05
- [ ] Phase 4 complete: display layer polished, errors finalized — target 2026-06-09
- [ ] Phase 4 complete: display layer polished, errors finalized — target 2026-06-09
- [ ] v0.1.0 release — target 2026-06-23

### At-Risk Milestones

_None identified yet._

## Build and Test Status

### Build Health

- **Last Successful Build:** 2026-04-05 (`uv run pytest` — 288 tests, ruff clean)
- **Build Warnings:** None

### Test Results

- **Unit Tests:** 288 passing (15 models, 15 arXiv, 15 SS, 24 dedup, 22 ranking, 19 cache, 25 search, 15 cache-cmd, 10 paper-unit + CLI, 9 recommend, 9 author, 25 export-core, 8 export-cmd, 8 init, 13 doctor, 16 query, 18 zotero)
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
- [x] `core/query.py` — `parse_query`, `build_arxiv_query`, `build_ss_query`, `ss_year_param`, `in_year_range`, `cache_key`
- [x] `display/json_fmt.py` — ndjson serialiser via `Paper.model_dump_json()`
- [x] `display/table.py` — Rich Table with #, Title, Authors, Year, Source, Cites columns
- [x] `display/list.py` — Rich Panel per paper (meta line + abstract snippet + URL)
- [x] `display/__init__.py` — unified `render()` dispatcher (table/list/detail/json)
- [x] `commands/search.py` — full async pipeline; 25 integration tests
- [x] `commands/cache.py` — `stats/clean/clear` subcommands; Rich Table for stats; confirmation prompt; 15 CLI tests
- [x] `commands/paper.py` — `_detect_id_type`, `_normalize_for_ss`, arXiv + SS dispatch, cache tier `paper`; `fetch_paper()` shared helper; full test suite
- [x] `commands/cite.py` — SS `get_citations`, cache tier `citations`, consistent error handling; CLI tests
- [x] `clients/semantic_scholar.py` — extended with `search_authors(name, limit)` two-step method
- [x] `core/export.py` — `to_bibtex` (`_bibtex_key`, author joining, field escaping), `to_ris`, `to_csl_json`; 25 unit tests
- [x] `commands/recommend.py` — SS recommendations, `--method` (content/citation/hybrid), cache; 9 tests
- [x] `commands/author.py` — SS author search via `search_authors`, same error/display pattern; 9 tests
- [x] `commands/export.py` — stdin ndjson + `--query` paths, `--output` file, BibTeX/RIS/CSL-JSON dispatch; 8 tests
- [x] `commands/init.py` — fixed (`ctx.obj.config`), 8 tests
- [x] `commands/doctor.py` — fixed (`ctx.obj.config`), 13 tests
- [x] `commands/query.py` — `_parse_natural` heuristic, `_build_command`, `--run` via `ctx.invoke`; 16 tests
- [x] `zotero/client.py` — `add_paper`, `list_collections`, `create_collection`, `find_collection_key` (case-insensitive)
- [x] `commands/zotero.py` — `add/collections/new` subcommands; collection name resolution; tag building; 18 tests
- [x] 288 tests total, ruff clean

### In Progress

_Nothing in progress — Phase 3 complete, Phase 4 starting._

### Planned

- [ ] `display/detail.py` — full single-paper Rich layout (Phase 4)
- [ ] TTY auto-detection for default `--format` (Phase 4)
- [ ] Pager integration (`$PAGER`, disable with `LUMEN_NO_PAGER`) (Phase 4)
- [ ] Error message polish across all commands (Phase 4)
- [ ] Shell completions for Zsh, Bash, Fish (Phase 4)

### Deferred or Cut

_Nothing deferred yet._

## Technical Debt

### Known Debt

- `test_cache.py` imports `_TTL` and `CacheStats` that are unused (ruff auto-fixed); no functional debt
- SS `get_recommendations` fixture returned 0 results (API behaviour without key); test only asserts type, not content
- No test coverage measurement yet — `pytest-cov` not yet run against Phase 2 or Phase 3 modules
- `display/detail.py` still a stub — falls back to `render_list` for now; proper full-paper view deferred to Phase 4
- TTY auto-detection for default `--format` not yet implemented — always uses config default (`table`)
- `lumen query --run` depends on `ctx.invoke`; integration test uses mocked search — live `--run` path not covered
- Pager integration not yet implemented — long result sets truncate at terminal height
- `lumen export` stdin detection may behave unexpectedly in non-TTY CI environments — documented in test skip

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

- [ ] Generate shell completions for Zsh, Bash, Fish via Typer and test manually
- [ ] Finalize README with usage examples for all 11 commands
- [ ] Write end-to-end smoke tests hitting live APIs (run manually pre-release)
- [ ] Set up GitHub Actions CI (lint, typecheck, test, build stages)

### Medium-term Goals (Next Month)

- [ ] Prepare `v0.1.0` release: update `pyproject.toml` version, `CHANGELOG.md`
- [ ] `uv build` and test install from wheel
- [ ] Publish to PyPI or document `uv tool install` from git

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
