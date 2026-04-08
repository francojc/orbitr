"""orbitr zotero — Zotero library integration (add, collections, new, list, get, search, export-md)."""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from orbitr._async import run
from orbitr.commands.paper import fetch_paper
from orbitr.exceptions import ConfigError, LumenError, SourceError
from orbitr.zotero.client import ZoteroClient

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_VALID_SORTS = {"dateModified", "title", "date"}
_VALID_LIST_FMTS = {"table", "json", "keys"}
_VALID_GET_FMTS = {"detail", "json"}


def _item_year(data: dict) -> str:
    """Extract a 4-digit year string from a Zotero item data dict."""
    raw = data.get("date", "")
    m = re.search(r"\b(\d{4})\b", raw)
    return m.group(1) if m else ""


def _item_authors(data: dict, max_authors: int = 1) -> str:
    """Return a short author string (first author + 'et al.' when needed)."""
    creators = [c for c in data.get("creators", []) if c.get("creatorType") == "author"]
    if not creators:
        return ""
    names = []
    for c in creators:
        if c.get("lastName"):
            names.append(c["lastName"])
        else:
            names.append(c.get("name", ""))
    if len(names) > max_authors:
        return f"{names[0]} et al."
    return ", ".join(names)


def _item_authors_full(data: dict) -> str:
    """Return a full comma-joined author string."""
    creators = [c for c in data.get("creators", []) if c.get("creatorType") == "author"]
    parts = []
    for c in creators:
        if c.get("firstName") and c.get("lastName"):
            parts.append(f"{c['firstName']} {c['lastName']}")
        elif c.get("lastName"):
            parts.append(c["lastName"])
        else:
            parts.append(c.get("name", ""))
    return ", ".join(parts)


def _strip_html(text: str) -> str:
    """Remove HTML tags from a Zotero note string."""
    return re.sub(r"<[^>]+>", "", text).strip()


def _item_table(items: list[dict], title: str = "Zotero items") -> Table:
    """Build a Rich Table for a list of raw Zotero item dicts."""
    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("Key", style="dim", width=10)
    table.add_column("Title", max_width=60)
    table.add_column("Authors", max_width=24)
    table.add_column("Year", width=6)
    table.add_column("Type", width=16)
    for item in items:
        data = item.get("data", item)
        key = data.get("key", item.get("key", ""))
        title_str = (data.get("title") or "")[:60]
        authors = _item_authors(data)
        year = _item_year(data)
        item_type = data.get("itemType", "")
        table.add_row(key, title_str, authors, year, item_type)
    return table


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


# ---------------------------------------------------------------------------
# orbitr zotero list
# ---------------------------------------------------------------------------


@app.command("list")
def zotero_list(
    ctx: typer.Context,
    collection: Annotated[
        str | None,
        typer.Option("--collection", "-c", help="Collection name or key to browse."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of items to return."),
    ] = 25,
    sort: Annotated[
        str,
        typer.Option("--sort", help="Sort field: dateModified, title, date."),
    ] = "dateModified",
    fmt: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: table, json, keys."),
    ] = "table",
) -> None:
    """Browse items in your Zotero library or a specific collection.

    Examples:

      orbitr zotero list

      orbitr zotero list -c "NLP" -n 50

      orbitr zotero list -c "NLP" --format keys | xargs -I{} orbitr zotero get {}
    """
    if sort not in _VALID_SORTS:
        _err.print(
            f"[red]Error:[/red] Unknown sort '{sort}'. Choose: {', '.join(sorted(_VALID_SORTS))}"
        )
        raise typer.Exit(code=2)
    if fmt not in _VALID_LIST_FMTS:
        _err.print(
            f"[red]Error:[/red] Unknown format '{fmt}'. Choose: {', '.join(sorted(_VALID_LIST_FMTS))}"
        )
        raise typer.Exit(code=2)

    cfg = ctx.obj.config
    try:
        zot = _get_zotero(ctx)

        # Resolve collection name to key
        collection_key: str | None = None
        if collection:
            collection_key = zot.find_collection_key(collection)
            if collection_key is None:
                if len(collection) == 8 and collection.isalnum():
                    collection_key = collection
                else:
                    _err.print(
                        f"[red]Error:[/red] Collection '{collection}' not found."
                    )
                    _err.print(
                        "[dim]Run `orbitr zotero collections` to list collections.[/dim]"
                    )
                    raise typer.Exit(code=1)

        items = zot.list_items(
            collection_key=collection_key,
            limit=limit,
            sort=sort,
        )
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

    if not items:
        Console(no_color=cfg.no_color).print("[yellow]No items found.[/yellow]")
        raise typer.Exit(code=4)

    if fmt == "keys":
        for item in items:
            data = item.get("data", item)
            typer.echo(data.get("key", item.get("key", "")))
        return

    if fmt == "json":
        typer.echo(json.dumps([item.get("data", item) for item in items], indent=2))
        return

    scope = f" in '{collection}'" if collection else ""
    Console(no_color=cfg.no_color).print(
        _item_table(items, title=f"Zotero items{scope}")
    )


