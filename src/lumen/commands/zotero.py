"""lumen zotero — Zotero library integration (add, collections, new)."""

from __future__ import annotations

from typing import Annotated

import typer

app = typer.Typer(
    name="zotero",
    help="Manage your Zotero library from the terminal.",
    no_args_is_help=True,
)


@app.command("add")
def zotero_add(
    ctx: typer.Context,
    paper_id: Annotated[
        str, typer.Argument(help="Paper ID (arXiv ID, DOI, or Semantic Scholar ID).")
    ],
    collection: Annotated[
        str | None,
        typer.Option(
            "--collection", "-c", help="Collection name or key to add the paper to."
        ),
    ] = None,
    tags: Annotated[
        str | None,
        typer.Option("--tags", "-t", help="Comma-separated tags to apply."),
    ] = None,
) -> None:
    """Add a paper to your Zotero library.

    Fetches paper metadata and creates a Zotero item. Optionally places
    it in a named collection and applies tags.

    Examples:

      lumen zotero add 1706.03762

      lumen zotero add 1706.03762 --collection "Transformers" --tags "nlp,attention"
    """
    # TODO: implement in Phase 3
    typer.echo(
        f"[stub] zotero add: {paper_id!r} (collection={collection!r}, tags={tags!r})"
    )
    raise typer.Exit()


@app.command("collections")
def zotero_collections(
    ctx: typer.Context,
    fmt: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: table or json."),
    ] = "table",
) -> None:
    """List all collections in your Zotero library.

    Examples:

      lumen zotero collections

      lumen zotero collections --format json
    """
    # TODO: implement in Phase 3
    typer.echo(f"[stub] zotero collections (format={fmt!r})")
    raise typer.Exit()


@app.command("new")
def zotero_new(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name for the new collection.")],
    parent: Annotated[
        str | None,
        typer.Option(
            "--parent",
            "-p",
            help="Parent collection name or key (creates nested collection).",
        ),
    ] = None,
) -> None:
    """Create a new collection in your Zotero library.

    Examples:

      lumen zotero new "Deep Learning 2024"

      lumen zotero new "Attention" --parent "Transformers"
    """
    # TODO: implement in Phase 3
    typer.echo(f"[stub] zotero new: {name!r} (parent={parent!r})")
    raise typer.Exit()
