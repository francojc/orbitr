# orbitr

Academic literature search and reference management for the terminal. Search
arXiv and Semantic Scholar concurrently, inspect papers and their citations,
get recommendations, export bibliographies, and manage your Zotero library —
all without leaving the shell.

## Contents

- [Installation](#installation)
- [Quick start](#quick-start)
- [Global flags](#global-flags)
- [Commands](#commands)
  - [search](#orbitr-search)
  - [paper](#orbitr-paper)
  - [cite](#orbitr-cite)
  - [author](#orbitr-author)
  - [recommend](#orbitr-recommend)
  - [export](#orbitr-export)
  - [query](#orbitr-query)
  - [zotero](#orbitr-zotero)
  - [cache](#orbitr-cache)
  - [init](#orbitr-init)
  - [doctor](#orbitr-doctor)
- [Configuration](#configuration)
- [Output formats](#output-formats)
- [Piping and scripting](#piping-and-scripting)
- [Exit codes](#exit-codes)
- [Shell completions](#shell-completions)
- [Project layout](#project-layout)
- [Dependencies](#dependencies)

---

## Installation

**Requirements:** Python ≥ 3.10, [`uv`](https://docs.astral.sh/uv/)

```bash
git clone <repo-url> orbitr
cd orbitr
uv tool install .
orbitr --version
```

### Development setup

`orbitr` uses a [Nix flake](https://nixos.org/manual/nix/stable/command-ref/new-cli/nix3-flake.html)
to pin the development environment (Python 3.12, uv, ruff, pyright) and
[`just`](https://just.systems) as a task runner.

**Prerequisites:** Nix with flakes enabled, direnv, just.

```bash
git clone <repo-url> orbitr
cd orbitr          # direnv activates the flake shell automatically
just setup        # uv sync inside the pinned environment
just run -- --help
```

Without direnv: `nix develop && just setup`.

**Common tasks:**

```bash
just test        # full test suite
just cov         # tests with coverage report
just check       # lint + format check (no writes)
just qa          # check + type check
just fmt         # auto-format source files
```

### API credentials

`orbitr` works without credentials; providing them increases rate limits and
enables Zotero integration.

| Credential | Purpose |
|---|---|
| Semantic Scholar API key | Higher rate limits (get one at semanticscholar.org/product/api) |
| Zotero User ID + API key | `orbitr zotero` commands |

```bash
orbitr init      # guided interactive setup
```

Or set environment variables directly — see [Configuration](#configuration).

---

## Quick start

```bash
# Search across arXiv and Semantic Scholar
orbitr search "retrieval augmented generation"

# Field filters and date range
orbitr search "scaling laws" --from 2022 --sort citations

# Full metadata for a specific paper (arXiv ID, DOI, or SS ID accepted)
orbitr paper 2005.14165

# Papers citing the Transformer paper
orbitr cite 1706.03762 --limit 20

# Papers by an author
orbitr author "Percy Liang"

# Recommendations from a seed paper
orbitr recommend 1706.03762

# Export search results as BibTeX
orbitr search "in-context learning" --format json \
  | orbitr export --format bibtex --output refs.bib

# Add a paper to Zotero
orbitr zotero add 2503.19260 --collection "Reading List" --tags "llm,linguistics"
```

---

## Global flags

These flags work with every command.

| Flag | Short | Description |
|---|---|---|
| `--help` | | Show help for any command |
| `--version` | `-V` | Print version and exit |
| `--verbose` | `-v` | Show debug output and request details |
| `--quiet` | `-q` | Suppress informational output; only results and errors |
| `--no-color` | | Disable ANSI color (also: `NO_COLOR` env var) |
| `--config <path>` | | Use an alternate config file |

---

## Commands

### `orbitr search`

Search for papers across arXiv and Semantic Scholar concurrently. Results are
deduplicated by DOI, arXiv ID, and title similarity, then ranked by the chosen
criterion.

```
orbitr search QUERY [OPTIONS]
```

Field filters can be given as CLI flags or embedded directly in the query
string using `field:value` syntax (e.g. `"title:attention author:Vaswani"`).

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--sources` | `-s` | `arxiv,semantic_scholar` | Comma-separated sources |
| `--limit` | `-n` | `10` | Max results (1–200) |
| `--title` | `-T` | | Filter by title keywords |
| `--author` | `-a` | | Filter by author name |
| `--venue` | `-j` | | Filter by journal or conference |
| `--from` | | | Earliest publication year |
| `--to` | | | Latest publication year |
| `--sort` | | `relevance` | `relevance`, `citations`, `date`, `impact`, `combined` |
| `--format` | `-f` | `table` | `table`, `list`, `detail`, `json` |
| `--no-cache` | | | Bypass the local result cache |

```bash
# Keyword search
orbitr search "diffusion models image generation"

# Field-filter flags
orbitr search "RLHF" --author "Ouyang" --from 2022 --to 2023

# Inline field syntax
orbitr search "title:contrastive learning author:Chen"

# Single source, sorted by citations
orbitr search "vision transformer" --sources semantic_scholar \
  --limit 25 --sort citations

# Machine-readable output
orbitr search "federated learning" --format json
```

---

### `orbitr paper`

Fetch full metadata for a single paper. Accepts arXiv IDs, DOIs, and
Semantic Scholar paper IDs — the source is detected automatically.

```
orbitr paper PAPER_ID [OPTIONS]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--format` | `-f` | `table` | `table`, `list`, `detail`, `json` |
| `--no-cache` | | | Bypass the local paper cache |

```bash
orbitr paper 1706.03762                          # arXiv ID
orbitr paper arxiv:2503.19260                    # arXiv ID with prefix
orbitr paper 10.18653/v1/2020.acl-main.196       # DOI
orbitr paper 1706.03762 --format detail          # full single-paper view
orbitr paper 1706.03762 --format json            # machine-readable
```

---

### `orbitr cite`

List papers that cite a given paper via Semantic Scholar. Accepts arXiv IDs,
DOIs, and Semantic Scholar paper IDs.

```
orbitr cite PAPER_ID [OPTIONS]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--limit` | `-n` | `10` | Max citing papers (1–200) |
| `--format` | `-f` | `table` | `table`, `list`, `detail`, `json` |
| `--no-cache` | | | Bypass the local citation cache |

```bash
orbitr cite 1706.03762
orbitr cite 1706.03762 --limit 50 --format list
orbitr cite 10.18653/v1/2020.acl-main.196 --format json
```

---

### `orbitr author`

Search for an author by name and list their papers via Semantic Scholar.
Returns publications from the best-matching author result.

```
orbitr author NAME [OPTIONS]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--limit` | `-n` | `10` | Max papers to list (1–200) |
| `--format` | `-f` | `table` | `table`, `list`, `detail`, `json` |
| `--no-cache` | | | Bypass the local cache |

```bash
orbitr author "Emily M. Bender"
orbitr author "LeCun" --limit 20 --format list
orbitr author "Percy Liang" --format json | jq '.[].title'
```

---

### `orbitr recommend`

Get papers similar to a seed paper via Semantic Scholar's recommendation API.
The seed is any paper ID — arXiv ID, DOI, or Semantic Scholar ID.

```
orbitr recommend SEED [OPTIONS]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--method` | `-m` | `hybrid` | `content`, `citation`, or `hybrid` |
| `--limit` | `-n` | `10` | Number of recommendations (1–50) |
| `--format` | `-f` | `table` | `table`, `list`, `detail`, `json` |
| `--no-cache` | | | Bypass the local cache |

```bash
orbitr recommend 1706.03762
orbitr recommend 1706.03762 --method citation --limit 20
orbitr recommend 10.18653/v1/2020.acl-main.196 --format json
```

---

### `orbitr export`

Export papers to a bibliography format. Reads paper JSON piped from another
`orbitr` command, or runs a fresh search with `--query`.

```
orbitr export [OPTIONS]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--format` | `-f` | `bibtex` | `bibtex`, `ris`, `csl-json` |
| `--output` | `-o` | stdout | Output file path |
| `--query` | `-q` | | Run a fresh search and export results |

```bash
# Pipe from search
orbitr search "sparse attention" --limit 10 --format json \
  | orbitr export --format bibtex --output sparse.bib

# Single paper via pipe
orbitr paper 1706.03762 --format json \
  | orbitr export --format csl-json

# Direct query (no pipe needed)
orbitr export --query "BERT language model" --format ris --output bert.ris

# RIS to stdout for inspection
orbitr search "contrastive learning" --format json | orbitr export --format ris
```

---

### `orbitr query`

Translate a plain-language description into a `orbitr search` command.
Extracts year, author, and keywords heuristically.

```
orbitr query NATURAL [OPTIONS]
```

**Options:**

| Flag | Short | Description |
|---|---|---|
| `--run` | `-r` | Execute the generated command immediately |

```bash
# Show the generated command
orbitr query "recent papers on contrastive learning in NLP"

# Show and run immediately
orbitr query "Vaswani attention transformer 2017" --run
```

---

### `orbitr zotero`

Manage your Zotero library. Requires `zotero_user_id` and `zotero_api_key` —
run `orbitr init` to configure them, then `orbitr doctor` to verify.

---

#### `orbitr zotero add`

Add a paper to your Zotero library by ID. Fetches full metadata from arXiv or
Semantic Scholar and creates a `journalArticle` item.

```
orbitr zotero add PAPER_ID [OPTIONS]
```

**Options:**

| Flag | Short | Description |
|---|---|---|
| `--collection` | `-c` | Target collection name or key |
| `--tags` | `-t` | Comma-separated tags |
| `--no-cache` | | Bypass the local paper cache |

```bash
orbitr zotero add 1706.03762
orbitr zotero add arxiv:2503.19260 --collection "Reading List" --tags "llm,linguistics"
orbitr zotero add 10.18653/v1/2020.acl-main.196 --collection "NLP Papers"
```

---

#### `orbitr zotero collections`

List all collections in your Zotero library.

```
orbitr zotero collections [OPTIONS]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--format` | `-f` | `table` | `table` or `json` |

```bash
orbitr zotero collections
orbitr zotero collections --format json | jq '.[].name'
```

---

#### `orbitr zotero new`

Create a new collection in your Zotero library.

```
orbitr zotero new NAME [OPTIONS]
```

**Options:**

| Flag | Short | Description |
|---|---|---|
| `--parent` | `-p` | Parent collection name or key |

```bash
orbitr zotero new "PhD Research"
orbitr zotero new "Chapter 3" --parent "PhD Research"
```

---

### `orbitr cache`

Manage the local SQLite result cache. Three tiers are maintained independently:
`search` (1 h TTL), `paper` (24 h), `citations` (6 h).

```
orbitr cache COMMAND
```

| Subcommand | Description |
|---|---|
| `stats` | Entry counts per tier, disk usage, and cache path |
| `clean [--tier T]` | Remove expired entries; optional tier filter |
| `clear [--tier T] [--yes]` | Delete all entries; prompts unless `--yes` |

```bash
orbitr cache stats
orbitr cache clean
orbitr cache clean --tier search
orbitr cache clear --yes
orbitr cache clear --tier paper --yes
```

---

### `orbitr init`

Interactive first-time setup. Writes `~/.config/orbitr/config.toml` with mode
`0600`. Run once after installing, or again to rotate credentials.

```bash
orbitr init
```

Prompts for Semantic Scholar API key, Zotero credentials, and default
preferences. All values are optional and can be skipped.

---

### `orbitr doctor`

Check configuration and connectivity to arXiv and Semantic Scholar (and Zotero
if credentials are configured). Exits `0` if all checks pass, `1` if any
connectivity check fails.

```bash
orbitr doctor
```

---

## Configuration

Settings are resolved in this order (earlier sources win):

```
CLI flags  >  environment variables  >  config file  >  built-in defaults
```

### Config file

Location: `~/.config/orbitr/config.toml` (XDG; override with `--config`).

```toml
[defaults]
sources     = ["arxiv", "semantic_scholar"]
max_results = 10
format      = "table"
no_cache    = false
no_pager    = false

[credentials]
semantic_scholar_api_key = ""
zotero_user_id           = ""
zotero_api_key           = ""
```

### Environment variables

| Variable | Description |
|---|---|
| `LUMEN_SOURCES` | Default sources (comma-separated) |
| `LUMEN_MAX_RESULTS` | Default result limit |
| `LUMEN_FORMAT` | Default output format |
| `LUMEN_CACHE_DIR` | Override cache directory |
| `LUMEN_NO_CACHE` | Disable caching (`1` = true) |
| `LUMEN_NO_PAGER` | Disable pager (`1` = true) |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar API key |
| `ZOTERO_USER_ID` | Zotero user ID |
| `ZOTERO_API_KEY` | Zotero API key |
| `NO_COLOR` | Disable all ANSI color output |

A template is provided in `.env.example`.

---

## Output formats

All paper-returning commands support `--format` / `-f`:

| Format | Description | Best for |
|---|---|---|
| `table` | Compact multi-column table (truncated fields) | Interactive browsing |
| `list` | One labeled block per paper, abstract snippet | Skimming results |
| `detail` | Full single-paper view with wrapped abstract | `orbitr paper` |
| `json` | Newline-delimited JSON objects | Piping, `jq`, scripting |

**Auto-detection:** when stdout is not a TTY (pipe or redirect), `--format`
defaults to `json` automatically unless set explicitly.

**Pager:** long output is paged through `$PAGER` (default: `less -R`) when
stdout is a TTY. Disable with `LUMEN_NO_PAGER=1` or `--no-color`.

---

## Piping and scripting

- Results → **stdout**; warnings and errors → **stderr**.
- `--format json` always produces newline-delimited JSON regardless of TTY.
- `orbitr export` reads piped JSON from any `orbitr` command.
- Use `-q` / `--quiet` to suppress progress output in scripts.

```bash
# Search → BibTeX file
orbitr search "in-context learning" --sort citations --limit 10 --format json \
  | orbitr export --format bibtex --output icl.bib

# Extract titles with jq
orbitr search "model merging" --format json | jq -r '.[].title'

# Author publication list as CSV
orbitr author "Danqi Chen" --format json \
  | jq -r '.[] | [.title, (.published_date // ""), (.citation_count // 0)] | @csv' \
  > danqi_chen.csv

# Pipe into a custom script
orbitr search "continual learning" --limit 20 --format json | python triage.py
```

---

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Source error (network failure, API error) |
| `2` | Usage error (bad argument, invalid flag value) |
| `3` | Config error (missing credentials) |
| `4` | No results found |

---

## Shell completions

`orbitr` supports tab-completion for Zsh, Bash, and Fish via Click's completion
system. The simplest method is the built-in flag (works when run directly from
an interactive shell):

```bash
orbitr --install-completion   # detects your shell and installs automatically
```

If auto-detection fails, generate the script manually with the `_LUMEN_COMPLETE`
environment variable:

**Zsh:**

```bash
_LUMEN_COMPLETE=source_zsh orbitr > ~/.zfunc/_orbitr
# Add to ~/.zshrc (if not already present):
#   fpath=(~/.zfunc $fpath)
#   autoload -Uz compinit && compinit
```

**Bash:**

```bash
_LUMEN_COMPLETE=source_bash orbitr > ~/.bash_completion.d/orbitr
# Add to ~/.bashrc:
#   source ~/.bash_completion.d/orbitr
```

**Fish:**

```bash
_LUMEN_COMPLETE=source_fish orbitr > ~/.config/fish/completions/orbitr.fish
```

---

## Project layout

```
orbitr/
├── pyproject.toml
├── flake.nix
├── .env.example
├── README.md
├── src/
│   └── orbitr/
│       ├── __init__.py
│       ├── cli.py              # Typer app root; global flags; command registration
│       ├── config.py           # Layered config: flags > env vars > file > defaults
│       ├── _async.py           # asyncio.run() helper
│       ├── exceptions.py       # LumenError hierarchy with exit codes
│       ├── commands/
│       │   ├── search.py       # orbitr search
│       │   ├── paper.py        # orbitr paper, orbitr cite
│       │   ├── author.py       # orbitr author
│       │   ├── recommend.py    # orbitr recommend
│       │   ├── export.py       # orbitr export
│       │   ├── query.py        # orbitr query
│       │   ├── zotero.py       # orbitr zotero add / collections / new
│       │   ├── cache.py        # orbitr cache stats / clean / clear
│       │   ├── init.py         # orbitr init
│       │   └── doctor.py       # orbitr doctor
│       ├── clients/
│       │   ├── base.py         # Retry, backoff, circuit-break; HTTPError → SourceError
│       │   ├── arxiv.py        # arXiv Atom feed client
│       │   └── semantic_scholar.py  # Semantic Scholar Graph API client
│       ├── core/
│       │   ├── models.py       # Paper, Author, SearchResult (Pydantic v2)
│       │   ├── deduplication.py # DOI / arXiv ID / fuzzy-title dedup
│       │   ├── ranking.py      # relevance, citations, date, impact, combined
│       │   ├── cache.py        # SQLite TTL cache (3 tiers)
│       │   ├── export.py       # BibTeX, RIS, CSL-JSON formatters
│       │   └── query.py        # field:value parsing; per-source query builders
│       ├── zotero/
│       │   └── client.py       # pyzotero wrapper
│       └── display/
│           ├── __init__.py     # render() dispatcher; effective_format(); pager
│           ├── table.py        # Rich Table renderer
│           ├── list.py         # Rich Panel renderer
│           ├── detail.py       # Full single-paper Rich layout
│           └── json_fmt.py     # Newline-delimited JSON serialiser
└── tests/
    ├── conftest.py
    ├── fixtures/               # Recorded API responses for offline testing
    ├── test_models.py
    ├── test_arxiv.py
    ├── test_semantic_scholar.py
    ├── test_deduplication.py
    ├── test_ranking.py
    ├── test_cache.py
    ├── test_search.py
    ├── test_cache_cmd.py
    ├── test_paper.py
    ├── test_recommend.py
    ├── test_author.py
    ├── test_export.py
    ├── test_init.py
    ├── test_doctor.py
    ├── test_query.py
    ├── test_zotero.py
    ├── test_display_phase4.py
    └── test_base_client.py
```

---

## Dependencies

| Package | Purpose |
|---|---|
| [`typer`](https://typer.tiangolo.com) | CLI framework; command tree, flags, completions |
| [`rich`](https://rich.readthedocs.io) | Tables, panels, color, pager integration |
| [`httpx`](https://www.python-httpx.org) | Async HTTP client |
| [`pydantic`](https://docs.pydantic.dev) | Data models and validation |
| [`feedparser`](https://feedparser.readthedocs.io) | arXiv Atom feed parsing |
| [`rapidfuzz`](https://rapidfuzz.github.io/RapidFuzz/) | Fuzzy title matching for deduplication |
| [`pyzotero`](https://pyzotero.readthedocs.io) | Zotero Web API client |
| [`python-dateutil`](https://dateutil.readthedocs.io) | Flexible date parsing |
| [`python-dotenv`](https://saurabh-kumar.com/python-dotenv/) | `.env` file loading |
