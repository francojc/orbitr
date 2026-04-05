"""Zotero Web API client wrapping pyzotero.

Supports: add paper, list collections, create collection.
Group libraries and linked attachments are deferred to v2.
"""

from __future__ import annotations

import logging

from lumen.core.models import Paper
from lumen.exceptions import ConfigError

logger = logging.getLogger(__name__)


class ZoteroClient:
    """Thin wrapper around pyzotero for lumen's required operations."""

    def __init__(self, user_id: str, api_key: str) -> None:
        if not user_id or not api_key:
            raise ConfigError(
                "Zotero credentials are not configured.",
                suggestion="Run `lumen init` to enter your Zotero User ID and API key.",
            )
        self._user_id = user_id
        self._api_key = api_key
        self._zot = self._build_client()

    def _build_client(self):
        """Instantiate and return a pyzotero.zotero.Zotero client."""
        try:
            from pyzotero import zotero

            return zotero.Zotero(self._user_id, "user", self._api_key)
        except ImportError as exc:
            raise ImportError("pyzotero is required for Zotero integration.") from exc

    def add_paper(
        self,
        paper: Paper,
        collection_key: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Add a paper to the Zotero library.

        Args:
            paper: Paper to add.
            collection_key: Zotero collection key to place the item in.
            tags: Tags to apply to the created item.

        Returns:
            Zotero API response dict with the created item key.
        """
        # TODO: implement in Phase 3
        raise NotImplementedError

    def list_collections(self) -> list[dict]:
        """Return all top-level and nested collections.

        Returns:
            List of Zotero collection dicts with 'key' and 'data.name'.
        """
        # TODO: implement in Phase 3
        raise NotImplementedError

    def create_collection(self, name: str, parent_key: str | None = None) -> dict:
        """Create a new Zotero collection.

        Args:
            name: Collection name.
            parent_key: Parent collection key for nested collections.

        Returns:
            Zotero API response dict with the new collection key.
        """
        # TODO: implement in Phase 3
        raise NotImplementedError

    def find_collection_key(self, name: str) -> str | None:
        """Look up a collection key by name (case-insensitive).

        Args:
            name: Human-readable collection name.

        Returns:
            Zotero collection key string, or None if not found.
        """
        # TODO: implement in Phase 3
        raise NotImplementedError
