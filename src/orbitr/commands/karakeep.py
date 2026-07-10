"""Dedicated Karakeep bookmark search command."""

from __future__ import annotations

import sys
from typing import Annotated

import typer
from rich.console import Console

from orbitr._async import run
from orbitr.clients.karakeep import KarakeepClient
from orbitr.config import VALID_FORMATS, normalize_server_url
from orbitr.display import effective_format, render
from orbitr.exceptions import ConfigError, NoResultsError, SourceError, UsageError

_err = Console(stderr=True)
app = typer.Typer(
    name="karakeep",
    help="Search your private Karakeep bookmark library.",
    no_args_is_help=True,
)


@app.command("search")
def search(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(help="Bookmark search query.")],
    server: Annotated[
        str | None,
        typer.Option("--server", help="Override the configured Karakeep server URL."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", min=1, max=100, help="Maximum bookmarks."),
    ] = 10,
    fmt: Annotated[
        str | None,
        typer.Option(
            "--format", "-f", help="Output format: table, list, detail, json."
        ),
    ] = None,
) -> None:
    """Search saved Karakeep bookmarks without changing academic search.

    Examples:

      orbitr karakeep search "transformer"

      orbitr karakeep search "reading list" --limit 20 --format json | jq .title

      orbitr karakeep search "papers" --server https://keep.example.org
    """
    cfg = ctx.obj.config
    effective_fmt = effective_format(fmt, cfg.format)
    if effective_fmt not in VALID_FORMATS:
        _err.print(
            f"[red]Error:[/red] Unknown format {effective_fmt!r}. "
            f"Choose: {', '.join(VALID_FORMATS)}."
        )
        raise typer.Exit(code=2)
    server_url = server or cfg.credentials.karakeep_server_url
    try:
        if not cfg.credentials.karakeep_api_key:
            raise ConfigError(
                "Karakeep API key is not configured.",
                suggestion="Run `orbitr init` or set KARAKEEP_API_KEY.",
            )
        try:
            server_url = normalize_server_url(server_url)
        except ValueError as exc:
            raise ConfigError(
                "Karakeep server URL is invalid.",
                suggestion="Set KARAKEEP_SERVER_URL to an http(s) URL, or use `--server`.",
            ) from exc
        result = run(
            _search_async(
                cfg.credentials.karakeep_api_key,
                server_url,
                query,
                limit,
            )
        )
    except ConfigError as exc:
        _print_error(exc)
        raise typer.Exit(code=3) from exc
    except NoResultsError as exc:
        _err.print(f"[yellow]No results found.[/yellow] {exc.suggestion}")
        raise typer.Exit(code=4) from None
    except (SourceError, UsageError) as exc:
        _print_error(exc)
        raise typer.Exit(code=1 if isinstance(exc, SourceError) else 2) from exc

    console = Console(no_color=cfg.no_color)
    pager = sys.stdout.isatty() and not cfg.no_pager
    render(result.papers, fmt=effective_fmt, console=console, pager=pager)  # type: ignore[arg-type]


async def _search_async(api_key: str, server_url: str, query: str, limit: int):
    """Fetch and validate one Karakeep search."""
    result = await KarakeepClient(api_key, server_url).search_bookmarks(query, limit)
    if not result.papers:
        raise NoResultsError(
            "No Karakeep bookmarks matched the query.",
            suggestion="Try broader keywords or check the configured server.",
        )
    return result


def _print_error(exc: ConfigError | SourceError | UsageError) -> None:
    """Print a safe diagnostic to stderr."""
    _err.print(f"[red]Error:[/red] {exc.message}")
    if exc.suggestion:
        _err.print(f"[dim]{exc.suggestion}[/dim]")
