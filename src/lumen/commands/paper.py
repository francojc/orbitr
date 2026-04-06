"""lumen paper / lumen cite — fetch a paper or its citations by ID."""

from __future__ import annotations

import json
import logging
import re
from typing import Annotated, Literal

import typer
from rich.console import Console

from lumen._async import run
from lumen.clients.arxiv import ArxivClient
from lumen.clients.semantic_scholar import SemanticScholarClient
from lumen.config import VALID_FORMATS
from lumen.core.cache import Cache
from lumen.core.models import Paper
from lumen.display import effective_format, render
from lumen.exceptions import LumenError, NoResultsError, SourceError

logger = logging.getLogger(__name__)

_err = Console(stderr=True)

# ---------------------------------------------------------------------------
# ID type detection
# ---------------------------------------------------------------------------

IdType = Literal["arxiv", "doi", "semantic_scholar", "unknown"]

# arXiv IDs:
#   New format:  1706.03762 or 1706.03762v2
#   Old format:  cs/0301027 or hep-th/9401001
#   With prefix: arxiv:1706.03762 or https://arxiv.org/abs/1706.03762
_ARXIV_BARE_RE = re.compile(
    r"^(?:arxiv:)?"
    r"(?:\d{4}\.\d{4,5}(?:v\d+)?|[a-z][a-z-]*(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)$",
    re.IGNORECASE,
)
_ARXIV_URL_RE = re.compile(r"^https?://arxiv\.org/abs/", re.IGNORECASE)

# DOIs: start with 10.NNNN/ optionally preceded by a URL or "DOI:" prefix.
_DOI_RE = re.compile(
    r"^(?:https?://(?:doi\.org|dx\.doi\.org)/|DOI:)?10\.\d{4,}/\S+$",
    re.IGNORECASE,
)

# Semantic Scholar IDs: exactly 40 lowercase hex characters.
_SS_ID_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)


def _detect_id_type(paper_id: str) -> IdType:
    """Classify a paper identifier as arxiv, doi, semantic_scholar, or unknown.

    Args:
        paper_id: Raw identifier string from the user.

    Returns:
        One of ``"arxiv"``, ``"doi"``, ``"semantic_scholar"``, ``"unknown"``.
    """
    s = paper_id.strip()
    if _ARXIV_URL_RE.match(s) or _ARXIV_BARE_RE.match(s):
        return "arxiv"
    if _DOI_RE.match(s):
        return "doi"
    if _SS_ID_RE.match(s):
        return "semantic_scholar"
    return "unknown"


