"""lumen init — guided interactive setup for credentials and defaults."""

from __future__ import annotations

import os

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from lumen.config import CONFIG_FILE, Credentials, write_config

# Names of the environment variables that supply credentials.
_ENV_SS_KEY = "SEMANTIC_SCHOLAR_API_KEY"
_ENV_ZOTERO_USER = "ZOTERO_USER_ID"
_ENV_ZOTERO_KEY = "ZOTERO_API_KEY"

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

    # Use already-resolved config so re-runs pre-fill current values.
    config = ctx.obj.config

    console.print("\n[bold]Semantic Scholar[/bold]")
    console.print("An API key is optional but increases your rate limit.")
    console.print("Get one at: https://www.semanticscholar.org/product/api")

    ss_from_env = bool(os.environ.get(_ENV_SS_KEY))
    if ss_from_env:
        console.print(
            f"\n[dim]Already set via [bold]{_ENV_SS_KEY}[/bold] env var.[/dim]"
        )
        console.print(
            "[dim]Leave blank to keep using the env var "
            "(value will not be written to config.toml).[/dim]"
        )
    ss_key = Prompt.ask(
        "\nSemantic Scholar API key",
        default="" if ss_from_env else (config.credentials.semantic_scholar_api_key or ""),
        password=True,
    )

    console.print("\n[bold]Zotero[/bold]")
    console.print("Required for `lumen zotero` commands.")
    console.print(
        "Find your User ID and API key at: https://www.zotero.org/settings/keys"
    )

    zotero_user_from_env = bool(os.environ.get(_ENV_ZOTERO_USER))
    zotero_key_from_env = bool(os.environ.get(_ENV_ZOTERO_KEY))
    if zotero_user_from_env or zotero_key_from_env:
        vars_active = ", ".join(
            v for v, active in [
                (_ENV_ZOTERO_USER, zotero_user_from_env),
                (_ENV_ZOTERO_KEY, zotero_key_from_env),
            ] if active
        )
        console.print(
            f"\n[dim]Already set via [bold]{vars_active}[/bold] env var(s).[/dim]"
        )
        console.print(
            "[dim]Leave blank to keep using the env var(s) "
            "(values will not be written to config.toml).[/dim]"
        )

    zotero_user_id = Prompt.ask(
        "\nZotero User ID",
        default="" if zotero_user_from_env else (config.credentials.zotero_user_id or ""),
    )
    zotero_api_key = Prompt.ask(
        "Zotero API key",
        default="" if zotero_key_from_env else (config.credentials.zotero_api_key or ""),
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

    # For each credential: if the user left the prompt blank AND an env var is
    # active, preserve whatever value was already in config.toml rather than
    # overwriting it with an empty string.  The env var will continue to take
    # precedence at runtime regardless.
    from lumen.config import _load_toml  # avoid circular at module level

    existing_creds = _load_toml(CONFIG_FILE).get("credentials", {})

    config.credentials = Credentials(
        semantic_scholar_api_key=(
            ss_key
            if ss_key
            else existing_creds.get("semantic_scholar_api_key", "")
        ),
        zotero_user_id=(
            zotero_user_id
            if zotero_user_id
            else existing_creds.get("zotero_user_id", "")
        ),
        zotero_api_key=(
            zotero_api_key
            if zotero_api_key
            else existing_creds.get("zotero_api_key", "")
        ),
    )
    config.max_results = int(max_results)
    config.format = fmt

    path = write_config(config)
    console.print(f"[green]✓[/green] Config written to [bold]{path}[/bold] (mode 0600)")
    console.print("\nRun [bold]lumen doctor[/bold] to verify your setup.")
    raise typer.Exit()
