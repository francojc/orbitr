#!/usr/bin/env bash
# smoke_test.sh — live-API smoke tests for lumen v0.1.0
#
# Hits real arXiv and Semantic Scholar endpoints. Run manually before a release;
# not part of the pytest suite.
#
# Usage:
#   bash tests/smoke_test.sh
#   bash tests/smoke_test.sh --verbose    # print full output of each check
#
# Exit codes:
#   0  all checks passed
#   1  one or more checks failed

set -uo pipefail

VERBOSE=0
[[ "${1:-}" == "--verbose" ]] && VERBOSE=1

PASS=0
FAIL=0
SKIP=0

# ---- helpers ----------------------------------------------------------------

green()  { printf "\033[32m%s\033[0m" "$*"; }
red()    { printf "\033[31m%s\033[0m" "$*"; }
yellow() { printf "\033[33m%s\033[0m" "$*"; }
dim()    { printf "\033[2m%s\033[0m"  "$*"; }

check() {
  local label="$1"; shift
  local output exit_code

  output=$(eval "$@" 2>&1) && exit_code=0 || exit_code=$?

  if [[ $exit_code -eq 0 ]]; then
    printf "  %s %s\n" "$(green "✓")" "$label"
    (( PASS++ )) || true
  else
    printf "  %s %s\n" "$(red "✗")" "$label"
    (( FAIL++ )) || true
    if [[ $VERBOSE -eq 1 || $exit_code -ne 0 ]]; then
      printf "%s\n" "$output" | sed 's/^/      /'
    fi
  fi
}

check_contains() {
  local label="$1"; local pattern="$2"; shift 2
  local output exit_code
  output=$(eval "$@" 2>&1) && exit_code=0 || exit_code=$?
  if [[ $exit_code -eq 0 ]] && echo "$output" | grep -q "$pattern"; then
    printf "  %s %s\n" "$(green "✓")" "$label"
    (( PASS++ )) || true
  else
    printf "  %s %s %s\n" "$(red "✗")" "$label" "$(dim "(pattern: $pattern)")"
    (( FAIL++ )) || true
    [[ $VERBOSE -eq 1 ]] && printf "%s\n" "$output" | sed 's/^/      /'
  fi
}

skip() {
  printf "  %s %s\n" "$(yellow "–")" "$1"
  (( SKIP++ )) || true
}

section() { printf "\n$(dim "───") %s\n" "$1"; }

# ---- API availability note --------------------------------------------------
printf "\n%s\n" "$(dim 'Note: tests marked [API] may fail when arXiv is unavailable or')"
printf "%s\n" "$(dim 'Semantic Scholar is rate-limiting unauthenticated requests.')"
printf "%s\n\n" "$(dim 'Set SEMANTIC_SCHOLAR_API_KEY to resolve SS failures.')"

# ---- prerequisite -----------------------------------------------------------

section "Prerequisites"
check "lumen is on PATH" command -v lumen
check "--version returns 0" lumen --version

# ---- search -----------------------------------------------------------------

section "lumen search"
check_contains \
  "keyword search returns results (table)" \
  "Title" \
  'lumen search "transformer attention" --sources arxiv --limit 3 --no-cache'

check_contains \
  "single-source search (arxiv, field filter)" \
  "arXiv" \
  'lumen search "language model" --sources arxiv --limit 3 --no-cache'

check_contains \
  "--from year filter" \
  "201[789]\|202" \
  'lumen search "word embeddings" --from 2017 --limit 3 --no-cache'

check \
  "json output is valid JSON (ndjson)" \
  'lumen search "attention mechanism" --limit 2 --format json --no-cache | python3 -c "import json,sys; [json.loads(l) for l in sys.stdin if l.strip()]"'

check_contains \
  "piped output auto-switches to json" \
  '"title"' \
  'lumen search "graph neural networks" --limit 2 --no-cache | head -1'

check \
  "no-results exits 4 (arxiv only)" \
  'lumen --quiet search "xyzzy_nonexistent_term_zzz999" --sources arxiv --no-cache; [[ $? -eq 4 ]]'

# ---- paper ------------------------------------------------------------------

section "lumen paper"
check_contains \
  "fetch by arXiv ID" \
  "Attention Is All You Need\|transformer\|Vaswani" \
  'lumen paper 1706.03762 --no-cache'

check_contains \
  "fetch by arxiv: prefix" \
  "Attention Is All You Need\|transformer\|Vaswani" \
  'lumen paper arxiv:1706.03762 --no-cache'

