from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from orbitr.cli import app
from orbitr.config import Config, Credentials
from orbitr.core.models import Paper, SearchResult

runner = CliRunner()


def _config() -> Config:
    return Config(
        no_cache=True,
        credentials=Credentials(
            karakeep_api_key="secret-token",
            karakeep_server_url="https://keep.example.test/",
        ),
    )


def _invoke(*args: str, config: Config | None = None):
    with patch("orbitr.config.load_config", return_value=config or _config()):
        return runner.invoke(app, list(args))


def _result() -> SearchResult:
    return SearchResult(
        query="paper",
        sources=["karakeep"],
        total_count=1,
        papers=[
            Paper(
                id="karakeep:1",
                title="Saved paper",
                authors=[],
                url="https://example.test/paper",
                source="karakeep",
            )
        ],
    )


def test_help_is_registered():
    result = _invoke("karakeep", "search", "--help")
    assert result.exit_code == 0
    assert "--server" in result.output
    assert "Kara" in result.output


def test_json_search_uses_override_and_keeps_data_on_stdout():
    with patch(
        "orbitr.commands.karakeep.KarakeepClient.search_bookmarks",
        new_callable=AsyncMock,
        return_value=_result(),
    ) as search:
        result = _invoke(
            "karakeep", "search", "paper", "--server", "https://override.test"
        )
    assert result.exit_code == 0
    assert '"title":"Saved paper"' in result.stdout
    assert result.stderr == ""
    search.assert_awaited_once_with("paper", 10)


def test_missing_credentials_exit_3():
    result = _invoke("karakeep", "search", "paper", config=Config())
    assert result.exit_code == 3
    assert "KARAKEEP_API_KEY" in result.output
    assert "Traceback" not in result.output


def test_invalid_server_exit_3_without_secret_leak():
    cfg = _config()
    cfg.credentials.karakeep_server_url = "not-a-url"
    result = _invoke("karakeep", "search", "paper", config=cfg)
    assert result.exit_code == 3
    assert "invalid" in result.output.lower()
    assert "secret-token" not in result.output


def test_empty_results_exit_4():
    empty = SearchResult(query="none", sources=["karakeep"], total_count=0, papers=[])
    with patch(
        "orbitr.commands.karakeep.KarakeepClient.search_bookmarks",
        new_callable=AsyncMock,
        return_value=empty,
    ):
        result = _invoke("karakeep", "search", "none")
    assert result.exit_code == 4
    assert "No results" in result.output
