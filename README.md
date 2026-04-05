# lumen

Academic literature search and reference management for the terminal. Search arXiv, Semantic Scholar, and Google Scholar; inspect papers and their citations; get recommendations; export bibliographies; and manage your Zotero library – all from the command line.

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
- [Error handling](#error-handling)
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
```

Verify the install:

```bash
lumen --version
```

### Development setup

`lumen` uses a [Nix flake](https://nixos.org/manual/nix/stable/command-ref/new-cli/nix3-flake.html) to pin the development environment (Python 3.12, uv, ruff, pyright) and [`just`](https://just.systems) as a task runner.

**Prerequisites:** Nix with flakes enabled, direnv, just.

```bash
git clone <repo-url> lumen
cd lumen                  # direnv activates the flake shell automatically
just setup                # uv sync inside the pinned environment
just run -- --help        # verify
```

If direnv is not installed, enter the shell manually:

```bash
nix develop
just setup
```

**Common tasks:**

```bash
just test        # run the full test suite
just cov         # test with coverage report
just check       # lint + format check (CI-safe, no writes)
just qa          # check + type check
just fmt         # auto-format source files
just doctor      # verify credentials and API connectivity
just run -- search "transformers"  # run lumen directly
```

Run `just` with no arguments to list all available recipes.

### API credentials

`lumen` works out of the box with no credentials. Providing them unlocks higher rate limits and Zotero integration.

| Variable | Purpose |
|---|---|
| `SEMANTIC_SCHOLAR_API_KEY` | Increased rate limits on Semantic Scholar |
| `ZOTERO_USER_ID` | Zotero library access |
| `ZOTERO_API_KEY` | Zotero library access (read/write) |

Run the guided setup to store credentials:

```bash
lumen init
```

Or set them manually in `~/.config/lumen/config.toml` (see [Configuration](#configuration)).

---

## Quick start

```bash
# Search for papers
lumen search "retrieval augmented generation"

# Narrow by field and date
lumen search --title "scaling laws" --year-from 2022

# Get full details on a paper
lumen paper 2005.14165 --source arxiv

# See what cites it
lumen cite 2005.14165 --source arxiv

# Find papers by an author
lumen author "Percy Liang"

# Get recommendations from a seed paper
lumen recommend "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"

# Export results as BibTeX
lumen search "in-context learning" --format json | lumen export --format bibtex --output refs.bib

# Add papers to Zotero
lumen zotero add "sparse mixture of experts" --collection "Reading/MoE"
```

---

## Global flags

These flags apply to every command.

| Flag | Short | Description |
|---|---|---|
| `--help` | `-h` | Show help for any command |
| `--version` | `-V` | Print version and exit |
| `--verbose` | `-v` | Show debug output and request details |
| `--quiet` | `-q` | Suppress all output except results and errors |
| `--no-color` | | Disable colored output (also respected via `NO_COLOR` env var) |
| `--config <path>` | | Use an alternate config file |

```bash
lumen --help
lumen search --help
lumen --version
lumen --no-color search "neural ODEs"
```

Every subcommand also accepts `--help` and prints a compact usage summary, option descriptions, and a short example.

---

## Commands

### `lumen search`

Search for papers across one or more sources. Supports both general keyword queries and field-specific filters; mix them freely.

```
lumen search [query] [options]
```

When `query` is omitted, at least one field flag (`--title`, `--author`, etc.) is required.

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--title <text>` | `-t` | | Match within paper titles |
| `--author <name>` | `-a` | | Match by author name |
| `--abstract <text>` | | | Match within abstracts |
| `--venue <name>` | | | Filter by journal or conference |
| `--year-from <year>` | | | Earliest publication year |
| `--year-to <year>` | | | Latest publication year |
| `--sources <list>` | `-s` | `arxiv,semantic_scholar` | Comma-separated sources: `arxiv`, `semantic_scholar`, `google_scholar` |
| `--max <n>` | `-n` | `10` | Maximum results to return |
| `--sort <by>` | | `relevance` | Sort order: `relevance`, `date`, `citations`, `impact` |
| `--format <fmt>` | `-f` | `table` | Output format: `table`, `list`, `json` |

```bash
# General keyword search
lumen search "diffusion models image generation"

# Field-specific filters
lumen search --author "Andrej Karpathy" --year-from 2021

# Combine keyword and filters
lumen search "RLHF" --venue "NeurIPS" --year-from 2022 --year-to 2023

# Widen sources and sort by citations
lumen search "vision transformer" \
  --sources arxiv,semantic_scholar,google_scholar \
  --sort citations --max 25

# Machine-readable output
lumen search "federated learning" --format json
```

**Deduplication and ranking:** results from multiple sources are automatically deduplicated (by DOI, arXiv ID, and title similarity) and ranked before display.

---

### `lumen paper`

Retrieve full metadata for a specific paper by its ID.

```
lumen paper <id> --source <source> [options]
```

**Arguments:**

| Argument | Description |
|---|---|
| `<id>` | arXiv ID (e.g. `2310.06825`) or Semantic Scholar paper ID |

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--source <src>` | `-s` | required | `arxiv` or `semantic_scholar` |
| `--format <fmt>` | `-f` | `detail` | `detail` or `json` |

```bash
lumen paper 2310.06825 --source arxiv

lumen paper 204e3073870fae3d05bcbc2f6a8e263d9b72e776 --source semantic_scholar

lumen paper 2310.06825 --source arxiv --format json
```

---

### `lumen cite`

List papers that cite a given paper.

```
lumen cite <id> [options]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--source <src>` | `-s` | `semantic_scholar` | Source for citation data |
| `--max <n>` | `-n` | `10` | Maximum citations to return |
| `--sort <by>` | | `date` | Sort order: `date`, `citations`, `relevance` |
| `--format <fmt>` | `-f` | `list` | `list` or `json` |

```bash
lumen cite 204e3073870fae3d05bcbc2f6a8e263d9b72e776

lumen cite 2005.14165 --source arxiv --max 50 --sort citations
```

---

### `lumen author`

Find papers by a specific author.

```
lumen author <name> [options]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--sources <list>` | `-s` | `arxiv,semantic_scholar` | Sources to query |
| `--max <n>` | `-n` | `10` | Maximum results |
| `--sort <by>` | | `date` | Sort order: `date`, `citations`, `relevance` |
| `--format <fmt>` | `-f` | `table` | `table`, `list`, or `json` |

```bash
lumen author "Emily M. Bender"

lumen author "Geoffrey Hinton" --max 50 --sort citations

lumen author "Percy Liang" --sources semantic_scholar --format json
```

Names are matched flexibly; partial last names and initials are supported.

---

### `lumen recommend`

Get paper recommendations based on one or more seed titles.

```
lumen recommend <title> [<title> ...] [options]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--method <m>` | `-m` | `hybrid` | Recommendation method: `content`, `citations`, `hybrid` |
| `--max <n>` | `-n` | `10` | Number of recommendations |
| `--sources <list>` | `-s` | `arxiv,semantic_scholar` | Candidate pool sources |
| `--format <fmt>` | `-f` | `list` | `list` or `json` |

**Methods:**

- `content` – similarity by title, abstract, and subject categories
- `citations` – co-citation patterns and citation velocity
- `hybrid` – weighted combination of content, citations, recency, and venue

```bash
lumen recommend "Attention Is All You Need"

lumen recommend "BERT" "RoBERTa" --method citations --max 20

lumen recommend "constitutional AI" --method hybrid --format json
```

---

### `lumen export`

Export one or more papers to a bibliography format. Accepts explicit paper IDs or reads from piped `lumen search --format json` output.

```
lumen export [<id>] [options]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--source <src>` | `-s` | required (unless piped) | Source for each ID; repeat for multiple |
| `--format <fmt>` | `-f` | `bibtex` | `bibtex`, `ris`, or `csl-json` |
| `--output <path>` | `-o` | stdout | File path to write output |
| `--append` | | false | Append to output file instead of overwriting |

```bash
# Single paper to stdout
lumen export 2310.06825 --source arxiv

# Multiple papers to file
lumen export 2310.06825 --source arxiv \
             2005.14165 --source arxiv \
  --format bibtex --output refs.bib

# Pipe from search results
lumen search "sparse attention" --sort citations --max 5 --format json \
  | lumen export --format bibtex --output sparse_attention.bib

# Append to an existing file
lumen export 2310.06825 --source arxiv --format bibtex --output refs.bib --append
```

---

### `lumen query`

Translate a plain-language description into an optimized search query for a specific source. Useful for understanding advanced query syntax before running a search.

```
lumen query <description> [options]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--target <src>` | `-t` | `arxiv` | Target source: `arxiv`, `semantic_scholar`, `google_scholar` |

```bash
lumen query "recent interpretability work on large language models"

lumen query "transformer models for protein folding since 2021" --target semantic_scholar
```

Output includes the suggested query string, a breakdown of how it was constructed, and alternative phrasings.

---

### `lumen zotero`

Manage your Zotero library. Requires `ZOTERO_USER_ID` and `ZOTERO_API_KEY` (set via `lumen init` or config file).

Run `lumen doctor` to verify your Zotero credentials before using these commands.

---

#### `lumen zotero add`

Add papers to your Zotero library by search query or explicit paper IDs.

```
lumen zotero add <query-or-id> [options]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--source <src>` | `-s` | auto-detect | Source when adding by ID |
| `--collection <path>` | `-c` | none | Target collection; supports nested paths (`Research/NLP`) |
| `--tags <list>` | `-t` | none | Comma-separated tags to apply |
| `--no-create` | | false | Fail if the target collection does not exist |
| `--no-auto-tag` | | false | Skip automatic source and category tagging |
| `--dry-run` | | false | Show what would be added without making changes |

Every paper added by `lumen` is automatically tagged `lumen` for tracking. Additional automatic tags include source (`source-arxiv`, `source-semantic_scholar`) and subject categories where available.

```bash
# Add by keyword query
lumen zotero add "mixture of experts" --collection "Reading/MoE" --tags "survey"

# Add a specific paper by arXiv ID
lumen zotero add 2310.06825 --source arxiv --collection "Reading List"

# Preview before committing
lumen zotero add "RLHF alignment" --collection "PhD/Ch2" --dry-run
```

---

#### `lumen zotero collections`

List collections in your Zotero library.

```
lumen zotero collections [options]
```

**Options:**

| Flag | Short | Description |
|---|---|---|
| `--filter <text>` | `-f` | Filter collection names by substring |
| `--lumen-only` | | Show only collections containing lumen-added papers |
| `--no-counts` | | Hide item counts |

```bash
lumen zotero collections

lumen zotero collections --filter "dissertation"

lumen zotero collections --lumen-only
```

Output is displayed as an indented hierarchy reflecting the collection tree in your library.

---

#### `lumen zotero new`

Create a new collection in your Zotero library.

```
lumen zotero new <name> [options]
```

Nested collections can be created in one step using `/` as a separator.

**Options:**

| Flag | Short | Description |
|---|---|---|
| `--parent <name>` | `-p` | Parent collection (alternative to `/` separator) |
| `--description <text>` | `-d` | Optional description |

```bash
lumen zotero new "PhD Research/Chapter 3/Methods"

lumen zotero new "Side Projects" --description "Exploratory reading, low priority"
```

---

### `lumen cache`

Manage the local result cache. Caching reduces redundant API calls and speeds up repeated queries. Three cache tiers are maintained independently: search results, individual papers, and citation lists.

```
lumen cache <subcommand>
```

| Subcommand | Description |
|---|---|
| `stats` | Show entry counts, hit/miss rates, and disk usage per tier |
| `clean` | Remove expired entries while keeping valid ones |
| `clear` | Wipe all cached data |

```bash
lumen cache stats
lumen cache clean
lumen cache clear
```

---

### `lumen init`

Interactive first-time setup. Guides you through storing API credentials and setting default preferences.

```
lumen init [options]
```

**Options:**

| Flag | Description |
|---|---|
| `--zotero` | Configure only Zotero credentials |
| `--apis` | Configure only academic API keys |
| `--defaults` | Set only default search preferences |
| `--reset` | Overwrite any existing configuration |

```bash
# Full guided setup
lumen init

# Re-configure Zotero only
lumen init --zotero
```

Credentials are written to `~/.config/lumen/config.toml`. Sensitive keys are stored under a `[credentials]` section and the file is created with `0600` permissions.

---

### `lumen doctor`

Check that `lumen` is correctly configured and all upstream services are reachable. Useful after initial setup or when troubleshooting errors.

```
lumen doctor [options]
```

**Options:**

| Flag | Description |
|---|---|
| `--fix` | Attempt to resolve detected issues automatically |

```bash
lumen doctor
```

**Checks performed:**

- Config file presence and validity
- arXiv API reachability and response time
- Semantic Scholar API reachability; key validity if configured
- Google Scholar reachability
- Zotero credentials validity and write permissions (if configured)
- Cache directory permissions and disk space
- `lumen` version vs. latest release

Example output:

```
lumen doctor

✓  Config         ~/.config/lumen/config.toml
✓  arXiv          reachable (143 ms)
✓  Semantic Scholar  reachable, API key valid (87 ms)
⚠  Google Scholar  reachable but rate-limited – consider reducing request frequency
✓  Zotero         credentials valid, read/write access confirmed
✓  Cache          ~/.cache/lumen (34 MB, 1 247 entries)
✓  Version        0.1.0 (up to date)

1 warning. Run `lumen doctor --fix` to apply suggestions.
```

---

## Configuration

`lumen` resolves settings in this order, with earlier sources taking precedence:

```
CLI flags  >  environment variables  >  config file  >  built-in defaults
```

### Config file

Location: `~/.config/lumen/config.toml` (XDG Base Directory compliant; override with `LUMEN_CONFIG` or `--config`).

```toml
[defaults]
sources     = "arxiv,semantic_scholar"
max_results = 10
sort_by     = "relevance"
format      = "table"

[cache]
enabled       = true
dir           = "~/.cache/lumen"
ttl_search    = 3600     # 1 hour
ttl_paper     = 86400    # 24 hours
ttl_citations = 21600    # 6 hours

[zotero]
auto_tag           = true
default_collection = ""

[credentials]
semantic_scholar_api_key = ""
zotero_user_id           = ""
zotero_api_key           = ""
```

### Environment variables

All settings have a `LUMEN_` equivalent that overrides the config file.

| Variable | Equivalent config key |
|---|---|
| `LUMEN_SOURCES` | `defaults.sources` |
| `LUMEN_MAX_RESULTS` | `defaults.max_results` |
| `LUMEN_FORMAT` | `defaults.format` |
| `LUMEN_CACHE_DIR` | `cache.dir` |
| `LUMEN_NO_CACHE` | disables caching entirely |
| `SEMANTIC_SCHOLAR_API_KEY` | `credentials.semantic_scholar_api_key` |
| `ZOTERO_USER_ID` | `credentials.zotero_user_id` |
| `ZOTERO_API_KEY` | `credentials.zotero_api_key` |
| `NO_COLOR` | disables all ANSI color output |
| `LUMEN_CONFIG` | path to alternate config file |

---

## Output formats

All commands that return paper data support `--format` / `-f`:

| Format | Description | Best for |
|---|---|---|
| `table` | Compact multi-column table with truncated fields | Interactive browsing |
| `list` | One paper per block, all fields labeled | Reading in the terminal |
| `detail` | Full single-paper view with wrapped abstract | `lumen paper` |
| `json` | Array of paper objects, newline-delimited | Scripting, piping, `jq` |

When stdout is not a TTY (i.e. output is piped or redirected), `lumen` defaults to `json` automatically unless `--format` is specified explicitly.

**Color and paging:**

- Color output is disabled when `NO_COLOR` is set or `--no-color` is passed.
- Long output is paged through `$PAGER` (defaulting to `less -R`) when stdout is a TTY. Disable with `LUMEN_NO_PAGER=1`.

---

## Piping and scripting

`lumen` follows Unix conventions to compose well with other tools.

- Results go to **stdout**; progress messages, warnings, and errors go to **stderr**.
- `--format json` always produces valid JSON regardless of TTY state.
- `lumen export` reads piped JSON from `lumen search` or `lumen author`.
- Use `--quiet` / `-q` to suppress progress output in scripts.

```bash
# Collect top-cited papers on a topic and export to BibTeX
lumen search "retrieval augmented generation" \
  --sort citations --max 10 --format json \
  | lumen export --format bibtex --output rag.bib

# Extract URLs with jq
lumen search "model merging" --format json \
  | jq -r '.[].url'

# Build a reading list CSV
lumen author "Danqi Chen" --format json \
  | jq -r '.[] | [.title, .published_date, .citation_count] | @csv' \
  > danqi_chen.csv

# Pipe into an external script
lumen search "continual learning" --format json | python triage.py
```

---

## Error handling

`lumen` writes errors to **stderr** and exits with a non-zero code. Error messages identify what failed, why, and what to do next.

**Examples:**

```
Error: Zotero credentials are not configured.

Set ZOTERO_USER_ID and ZOTERO_API_KEY, then re-run:
  lumen init --zotero

For help: lumen zotero --help
```

```
Error: arXiv returned no results for paper ID "9999.99999".

Check that the ID is correct:
  https://arxiv.org/abs/9999.99999

To search instead: lumen search "your query"
```

```
Error: Rate limit reached for Semantic Scholar (429).

lumen will retry automatically with backoff. To search only arXiv in the meantime:
  lumen search "your query" --sources arxiv
```

```
Error: --source is required when exporting by paper ID.

Usage: lumen export <id> --source <arxiv|semantic_scholar>
For help: lumen export --help
```

**Automatic retry:** transient network errors and rate-limit responses (429, 503) are retried with exponential backoff before surfacing as errors. Source failures are isolated – if one source fails, results from the remaining sources are still returned.

---

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | General error (network failure, API error, unexpected exception) |
| `2` | Usage error (missing argument, invalid option, bad combination) |
| `3` | Configuration error (missing credentials, invalid config file) |
| `4` | No results found |

---

## Shell completions

Generate and install completion scripts for your shell:

```bash
# Zsh
lumen --completion zsh > ~/.zfunc/_lumen
# add to ~/.zshrc: fpath=(~/.zfunc $fpath); autoload -Uz compinit && compinit

# Bash
lumen --completion bash > ~/.bash_completion.d/lumen
# add to ~/.bashrc: source ~/.bash_completion.d/lumen

# Fish
lumen --completion fish > ~/.config/fish/completions/lumen.fish
```

Completions cover subcommands, flags, and dynamic values where feasible (e.g. Zotero collection names for `--collection`).

---

## Project layout

```
lumen/
├── pyproject.toml
├── README.md
├── .env.example
├── src/
│   └── lumen/
│       ├── __init__.py
│       ├── cli.py              # Entry point and command tree (Typer)
│       ├── config.py           # Config file, env var, and defaults resolution
│       ├── commands/
│       │   ├── search.py       # search, author
│       │   ├── paper.py        # paper, cite
│       │   ├── recommend.py    # recommend, query
│       │   ├── export.py       # export
│       │   ├── zotero.py       # zotero add / collections / new
│       │   ├── cache.py        # cache stats / clean / clear
│       │   ├── init.py         # init
│       │   └── doctor.py       # doctor
│       ├── clients/
│       │   ├── arxiv.py
│       │   ├── semantic_scholar.py
│       │   └── google_scholar.py
│       ├── core/
│       │   ├── models.py       # Paper, Author, SearchResult
│       │   ├── deduplication.py
│       │   ├── ranking.py
│       │   ├── cache.py
│       │   └── export.py
│       ├── zotero/
│       │   └── client.py
│       └── display/
│           ├── table.py
│           ├── list.py
│           ├── detail.py
│           └── json.py
└── tests/
    ├── conftest.py
    ├── test_search.py
    ├── test_export.py
    ├── test_zotero.py
    └── test_cache.py
```

---

## Dependencies

| Package | Purpose |
|---|---|
| [`typer`](https://typer.tiangolo.com) | CLI framework; command tree, flags, completions |
| [`rich`](https://rich.readthedocs.io) | Terminal output: tables, panels, progress bars, color |
| [`httpx`](https://www.python-httpx.org) | Async HTTP client for API calls |
| [`pydantic`](https://docs.pydantic.dev) | Data models and validation |
| [`pyzotero`](https://pyzotero.readthedocs.io) | Zotero Web API client |
| [`feedparser`](https://feedparser.readthedocs.io) | arXiv Atom feed parsing |
| [`python-dateutil`](https://dateutil.readthedocs.io) | Flexible date parsing |
| [`beautifulsoup4`](https://www.crummy.com/software/BeautifulSoup/) | HTML parsing for Google Scholar |
| [`python-dotenv`](https://saurabh-kumar.com/python-dotenv/) | `.env` file loading |
