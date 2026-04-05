# justfile — lumen development workflow
# Requires: just, nix (with flakes), uv
# Entry point: `nix develop` (or direnv with `use flake .`) then `just <recipe>`

default:
  @just --list

# ── Setup ──────────────────────────────────────────────────────────────────────

# Install all dependencies and editable package into .venv
setup:
  uv sync
  @echo "Run 'uv run lumen --help' to verify."

# Install lumen as a tool (production-style, not editable)
install:
  uv tool install .

# Install lumen as an editable tool (changes take effect immediately)
install-dev:
  uv tool install --editable .

# ── Development ────────────────────────────────────────────────────────────────

# Run lumen (pass args after --: just run -- search "transformers")
run *args:
  uv run lumen {{ args }}

# Open a Python REPL with lumen on the path
repl:
  uv run python

# ── Code quality ───────────────────────────────────────────────────────────────

# Format source files with ruff
fmt:
  uv run ruff format src/ tests/

# Lint source files with ruff (auto-fix safe issues)
lint:
  uv run ruff check --fix src/ tests/

# Check formatting and lint without modifying files (CI-safe)
check:
  uv run ruff format --check src/ tests/
  uv run ruff check src/ tests/

# Run pyright type checks
types:
  uv run pyright src/

# Run all code quality checks (fmt + lint + types)
qa: check types

# ── Testing ────────────────────────────────────────────────────────────────────

# Run the full test suite
test:
  uv run pytest

# Run tests with verbose output
test-v:
  uv run pytest -v

# Run only unit tests (exclude integration)
test-unit:
  uv run pytest tests/ -m "not integration"

# Run tests with coverage report
cov:
  uv run pytest --cov=src/lumen --cov-report=term-missing

# Run tests for a single module (e.g.: just test-mod core/test_deduplication)
test-mod mod:
  uv run pytest tests/{{ mod }}.py -v

# ── Build & release ────────────────────────────────────────────────────────────

# Build a distributable wheel and sdist
build:
  uv build

# Publish to PyPI (requires PYPI_TOKEN env var or uv keyring config)
publish:
  uv publish

# ── Nix ────────────────────────────────────────────────────────────────────────

# Update flake.lock to latest nixpkgs
update:
  nix flake update

# Check the flake for evaluation errors
check-flake:
  nix flake check

# ── Utilities ──────────────────────────────────────────────────────────────────

# Remove build artifacts and caches
clean:
  rm -rf dist/ build/ .pytest_cache/ .ruff_cache/ .pyright/ htmlcov/ coverage.xml
  find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
  find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
  @echo "Cleaned."

# Wipe and reinstall the .venv (useful after dependency conflicts)
reset: clean
  rm -rf .venv
  uv sync
  @echo "Environment reset."

# Show all installed package versions
deps:
  uv pip list

# Run lumen doctor to check connectivity and credentials
doctor:
  uv run lumen doctor

# Run lumen init to configure credentials interactively
init:
  uv run lumen init
