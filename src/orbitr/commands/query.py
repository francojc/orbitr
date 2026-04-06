"""orbitr query — translate natural language to orbitr search query syntax."""

from __future__ import annotations

import re
from typing import Annotated

import typer
from rich.console import Console

_err = Console(stderr=True)

# ---------------------------------------------------------------------------
# Heuristic NL → query parser
# ---------------------------------------------------------------------------

_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")

# Common words that should not be mistaken for author surnames
_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "on",
        "in",
        "at",
        "to",
        "for",
        "and",
        "or",
        "but",
        "with",
        "by",
        "from",
        "about",
        "using",
        "based",
        "via",
        "towards",
        "toward",
        "between",
        "recent",
        "paper",
        "papers",
        "study",
        "approach",
        "method",
        "methods",
        "model",
        "models",
        "learning",
        "deep",
        "neural",
        "language",
        "natural",
        "machine",
        "large",
        "new",
        "novel",
        "efficient",
        "improved",
        "better",
    }
)


def _parse_natural(text: str) -> dict:
    """Extract structured fields from a natural-language query string.

    Heuristics applied in order:
    1. Find a four-digit year (1900–2099) and record it.
    2. If the token immediately before the year is a capitalised word
       that is not a stop word, treat it as an author surname.
    3. Everything remaining (minus stop words at the *start* of the
       string, e.g. "recent papers on …") forms the keyword query.

    Args:
        text: Raw natural language input from the user.

    Returns:
        dict with keys ``keywords``, ``author``, ``year_from``,
        ``year_to`` (all possibly None / empty string).
    """
    tokens = text.split()
    year: int | None = None
    year_idx: int | None = None

    for i, tok in enumerate(tokens):
        m = _YEAR_RE.match(tok.strip(".,;:"))
        if m:
            year = int(m.group(1))
            year_idx = i
            break

    # Author candidate: capitalised token immediately before the year
    author: str | None = None
    if year_idx is not None and year_idx > 0:
        prev = tokens[year_idx - 1].strip(".,;:")
        if prev and prev[0].isupper() and prev.lower() not in _STOP_WORDS:
            author = prev

    # Build keyword list, dropping year token, author token, and leading
    # filler phrases like "recent papers on …"
    skip: set[int] = set()
    if year_idx is not None:
        skip.add(year_idx)
    if author is not None and year_idx is not None:
        skip.add(year_idx - 1)

    raw_kws: list[str] = []
    for i, tok in enumerate(tokens):
        if i in skip:
            continue
        clean = tok.strip(".,;:'\"")
        if clean and clean.lower() not in _STOP_WORDS:
            raw_kws.append(clean)

    keywords = " ".join(raw_kws)

    return {
        "keywords": keywords,
        "author": author,
        "year_from": year,
        "year_to": year,
    }


def _build_command(parsed: dict) -> str:
    """Render a parsed query dict as a ``orbitr search …`` command string."""
    parts = ["orbitr search"]

    kw = parsed["keywords"]
    if kw:
        parts.append(f'"{kw}"' if " " in kw else kw)

    if parsed["author"]:
        parts.append(f'--author "{parsed["author"]}"')

    if parsed["year_from"]:
        parts.append(f"--from {parsed['year_from']}")

    if parsed["year_to"] and parsed["year_to"] != parsed["year_from"]:
        parts.append(f"--to {parsed['year_to']}")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Typer command
# ---------------------------------------------------------------------------


def query(
    ctx: typer.Context,
    natural: Annotated[
        str,
        typer.Argument(help="Natural language description of what you want to find."),
    ],
    run: Annotated[
        bool,
        typer.Option("--run", "-r", help="Execute the generated query immediately."),
    ] = False,
) -> None:
    """Translate a natural language description into a orbitr search query.

    Prints the equivalent ``orbitr search`` command. With --run, executes
    it immediately using the current configuration.

    Examples:

      orbitr query "recent papers on contrastive learning in NLP"

      orbitr query "Vaswani 2017 attention transformer" --run
    """
    parsed = _parse_natural(natural)

    if not parsed["keywords"] and not parsed["author"]:
        _err.print(
            "[red]Error:[/red] Could not extract any keywords from the input. "
            "Try a more descriptive phrase."
        )
        raise typer.Exit(code=2)

    cmd_str = _build_command(parsed)
    console = Console(no_color=ctx.obj.config.no_color)
    console.print(f"[dim]Generated:[/dim] {cmd_str}")

    if run:
        console.print()
        # Invoke the search command directly via Click's ctx.invoke,
        # passing the parsed Python values.
        from orbitr.commands.search import search as _search

        ctx.invoke(
            _search,
            query=parsed["keywords"] or "",
            author=parsed["author"],
            year_from=parsed["year_from"],
            year_to=parsed["year_to"],
        )