# ---------------------------------------------------------------------------
# orbitr zotero get
# ---------------------------------------------------------------------------


@app.command("get")
def zotero_get(
    ctx: typer.Context,
    item_key: Annotated[
        str, typer.Argument(help="Zotero item key (8-character alphanumeric).")
    ],
    fmt: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: detail or json."),
    ] = "detail",
    notes: Annotated[
        bool,
        typer.Option("--notes/--no-notes", help="Include or exclude Zotero notes."),
    ] = True,
) -> None:
    """Show full metadata and notes for a single Zotero item.

    Examples:

      orbitr zotero get ABCD1234

      orbitr zotero get ABCD1234 --format json

      orbitr zotero get ABCD1234 --no-notes
    """
    if fmt not in _VALID_GET_FMTS:
        _err.print(
            f"[red]Error:[/red] Unknown format '{fmt}'. Choose: {', '.join(sorted(_VALID_GET_FMTS))}"
        )
        raise typer.Exit(code=2)

    cfg = ctx.obj.config
    try:
        zot = _get_zotero(ctx)
        result = zot.get_item(item_key, include_children=notes)
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

    if fmt == "json":
        typer.echo(json.dumps(result, indent=2))
        return

    # detail format
    from rich.panel import Panel

    console = Console(no_color=cfg.no_color)
    data = result["meta"].get("data", result["meta"])

    title = data.get("title") or "(no title)"
    authors = _item_authors_full(data)
    year = _item_year(data)
    venue = data.get("publicationTitle") or data.get("bookTitle") or ""
    doi = data.get("DOI") or ""
    url = data.get("url") or ""
    abstract = data.get("abstractNote") or ""
    tags = ", ".join(t["tag"] for t in data.get("tags", []) if t.get("tag"))
    item_type = data.get("itemType", "")

    lines = []
    if authors:
        lines.append(f"[bold]Authors:[/bold]  {authors}")
    meta_parts = []
    if year:
        meta_parts.append(f"Year: {year}")
    if item_type:
        meta_parts.append(f"Type: {item_type}")
    if venue:
        meta_parts.append(f"Venue: {venue}")
    if meta_parts:
        lines.append("[bold]Meta:[/bold]     " + " | ".join(meta_parts))
    if doi:
        lines.append(f"[bold]DOI:[/bold]      {doi}")
    if url:
        lines.append(f"[bold]URL:[/bold]      {url}")
    if tags:
        lines.append(f"[bold]Tags:[/bold]     {tags}")
    if abstract:
        lines.append("")
        lines.append("[bold]Abstract:[/bold]")
        lines.append(abstract)

    # PDF attachment path
    pdfs = [
        a for a in result["attachments"] if "pdf" in a.get("content_type", "").lower()
    ]
    if pdfs:
        lines.append("")
        lines.append(
            f"[bold]PDF:[/bold]      {pdfs[0].get('path') or pdfs[0].get('filename')}"
        )

    if notes and result["notes"]:
        lines.append("")
        lines.append("[bold]Notes:[/bold]")
        for note in result["notes"]:
            clean = _strip_html(note)
            if clean:
                lines.append(f"  {clean}")

    body = "\n".join(lines)
    console.print(Panel(body, title=f"[bold]{title[:72]}[/bold]", expand=False))


# ---------------------------------------------------------------------------
# orbitr zotero search
# ---------------------------------------------------------------------------


@app.command("search")
def zotero_search(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(help="Search query.")],
    collection: Annotated[
        str | None,
        typer.Option(
            "--collection", "-c", help="Scope search to this collection name or key."
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of results to return."),
    ] = 25,
    fmt: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: table, json, keys."),
    ] = "table",
) -> None:
    """Search within your Zotero library by keyword.

    Examples:

      orbitr zotero search "language learning"

      orbitr zotero search "transformer" -c "NLP" --format keys
    """
    if fmt not in _VALID_LIST_FMTS:
        _err.print(
            f"[red]Error:[/red] Unknown format '{fmt}'. Choose: {', '.join(sorted(_VALID_LIST_FMTS))}"
        )
        raise typer.Exit(code=2)

    cfg = ctx.obj.config
    try:
        zot = _get_zotero(ctx)

        collection_key: str | None = None
        if collection:
            collection_key = zot.find_collection_key(collection)
            if collection_key is None:
                if len(collection) == 8 and collection.isalnum():
                    collection_key = collection
                else:
                    _err.print(
                        f"[red]Error:[/red] Collection '{collection}' not found."
                    )
                    _err.print(
                        "[dim]Run `orbitr zotero collections` to list collections.[/dim]"
                    )
                    raise typer.Exit(code=1)

        items = zot.search_items(
            query=query, collection_key=collection_key, limit=limit
        )
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

    if not items:
        Console(no_color=cfg.no_color).print(
            f"[yellow]No results for '{query}'.[/yellow]"
        )
        raise typer.Exit(code=4)

    if fmt == "keys":
        for item in items:
            data = item.get("data", item)
            typer.echo(data.get("key", item.get("key", "")))
        return

    if fmt == "json":
        typer.echo(json.dumps([item.get("data", item) for item in items], indent=2))
        return

    Console(no_color=cfg.no_color).print(
        _item_table(items, title=f"Zotero search: '{query}'")
    )


