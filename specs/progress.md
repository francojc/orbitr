# Development Project Progress

**Project:** orbitr
**Status:** v0.4.0 release hardening; v0.3.0 shipped
**Last Updated:** 2026-07-10

## Current Status Overview

### Development Phase

- **Current Phase:** Phase 9 (reliability hardening and v1.1 exploration)
- **Phase Progress:** Phases 1-8 complete; v0.3.0 tagged 2026-05-08
- **Overall Project Progress:** v0.1.x, v0.2.0, and v0.3.0 shipped

### Recent Accomplishments

- Phase 8 delivered: `zotero recent`, docs-consistency guardrail, and coverage CI gate shipped in v0.3.0
- `v0.3.0` tagged 2026-05-08
- CI coverage threshold set to 80%; current combined coverage is ~90%
- README, CHANGELOG, and release docs updated
- Test suite expanded to 421 passing tests

## Milestone Tracking

### Completed Milestones

- [x] Phase 1: Architecture and scaffolding
- [x] Phase 2: Core data layer
- [x] Phase 3: Command implementation
- [x] Phase 4: Display and polish
- [x] Phase 5: Testing and documentation
- [x] Phase 6: Initial release
- [x] Phase 7: Zotero library enhancements
- [x] Phase 8: v0.3.0 planning and reliability
- [x] v0.2.0 release tag
- [x] v0.3.0 release tag

### Active Milestones (Phase 9)

- Reliability hardening and dedicated Karakeep workflow are implemented; automated release gates pass and Zotero live read smoke is recorded. Karakeep live smoke remains pending until server URL is configured.

- [ ] Milestone 9.1 - Zotero/API reliability polish (target: 2026-07-23)
- [ ] Milestone 9.2 - Google Scholar v1.1 feasibility spike (target: 2026-08-06)
- [ ] Milestone 9.3 - Operational cadence reset (target: 2026-07-23)
- [ ] Milestone 9.4 - v0.4.0/v1.1 scope and acceptance criteria (target: 2026-08-13)
- [ ] Milestone 9.5 - Karakeep bookmark search integration (target: 2026-08-13)

### At-Risk Milestones

- **Risk:** Project paused after v0.3.0 tag (no commits since 2026-05-08); momentum and log cadence lost
- **Risk:** Google Scholar feasibility may fail reliability criteria
- **Decision:** Karakeep remains a dedicated command in v0.4 and is not added to `orbitr search --sources`.
- **Risk:** `zotero recent` shipped without deep Zotero exception mapping; API failures may surface raw tracebacks

## Build and Test Status

### Build Health

- **Last Confirmed Healthy Run:** 2026-07-09 (`pytest` 421 passed, `ruff`, `pyright`, coverage 89.6%)
- **Warnings:** None currently tracked

### Test Status

- **Tests Passing:** 421
- **Coverage Tracking:** Enforced in CI at 80% threshold; current coverage ~89.6%
- **Open Defects:** No active critical/high defects recorded

## Current Work

### Active Focus

- Catch up `logs/` entries since 2026-W16 and restart weekly cadence
- Map Zotero/pyzotero failures to `SourceError` with actionable suggestions
- Add failure-mode tests for Zotero API timeouts, 401/403, and transient 5xx
- Decide on and optionally implement `doctor --deep` semantic checks
- Prototype Google Scholar client behind feature flag and decide ship/defer
- Define v0.4.0/v1.1 scope, acceptance criteria, and issue list
- Design and scaffold Karakeep API integration (`clients/karakeep.py` + `orbitr karakeep search`)

### Open Tasks (next 2 weeks)

- [x] Catch up `logs/weekly/` entries and add this session note
- [x] Write `logs/weekly/2026-W28.md` to restart status cadence
- [x] Map `ZoteroClient` network/API failures to `SourceError` and add tests
- [ ] Prototype Google Scholar client behind feature flag
- [x] Define v0.4.0/v1.1 milestone issue list with acceptance criteria
- [x] Add Karakeep credentials to `config.py` and `orbitr init`
- [x] Create `src/orbitr/clients/karakeep.py` with `search_bookmarks` and tests
- [x] Add `orbitr karakeep search <query>` command with `--format` support

### Blockers

- None currently identified

## Verification Notes (2026-04-17)

- `zotero search` is currently query-based and does not support date-added filters.
- Current code supports sorting in `zotero list`, but accepted sort values exclude `dateAdded`.
- `doctor` currently verifies endpoint reachability, but it does not perform semantic payload checks.
- Search/query command paths already use `SourceError` with user-facing suggestions.
- Zotero client methods do not yet consistently map backend/network exceptions into `SourceError`/`LumenError`; this is a v0.3 reliability task.

## Deferred Items

- Group library support in Zotero (v2)
- PDF text extraction/full-text indexing (v2)
- Custom Jinja templates for `zotero export-md` (v2)
- Batch `export-md` workflow enhancements (v2)
- CLI-based Zotero item editing/update support (v2)

## Release Outlook

### Next Release

- **Version:** v0.4.0 (planning stage)
- **Target Window:** TBD after Milestone 9.4
- **Candidate Themes:** reliability hardening, Karakeep bookmark search, optional Google Scholar feasibility outcome

### Release History

| Version | Date | Key Changes |
|---|---|---|
| 0.3.0 | 2026-04-17 | `zotero recent`, docs-consistency guardrail, coverage CI gate |
| 0.2.0 | 2026-04-08 | Zotero `list/get/search/export-md`, command and docs expansion |
| 0.1.1 | 2026-04-06 | Stabilization patch after initial release |
