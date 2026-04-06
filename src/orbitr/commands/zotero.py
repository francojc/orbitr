"""orbitr zotero — Zotero library integration (add, collections, new)."""

from __future__ import annotations

import json
import logging
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from orbitr._async import run
from orbitr.commands.paper import fetch_paper
from orbitr.exceptions import ConfigError, LumenError, SourceError
from orbitr.zotero.client import ZoteroClient

logger = logging.getLogger(__name__)

_err = Console(stderr=True)

app = typer.Typer(
    name="zotero",
    help="Manage your Zotero library from the terminal.",
    no_args_is_help=True,
)


def _get_zotero(ctx: typer.Context) -> ZoteroClient:
    """Build a ZoteroClient from the resolved config credentials."""
    cfg = ctx.obj.config
    return ZoteroClient(
        user_id=cfg.credentials.zotero_user_id,
        api_key=cfg.credentials.zotero_api_key,
    )


# ---------------------------------------------------------------------------
# orbitr zotero add
# ---------------------------------------------------------------------------


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
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Bypass the local paper cache."),
    ] = False,
) -> None:
    """Add a paper to your Zotero library.

    Fetches paper metadata and creates a Zotero item. Optionally places
    it in a named collection and applies tags.

    Examples:

      orbitr zotero add 1706.03762

      orbitr zotero add 1706.03762 --collection "Transformers" --tags "nlp,attention"
    """
    cfg = ctx.obj.config
    try:
        run(
            _zotero_add_async(
                paper_id=paper_id,
                collection=collection,
                tags=tags,
                no_cache=no_cache or cfg.no_cache,
                cfg=cfg,
            )
        )
    except ConfigError as exc:
        _err.print(f"[red]Error:[/red] {exc.message}")
        if exc.suggestion:
            _err.print(exc.suggestion)
        raise typer.Exit(code=3) from exc
    except SourceError as exc:
        _err.print(f"[red]Error:[/red] {exc.message}")
        if exc.suggestion:
            _err.print(exc.suggestion)
        raise typer.Exit(code=1) from exc
    except LumenError as exc:
        _err.print(f"[red]Error:[/red] {exc.message}")
        raise typer.Exit(code=1) from exc


async def _zotero_add_async(
    *, paper_id: str, collection: str | None, tags: str | None, no_cache: bool, cfg
) -> None:
    """Fetch paper metadata then create a Zotero item."""
    console = Console(no_color=cfg.no_color)

    # Fetch paper
    paper = await fetch_paper(paper_id, cfg=cfg, no_cache=no_cache)

    # Build Zotero client (raises ConfigError if credentials missing)
    zot = ZoteroClient(
        user_id=cfg.credentials.zotero_user_id,
        api_key=cfg.credentials.zotero_api_key,
    )

    # Resolve collection key
    collection_key: str | None = None
    if collection:
        collection_key = zot.find_collection_key(collection)
        if collection_key is None:
            # Treat as a raw key if it looks like one, else warn
            if len(collection) == 8 and collection.isalnum():
                collection_key = collection
            else:
                _err.print(
                    f"[yellow]Warning:[/yellow] Collection '{collection}' not found; "
                    "adding without collection."
                )

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    resp = zot.add_paper(paper, collection_key=collection_key, tags=tag_list)
    item_key = (resp.get("success") or {}).get("0", "?")

    console.print(
        f"[green]✓[/green] Added [bold]{paper.title[:60]}[/bold] "
        f"to Zotero (key: [dim]{item_key}[/dim])"
    )
    if collection_key:
        console.print(f"  Collection: [dim]{collection}[/dim]")
    if tag_list:
        console.print(f"  Tags: [dim]{', '.join(tag_list)}[/dim]")


# ---------------------------------------------------------------------------
# orbitr zotero collections
# ---------------------------------------------------------------------------


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

      orbitr zotero collections

      orbitr zotero collections --format json
    """
    cfg = ctx.obj.config
    try:
        zot = _get_zotero(ctx)
        collections = zot.list_collections()
    except ConfigError as exc:
        _err.print(f"[red]Error:[/red] {exc.message}")
        if exc.suggestion:
            _err.print(exc.suggestion)
        raise typer.Exit(code=3) from exc
    except LumenError as exc:
        _err.print(f"[red]Error:[/red] {exc.message}")
        raise typer.Exit(code=1) from exc

    if not collections:
        Console(no_color=cfg.no_color).print("[yellow]No collections found.[/yellow]")
        raise typer.Exit()

    if fmt == "json":
        typer.echo(json.dumps([c.get("data", c) for c in collections], indent=2))
        return

    console = Console(no_color=cfg.no_color)
    table = Table(title="Zotero collections", show_header=True, header_style="bold")
    table.add_column("Key", style="dim", width=10)
    table.add_column("Name")
    table.add_column("Parent", style="dim")

    for coll in collections:
        data = coll.get("data", coll)
        key = data.get("key", coll.get("key", ""))
        name = data.get("name", "")
        parent = data.get("parentCollection") or ""
        if parent is False:
            parent = ""
        table.add_row(key, name, str(parent))

    console.print(table)


# ---------------------------------------------------------------------------
# orbitr zotero new
# ---------------------------------------------------------------------------


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

      orbitr zotero new "Deep Learning 2024"

      orbitr zotero new "Attention" --parent "Transformers"
    """
    cfg = ctx.obj.config
    try:
        zot = _get_zotero(ctx)

        parent_key: str | None = None
        if parent:
            parent_key = zot.find_collection_key(parent)
            if parent_key is None:
                _err.print(f"[red]Error:[/red] Parent collection '{parent}' not found.")
                _err.print(
                    "[dim]Run `orbitr zotero collections` to list available collections.[/dim]"
                )
                raise typer.Exit(code=1)

        resp = zot.create_collection(name, parent_key=parent_key)
        coll_key = (resp.get("success") or {}).get("0", "?")

        console = Console(no_color=cfg.no_color)
        console.print(
            f"[green]✓[/green] Created collection [bold]{name}[/bold] "
            f"(key: [dim]{coll_key}[/dim])"
        )
        if parent_key:
            console.print(f"  Parent: [dim]{parent}[/dim]")

    except ConfigError as exc:
        _err.print(f"[red]Error:[/red] {exc.message}")
        if exc.suggestion:
            _err.print(f"[dim]{exc.suggestion}[/dim]")
        raise typer.Exit(code=3) from exc
    except LumenError as exc:
        _err.print(f"[red]Error:[/red] {exc.message}")
        if exc.suggestion:
            _err.print(f"[dim]{exc.suggestion}[/dim]")
        raise typer.Exit(code=1) from exc