# ---------------------------------------------------------------------------
# orbitr zotero export-md
# ---------------------------------------------------------------------------


@app.command("export-md")
def zotero_export_md(
    ctx: typer.Context,
    item_key: Annotated[str, typer.Argument(help="Zotero item key.")],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output file or directory. Defaults to stdout. "
            "When a directory is given the filename is auto-generated.",
        ),
    ] = None,
) -> None:
    """Export a Zotero item as a Markdown file with YAML frontmatter.

    Outputs to stdout by default. Pass --output to write to a file or
    directory (auto-generates YYYY-Author-Short-Title.md).

    Examples:

      orbitr zotero export-md ABCD1234

      orbitr zotero export-md ABCD1234 -o kb/sources/raw/

      orbitr zotero list -c "NLP" --format keys | xargs -I{} orbitr zotero export-md {} -o kb/sources/raw/
    """
    try:
        zot = _get_zotero(ctx)
        result = zot.get_item(item_key, include_children=True)
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

    data = result["meta"].get("data", result["meta"])
    content = _build_export_md(item_key, data, result["notes"])

    if output is None:
        sys.stdout.write(content)
        return

    dest = Path(output)
    if dest.is_dir():
        filename = _auto_filename(data)
        dest = dest / filename

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    Console().print(f"[green]✓[/green] Exported to [bold]{dest}[/bold]")


def _auto_filename(data: dict) -> str:
    """Generate a filename like YYYY-LastName-Short-Title.md."""
    year = _item_year(data) or "0000"
    creators = [c for c in data.get("creators", []) if c.get("creatorType") == "author"]
    first_last = creators[0].get("lastName", "") if creators else ""
    title = data.get("title") or ""
    # Slug: keep alphanumeric and spaces, collapse, title-case words, join with hyphens
    slug_words = re.sub(r"[^\w\s]", "", title).split()[:6]
    slug = "-".join(w.capitalize() for w in slug_words) if slug_words else "untitled"
    parts = [
        p for p in [year, first_last.capitalize() if first_last else "", slug] if p
    ]
    return "-".join(parts) + ".md"


def _build_export_md(item_key: str, data: dict, notes: list[str]) -> str:
    """Render a Zotero item as a Markdown string with YAML frontmatter."""
    title = data.get("title") or ""
    authors_full = _item_authors_full(data)
    year = _item_year(data) or ""
    doi = data.get("DOI") or ""
    url = data.get("url") or ""
    venue = data.get("publicationTitle") or data.get("bookTitle") or ""
    abstract = data.get("abstractNote") or ""
    tags = [t["tag"] for t in data.get("tags", []) if t.get("tag")]
    zotero_url = f"zotero://select/items/0_{item_key}"

    # YAML frontmatter — build line by line to avoid yaml dependency
    fm_lines = ["---"]
    fm_lines.append(f'title: "{_yaml_escape(title)}"')
    if authors_full:
        fm_lines.append(f"authors: [{authors_full}]")
    if year:
        fm_lines.append(f"year: {year}")
    if doi:
        fm_lines.append(f'doi: "{doi}"')
    fm_lines.append(f"zotero_key: {item_key}")
    fm_lines.append(f'zotero_url: "{zotero_url}"')
    if tags:
        fm_lines.append(f"tags: [{', '.join(tags)}]")
    fm_lines.append("type: source")
    fm_lines.append("---")
    frontmatter = "\n".join(fm_lines)

    # Body
    body_lines = ["", f"# {title}", ""]
    meta_parts: list[str] = []
    if authors_full:
        meta_parts.append(f"**Authors:** {authors_full}")
    if year:
        meta_parts.append(f"**Year:** {year}")
    if venue:
        meta_parts.append(f"**Venue:** {venue}")
    if meta_parts:
        body_lines.append("  ".join(meta_parts))
    if doi:
        body_lines.append(f"**DOI:** [{doi}](https://doi.org/{doi})")
    elif url:
        body_lines.append(f"**URL:** {url}")
    if abstract:
        body_lines += ["", "## Abstract", "", abstract]
    if notes:
        clean_notes = [_strip_html(n) for n in notes if _strip_html(n)]
        if clean_notes:
            body_lines += ["", "## Notes", ""]
            for note in clean_notes:
                body_lines.append(note)

    return frontmatter + "\n".join(body_lines) + "\n"


def _yaml_escape(text: str) -> str:
    """Escape double-quotes in a YAML double-quoted string."""
    return text.replace('"', '\\"')
