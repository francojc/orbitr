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
  (Graph API v1) via `orbitr search`
- Intelligent deduplication: exact DOI match → exact arXiv ID match → fuzzy
  title similarity (rapidfuzz, 85% threshold) with author-overlap gating
- Five ranking criteria: `relevance` (TF-IDF), `citations` (log-scaled),
  `date` (recency), `impact` (citations × date), `combined` (weighted blend)
- SQLite TTL cache with three independent tiers:
  `search` (1 h), `paper` (24 h), `citations` (6 h)

**Commands**

- `orbitr search` — keyword + `field:value` syntax, field flags (`--title`,
  `--author`, `--venue`), year range (`--from`, `--to`), sort, format
- `orbitr paper` — fetch by arXiv ID, DOI, or Semantic Scholar ID; auto-detects
  ID type; accepts `arxiv:`, `abs/`, URL, and bare ID forms
- `orbitr cite` — citing papers via Semantic Scholar
- `orbitr author` — author search via Semantic Scholar two-step (search → papers)
- `orbitr recommend` — content/citation/hybrid recommendations via SS
- `orbitr export` — BibTeX, RIS, CSL-JSON; reads ndjson from stdin or `--query`
- `orbitr query` — heuristic NL-to-query translator with `--run` flag
- `orbitr zotero add/collections/new` — Zotero Web API integration via pyzotero
- `orbitr cache stats/clean/clear` — cache inspection and management
- `orbitr init` — interactive credential and defaults setup (writes `config.toml`
  with mode `0600`)
- `orbitr doctor` — async connectivity checks for arXiv, SS, and Zotero

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
  `orbitr init` for API key setup
- Dim suggestion lines on all error messages

**Infrastructure**

- Layered config: CLI flags > env vars > `~/.config/orbitr/config.toml` > defaults
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
- `orbitr recommend --method` flag is accepted but all methods use the same
  SS endpoint; method distinctions planned for v1.1
- `display/detail.py` falls back to list view for multi-paper input in some
  edge cases

---

## [0.1.1] — 2026-04-06

### Fixed

- **`orbitr init` — env-var credential protection** (`commands/init.py`, `config.py`):
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

## [0.2.0] — 2026-04-08

### Added

**Zotero library browsing (Phase 7)**

- `orbitr zotero list` — browse items in the full library or a specific
  collection; options: `--collection/-c`, `--limit/-n`, `--sort`
  (dateModified/title/date), `--format/-f` (table/json/keys)
- `orbitr zotero get <item_key>` — full item detail with authors, abstract,
  DOI, URL, tags, notes (HTML-stripped), and PDF attachment path; options:
  `--format/-f` (detail/json), `--notes/--no-notes`
- `orbitr zotero search <query>` — full-text search within the Zotero library
  via pyzotero `q` parameter; options: `--collection/-c`, `--limit/-n`,
  `--format/-f` (table/json/keys)
- `orbitr zotero export-md <item_key>` — export a Zotero item as a Markdown
  file with YAML frontmatter (title, authors, year, doi, zotero_key,
  zotero_url, tags, type); options: `--output/-o` (file or directory; when a
  directory is given the filename is auto-generated as `YYYY-Author-Slug.md`);
  defaults to stdout for pipeline use
- `--format keys` on `zotero list` and `zotero search` outputs bare item keys
  one-per-line, enabling pipeline composition:
  `orbitr zotero list -c "NLP" --format keys | xargs -I{} orbitr zotero export-md {} -o kb/`

**ZoteroClient new methods** (`zotero/client.py`)

- `list_items(collection_key, limit, sort, direction, item_type)` — scoped or
  full-library listing; uses pyzotero `everything()` for `limit > 100`
- `get_item(item_key, include_children)` — fetches item metadata, notes, and
  attachment dicts via two pyzotero calls
- `search_items(query, collection_key, limit)` — delegates to pyzotero `q`
  parameter for full-text search

### Test coverage

- 410 tests (was 288 in v0.1.0 / 343 in smoke-tested state)
- 19 new client unit tests (`test_zotero_client.py`)
- 49 new CLI integration tests (new `zotero list/get/search/export-md` classes
  in `test_zotero.py`)

## [0.3.0] — 2026-04-17

### Added

- `orbitr zotero recent` subcommand for date-added browsing of recent Zotero entries.
  - Supports `--days` and `--since` time windows.
  - Supports `--collection/-c`, `--limit/-n`, and `--format/-f` (`table`, `json`, `keys`).
  - Uses `dateAdded` descending sort for recency-first output.
- Docs consistency guardrail script: `scripts/check_docs_consistency.py`.
  - Validates `specs/planning.md` and `specs/progress.md` alignment for project, phase, and status version markers.
- CI and local workflow integration for docs consistency checks.
  - CI lint job now runs the docs check.
  - `just check` includes docs consistency verification.
  - New `just docs-check` recipe.

### Changed

- `zotero list --sort` accepted values now include `dateAdded`.

### Fixed

- `orbitr zotero recent` now excludes non-reference child item types by default (`annotation`, `attachment`, `note`).
- Fixed `orbitr zotero recent --days ...` appearing to hang on large libraries by avoiding pyzotero `everything()` pagination in this path (single-page fetch `<= 100`).

## Unreleased

_Nothing yet._
