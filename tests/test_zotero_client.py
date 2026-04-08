"""Unit tests for ZoteroClient.list_items, get_item, and search_items."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from orbitr.exceptions import ConfigError, LumenError
from orbitr.zotero.client import ZoteroClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_RAW_ITEMS = [
    {
        "key": "ITEM0001",
        "data": {
            "key": "ITEM0001",
            "itemType": "journalArticle",
            "title": "Attention Is All You Need",
            "creators": [
                {"creatorType": "author", "firstName": "Ashish", "lastName": "Vaswani"},
                {"creatorType": "author", "firstName": "Noam", "lastName": "Shazeer"},
            ],
            "date": "2017-06-12",
            "publicationTitle": "arXiv",
            "abstractNote": "Transformer architecture.",
            "DOI": "10.48550/arXiv.1706.03762",
            "url": "https://arxiv.org/abs/1706.03762",
            "tags": [{"tag": "nlp"}, {"tag": "attention"}],
            "collections": ["COLL0001"],
        },
    },
    {
        "key": "ITEM0002",
        "data": {
            "key": "ITEM0002",
            "itemType": "journalArticle",
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "creators": [
                {"creatorType": "author", "firstName": "Jacob", "lastName": "Devlin"},
            ],
            "date": "2018-10-11",
            "publicationTitle": "arXiv",
            "abstractNote": "BERT model.",
            "DOI": "",
            "url": "https://arxiv.org/abs/1810.04805",
            "tags": [],
            "collections": [],
        },
    },
]

_CHILD_NOTE = {
    "key": "NOTE0001",
    "data": {
        "key": "NOTE0001",
        "itemType": "note",
        "note": "<p>Important paper.</p>",
    },
}

_CHILD_ATTACHMENT = {
    "key": "ATTC0001",
    "data": {
        "key": "ATTC0001",
        "itemType": "attachment",
        "filename": "vaswani2017.pdf",
        "path": "/home/user/papers/vaswani2017.pdf",
        "contentType": "application/pdf",
    },
}


def _make_client() -> tuple[ZoteroClient, MagicMock]:
    """Return a ZoteroClient whose pyzotero internals are mocked."""
    zot_inner = MagicMock()
    with patch(
        "orbitr.zotero.client.ZoteroClient._build_client", return_value=zot_inner
    ):
        client = ZoteroClient.__new__(ZoteroClient)
        client._user_id = "123456"
        client._api_key = "testkey"
        client._zot = zot_inner
    return client, zot_inner


# ---------------------------------------------------------------------------
# ZoteroClient instantiation
# ---------------------------------------------------------------------------


class TestZoteroClientInit:
    def test_missing_credentials_raises_config_error(self):
        with pytest.raises(ConfigError):
            ZoteroClient(user_id="", api_key="")

    def test_missing_user_id_raises_config_error(self):
        with pytest.raises(ConfigError):
            ZoteroClient(user_id="", api_key="somekey")

    def test_missing_api_key_raises_config_error(self):
        with pytest.raises(ConfigError):
            ZoteroClient(user_id="123456", api_key="")


# ---------------------------------------------------------------------------
# ZoteroClient.list_items
# ---------------------------------------------------------------------------


class TestListItems:
    def test_returns_all_library_items(self):
        client, zot_inner = _make_client()
        zot_inner.items.return_value = _RAW_ITEMS
        result = client.list_items()
        assert len(result) == 2
        zot_inner.items.assert_called_once()

    def test_returns_collection_items(self):
        client, zot_inner = _make_client()
        zot_inner.collection_items.return_value = [_RAW_ITEMS[0]]
        result = client.list_items(collection_key="COLL0001")
        assert len(result) == 1
        zot_inner.collection_items.assert_called_once_with(
            "COLL0001", limit=25, sort="dateModified", direction="desc"
        )

    def test_respects_limit(self):
        client, zot_inner = _make_client()
        zot_inner.items.return_value = [_RAW_ITEMS[0]]
        client.list_items(limit=1)
        # limit is passed as keyword arg
        call_kwargs = zot_inner.items.call_args[1]
        assert call_kwargs["limit"] == 1

    def test_respects_sort(self):
        client, zot_inner = _make_client()
        zot_inner.items.return_value = _RAW_ITEMS
        client.list_items(sort="title")
        call_kwargs = zot_inner.items.call_args[1]
        assert call_kwargs["sort"] == "title"

    def test_empty_library(self):
        client, zot_inner = _make_client()
        zot_inner.items.return_value = []
        result = client.list_items()
        assert result == []

    def test_large_limit_uses_everything(self):
        client, zot_inner = _make_client()
        zot_inner.everything.return_value = _RAW_ITEMS
        zot_inner.items.return_value = _RAW_ITEMS
        result = client.list_items(limit=200)
        zot_inner.everything.assert_called_once()
        assert result == _RAW_ITEMS

    def test_item_type_filter_passed(self):
        client, zot_inner = _make_client()
        zot_inner.items.return_value = [_RAW_ITEMS[0]]
        client.list_items(item_type="journalArticle")
        call_kwargs = zot_inner.items.call_args[1]
        assert call_kwargs.get("itemType") == "journalArticle"


# ---------------------------------------------------------------------------
# ZoteroClient.get_item
# ---------------------------------------------------------------------------


class TestGetItem:
    def test_returns_meta_notes_attachments(self):
        client, zot_inner = _make_client()
        zot_inner.item.return_value = _RAW_ITEMS[0]
        zot_inner.children.return_value = [_CHILD_NOTE, _CHILD_ATTACHMENT]
        result = client.get_item("ITEM0001")
        assert result["meta"] == _RAW_ITEMS[0]
        assert "Important paper." in result["notes"][0]
        assert result["attachments"][0]["filename"] == "vaswani2017.pdf"
        assert result["attachments"][0]["content_type"] == "application/pdf"

    def test_not_found_raises_lumen_error(self):
        client, zot_inner = _make_client()
        zot_inner.item.return_value = None
        with pytest.raises(LumenError):
            client.get_item("NOTFOUND")

    def test_include_children_false_skips_children_call(self):
        client, zot_inner = _make_client()
        zot_inner.item.return_value = _RAW_ITEMS[0]
        result = client.get_item("ITEM0001", include_children=False)
        zot_inner.children.assert_not_called()
        assert result["notes"] == []
        assert result["attachments"] == []

    def test_item_with_no_children(self):
        client, zot_inner = _make_client()
        zot_inner.item.return_value = _RAW_ITEMS[1]
        zot_inner.children.return_value = []
        result = client.get_item("ITEM0002")
        assert result["notes"] == []
        assert result["attachments"] == []

    def test_note_html_is_included_raw(self):
        """Notes are returned as-is; stripping happens in the display layer."""
        client, zot_inner = _make_client()
        zot_inner.item.return_value = _RAW_ITEMS[0]
        zot_inner.children.return_value = [_CHILD_NOTE]
        result = client.get_item("ITEM0001")
        # Raw HTML from pyzotero
        assert "<p>" in result["notes"][0]


# ---------------------------------------------------------------------------
# ZoteroClient.search_items
# ---------------------------------------------------------------------------


class TestSearchItems:
    def test_full_library_search(self):
        client, zot_inner = _make_client()
        zot_inner.items.return_value = [_RAW_ITEMS[0]]
        result = client.search_items("attention")
        assert len(result) == 1
        call_kwargs = zot_inner.items.call_args[1]
        assert call_kwargs["q"] == "attention"

    def test_collection_scoped_search(self):
        client, zot_inner = _make_client()
        zot_inner.collection_items.return_value = [_RAW_ITEMS[0]]
        result = client.search_items("attention", collection_key="COLL0001")
        assert len(result) == 1
        zot_inner.collection_items.assert_called_once_with("COLL0001")

    def test_no_results_returns_empty_list(self):
        client, zot_inner = _make_client()
        zot_inner.items.return_value = []
        result = client.search_items("xyznonexistent")
        assert result == []

    def test_limit_respected(self):
        client, zot_inner = _make_client()
        zot_inner.items.return_value = []
        client.search_items("bert", limit=10)
        call_kwargs = zot_inner.items.call_args[1]
        assert call_kwargs["limit"] == 10
