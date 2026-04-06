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
