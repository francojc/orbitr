"""Shared pytest fixtures for lumen tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from lumen.config import Config, Credentials


@pytest.fixture()
def tmp_config_path(tmp_path: Path) -> Path:
    """Return a path inside a temp directory for an isolated config file."""
    return tmp_path / "config.toml"


@pytest.fixture()
def default_config() -> Config:
    """Return a Config instance with safe test defaults (no real credentials)."""
    return Config(
        sources=["arxiv", "semantic_scholar"],
        max_results=5,
        format="table",
        no_cache=True,
        credentials=Credentials(
            semantic_scholar_api_key="",
            zotero_user_id="",
            zotero_api_key="",
        ),
    )
