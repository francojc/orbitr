"""orbitr cache — inspect and manage the local result cache."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from orbitr.core.cache import Cache

_VALID_TIERS = ("search", "paper", "citations", "all")

_err = Console(stderr=True)

app = typer.Typer(
    name="cache",
    help="Inspect and manage the local SQLite result cache.",
    no_args_is_help=True,
)


def _get_cache(ctx: typer.Context) -> Cache:
    cfg = ctx.obj.config
    return Cache(cfg.cache_dir / "cache.db")


@app.command("stats")
def cache_stats(ctx: typer.Context) -> None:
    """Show cache statistics (size, entry counts, TTL tiers).

    Displays the number of cached entries per tier (search, paper,
    citations), total disk usage, and the path to the cache file.

    Example:

      orbitr cache stats
    """
    cache = _get_cache(ctx)
    stats = cache.stats()
    cache.close()

    console = Console(no_color=ctx.obj.config.no_color)

    table = Table(title="Cache statistics", show_header=True, header_style="bold")
    table.add_column("Tier", style="bold")
    table.add_column("Entries", justify="right")

    for tier in ("search", "paper", "citations"):
        count = stats.entries_by_tier.get(tier, 0)
        table.add_row(tier, str(count))

    table.add_section()
    table.add_row("[bold]total[/bold]", str(stats.total_entries))

    console.print(table)
    size_kb = stats.size_bytes / 1024
    console.print(f"[dim]Path: {stats.db_path}  ({size_kb:.1f} KB)[/dim]")


@app.command("clean")
def cache_clean(
    ctx: typer.Context,
    tier: Annotated[
        str,
        typer.Option(
            "--tier",
            "-t",
            help="Tier to clean: search, paper, citations, or all.",
        ),
    ] = "all",
) -> None:
    """Remove expired entries from the cache.

    Only deletes entries whose TTL has elapsed. Safe to run at any time.

    Examples:

      orbitr cache clean

      orbitr cache clean --tier search
    """
    if tier not in _VALID_TIERS:
        _err.print(
            f"[red]Error:[/red] Invalid tier {tier!r}. "
            f"Choose: {', '.join(_VALID_TIERS)}"
        )
        raise typer.Exit(code=2)

    cache = _get_cache(ctx)
    removed = cache.clean(tier)  # type: ignore[arg-type]
    cache.close()

    console = Console(no_color=ctx.obj.config.no_color)
    tier_label = f" from tier [bold]{tier}[/bold]" if tier != "all" else ""
    noun = "entry" if removed == 1 else "entries"
    console.print(f"Removed [bold]{removed}[/bold] expired {noun}{tier_label}.")


@app.command("clear")
def cache_clear(
    ctx: typer.Context,
    tier: Annotated[
        str,
        typer.Option(
            "--tier",
            "-t",
            help="Tier to clear: search, paper, citations, or all.",
        ),
    ] = "all",
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Delete all cache entries (expired or not).

    Prompts for confirmation unless --yes is passed.

    Examples:

      orbitr cache clear

      orbitr cache clear --tier paper --yes
    """
    if tier not in _VALID_TIERS:
        _err.print(
            f"[red]Error:[/red] Invalid tier {tier!r}. "
            f"Choose: {', '.join(_VALID_TIERS)}"
        )
        raise typer.Exit(code=2)

    if not yes:
        scope = f"tier '{tier}'" if tier != "all" else "all tiers"
        confirmed = typer.confirm(f"Clear {scope}? This cannot be undone.")
        if not confirmed:
            raise typer.Abort()

    cache = _get_cache(ctx)
    removed = cache.clear(tier)  # type: ignore[arg-type]
    cache.close()

    console = Console(no_color=ctx.obj.config.no_color)
    tier_label = f" from tier [bold]{tier}[/bold]" if tier != "all" else ""
    noun = "entry" if removed == 1 else "entries"
    console.print(f"Cleared [bold]{removed}[/bold] {noun}{tier_label}.")
