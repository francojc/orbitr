"""lumen cache — inspect and manage the local result cache."""

from __future__ import annotations

from typing import Annotated

import typer

app = typer.Typer(
    name="cache",
    help="Inspect and manage the local SQLite result cache.",
    no_args_is_help=True,
)


@app.command("stats")
def cache_stats(ctx: typer.Context) -> None:
    """Show cache statistics (size, entry counts, TTL tiers).

    Displays the number of cached entries per tier (search, paper,
    citations), total disk usage, and oldest/newest entry timestamps.

    Example:

      lumen cache stats
    """
    # TODO: implement in Phase 3
    typer.echo("[stub] cache stats")
    raise typer.Exit()


@app.command("clean")
def cache_clean(
    ctx: typer.Context,
    tier: Annotated[
        str,
        typer.Option(
            "--tier", "-t", help="Tier to clean: search, paper, citations, or all."
        ),
    ] = "all",
) -> None:
    """Remove expired entries from the cache.

    Only deletes entries whose TTL has elapsed. Safe to run at any time.

    Examples:

      lumen cache clean

      lumen cache clean --tier search
    """
    # TODO: implement in Phase 3
    typer.echo(f"[stub] cache clean (tier={tier!r})")
    raise typer.Exit()


@app.command("clear")
def cache_clear(
    ctx: typer.Context,
    tier: Annotated[
        str,
        typer.Option(
            "--tier", "-t", help="Tier to clear: search, paper, citations, or all."
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

      lumen cache clear

      lumen cache clear --tier paper --yes
    """
    # TODO: implement in Phase 3
    typer.echo(f"[stub] cache clear (tier={tier!r}, yes={yes})")
    raise typer.Exit()
