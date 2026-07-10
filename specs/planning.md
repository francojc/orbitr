# Development Project Planning

**Project:** orbitr
**Status:** v0.4.0 release hardening (v0.3.0 shipped)
**Last Updated:** 2026-07-10

## Project Overview

### Software Description

- **Application Type:** CLI tool
- **Target Platform:** macOS and Linux (cross-platform)
- **Primary Language:** Python >= 3.10
- **Key Libraries/Frameworks:** Typer (CLI), Rich (terminal output), httpx (async HTTP), Pydantic (models), pyzotero (Zotero), feedparser (arXiv)

### Problem Statement

- Researchers, academics, and students need a fast, composable terminal workflow for literature discovery and reference management.
- Existing tools are often GUI-first, source-limited, or weak for automation.
- `orbitr` provides multi-source search, ranking, export, and Zotero integration with Unix-friendly JSON and piping.

### Goals and Non-Goals

#### Goals

- [x] Multi-source search (arXiv, Semantic Scholar) with intelligent deduplication and ranking
- [x] Advanced field-specific queries (title, author, abstract, venue, date range) via a single `search` command
- [x] Citation lookup, author search, and paper recommendations from seed titles
- [x] Bibliography export to BibTeX, RIS, and CSL-JSON
- [x] Zotero library integration: add papers, create/list collections, browse/search items, export items as markdown
- [x] Local result caching with TTL tiers for search, paper, and citation data
- [x] Full Unix composability: stdout/stderr discipline, JSON output, pipe-friendly design
- [x] Robust help system, informative errors with suggestions, and `orbitr doctor` diagnostics
- [x] Shell completions for Zsh, Bash, and Fish
- [x] `orbitr init` guided setup for credentials and defaults
- [ ] Karakeep API integration for personal bookmark search (read-only in v0.4)

#### Non-Goals

- No GUI or TUI - terminal output only
- No PDF download or full-text retrieval
- No built-in AI summarization or annotation
- No Zotero group library support in v1/v0.2
- No PDF text extraction or full-text indexing
- No custom Jinja templates for `zotero export-md` in v0.2
- No support for databases beyond arXiv and Semantic Scholar in v0.2 (Google Scholar deferred)
- No Karakeep write/upload/sync operations in v0.4 (read-only search)
- No multi-user or server mode

## Timeline and Milestones

### Phase 1: Architecture and Scaffolding - COMPLETE

- [x] Initialize repo and packaging scaffold
- [x] Typer skeleton with global flags
- [x] Config resolution layer
- [x] Command stubs
- [x] `orbitr init` and `orbitr doctor` skeletons

### Phase 2: Core Data Layer - COMPLETE

- [x] Pydantic models (`Paper`, `Author`, `SearchResult`)
- [x] arXiv client
- [x] Semantic Scholar client
- [x] Deduplication and ranking
- [x] SQLite cache with TTL tiers
- [ ] Google Scholar client (deferred)

### Phase 3: Command Implementation - COMPLETE

- [x] `search`, `paper`, `cite`, `author`, `recommend`
- [x] `export`, `query`, `cache`, `init`, `doctor`
- [x] `zotero add/collections/new`

### Phase 4: Display and Polish - COMPLETE

- [x] Table/list/detail/json renderers
- [x] TTY format auto-selection
- [x] Pager integration
- [x] Error polish and consistency

### Phase 5: Testing and Documentation - COMPLETE

- [x] Expanded unit/integration tests
- [x] CI pipeline
- [x] README and setup docs
- [x] Smoke test script

### Phase 6: Initial Release - COMPLETE

- [x] Build artifacts verified
- [x] v0.1.x release/tag complete

### Phase 7: Zotero Library Enhancements - COMPLETE

- [x] `ZoteroClient.list_items()`
- [x] `ZoteroClient.get_item()`
- [x] `ZoteroClient.search_items()`
- [x] `orbitr zotero list`
- [x] `orbitr zotero get <item_key>`
- [x] `orbitr zotero search <query>`
- [x] `orbitr zotero export-md <item_key>`
- [x] `--format keys` support on list/search
- [x] Tests for new client methods and subcommands
- [x] v0.2.0 release and tag

### Phase 8: v0.3.0 Planning and Reliability - COMPLETE

#### Milestone 8.1 - Scope and acceptance criteria (target: 2026-04-24; delivered 2026-04-17)

- [x] Define v0.3.0 feature scope (must-have: `zotero recent`, docs guardrail, coverage gate)
- [x] Define acceptance criteria per feature
- [x] Publish milestone issue list (captured in CHANGELOG and commits)
- [x] Decide Zotero UX for recently added entries:
  - [x] Evaluate `zotero search --recent-*` extension vs dedicated `zotero recent`
  - [x] Preferred direction: keep `search` query-driven and add `zotero recent` as a browse workflow
  - [x] Define flags (`--days`, `--since`, `--collection`, `--limit`, `--format`) and output contracts
- [x] Define docs consistency guardrail policy:
  - [x] `specs/planning.md` and `specs/progress.md` must be updated in same PR for milestone/status changes
  - [x] Add CI check that fails on inconsistent project status/version/phase fields
