"""lumen query — translate natural language to lumen query syntax."""

from __future__ import annotations

from typing import Annotated

import typer


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
    """Translate a natural language description into a lumen search query.

    Prints the equivalent `lumen search` command. With --run, executes
    it immediately.

    Examples:

      lumen query "recent papers on contrastive learning in NLP"

      lumen query "Vaswani 2017 attention transformer" --run
    """
    # TODO: implement in Phase 3
    typer.echo(f"[stub] query: {natural!r} (run={run})")
    raise typer.Exit()