def _normalize_for_ss(paper_id: str, id_type: IdType) -> str:
    """Return a Semantic Scholar-compatible paper ID string.

    Semantic Scholar accepts ``ARXIV:`` and ``DOI:`` prefixed IDs in
    addition to bare SS paper IDs.

    Args:
        paper_id: Raw identifier string from the user.
        id_type: Pre-classified type from :func:`_detect_id_type`.

    Returns:
        String suitable for passing to SS endpoints (e.g. ``ARXIV:1706.03762``).
    """
    s = paper_id.strip()
    if id_type == "arxiv":
        s = re.sub(r"^https?://arxiv\.org/abs/", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^arxiv:", "", s, flags=re.IGNORECASE)
        s = re.sub(r"v\d+$", "", s)
        return f"ARXIV:{s}"
    if id_type == "doi":
        s = re.sub(r"^https?://(?:doi\.org|dx\.doi\.org)/", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^DOI:", "", s, flags=re.IGNORECASE)
        return f"DOI:{s}"
    # Bare SS ID or unknown — pass through as-is.
    return s


# ---------------------------------------------------------------------------
# lumen paper
# ---------------------------------------------------------------------------


def paper(
    ctx: typer.Context,
    paper_id: Annotated[
        str, typer.Argument(help="Paper ID (arXiv ID, DOI, or Semantic Scholar ID).")
    ],
    fmt: Annotated[
        str | None,
        typer.Option(
            "--format", "-f", help=f"Output format. ({', '.join(VALID_FORMATS)})"
        ),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Bypass the local paper cache."),
    ] = False,
) -> None:
    """Fetch full details for a single paper by ID.

    Accepts arXiv IDs (e.g. 1706.03762), DOIs, or Semantic Scholar paper IDs.
    Displays title, authors, abstract, venue, citation count, and links.

    Examples:

      lumen paper 1706.03762

      lumen paper 10.18653/v1/2020.acl-main.196

      lumen paper 1706.03762 --format json
    """
    cfg = ctx.obj.config
    effective_fmt = effective_format(fmt, cfg.format)

    if effective_fmt not in VALID_FORMATS:
        _err.print(
            f"[red]Error:[/red] Unknown format {effective_fmt!r}. "
            f"Choose: {', '.join(VALID_FORMATS)}"
        )
        raise typer.Exit(code=2)

    try:
        run(
            _paper_async(
                paper_id=paper_id,
                fmt=effective_fmt,
                no_cache=no_cache or cfg.no_cache,
                cfg=cfg,
            )
        )
    except NoResultsError as exc:
        if not cfg.quiet:
            Console(no_color=cfg.no_color).print(
                f"[yellow]Paper not found.[/yellow] {exc.suggestion}"
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


async def fetch_paper(paper_id: str, *, cfg, no_cache: bool = False) -> Paper:
    """Fetch a single Paper by ID without rendering it.

    Shared helper used by ``lumen paper``, ``lumen zotero add``, etc.
    Caches the result under the ``'paper'`` tier.

    Strategy:
      - arXiv ID  → ArxivClient.get_by_id
      - DOI/SS/unknown → SemanticScholarClient.get_by_id with prefix
    """
    id_type = _detect_id_type(paper_id)
    cache_key = f"paper:{paper_id}"
    cache = Cache(cfg.cache_dir / "cache.db")

    if not no_cache:
        cached = cache.get(cache_key, "paper")
        if cached is not None:
            try:
                return Paper.model_validate(cached)
            except Exception:
                logger.debug("Cache entry corrupt for %s; refetching.", cache_key)

    api_key = cfg.credentials.semantic_scholar_api_key
    if id_type == "arxiv":
        result: Paper = await ArxivClient().get_by_id(paper_id)
    else:
        ss_id = _normalize_for_ss(paper_id, id_type)
        result = await SemanticScholarClient(api_key=api_key).get_by_id(ss_id)

    if not no_cache:
        cache.set(cache_key, json.loads(result.model_dump_json()), "paper")

    return result


async def _paper_async(*, paper_id: str, fmt: str, no_cache: bool, cfg) -> None:
    """Fetch a single paper by ID and render it."""
    import sys

    try:
        result = await fetch_paper(paper_id, cfg=cfg, no_cache=no_cache)
    except SourceError:
        raise

    console = Console(no_color=cfg.no_color)
    pager = sys.stdout.isatty() and not cfg.no_pager
    render([result], fmt=fmt, console=console, pager=pager)


# ---------------------------------------------------------------------------
# lumen cite
# ---------------------------------------------------------------------------


def cite(
    ctx: typer.Context,
    paper_id: Annotated[
        str, typer.Argument(help="Paper ID whose citations to retrieve.")
    ],
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-n",
            help="Maximum number of citing papers to return.",
            min=1,
            max=200,
        ),
    ] = 10,
    fmt: Annotated[
        str | None,
        typer.Option(
            "--format", "-f", help=f"Output format. ({', '.join(VALID_FORMATS)})"
        ),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Bypass the local citation cache."),
    ] = False,
) -> None:
    """List papers that cite a given paper (via Semantic Scholar).

    Accepts arXiv IDs, DOIs, or Semantic Scholar paper IDs.

    Examples:

      lumen cite 1706.03762

      lumen cite 1706.03762 --limit 50 --format json
    """
    cfg = ctx.obj.config
    effective_fmt = effective_format(fmt, cfg.format)

    if effective_fmt not in VALID_FORMATS:
        _err.print(
            f"[red]Error:[/red] Unknown format {effective_fmt!r}. "
            f"Choose: {', '.join(VALID_FORMATS)}"
        )
        raise typer.Exit(code=2)

    try:
        run(
            _cite_async(
                paper_id=paper_id,
                limit=limit,
                fmt=effective_fmt,
                no_cache=no_cache or cfg.no_cache,
                cfg=cfg,
            )
        )
    except NoResultsError as exc:
        if not cfg.quiet:
            Console(no_color=cfg.no_color).print(
                f"[yellow]No citations found.[/yellow] {exc.suggestion}"
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


async def _cite_async(
    *, paper_id: str, limit: int, fmt: str, no_cache: bool, cfg
) -> None:
    """Fetch citing papers via Semantic Scholar and render them."""
    id_type = _detect_id_type(paper_id)
    ss_id = _normalize_for_ss(paper_id, id_type)
    cache_key = f"citations:{ss_id}:{limit}"
    cache = Cache(cfg.cache_dir / "cache.db")

    # Cache read
    if not no_cache:
        cached = cache.get(cache_key, "citations")
        if cached is not None:
            try:
                papers = [Paper.model_validate(p) for p in cached]
                if not papers:
                    raise NoResultsError(
                        f"No citations found for '{paper_id}'.",
                        suggestion="Try a different ID or check the paper exists on Semantic Scholar.",
                    )
                import sys

                console = Console(no_color=cfg.no_color)
                pager = sys.stdout.isatty() and not cfg.no_pager
                render(papers, fmt=fmt, console=console, pager=pager)
                return
            except NoResultsError:
                raise
            except Exception:
                logger.debug("Cache entry corrupt for %s; refetching.", cache_key)

    # Live fetch — citations only available via Semantic Scholar
    api_key = cfg.credentials.semantic_scholar_api_key
    client = SemanticScholarClient(api_key=api_key)
    papers = await client.get_citations(ss_id, limit=limit)

    # Cache write (store even empty lists to avoid hammering the API)
    if not no_cache:
        cache.set(
            cache_key, [json.loads(p.model_dump_json()) for p in papers], "citations"
        )

    if not papers:
        raise NoResultsError(
            f"No citations found for '{paper_id}'.",
            suggestion="Try a different ID or check the paper exists on Semantic Scholar.",
        )

    import sys

    console = Console(no_color=cfg.no_color)
    pager = sys.stdout.isatty() and not cfg.no_pager
    render(papers[:limit], fmt=fmt, console=console, pager=pager)
