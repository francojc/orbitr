"""orbitr export — export results to BibTeX, RIS, or CSL-JSON."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from orbitr._async import run
from orbitr.core.export import ExportFormat
from orbitr.core.export import export as fmt_export
from orbitr.core.models import Paper, SearchResult
from orbitr.exceptions import LumenError, NoResultsError, SourceError

logger = logging.getLogger(__name__)

_err = Console(stderr=True)

EXPORT_FORMATS = ("bibtex", "ris", "csl-json")


def export(
    ctx: typer.Context,
    fmt: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help=f"Bibliography format. ({', '.join(EXPORT_FORMATS)})",
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

    Reads paper JSON from stdin (piped from ``orbitr search --format json``)
    or runs a fresh query with --query. Outputs BibTeX, RIS, or CSL-JSON.

    Examples:

      orbitr search "transformers" --format json | orbitr export --format bibtex

      orbitr export --query "BERT language model" --format ris --output refs.ris

      orbitr paper 1706.03762 --format json | orbitr export --format csl-json
    """
    cfg = ctx.obj.config

    if fmt not in EXPORT_FORMATS:
        _err.print(
            f"[red]Error:[/red] Invalid format {fmt!r}. "
            f"Choose: {', '.join(EXPORT_FORMATS)}"
        )
        raise typer.Exit(code=2)

    if query:
        # Run a fresh search and export the results
        try:
            run(_export_query_async(query=query, fmt=fmt, output=output, cfg=cfg))
        except NoResultsError as exc:
            if not cfg.quiet:
                Console(no_color=cfg.no_color).print(
                    f"[yellow]No results found.[/yellow] {exc.suggestion}"
                )
            raise typer.Exit(code=4) from None
        except SourceError as exc:
            _err.print(f"[red]Error:[/red] {exc.message}")
            if exc.suggestion:
                _err.print(f"[dim]{exc.suggestion}[/dim]")
            raise typer.Exit(code=1) from exc
        except LumenError as exc:
            _err.print(f"[red]Error:[/red] {exc.message}")
            if exc.suggestion:
                _err.print(f"[dim]{exc.suggestion}[/dim]")
            raise typer.Exit(code=1) from exc
        return

    # Read ndjson from stdin
    if sys.stdin.isatty():
        _err.print("[red]Error:[/red] No input provided.")
        _err.print(
            "[dim]Pipe results with `orbitr search 'query' --format json | orbitr export`, "
            "or run a search with `--query 'keywords'`.[/dim]"
        )
        raise typer.Exit(code=2)

    papers: list[Paper] = []
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            papers.append(Paper.model_validate_json(line))
        except Exception:
            logger.debug("Skipping unparseable line: %r", line[:80])

    if not papers:
        if not cfg.quiet:
            Console(no_color=cfg.no_color).print(
                "[yellow]No papers found in input.[/yellow] "
                "[dim]Check that the piped data contains valid orbitr JSON.[/dim]"
            )
        raise typer.Exit(code=4)

    _write_export(papers, fmt=fmt, output=output, cfg=cfg)  # type: ignore[arg-type]


async def _export_query_async(
    *, query: str, fmt: str, output: Path | None, cfg
) -> None:
    """Run a search query and export the results."""
    from orbitr.clients.arxiv import ArxivClient
    from orbitr.clients.semantic_scholar import SemanticScholarClient
    from orbitr.core.deduplication import deduplicate

    api_key = cfg.credentials.semantic_scholar_api_key
    limit = cfg.max_results

    results = await asyncio.gather(
        ArxivClient().search(query, max_results=limit),
        SemanticScholarClient(api_key=api_key).search(query, max_results=limit),
        return_exceptions=True,
    )

    papers: list[Paper] = []
    errors: list[Exception] = []
    for r in results:
        if isinstance(r, SearchResult):
            papers.extend(r.papers)
        elif isinstance(r, Exception):
            errors.append(r)

    if not papers and errors:
        raise SourceError(
            f"All sources failed for query '{query}'.",
            suggestion="Check your network connection and try again.",
        )

    papers = deduplicate(papers)

    if not papers:
        raise NoResultsError(
            f"No results found for '{query}'.",
            suggestion="Try a broader query.",
        )

    _write_export(papers, fmt=fmt, output=output, cfg=cfg)  # type: ignore[arg-type]


def _write_export(
    papers: list[Paper], *, fmt: ExportFormat, output: Path | None, cfg
) -> None:
    """Format papers and write to stdout or a file."""
    text = fmt_export(papers, fmt)

    if output:
        output.write_text(text, encoding="utf-8")
        Console(no_color=cfg.no_color).print(
            f"Exported [bold]{len(papers)}[/bold] paper(s) to [bold]{output}[/bold]."
        )
    else:
        sys.stdout.write(text)
