"""Zotero Web API client wrapping pyzotero.

Supports: add paper, list collections, create collection.
Group libraries and linked attachments are deferred to v2.
"""

from __future__ import annotations

import logging

from orbitr.core.models import Paper
from orbitr.exceptions import ConfigError, LumenError

logger = logging.getLogger(__name__)


class ZoteroClient:
    """Thin wrapper around pyzotero for orbitr's required operations."""

    def __init__(self, user_id: str, api_key: str) -> None:
        if not user_id or not api_key:
            raise ConfigError(
                "Zotero credentials are not configured.",
                suggestion="Run `orbitr init` to enter your Zotero User ID and API key.",
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

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def add_paper(
        self,
        paper: Paper,
        collection_key: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Add a paper to the Zotero library as a journalArticle item.

        Args:
            paper: Paper to add.
            collection_key: Zotero collection key to place the item in.
            tags: Tags to apply to the created item.

        Returns:
            Zotero API response dict; the new item key is under
            ``response["success"]["0"]``.

        Raises:
            LumenError: If the Zotero API returns a failure.
        """
        item = {
            "itemType": "journalArticle",
            "title": paper.title,
            "abstractNote": paper.abstract or "",
            "publicationTitle": paper.venue or "",
            "date": str(paper.year) if paper.year else "",
            "DOI": paper.doi or "",
            "url": paper.url,
            "creators": [
                {"creatorType": "author", "name": a.name} for a in paper.authors
            ],
            "collections": [collection_key] if collection_key else [],
            "tags": [{"tag": t} for t in (tags or [])],
        }
        resp = self._zot.create_items([item])
        if resp.get("failed"):
            first_error = next(iter(resp["failed"].values()), {})
            raise LumenError(
                f"Zotero API rejected the item: {first_error.get('message', 'unknown error')}",
                suggestion="Check your Zotero credentials and try again.",
            )
        return resp

    def list_collections(self) -> list[dict]:
        """Return all collections in the library (top-level and nested).

        Returns:
            List of Zotero collection objects, each with ``key`` and
            ``data`` sub-dict containing at least ``name`` and
            ``parentCollection``.
        """
        return self._zot.collections()

    def create_collection(self, name: str, parent_key: str | None = None) -> dict:
        """Create a new Zotero collection.

        Args:
            name: Collection name.
            parent_key: Parent collection key for a nested collection.

        Returns:
            Zotero API response dict; the new collection key is under
            ``response["success"]["0"]``.

        Raises:
            LumenError: If the Zotero API returns a failure.
        """
        payload: dict = {"name": name}
        if parent_key:
            payload["parentCollection"] = parent_key
        resp = self._zot.create_collections([payload])
        if resp.get("failed"):
            first_error = next(iter(resp["failed"].values()), {})
            raise LumenError(
                f"Zotero API rejected the collection: {first_error.get('message', 'unknown error')}",
                suggestion="Check your Zotero credentials and try again.",
            )
        return resp

    def find_collection_key(self, name: str) -> str | None:
        """Look up a collection key by name (case-insensitive).

        Args:
            name: Human-readable collection name.

        Returns:
            Zotero collection key string, or ``None`` if not found.
        """
        for coll in self.list_collections():
            if coll.get("data", {}).get("name", "").lower() == name.lower():
                return coll.get("key")
        return None