check_contains \
  "detail format shows abstract" \
  "Abstract" \
  'lumen paper 1706.03762 --format detail --no-cache'

check \
  "json output is valid JSON" \
  'lumen paper 1706.03762 --format json --no-cache | python3 -c "import sys,json; json.loads(sys.stdin.read())"'

# ---- cite -------------------------------------------------------------------

section "lumen cite"
check_contains \
  "citations for transformer paper" \
  "Title\|title" \
  'lumen cite 1706.03762 --limit 3 --no-cache'

check \
  "cite json is valid ndjson" \
  'lumen cite 1706.03762 --limit 2 --format json --no-cache | python3 -c "import json,sys; [json.loads(l) for l in sys.stdin if l.strip()]"'

# ---- author -----------------------------------------------------------------

section "lumen author"
check_contains \
  "author search returns papers" \
  "Title\|title" \
  'lumen author "Vaswani" --limit 3 --no-cache'

check \
  "author json is valid ndjson" \
  'lumen author "LeCun" --limit 2 --format json --no-cache | python3 -c "import json,sys; [json.loads(l) for l in sys.stdin if l.strip()]"'

# ---- recommend --------------------------------------------------------------

section "lumen recommend"
# Recommendations require Semantic Scholar API access; may fail without a key.
check_contains \
  "recommendations for transformer paper" \
  "Title\|title" \
  'lumen recommend 1706.03762 --limit 3 --no-cache'

# ---- export -----------------------------------------------------------------

section "lumen export"
check_contains \
  "bibtex export via pipe" \
  "@article\|@misc" \
  'lumen search "word2vec" --limit 2 --format json --no-cache | lumen export --format bibtex'

check_contains \
  "ris export via pipe" \
  "^TY  -\|^TI  -" \
  'lumen search "BERT" --limit 2 --format json --no-cache | lumen export --format ris'

check_contains \
  "csl-json export via pipe" \
  '"title"\|"author"' \
  'lumen search "GPT" --limit 2 --format json --no-cache | lumen export --format csl-json'

check_contains \
  "direct --query export" \
  "@article\|@misc" \
  'lumen export --query "attention mechanism" --format bibtex'

check \
  "export to file" \
  'tmpf=$(mktemp /tmp/lumen_smoke_XXXXXX.bib); lumen search "transformers" --limit 2 --format json --no-cache | lumen export --format bibtex --output "$tmpf" && [[ -s "$tmpf" ]]; rm -f "$tmpf"'

# ---- query ------------------------------------------------------------------

section "lumen query"
check_contains \
  "NL query produces lumen search command" \
  "lumen search" \
  'lumen query "Vaswani attention 2017"'

# ---- cache ------------------------------------------------------------------

section "lumen cache"
check \
  "cache stats exits 0" \
  'lumen cache stats'

check \
  "cache clean exits 0" \
  'lumen cache clean'

check \
  "cache clear --yes exits 0" \
  'lumen cache clear --yes'

check \
  "cache clean --tier search exits 0" \
  'lumen cache clean --tier search'

# ---- doctor -----------------------------------------------------------------

section "lumen doctor"
check \
  "doctor exits 0 or 1 (not crash)" \
  'lumen doctor; code=$?; [[ $code -eq 0 || $code -eq 1 ]]'

# ---- piping -----------------------------------------------------------------

section "Pipe chains"
check \
  "search | jq titles" \
  'lumen search "neural networks" --limit 3 --format json --no-cache | python3 -c "import sys,json; [print(p[\"title\"]) for p in json.loads(\"[\"+\",\".join(sys.stdin)+\"]\")]"'

check_contains \
  "paper | export bibtex" \
  "@article\|@misc" \
  'lumen paper 1706.03762 --format json --no-cache | lumen export --format bibtex'

# ---- error handling ---------------------------------------------------------

section "Error handling"
check \
  "unknown format exits 2" \
  'lumen search "test" --format csv 2>/dev/null; [[ $? -eq 2 ]]'

check \
  "zotero without credentials exits 3" \
  'ZOTERO_USER_ID="" ZOTERO_API_KEY="" lumen zotero collections 2>/dev/null; [[ $? -eq 3 ]]'

# ---- summary ----------------------------------------------------------------

printf "\n$(dim "───────────────────────────────────────")\n"
printf "  %s passed   %s failed   %s skipped\n" \
  "$(green $PASS)" "$(red $FAIL)" "$(yellow $SKIP)"

[[ $FAIL -eq 0 ]]
