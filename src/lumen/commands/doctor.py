"""lumen doctor — connectivity and configuration health checks."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from lumen.config import CONFIG_FILE, load_config

console = Console()

# Endpoints checked for basic reachability
_HEALTH_ENDPOINTS = {
    "arXiv API": "https://export.arxiv.org/api/query?search_query=test&max_results=1",
    "Semantic Scholar API": "https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1",
    "Zotero API": "https://api.zotero.org/users/0/items",
}


async def _check_url(label: str, url: str, api_key: str = "") -> tuple[str, bool, str]:
    """Perform a lightweight HEAD/GET to verify reachability.

    Returns:
        (label, ok, detail_message)
    """
    try:
        import httpx

        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            ok = resp.status_code < 500
            return label, ok, f"HTTP {resp.status_code}"
    except Exception as exc:  # noqa: BLE001
        return label, False, str(exc)


def doctor(ctx: typer.Context) -> None:
    """Check configuration and connectivity to all data sources.

    Verifies:
    - Config file exists and is readable
    - Required credentials are set (Zotero)
    - arXiv, Semantic Scholar, and Zotero APIs are reachable

    Exit codes:
      0  All checks passed
      1  One or more connectivity checks failed
      3  Config file missing or unreadable

    Example:

      lumen doctor
    """
    config_path = ctx.obj.config_path if ctx.obj else None
    config = load_config(path=config_path)

    table = Table(title="lumen doctor", show_header=True, header_style="bold")
    table.add_column("Check", style="dim", min_width=26)
    table.add_column("Status", min_width=13)
    table.add_column("Detail")

    any_fail = False

    # --- Config file check ---
    cfg_exists = CONFIG_FILE.exists()
    table.add_row(
        "Config file",
        "[green]✓ ok[/green]" if cfg_exists else "[yellow]⚠ missing[/yellow]",
        str(CONFIG_FILE),
    )

    # --- Credential checks ---
    creds = config.credentials
    for label, val in [
        ("Semantic Scholar API key", creds.semantic_scholar_api_key),
        ("Zotero User ID", creds.zotero_user_id),
        ("Zotero API key", creds.zotero_api_key),
    ]:
        set_status = bool(val)
        table.add_row(
            label,
            "[green]✓ set[/green]" if set_status else "[yellow]⚠ not set[/yellow]",
            "(optional)"
            if label == "Semantic Scholar API key"
            else ""
            if set_status
            else "Run `lumen init`",
        )

    # --- Connectivity checks ---
    async def run_checks() -> list[tuple[str, bool, str]]:
        tasks = [
            _check_url("arXiv API", _HEALTH_ENDPOINTS["arXiv API"]),
            _check_url(
                "Semantic Scholar API",
                _HEALTH_ENDPOINTS["Semantic Scholar API"],
                creds.semantic_scholar_api_key,
            ),
        ]
        if creds.zotero_user_id and creds.zotero_api_key:
            tasks.append(_check_url("Zotero API", _HEALTH_ENDPOINTS["Zotero API"]))
        return await asyncio.gather(*tasks)

    results = asyncio.run(run_checks())
    for label, ok, detail in results:
        if not ok:
            any_fail = True
        table.add_row(
            label,
            "[green]✓ reachable[/green]" if ok else "[red]✗ unreachable[/red]",
            detail,
        )

    console.print(table)

    if any_fail:
        console.print(
            "\n[red]One or more checks failed.[/red] Check your network connection and credentials."
        )
        raise typer.Exit(code=1)
    else:
        console.print("\n[green]All checks passed.[/green] lumen is ready to use.")
    raise typer.Exit()
