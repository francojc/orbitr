# lumen

Academic literature search and reference management for the terminal. Search
arXiv and Semantic Scholar concurrently, inspect papers and their citations,
get recommendations, export bibliographies, and manage your Zotero library —
all without leaving the shell.

## Contents

- [Installation](#installation)
- [Quick start](#quick-start)
- [Global flags](#global-flags)
- [Commands](#commands)
  - [search](#lumen-search)
  - [paper](#lumen-paper)
  - [cite](#lumen-cite)
  - [author](#lumen-author)
  - [recommend](#lumen-recommend)
  - [export](#lumen-export)
  - [query](#lumen-query)
  - [zotero](#lumen-zotero)
  - [cache](#lumen-cache)
  - [init](#lumen-init)
  - [doctor](#lumen-doctor)
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
git clone <repo-url> lumen
cd lumen
uv tool install .
lumen --version
```

### Development setup

`lumen` uses a [Nix flake](https://nixos.org/manual/nix/stable/command-ref/new-cli/nix3-flake.html)
to pin the development environment (Python 3.12, uv, ruff, pyright) and
[`just`](https://just.systems) as a task runner.

**Prerequisites:** Nix with flakes enabled, direnv, just.

```bash
git clone <repo-url> lumen
cd lumen          # direnv activates the flake shell automatically
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

`lumen` works without credentials; providing them increases rate limits and
enables Zotero integration.

| Credential | Purpose |
|---|---|
| Semantic Scholar API key | Higher rate limits (get one at semanticscholar.org/product/api) |
| Zotero User ID + API key | `lumen zotero` commands |

```bash
lumen init      # guided interactive setup
```

Or set environment variables directly — see [Configuration](#configuration).

---

## Quick start

```bash
# Search across arXiv and Semantic Scholar
lumen search "retrieval augmented generation"

# Field filters and date range
lumen search "scaling laws" --from 2022 --sort citations

# Full metadata for a specific paper (arXiv ID, DOI, or SS ID accepted)
lumen paper 2005.14165

# Papers citing the Transformer paper
lumen cite 1706.03762 --limit 20

# Papers by an author
lumen author "Percy Liang"

# Recommendations from a seed paper
lumen recommend 1706.03762

# Export search results as BibTeX
lumen search "in-context learning" --format json \
  | lumen export --format bibtex --output refs.bib

# Add a paper to Zotero
lumen zotero add 2503.19260 --collection "Reading List" --tags "llm,linguistics"
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

### `lumen search`

Search for papers across arXiv and Semantic Scholar concurrently. Results are
deduplicated by DOI, arXiv ID, and title similarity, then ranked by the chosen
criterion.

```
lumen search QUERY [OPTIONS]
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
lumen search "diffusion models image generation"

# Field-filter flags
lumen search "RLHF" --author "Ouyang" --from 2022 --to 2023

# Inline field syntax
lumen search "title:contrastive learning author:Chen"

# Single source, sorted by citations
lumen search "vision transformer" --sources semantic_scholar \
  --limit 25 --sort citations

# Machine-readable output
lumen search "federated learning" --format json
```

---

### `lumen paper`

Fetch full metadata for a single paper. Accepts arXiv IDs, DOIs, and
Semantic Scholar paper IDs — the source is detected automatically.

```
lumen paper PAPER_ID [OPTIONS]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--format` | `-f` | `table` | `table`, `list`, `detail`, `json` |
| `--no-cache` | | | Bypass the local paper cache |

```bash
lumen paper 1706.03762                          # arXiv ID
lumen paper arxiv:2503.19260                    # arXiv ID with prefix
lumen paper 10.18653/v1/2020.acl-main.196       # DOI
lumen paper 1706.03762 --format detail          # full single-paper view
lumen paper 1706.03762 --format json            # machine-readable
```

---

### `lumen cite`

List papers that cite a given paper via Semantic Scholar. Accepts arXiv IDs,
DOIs, and Semantic Scholar paper IDs.

```
lumen cite PAPER_ID [OPTIONS]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--limit` | `-n` | `10` | Max citing papers (1–200) |
| `--format` | `-f` | `table` | `table`, `list`, `detail`, `json` |
| `--no-cache` | | | Bypass the local citation cache |

```bash
lumen cite 1706.03762
lumen cite 1706.03762 --limit 50 --format list
lumen cite 10.18653/v1/2020.acl-main.196 --format json
```

---

### `lumen author`

Search for an author by name and list their papers via Semantic Scholar.
Returns publications from the best-matching author result.

```
lumen author NAME [OPTIONS]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--limit` | `-n` | `10` | Max papers to list (1–200) |
| `--format` | `-f` | `table` | `table`, `list`, `detail`, `json` |
| `--no-cache` | | | Bypass the local cache |

```bash
lumen author "Emily M. Bender"
lumen author "LeCun" --limit 20 --format list
lumen author "Percy Liang" --format json | jq '.[].title'
```

---

### `lumen recommend`

Get papers similar to a seed paper via Semantic Scholar's recommendation API.
The seed is any paper ID — arXiv ID, DOI, or Semantic Scholar ID.

```
lumen recommend SEED [OPTIONS]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--method` | `-m` | `hybrid` | `content`, `citation`, or `hybrid` |
| `--limit` | `-n` | `10` | Number of recommendations (1–50) |
| `--format` | `-f` | `table` | `table`, `list`, `detail`, `json` |
| `--no-cache` | | | Bypass the local cache |

```bash
lumen recommend 1706.03762
lumen recommend 1706.03762 --method citation --limit 20
lumen recommend 10.18653/v1/2020.acl-main.196 --format json
```

---

### `lumen export`

Export papers to a bibliography format. Reads paper JSON piped from another
`lumen` command, or runs a fresh search with `--query`.

```
lumen export [OPTIONS]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--format` | `-f` | `bibtex` | `bibtex`, `ris`, `csl-json` |
| `--output` | `-o` | stdout | Output file path |
| `--query` | `-q` | | Run a fresh search and export results |

```bash
# Pipe from search
lumen search "sparse attention" --limit 10 --format json \
  | lumen export --format bibtex --output sparse.bib

# Single paper via pipe
lumen paper 1706.03762 --format json \
  | lumen export --format csl-json

# Direct query (no pipe needed)
lumen export --query "BERT language model" --format ris --output bert.ris

# RIS to stdout for inspection
lumen search "contrastive learning" --format json | lumen export --format ris
```

---

### `lumen query`

Translate a plain-language description into a `lumen search` command.
Extracts year, author, and keywords heuristically.

```
lumen query NATURAL [OPTIONS]
```

**Options:**

| Flag | Short | Description |
|---|---|---|
| `--run` | `-r` | Execute the generated command immediately |

```bash
# Show the generated command
lumen query "recent papers on contrastive learning in NLP"

# Show and run immediately
lumen query "Vaswani attention transformer 2017" --run
```

---

### `lumen zotero`

Manage your Zotero library. Requires `zotero_user_id` and `zotero_api_key` —
run `lumen init` to configure them, then `lumen doctor` to verify.

---

#### `lumen zotero add`

Add a paper to your Zotero library by ID. Fetches full metadata from arXiv or
Semantic Scholar and creates a `journalArticle` item.

```
lumen zotero add PAPER_ID [OPTIONS]
```

**Options:**

| Flag | Short | Description |
|---|---|---|
| `--collection` | `-c` | Target collection name or key |
| `--tags` | `-t` | Comma-separated tags |
| `--no-cache` | | Bypass the local paper cache |

```bash
lumen zotero add 1706.03762
lumen zotero add arxiv:2503.19260 --collection "Reading List" --tags "llm,linguistics"
lumen zotero add 10.18653/v1/2020.acl-main.196 --collection "NLP Papers"
```

---

#### `lumen zotero collections`

List all collections in your Zotero library.

```
lumen zotero collections [OPTIONS]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--format` | `-f` | `table` | `table` or `json` |

```bash
lumen zotero collections
lumen zotero collections --format json | jq '.[].name'
```

---

#### `lumen zotero new`

Create a new collection in your Zotero library.

```
lumen zotero new NAME [OPTIONS]
```

**Options:**

| Flag | Short | Description |
|---|---|---|
| `--parent` | `-p` | Parent collection name or key |

```bash
lumen zotero new "PhD Research"
lumen zotero new "Chapter 3" --parent "PhD Research"
```

---

### `lumen cache`

Manage the local SQLite result cache. Three tiers are maintained independently:
`search` (1 h TTL), `paper` (24 h), `citations` (6 h).

```
lumen cache COMMAND
```

| Subcommand | Description |
|---|---|
| `stats` | Entry counts per tier, disk usage, and cache path |
| `clean [--tier T]` | Remove expired entries; optional tier filter |
| `clear [--tier T] [--yes]` | Delete all entries; prompts unless `--yes` |

```bash
lumen cache stats
lumen cache clean
lumen cache clean --tier search
lumen cache clear --yes
lumen cache clear --tier paper --yes
```

---

### `lumen init`

Interactive first-time setup. Writes `~/.config/lumen/config.toml` with mode
`0600`. Run once after installing, or again to rotate credentials.

```bash
lumen init
```

Prompts for Semantic Scholar API key, Zotero credentials, and default
preferences. All values are optional and can be skipped.

---

### `lumen doctor`

Check configuration and connectivity to arXiv and Semantic Scholar (and Zotero
if credentials are configured). Exits `0` if all checks pass, `1` if any
connectivity check fails.

```bash
lumen doctor
```

---

## Configuration

Settings are resolved in this order (earlier sources win):

```
CLI flags  >  environment variables  >  config file  >  built-in defaults
```

### Config file

Location: `~/.config/lumen/config.toml` (XDG; override with `--config`).

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
| `detail` | Full single-paper view with wrapped abstract | `lumen paper` |
| `json` | Newline-delimited JSON objects | Piping, `jq`, scripting |

**Auto-detection:** when stdout is not a TTY (pipe or redirect), `--format`
defaults to `json` automatically unless set explicitly.

**Pager:** long output is paged through `$PAGER` (default: `less -R`) when
stdout is a TTY. Disable with `LUMEN_NO_PAGER=1` or `--no-color`.

---

## Piping and scripting

- Results → **stdout**; warnings and errors → **stderr**.
- `--format json` always produces newline-delimited JSON regardless of TTY.
- `lumen export` reads piped JSON from any `lumen` command.
- Use `-q` / `--quiet` to suppress progress output in scripts.

```bash
# Search → BibTeX file
lumen search "in-context learning" --sort citations --limit 10 --format json \
  | lumen export --format bibtex --output icl.bib

# Extract titles with jq
lumen search "model merging" --format json | jq -r '.[].title'

# Author publication list as CSV
lumen author "Danqi Chen" --format json \
  | jq -r '.[] | [.title, (.published_date // ""), (.citation_count // 0)] | @csv' \
  > danqi_chen.csv

# Pipe into a custom script
lumen search "continual learning" --limit 20 --format json | python triage.py
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

`lumen` supports tab-completion for Zsh, Bash, and Fish via Click's completion
system. The simplest method is the built-in flag (works when run directly from
an interactive shell):

```bash
lumen --install-completion   # detects your shell and installs automatically
```

If auto-detection fails, generate the script manually with the `_LUMEN_COMPLETE`
environment variable:

**Zsh:**

```bash
_LUMEN_COMPLETE=source_zsh lumen > ~/.zfunc/_lumen
# Add to ~/.zshrc (if not already present):
#   fpath=(~/.zfunc $fpath)
#   autoload -Uz compinit && compinit
```

**Bash:**

```bash
_LUMEN_COMPLETE=source_bash lumen > ~/.bash_completion.d/lumen
# Add to ~/.bashrc:
#   source ~/.bash_completion.d/lumen
```

**Fish:**

```bash
_LUMEN_COMPLETE=source_fish lumen > ~/.config/fish/completions/lumen.fish
```

---

## Project layout

```
lumen/
├── pyproject.toml
├── flake.nix
├── .env.example
├── README.md
├── src/
│   └── lumen/
│       ├── __init__.py
│       ├── cli.py              # Typer app root; global flags; command registration
│       ├── config.py           # Layered config: flags > env vars > file > defaults
│       ├── _async.py           # asyncio.run() helper
│       ├── exceptions.py       # LumenError hierarchy with exit codes
│       ├── commands/
│       │   ├── search.py       # lumen search
│       │   ├── paper.py        # lumen paper, lumen cite
│       │   ├── author.py       # lumen author
│       │   ├── recommend.py    # lumen recommend
│       │   ├── export.py       # lumen export
│       │   ├── query.py        # lumen query
│       │   ├── zotero.py       # lumen zotero add / collections / new
│       │   ├── cache.py        # lumen cache stats / clean / clear
│       │   ├── init.py         # lumen init
│       │   └── doctor.py       # lumen doctor
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
