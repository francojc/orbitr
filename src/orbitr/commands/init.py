"""orbitr init — guided interactive setup for credentials and defaults."""

from __future__ import annotations

import os

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.text import Text

from orbitr.config import CONFIG_FILE, Credentials, write_config

# Mapping: human label → (env var name, is_password)
_CREDENTIALS: list[tuple[str, str, bool]] = [
    ("Semantic Scholar API key", "SEMANTIC_SCHOLAR_API_KEY", True),
    ("Zotero User ID", "ZOTERO_USER_ID", False),
    ("Zotero API key", "ZOTERO_API_KEY", True),
]

console = Console()


def _credential_prompt(
    label: str,
    env_var: str,
    current_file_value: str,
    *,
    password: bool = False,
) -> str:
    """Display a status indicator for *env_var* and prompt for the credential.

    Behaviour:
    - If the env var is set in the environment:
        shows a green ✓, advises leaving blank to keep using the env var,
        and defaults the prompt to "" (no file write on blank input).
    - If the env var is not set:
        shows a yellow ✗, suggests the export command to set it,
        and defaults the prompt to the current config.toml value.

    Args:
        label: Human-readable field name shown in the prompt.
        env_var: Name of the environment variable (e.g. ``ZOTERO_API_KEY``).
        current_file_value: Value currently stored in config.toml (may be "").
        password: Mask input with asterisks when True.

    Returns:
        The value entered by the user, or "" if they pressed Enter with an
        empty default.
    """
    env_value = os.environ.get(env_var, "")
    is_set = bool(env_value)

    # --- Status line ---------------------------------------------------------
    status = Text()
    if is_set:
        status.append("  ✓ ", style="bold green")
        status.append(env_var, style="bold")
        status.append("  is set in the environment", style="dim")
    else:
        status.append("  ✗ ", style="bold yellow")
        status.append(env_var, style="bold")
        status.append("  is not set", style="dim yellow")
    console.print(status)

    # --- Guidance ------------------------------------------------------------
    if is_set:
        console.print(
            "  [dim]Leave blank to keep using the env var "
            "(value will not be written to config.toml).[/dim]"
        )
    else:
        console.print(
            "  [dim]Tip: store this credential as an env var to avoid "
            "plain-text exposure in config.toml:[/dim]"
        )
        console.print(f'  [dim]  export {env_var}="<{label.lower()}>"[/dim]')
        if current_file_value:
            console.print("  [dim](A value is already stored in config.toml.)[/dim]")

    # --- Prompt --------------------------------------------------------------
    default = "" if is_set else current_file_value
    return Prompt.ask(
        f"\n  {label}",
        default=default,
        password=password,
    )


def init(ctx: typer.Context) -> None:
    """Interactively configure orbitr credentials and defaults.

    Creates (or updates) ~/.config/orbitr/config.toml with mode 0600.
    Guides you through setting your Semantic Scholar API key and Zotero
    credentials. All values are optional and can be skipped.

    Run this once after installing orbitr, or again to rotate credentials.

    Example:

      orbitr init
    """
    console.print(
        Panel.fit(
            "[bold cyan]orbitr setup[/bold cyan]\n"
            "Configure credentials and defaults.\n"
            f"Config file: [dim]{CONFIG_FILE}[/dim]",
        )
    )

    # Use already-resolved config so re-runs pre-fill current config.toml values.
    config = ctx.obj.config

    # Load the raw TOML now so we can pass file-only values to each prompt
    # (the resolved config may have folded in env vars already).
    from orbitr.config import _load_toml  # avoid circular at module level

    existing_creds = _load_toml(CONFIG_FILE).get("credentials", {})
    file_ss = existing_creds.get("semantic_scholar_api_key", "")
    file_uid = existing_creds.get("zotero_user_id", "")
    file_zot = existing_creds.get("zotero_api_key", "")

    # --- Semantic Scholar ----------------------------------------------------
    console.print("\n[bold]Semantic Scholar[/bold]")
    console.print(
        "An API key is optional but increases your rate limit.\n"
        "Get one at: [link]https://www.semanticscholar.org/product/api[/link]"
    )
    console.print()
    ss_key = _credential_prompt(
        "Semantic Scholar API key",
        "SEMANTIC_SCHOLAR_API_KEY",
        file_ss,
        password=True,
    )

    # --- Zotero --------------------------------------------------------------
    console.print("\n[bold]Zotero[/bold]")
    console.print(
        "Required for `orbitr zotero` commands.\n"
        "Get credentials at: [link]https://www.zotero.org/settings/keys[/link]"
    )
    console.print()
    zotero_user_id = _credential_prompt(
        "Zotero User ID",
        "ZOTERO_USER_ID",
        file_uid,
        password=False,
    )
    console.print()
    zotero_api_key = _credential_prompt(
        "Zotero API key",
        "ZOTERO_API_KEY",
        file_zot,
        password=True,
    )

    # --- Defaults ------------------------------------------------------------
    console.print("\n[bold]Defaults[/bold]\n")

    max_results = Prompt.ask(
        "  Default max results",
        default=str(config.max_results),
    )
    fmt = Prompt.ask(
        "  Default output format",
        default=config.format,
        choices=["table", "list", "detail", "json"],
    )

    # --- Confirm and save ----------------------------------------------------
    console.print()
    confirmed = Confirm.ask("Save configuration?", default=True)
    if not confirmed:
        console.print("[yellow]Aborted — no changes written.[/yellow]")
        raise typer.Exit()

    # For each credential: if the user left the prompt blank AND an env var is
    # active, preserve whatever value was already in config.toml rather than
    # overwriting it with an empty string.  The env var continues to take
    # precedence over config.toml at runtime regardless.
    config.credentials = Credentials(
        semantic_scholar_api_key=(ss_key or file_ss),
        zotero_user_id=(zotero_user_id or file_uid),
        zotero_api_key=(zotero_api_key or file_zot),
    )
    config.max_results = int(max_results)
    config.format = fmt

    path = write_config(config)
    console.print(
        f"\n[green]✓[/green] Config written to [bold]{path}[/bold] (mode 0600)"
    )
    console.print("Run [bold]orbitr doctor[/bold] to verify your setup.")
    raise typer.Exit()
