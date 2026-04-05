"""lumen export — export results to BibTeX, RIS, or CSL-JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

EXPORT_FORMATS = ("bibtex", "ris", "csl-json")


def export(
    ctx: typer.Context,
    fmt: Annotated[
        str,
        typer.Option(
            "--format", "-f", help=f"Bibliography format. ({', '.join(EXPORT_FORMATS)})"
        ),
    ] = "bibtex",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path. Defaults to stdout."),
    ] = None,
    query: Annotated[
        str | None,
        typer.Option(
            "--query", "-q", help="Run a search query and export its results."
        ),
    ] = None,
) -> None:
    """Export search results or piped paper data to a bibliography format.

    Reads paper JSON from stdin (piped from `lumen search --format json`)
    or runs a fresh query with --query. Outputs BibTeX, RIS, or CSL-JSON.

    Examples:

      lumen search "transformers" --format json | lumen export --format bibtex

      lumen export --query "BERT language model" --format ris --output refs.ris

      lumen paper 1706.03762 --format json | lumen export --format csl-json
    """
    # TODO: implement in Phase 3
    typer.echo(f"[stub] export: format={fmt!r}, output={output!r}, query={query!r}")
    raise typer.Exit()
