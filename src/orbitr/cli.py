"""Root Typer application: global flags, command registration, entry point."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import typer
from rich.console import Console

from orbitr import __version__
from orbitr.commands import (
    author,
    cache,
    doctor,
    export,
    init,
    paper,
    query,
    recommend,
    search,
    zotero,
)

app = typer.Typer(
    name="orbitr",
    help="Search academic literature across arXiv and Semantic Scholar.",
    add_completion=True,
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True)


def _version_callback(value: bool) -> None:
    """Eager callback that prints version and exits immediately."""
    if value:
        console.print(f"orbitr {__version__}")
        raise typer.Exit()


@dataclass
class AppState:
    """Global application state, injected into the Typer context object."""

    verbose: bool = False
    quiet: bool = False
    no_color: bool = False
    config_path: Path | None = None
    config: dict = field(default_factory=dict)


@app.callback()
def _callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output.",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress non-essential output.",
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Disable color output (also: NO_COLOR env var).",
        envvar="NO_COLOR",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Path to config file (default: ~/.config/orbitr/config.toml).",
        show_default=False,
        exists=False,
    ),
) -> None:
    """orbitr — academic literature search from the terminal."""
    ctx.ensure_object(AppState)
    state: AppState = ctx.obj
    state.verbose = verbose
    state.quiet = quiet
    state.no_color = no_color or bool(os.environ.get("NO_COLOR"))
    state.config_path = config

    from orbitr.config import load_config

    state.config = load_config(  # type: ignore[assignment]
        path=config,
        no_color=state.no_color,
        verbose=verbose,
        quiet=quiet,
    )


# ------------------------------------------------------------------
# Single commands
# ------------------------------------------------------------------
app.command("search")(search.search)
app.command("paper")(paper.paper)
app.command("cite")(paper.cite)
app.command("author")(author.author)
app.command("recommend")(recommend.recommend)
app.command("query")(query.query)
app.command("export")(export.export)
app.command("init")(init.init)
app.command("doctor")(doctor.doctor)

# ------------------------------------------------------------------
# Subcommand groups
# ------------------------------------------------------------------
app.add_typer(zotero.app, name="zotero")
app.add_typer(cache.app, name="cache")


def main() -> None:
    """CLI entry point (referenced by pyproject.toml [project.scripts])."""
    app()
