"""Integration tests for orbitr zotero subcommands."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from orbitr.cli import app
from orbitr.config import Config, Credentials
from orbitr.core.models import Author, Paper
from orbitr.exceptions import ConfigError, LumenError

runner = CliRunner()

_NO_CREDS = Credentials()
_CREDS = Credentials(
    zotero_user_id="123456",
    zotero_api_key="zot-test-key",
)


def _test_config(creds: Credentials = _CREDS, **overrides) -> Config:
    base = Config(format="table", no_cache=True, credentials=creds)
    for k, v in overrides.items():
        object.__setattr__(base, k, v)
    return base


def _paper() -> Paper:
    return Paper(
        id="ss:vaswani2017",
        title="Attention Is All You Need",
        authors=[Author(name="Ashish Vaswani"), Author(name="Noam Shazeer")],
        abstract="Transformer architecture.",
        published_date=datetime(2017, 6, 12, tzinfo=timezone.utc),
        url="https://arxiv.org/abs/1706.03762",
        source="arxiv",
        doi="10.48550/arXiv.1706.03762",
        venue="arXiv",
        citation_count=100_000,
    )


_DEFAULT_COLLECTIONS = [
    {
        "key": "COLL0001",
        "data": {"key": "COLL0001", "name": "Transformers", "parentCollection": False},
    },
    {
        "key": "COLL0002",
        "data": {"key": "COLL0002", "name": "NLP", "parentCollection": False},
    },
]


def _zot_mock(
    item_key: str = "ITEM0001",
    collections: list[dict] | None = None,  # None → use defaults; [] → empty
    coll_key: str = "COLL0001",
) -> MagicMock:
    """Build a ZoteroClient mock with sensible defaults."""
    mock = MagicMock()
    mock.add_paper.return_value = {"success": {"0": item_key}, "failed": {}}
    mock.list_collections.return_value = (
        _DEFAULT_COLLECTIONS if collections is None else collections
    )
    mock.find_collection_key.return_value = coll_key
    mock.create_collection.return_value = {"success": {"0": coll_key}, "failed": {}}
    return mock


def _invoke(*args: str, config: Config | None = None):
    cfg = config or _test_config()
    with patch("orbitr.config.load_config", return_value=cfg):
        return runner.invoke(app, list(args))


# ---------------------------------------------------------------------------
# orbitr zotero add
# ---------------------------------------------------------------------------


class TestZoteroAdd:
    def test_add_success(self):
        zot = _zot_mock()
        with (
            patch("orbitr.commands.zotero.ZoteroClient", return_value=zot),
            patch(
                "orbitr.commands.zotero.fetch_paper", new_callable=AsyncMock
            ) as mock_fp,
        ):
            mock_fp.return_value = _paper()
            result = _invoke("zotero", "add", "1706.03762")
        assert result.exit_code == 0
        assert "Attention Is All You Need" in result.output
        zot.add_paper.assert_called_once()

    def test_add_shows_item_key(self):
        zot = _zot_mock(item_key="ABCD1234")
        with (
            patch("orbitr.commands.zotero.ZoteroClient", return_value=zot),
            patch(
                "orbitr.commands.zotero.fetch_paper",
                new_callable=AsyncMock,
                return_value=_paper(),
            ),
        ):
            result = _invoke("zotero", "add", "1706.03762")
        assert "ABCD1234" in result.output

    def test_add_with_collection(self):
        zot = _zot_mock(coll_key="COLL0001")
        with (
            patch("orbitr.commands.zotero.ZoteroClient", return_value=zot),
            patch(
                "orbitr.commands.zotero.fetch_paper",
                new_callable=AsyncMock,
                return_value=_paper(),
            ),
        ):
            result = _invoke(
                "zotero", "add", "1706.03762", "--collection", "Transformers"
            )
        assert result.exit_code == 0
        _, kwargs = zot.add_paper.call_args
        assert kwargs["collection_key"] == "COLL0001"

    def test_add_with_tags(self):
        zot = _zot_mock()
        with (
            patch("orbitr.commands.zotero.ZoteroClient", return_value=zot),
            patch(
                "orbitr.commands.zotero.fetch_paper",
                new_callable=AsyncMock,
                return_value=_paper(),
            ),
        ):
            result = _invoke("zotero", "add", "1706.03762", "--tags", "nlp,attention")
        assert result.exit_code == 0
        _, kwargs = zot.add_paper.call_args
        assert kwargs["tags"] == ["nlp", "attention"]

    def test_add_no_credentials_exits_3(self):
        with (
            patch(
                "orbitr.commands.zotero.ZoteroClient",
                side_effect=ConfigError("No creds."),
            ),
            patch(
                "orbitr.commands.zotero.fetch_paper",
                new_callable=AsyncMock,
                return_value=_paper(),
            ),
        ):
            result = _invoke(
                "zotero",
                "add",
                "1706.03762",
                config=_test_config(creds=_NO_CREDS),
            )
        assert result.exit_code == 3

    def test_add_paper_fetch_error_exits_1(self):
        from orbitr.exceptions import SourceError

        with patch(
            "orbitr.commands.zotero.fetch_paper",
            new_callable=AsyncMock,
            side_effect=SourceError("Not found."),
        ):
            result = _invoke("zotero", "add", "9999.99999")
        assert result.exit_code == 1

    def test_add_zotero_api_error_exits_1(self):
        zot = _zot_mock()
        zot.add_paper.side_effect = LumenError("API error.")
        with (
            patch("orbitr.commands.zotero.ZoteroClient", return_value=zot),
            patch(
                "orbitr.commands.zotero.fetch_paper",
                new_callable=AsyncMock,
                return_value=_paper(),
            ),
        ):
            result = _invoke("zotero", "add", "1706.03762")
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# orbitr zotero collections
# ---------------------------------------------------------------------------


class TestZoteroCollections:
    def test_lists_collections(self):
        zot = _zot_mock()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "collections")
        assert result.exit_code == 0
        assert "Transformers" in result.output
        assert "NLP" in result.output

    def test_json_format(self):
        zot = _zot_mock()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "collections", "--format", "json")
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert any(c.get("name") == "Transformers" for c in data)

    def test_empty_collections(self):
        zot = _zot_mock(collections=[])
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "collections")
        assert result.exit_code == 0
        assert "No collections" in result.output

    def test_no_credentials_exits_3(self):
        with patch(
            "orbitr.commands.zotero.ZoteroClient",
            side_effect=ConfigError("No creds.", suggestion="Run orbitr init."),
        ):
            result = _invoke(
                "zotero", "collections", config=_test_config(creds=_NO_CREDS)
            )
        assert result.exit_code == 3


# ---------------------------------------------------------------------------
# orbitr zotero new
# ---------------------------------------------------------------------------


class TestZoteroNew:
    def test_create_collection(self):
        zot = _zot_mock(coll_key="NEW00001")
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "new", "My New Collection")
        assert result.exit_code == 0
        assert "My New Collection" in result.output
        assert "NEW00001" in result.output
        zot.create_collection.assert_called_once_with(
            "My New Collection", parent_key=None
        )

    def test_create_nested_collection(self):
        zot = _zot_mock(coll_key="PARENT01")
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "new", "Subtopic", "--parent", "Transformers")
        assert result.exit_code == 0
        zot.find_collection_key.assert_called_once_with("Transformers")
        _, kwargs = zot.create_collection.call_args
        assert kwargs["parent_key"] == "PARENT01"

    def test_parent_not_found_exits_1(self):
        zot = _zot_mock()
        zot.find_collection_key.return_value = None
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "new", "Child", "--parent", "Nonexistent")
        assert result.exit_code == 1

    def test_no_credentials_exits_3(self):
        with patch(
            "orbitr.commands.zotero.ZoteroClient",
            side_effect=ConfigError("No creds.", suggestion="Run orbitr init."),
        ):
            result = _invoke(
                "zotero", "new", "Test", config=_test_config(creds=_NO_CREDS)
            )
        assert result.exit_code == 3


# ---------------------------------------------------------------------------
# Shared fixture data for new commands
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

_GET_ITEM_RESULT = {
    "meta": _RAW_ITEMS[0],
    "notes": ["<p>Key paper on self-attention.</p>"],
    "attachments": [
        {
            "filename": "vaswani2017.pdf",
            "path": "/papers/vaswani2017.pdf",
            "content_type": "application/pdf",
        }
    ],
}

_GET_ITEM_NO_CHILDREN = {
    "meta": _RAW_ITEMS[0],
    "notes": [],
    "attachments": [],
}


def _zot_mock_full(
    items: list[dict] | None = None,
    get_result: dict | None = None,
    search_results: list[dict] | None = None,
    **existing_kwargs,
) -> MagicMock:
    """Extended mock covering new Phase 7 client methods."""
    mock = _zot_mock(**existing_kwargs)
    mock.list_items.return_value = items if items is not None else _RAW_ITEMS
    mock.get_item.return_value = (
        get_result if get_result is not None else _GET_ITEM_RESULT
    )
    mock.search_items.return_value = (
        search_results if search_results is not None else _RAW_ITEMS
    )
    return mock


# ---------------------------------------------------------------------------
# orbitr zotero list
# ---------------------------------------------------------------------------


class TestZoteroList:
    def test_list_table_output(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "list")
        assert result.exit_code == 0
        # Titles may wrap; check item keys which are in a fixed-width column
        assert "ITEM0001" in result.output
        assert "ITEM0002" in result.output

    def test_list_keys_format(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "list", "--format", "keys")
        assert result.exit_code == 0
        assert "ITEM0001" in result.output
        assert "ITEM0002" in result.output

    def test_list_json_format(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "list", "--format", "json")
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert any(item.get("title") == "Attention Is All You Need" for item in data)

    def test_list_with_collection_name(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "list", "--collection", "Transformers")
        assert result.exit_code == 0
        zot.find_collection_key.assert_called_with("Transformers")
        zot.list_items.assert_called_once()

    def test_list_collection_not_found_exits_1(self):
        zot = _zot_mock_full()
        zot.find_collection_key.return_value = None
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke(
                "zotero", "list", "--collection", "Nonexistent Collection XYZ"
            )
        assert result.exit_code == 1

    def test_list_empty_exits_4(self):
        zot = _zot_mock_full(items=[])
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "list")
        assert result.exit_code == 4
        assert "No items" in result.output

    def test_list_invalid_sort_exits_2(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "list", "--sort", "bogus")
        assert result.exit_code == 2

    def test_list_invalid_format_exits_2(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "list", "--format", "xml")
        assert result.exit_code == 2

    def test_list_no_credentials_exits_3(self):
        with patch(
            "orbitr.commands.zotero.ZoteroClient",
            side_effect=ConfigError("No creds.", suggestion="Run orbitr init."),
        ):
            result = _invoke("zotero", "list", config=_test_config(creds=_NO_CREDS))
        assert result.exit_code == 3


# ---------------------------------------------------------------------------
# orbitr zotero get
# ---------------------------------------------------------------------------


class TestZoteroGet:
    def test_detail_format_shows_title(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "get", "ITEM0001")
        assert result.exit_code == 0
        assert "Attention Is All You Need" in result.output

    def test_detail_shows_authors(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "get", "ITEM0001")
        assert "Vaswani" in result.output

    def test_detail_shows_doi(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "get", "ITEM0001")
        assert "10.48550" in result.output

    def test_detail_shows_notes(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "get", "ITEM0001")
        assert "Key paper on self-attention" in result.output

    def test_no_notes_flag_hides_notes(self):
        zot = _zot_mock_full(get_result=_GET_ITEM_NO_CHILDREN)
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "get", "ITEM0001", "--no-notes")
        assert result.exit_code == 0
        assert "Key paper on self-attention" not in result.output

    def test_json_format(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "get", "ITEM0001", "--format", "json")
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "meta" in data
        assert "notes" in data
        assert "attachments" in data

    def test_invalid_format_exits_2(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "get", "ITEM0001", "--format", "table")
        assert result.exit_code == 2

    def test_item_not_found_exits_1(self):
        zot = _zot_mock_full()
        zot.get_item.side_effect = LumenError("Not found.")
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "get", "NOTFOUND")
        assert result.exit_code == 1

    def test_no_credentials_exits_3(self):
        with patch(
            "orbitr.commands.zotero.ZoteroClient",
            side_effect=ConfigError("No creds.", suggestion="Run orbitr init."),
        ):
            result = _invoke(
                "zotero", "get", "ITEM0001", config=_test_config(creds=_NO_CREDS)
            )
        assert result.exit_code == 3


# ---------------------------------------------------------------------------
# orbitr zotero search
# ---------------------------------------------------------------------------


class TestZoteroSearch:
    def test_search_returns_results(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "search", "attention")
        assert result.exit_code == 0
        # Titles may wrap; check item keys which are in a fixed-width column
        assert "ITEM0001" in result.output
        zot.search_items.assert_called_once_with(
            query="attention", collection_key=None, limit=25
        )

    def test_search_keys_format(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "search", "attention", "--format", "keys")
        assert result.exit_code == 0
        assert "ITEM0001" in result.output

    def test_search_json_format(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "search", "bert", "--format", "json")
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_search_with_collection(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "search", "nlp", "--collection", "Transformers")
        assert result.exit_code == 0
        zot.find_collection_key.assert_called_with("Transformers")
        _, kwargs = zot.search_items.call_args
        assert kwargs["collection_key"] == "COLL0001"

    def test_search_no_results_exits_4(self):
        zot = _zot_mock_full(search_results=[])
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "search", "xyznonexistent")
        assert result.exit_code == 4
        assert "No results" in result.output

    def test_search_collection_not_found_exits_1(self):
        zot = _zot_mock_full()
        zot.find_collection_key.return_value = None
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke(
                "zotero", "search", "nlp", "--collection", "Nonexistent Collection XYZ"
            )
        assert result.exit_code == 1

    def test_search_invalid_format_exits_2(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "search", "nlp", "--format", "xml")
        assert result.exit_code == 2

    def test_search_no_credentials_exits_3(self):
        with patch(
            "orbitr.commands.zotero.ZoteroClient",
            side_effect=ConfigError("No creds.", suggestion="Run orbitr init."),
        ):
            result = _invoke(
                "zotero", "search", "nlp", config=_test_config(creds=_NO_CREDS)
            )
        assert result.exit_code == 3


# ---------------------------------------------------------------------------
# orbitr zotero export-md
# ---------------------------------------------------------------------------


class TestZoteroExportMd:
    def test_stdout_output(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "export-md", "ITEM0001")
        assert result.exit_code == 0
        assert "---" in result.output
        assert "title:" in result.output
        assert "Attention Is All You Need" in result.output

    def test_frontmatter_fields(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "export-md", "ITEM0001")
        output = result.output
        assert "year: 2017" in output
        assert "doi:" in output
        assert "zotero_key: ITEM0001" in output
        assert "type: source" in output

    def test_body_contains_abstract(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "export-md", "ITEM0001")
        assert "## Abstract" in result.output
        assert "Transformer architecture." in result.output

    def test_body_contains_notes(self):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "export-md", "ITEM0001")
        assert "## Notes" in result.output
        assert "Key paper on self-attention." in result.output

    def test_output_to_file(self, tmp_path):
        zot = _zot_mock_full()
        dest = tmp_path / "test.md"
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "export-md", "ITEM0001", "--output", str(dest))
        assert result.exit_code == 0
        content = dest.read_text()
        assert "Attention Is All You Need" in content

    def test_output_to_directory_auto_filename(self, tmp_path):
        zot = _zot_mock_full()
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke(
                "zotero", "export-md", "ITEM0001", "--output", str(tmp_path)
            )
        assert result.exit_code == 0
        md_files = list(tmp_path.glob("*.md"))
        assert len(md_files) == 1
        assert "2017" in md_files[0].name

    def test_item_not_found_exits_1(self):
        zot = _zot_mock_full()
        zot.get_item.side_effect = LumenError("Not found.")
        with patch("orbitr.commands.zotero.ZoteroClient", return_value=zot):
            result = _invoke("zotero", "export-md", "NOTFOUND")
        assert result.exit_code == 1

    def test_no_credentials_exits_3(self):
        with patch(
            "orbitr.commands.zotero.ZoteroClient",
            side_effect=ConfigError("No creds.", suggestion="Run orbitr init."),
        ):
            result = _invoke(
                "zotero", "export-md", "ITEM0001", config=_test_config(creds=_NO_CREDS)
            )
        assert result.exit_code == 3
