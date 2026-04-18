"""Zotero Web API client wrapping pyzotero.

Supports: add paper, list/get/search items, list/create collections.
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

    # ------------------------------------------------------------------
    # Item browsing / retrieval
    # ------------------------------------------------------------------

    def list_items(
        self,
        collection_key: str | None = None,
        limit: int = 25,
        sort: str = "dateModified",
        direction: str = "desc",
        item_type: str | None = None,
    ) -> list[dict]:
        """Return items from the library or a specific collection.

        Args:
            collection_key: Restrict to this collection; ``None`` for the
                whole library.
            limit: Maximum number of items to return.  When *limit* exceeds
                the Zotero API cap (100 per request) pyzotero's built-in
                ``everything()`` helper is used transparently.
            sort: Zotero sort field (e.g. ``dateModified``, ``dateAdded``, ``title``, ``date``).
            direction: ``"asc"`` or ``"desc"``.
            item_type: Optional Zotero item-type filter, e.g.
                ``"journalArticle"``.

        Returns:
            List of raw Zotero item dicts.
        """
        kwargs: dict = {
            "sort": sort,
            "direction": direction,
            "itemType": item_type,
        }
        # Remove None values — pyzotero passes them as query params
        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        if collection_key:
            self._zot.add_parameters(limit=limit, **kwargs)
            if limit > 100:
                return self._zot.everything(self._zot.collection_items(collection_key))
            return self._zot.collection_items(collection_key, limit=limit, **kwargs)
        else:
            self._zot.add_parameters(limit=limit, **kwargs)
            if limit > 100:
                return self._zot.everything(self._zot.items(**kwargs))
            return self._zot.items(limit=limit, **kwargs)

    def get_item(
        self,
        item_key: str,
        include_children: bool = True,
    ) -> dict:
        """Fetch full metadata, notes, and attachments for a single item.

        Args:
            item_key: Zotero item key (8-character alphanumeric string).
            include_children: When ``True`` (default), also fetch child
                items (notes and attachments) via a second API call.

        Returns:
            Dict with keys:

            - ``"meta"``        – full Zotero item data dict
            - ``"notes"``       – list of note body strings
            - ``"attachments"`` – list of dicts with ``filename``,
              ``path``, and ``content_type`` keys

        Raises:
            LumenError: If the item key is not found.
        """
        item = self._zot.item(item_key)
        if not item:
            raise LumenError(
                f"Zotero item '{item_key}' not found.",
                suggestion="Use `orbitr zotero list` or `orbitr zotero search` to find valid item keys.",
            )

        notes: list[str] = []
        attachments: list[dict] = []

        if include_children:
            for child in self._zot.children(item_key):
                data = child.get("data", {})
                if data.get("itemType") == "note":
                    notes.append(data.get("note", ""))
                elif data.get("itemType") == "attachment":
                    attachments.append(
                        {
                            "key": data.get("key", ""),
                            "filename": data.get("filename", ""),
                            "path": data.get("path", ""),
                            "content_type": data.get("contentType", ""),
                        }
                    )

        return {"meta": item, "notes": notes, "attachments": attachments}

    def search_items(
        self,
        query: str,
        collection_key: str | None = None,
        limit: int = 25,
    ) -> list[dict]:
        """Full-text search within the Zotero library.

        Args:
            query: Search string (passed to pyzotero's ``q`` parameter).
            collection_key: Scope the search to this collection; ``None``
                searches the whole library.
            limit: Maximum number of results to return.

        Returns:
            List of raw Zotero item dicts whose metadata matches *query*.
        """
        if collection_key:
            self._zot.add_parameters(q=query, limit=limit)
            return self._zot.collection_items(collection_key)
        return self._zot.items(q=query, limit=limit)