- [ ] Define API reliability posture for v0.3:
  - [x] Confirm whether `doctor` gets a deep mode (`doctor --deep`) with lightweight real queries and response-shape checks — deferred to Phase 9
  - [ ] Require graceful `SourceError` wrapping and actionable suggestions for all network/API failures, including Zotero client calls — moved to Phase 9

#### Milestone 8.2 - Coverage baseline and CI gate (target: 2026-05-01; delivered 2026-05-08)

- [x] Add `pytest-cov` config and baseline coverage report
- [x] Add minimum coverage threshold in CI (80%)
- [x] Document local coverage workflow in README/justfile

#### Milestone 8.3 - API reliability and Google Scholar feasibility (target: 2026-05-15; partially delivered)

- [x] Implement reliability baseline for user-facing API failures:
  - [x] Ensure query/search command paths exit gracefully with clear message and fix suggestion
  - [ ] Add Zotero client exception mapping to `SourceError` to avoid raw traceback leaks — moved to Phase 9
  - [ ] Add tests for network timeouts, 401/403, and transient 5xx failures across supported sources — moved to Phase 9
- [ ] Evaluate enhanced health checks:
  - [ ] Add optional `doctor --deep` mode with lightweight per-source semantic checks — moved to Phase 9
  - [x] Keep default `doctor` fast and low-cost
- [ ] Prototype Google Scholar best-effort client behind feature flag — moved to Phase 9
- [ ] Add fixture-driven tests for parser stability — moved to Phase 9
- [ ] Decide ship/defer based on reliability criteria — moved to Phase 9

#### Milestone 8.4 - Documentation and status operations (target: 2026-05-22; partially delivered)

- [ ] Keep `specs/planning.md` and `specs/progress.md` synchronized weekly — cadence broken after 2026-04-17; restarted 2026-07-09
- [ ] Reintroduce `logs/` weekly and session status cadence — broken after 2026-W16; restarted 2026-07-09
- [x] Add release checklist updates for post-v0.2 workflow
- [x] Implement docs consistency guardrail in CI:
  - [x] Add script/check to validate phase, status, and current version alignment between planning and progress docs
  - [x] Fail CI on drift and print a fix hint

### Phase 9: Reliability Hardening and v1.1 Exploration - ACTIVE

#### Milestone 9.1 - Zotero/API reliability polish (target: 2026-07-23)

- [ ] Map pyzotero/network failures in `ZoteroClient` to `SourceError` with actionable suggestions
- [ ] Add tests for Zotero API timeouts, 401/403, and transient failures
- [ ] Audit `doctor` output; decide on and optionally implement `doctor --deep` semantic checks

#### Milestone 9.2 - Google Scholar v1.1 feasibility (target: 2026-08-06)

- [ ] Prototype best-effort Google Scholar client behind feature flag
- [ ] Add fixture-driven parser tests
- [ ] Decide ship/defer based on reliability criteria

#### Milestone 9.3 - Operational cadence reset (target: 2026-07-23)

- [ ] Resume weekly logs under `logs/weekly/`
- [ ] Update release checklist for post-v0.3 workflow
- [ ] Keep planning/progress/docs consistency check passing weekly

#### Milestone 9.4 - v0.4.0 scope definition (target: 2026-08-13)

- [ ] Define v0.4.0/v1.1 feature scope (must-have / should-have / defer)
- [ ] Define acceptance criteria per feature
- [ ] Publish milestone issue list

#### Milestone 9.5 - Karakeep bookmark search integration (target: 2026-08-13)

- [ ] Add Karakeep credentials to `config.py` and `orbitr init` prompts (`karakeep_api_key`, `karakeep_server_url`)
- [ ] Create `src/orbitr/clients/karakeep.py` extending `BaseClient`
  - [ ] Implement `search_bookmarks(query, limit)` against `/api/search-bookmarks`
  - [ ] Implement `list_bookmarks(...)` for filtered listing
  - [ ] Map Karakeep JSON to `Paper` model with `source="karakeep"`
- [ ] Add `orbitr karakeep search <query>` command (Phase 1 scope)
  - [ ] Options: `--server`, `--limit`, `--format`
  - [ ] Honor TTY/JSON auto-format and `--no-color`
- [ ] (Optional Phase 2) Wire `karakeep` into `orbitr search --sources` alongside arXiv/Semantic Scholar
- [ ] Add fixture-based `respx` tests for `/api/search-bookmarks`
- [ ] Update README/help text with Karakeep setup example

## Risks and Constraints

### Technical Risks

- Google Scholar scraping fragility
- Semantic Scholar rate limiting when no API key is configured
- Async command complexity in Typer command boundaries
- Karakeep API availability and self-hosted URL configuration burden on users

### Scope Risks

- Recommendation quality can trigger scope creep
- Zotero edge cases (group libraries, linked attachments) remain deferred

## Success Metrics (v0.4/v1.1 planning window)

### Delivery Metrics

- [ ] v0.4.0/v1.1 milestones and dates approved
- [ ] All must-have features mapped to issues

### Quality Metrics

- [ ] CI coverage gate maintained at ≥ 80% with no regressions
- [ ] Zotero client failures map cleanly to `SourceError` without raw tracebacks
- [ ] No regression in existing command help, error handling, or output contracts

### Operational Metrics

- [ ] Weekly status entry added under `logs/`
- [ ] Session notes captured for major implementation blocks
- [ ] Planning/progress docs consistency check passes on every PR
