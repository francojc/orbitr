# Changelog

All notable changes are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-04-06

Initial release.

### Added

**Core pipeline**

- Multi-source concurrent search across arXiv (Atom feed) and Semantic Scholar
  (Graph API v1) via `lumen search`
- Intelligent deduplication: exact DOI match → exact arXiv ID match → fuzzy
  title similarity (rapidfuzz, 85% threshold) with author-overlap gating
- Five ranking criteria: `relevance` (TF-IDF), `citations` (log-scaled),
  `date` (recency), `impact` (citations × date), `combined` (weighted blend)
- SQLite TTL cache with three independent tiers:
  `search` (1 h), `paper` (24 h), `citations` (6 h)

**Commands**

- `lumen search` — keyword + `field:value` syntax, field flags (`--title`,
  `--author`, `--venue`), year range (`--from`, `--to`), sort, format
- `lumen paper` — fetch by arXiv ID, DOI, or Semantic Scholar ID; auto-detects
  ID type; accepts `arxiv:`, `abs/`, URL, and bare ID forms
- `lumen cite` — citing papers via Semantic Scholar
- `lumen author` — author search via Semantic Scholar two-step (search → papers)
- `lumen recommend` — content/citation/hybrid recommendations via SS
- `lumen export` — BibTeX, RIS, CSL-JSON; reads ndjson from stdin or `--query`
- `lumen query` — heuristic NL-to-query translator with `--run` flag
- `lumen zotero add/collections/new` — Zotero Web API integration via pyzotero
- `lumen cache stats/clean/clear` — cache inspection and management
- `lumen init` — interactive credential and defaults setup (writes `config.toml`
  with mode `0600`)
- `lumen doctor` — async connectivity checks for arXiv, SS, and Zotero

**Display layer**

- Four output formats: `table` (Rich Table), `list` (Rich Panels), `detail`
  (full single-paper layout with abstract, metadata, links), `json` (ndjson)
- TTY auto-detection: `--format` defaults to `json` when stdout is not a TTY
- Pager integration: long output routed through `$PAGER` (`less -R`) on TTY;
  disabled with `LUMEN_NO_PAGER=1`

**Error handling**

- `LumenError` hierarchy with exit codes: 1 (source), 2 (usage), 3 (config),
  4 (no results)
- HTTP errors converted to clean `SourceError` in `BaseClient._get`; no raw
  httpx messages surface to users
- 5xx errors retried up to 3× with exponential backoff; 403 directs to
  `lumen init` for API key setup
- Dim suggestion lines on all error messages

**Infrastructure**

- Layered config: CLI flags > env vars > `~/.config/lumen/config.toml` > defaults
- Nix flake dev environment (Python 3.12, uv, ruff, pyright)
- `justfile` with test, lint, format, coverage, build, and install recipes
- GitHub Actions CI: lint, typecheck, test (Python 3.10–3.12), coverage, build,
  publish-on-release

### Test coverage

- 343 tests; `core/` at 100%, `display/` at 97% overall
- Offline API tests via `respx` fixtures (no live network calls in CI)
- Smoke test script (`tests/smoke_test.sh`) for pre-release live-API validation

### Known limitations

- Google Scholar support deferred to v1.1 (scraping fragility)
- `lumen recommend --method` flag is accepted but all methods use the same
  SS endpoint; method distinctions planned for v1.1
- `display/detail.py` falls back to list view for multi-paper input in some
  edge cases

---

## [0.1.1] — 2026-04-06

### Fixed

- **`lumen init` — env-var credential protection** (`commands/init.py`, `config.py`):
  - Credentials supplied via `SEMANTIC_SCHOLAR_API_KEY`, `ZOTERO_USER_ID`, or
    `ZOTERO_API_KEY` environment variables are now detected at init time.
  - A clear dim note is shown for each active env var: *"Already set via
    ENV_VAR — leave blank to keep using the env var."*
  - Prompts for env-var-sourced credentials default to blank instead of
    pre-filling with the resolved (env) value, preventing accidental plain-text
    exposure in `config.toml`.
  - If the user leaves a credential blank and an env var is active, the
    existing `config.toml` value for that field is preserved rather than
    overwritten with an empty string.
  - Entering a new value at the prompt always writes it to `config.toml`,
    regardless of whether an env var is also set.
  - Config loading (`load_config`) was already correct (env vars take
    precedence over `config.toml` at runtime); this fix closes the init-time
    loophole.

## Unreleased

_Nothing yet._
