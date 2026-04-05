"""lumen init — guided interactive setup for credentials and defaults."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from lumen.config import CONFIG_FILE, Credentials, load_config, write_config

console = Console()


def init(ctx: typer.Context) -> None:
    """Interactively configure lumen credentials and defaults.

    Creates (or updates) ~/.config/lumen/config.toml with mode 0600.
    Guides you through setting your Semantic Scholar API key and Zotero
    credentials. All values are optional and can be skipped.

    Run this once after installing lumen, or again to rotate credentials.

    Example:

      lumen init
    """
    console.print(
        Panel.fit(
            "[bold cyan]lumen setup[/bold cyan]\n"
            "Configure credentials and defaults.\n"
            f"Config file: [dim]{CONFIG_FILE}[/dim]",
        )
    )

    # Load existing config so re-runs pre-fill current values.
    config = load_config(path=ctx.obj.config_path if ctx.obj else None)

    console.print("\n[bold]Semantic Scholar[/bold]")
    console.print("An API key is optional but increases your rate limit.")
    console.print("Get one at: https://www.semanticscholar.org/product/api\n")

    ss_key = Prompt.ask(
        "Semantic Scholar API key",
        default=config.credentials.semantic_scholar_api_key or "",
        password=True,
    )

    console.print("\n[bold]Zotero[/bold]")
    console.print("Required for `lumen zotero` commands.")
    console.print(
        "Find your User ID and API key at: https://www.zotero.org/settings/keys\n"
    )

    zotero_user_id = Prompt.ask(
        "Zotero User ID",
        default=config.credentials.zotero_user_id or "",
    )
    zotero_api_key = Prompt.ask(
        "Zotero API key",
        default=config.credentials.zotero_api_key or "",
        password=True,
    )

    console.print("\n[bold]Defaults[/bold]\n")

    max_results = Prompt.ask(
        "Default max results",
        default=str(config.max_results),
    )
    fmt = Prompt.ask(
        "Default output format",
        default=config.format,
        choices=["table", "list", "detail", "json"],
    )

    console.print()
    confirmed = Confirm.ask("Save configuration?", default=True)
    if not confirmed:
        console.print("[yellow]Aborted — no changes written.[/yellow]")
        raise typer.Exit()

    config.credentials = Credentials(
        semantic_scholar_api_key=ss_key,
        zotero_user_id=zotero_user_id,
        zotero_api_key=zotero_api_key,
    )
    config.max_results = int(max_results)
    config.format = fmt

    path = write_config(config)
    console.print(f"[green]✓[/green] Config written to [bold]{path}[/bold] (mode 0600)")
    console.print("\nRun [bold]lumen doctor[/bold] to verify your setup.")
    raise typer.Exit()
