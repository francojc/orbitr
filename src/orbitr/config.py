"""Layered config resolution: CLI flags > env vars > TOML file > defaults.

Config file location: ~/.config/orbitr/config.toml (XDG Base Directory spec).
Credentials file:     same file, under [credentials] section, mode 0600.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass, field
from pathlib import Path

# Python 3.11+ has tomllib in stdlib; 3.10 needs tomli.
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


# XDG-compliant default paths
CONFIG_DIR: Path = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "orbitr"
)
CACHE_DIR: Path = (
    Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "orbitr"
)
CONFIG_FILE: Path = CONFIG_DIR / "config.toml"

VALID_SOURCES = ("arxiv", "semantic_scholar")
VALID_FORMATS = ("table", "list", "detail", "json")


@dataclass
class Credentials:
    """API credentials for external services."""

    semantic_scholar_api_key: str = ""
    zotero_user_id: str = ""
    zotero_api_key: str = ""


@dataclass
class Config:
    """Fully resolved application configuration."""

    sources: list[str] = field(default_factory=lambda: ["arxiv", "semantic_scholar"])
    max_results: int = 10
    format: str = "table"
    cache_dir: Path = field(default_factory=lambda: CACHE_DIR)
    no_cache: bool = False
    no_pager: bool = False
    no_color: bool = False
    verbose: bool = False
    quiet: bool = False
    credentials: Credentials = field(default_factory=Credentials)


def _load_toml(path: Path) -> dict:
    """Load a TOML file; return empty dict if the file does not exist."""
    if not path.exists():
        return {}
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def _env_list(key: str, default: list[str]) -> list[str]:
    val = os.environ.get(key, "").strip()
    return [s.strip() for s in val.split(",")] if val else default


def _env_int(key: str, default: int) -> int:
    val = os.environ.get(key, "").strip()
    return int(val) if val.isdigit() else default


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key, "").lower().strip()
    if val:
        return val in ("1", "true", "yes")
    return default


def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, "").strip() or default


def load_config(
    path: Path | None = None,
    *,
    no_color: bool = False,
    verbose: bool = False,
    quiet: bool = False,
) -> Config:
    """Resolve configuration from CLI flags → env vars → TOML file → defaults.

    Args:
        path: Override path to the config TOML file.
        no_color: Disable color output (merged from CLI flag).
        verbose: Enable verbose output (merged from CLI flag).
        quiet: Suppress non-essential output (merged from CLI flag).

    Returns:
        Fully resolved Config instance.
    """
    config_path = path or CONFIG_FILE
    file_cfg = _load_toml(config_path)
    creds_cfg: dict = file_cfg.get("credentials", {})

    return Config(
        sources=_env_list(
            "LUMEN_SOURCES", file_cfg.get("sources", ["arxiv", "semantic_scholar"])
        ),
        max_results=_env_int("LUMEN_MAX_RESULTS", file_cfg.get("max_results", 10)),
        format=_env_str("LUMEN_FORMAT", file_cfg.get("format", "table")),
        cache_dir=Path(
            _env_str("LUMEN_CACHE_DIR", str(file_cfg.get("cache_dir", CACHE_DIR)))
        ),
        no_cache=_env_bool("LUMEN_NO_CACHE", file_cfg.get("no_cache", False)),
        no_pager=_env_bool("LUMEN_NO_PAGER", file_cfg.get("no_pager", False)),
        no_color=no_color or _env_bool("NO_COLOR", file_cfg.get("no_color", False)),
        verbose=verbose,
        quiet=quiet,
        credentials=Credentials(
            semantic_scholar_api_key=_env_str(
                "SEMANTIC_SCHOLAR_API_KEY",
                creds_cfg.get("semantic_scholar_api_key", ""),
            ),
            zotero_user_id=_env_str(
                "ZOTERO_USER_ID", creds_cfg.get("zotero_user_id", "")
            ),
            zotero_api_key=_env_str(
                "ZOTERO_API_KEY", creds_cfg.get("zotero_api_key", "")
            ),
        ),
    )


def write_config(config: Config, path: Path | None = None) -> Path:
    """Persist a Config to a TOML file with mode 0600.

    Args:
        config: Config instance to write.
        path: Target path (default: CONFIG_FILE).

    Returns:
        Path where the config was written.
    """
    import tomli_w  # runtime import; only needed for init

    target = path or CONFIG_FILE
    target.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {
        "sources": config.sources,
        "max_results": config.max_results,
        "format": config.format,
        "cache_dir": str(config.cache_dir),
        "no_cache": config.no_cache,
        "no_pager": config.no_pager,
        "no_color": config.no_color,
        "credentials": {
            "semantic_scholar_api_key": config.credentials.semantic_scholar_api_key,
            "zotero_user_id": config.credentials.zotero_user_id,
            "zotero_api_key": config.credentials.zotero_api_key,
        },
    }

    with open(target, "wb") as fh:
        tomli_w.dump(data, fh)

    target.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600 — owner read/write only
    return target
