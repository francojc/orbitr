"""Integration tests for orbitr doctor command."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from orbitr.cli import app
from orbitr.config import Config, Credentials

runner = CliRunner()

_CREDS = Credentials()


def _test_config(**overrides) -> Config:
    base = Config(format="table", credentials=_CREDS)
    for k, v in overrides.items():
        object.__setattr__(base, k, v)
    return base


def _invoke(*args: str, config: Config | None = None):
    cfg = config or _test_config()
    with patch("orbitr.config.load_config", return_value=cfg):
        return runner.invoke(app, list(args))


def _check_results(*results: tuple) -> AsyncMock:
    """Build a _check_url AsyncMock that returns the given result tuples."""
    mock = AsyncMock(side_effect=list(results))
    return mock


# ---------------------------------------------------------------------------
# All checks pass
# ---------------------------------------------------------------------------


class TestDoctorAllPass:
    def test_exits_0_when_all_ok(self):
        checks = [
            ("arXiv API", True, "HTTP 200"),
            ("Semantic Scholar API", True, "HTTP 200"),
        ]
        with patch(
            "orbitr.commands.doctor._check_url", new_callable=AsyncMock
        ) as mock_check:
            mock_check.side_effect = checks
            result = _invoke("doctor")
        assert result.exit_code == 0

    def test_success_message_shown(self):
        checks = [
            ("arXiv API", True, "HTTP 200"),
            ("Semantic Scholar API", True, "HTTP 200"),
        ]
        with patch(
            "orbitr.commands.doctor._check_url", new_callable=AsyncMock
        ) as mock_check:
            mock_check.side_effect = checks
            result = _invoke("doctor")
        assert "All checks passed" in result.output

    def test_table_shows_check_names(self):
        checks = [
            ("arXiv API", True, "HTTP 200"),
            ("Semantic Scholar API", True, "HTTP 200"),
        ]
        with patch(
            "orbitr.commands.doctor._check_url", new_callable=AsyncMock
        ) as mock_check:
            mock_check.side_effect = checks
            result = _invoke("doctor")
        assert "arXiv API" in result.output
        assert "Semantic Scholar" in result.output


# ---------------------------------------------------------------------------
# One or more checks fail
# ---------------------------------------------------------------------------


class TestDoctorFailures:
    def test_exits_1_when_any_fail(self):
        checks = [
            ("arXiv API", False, "Connection refused"),
            ("Semantic Scholar API", True, "HTTP 200"),
        ]
        with patch(
            "orbitr.commands.doctor._check_url", new_callable=AsyncMock
        ) as mock_check:
            mock_check.side_effect = checks
            result = _invoke("doctor")
        assert result.exit_code == 1

    def test_failure_message_shown(self):
        checks = [
            ("arXiv API", True, "HTTP 200"),
            ("Semantic Scholar API", False, "Timeout"),
        ]
        with patch(
            "orbitr.commands.doctor._check_url", new_callable=AsyncMock
        ) as mock_check:
            mock_check.side_effect = checks
            result = _invoke("doctor")
        assert "failed" in result.output.lower() or result.exit_code == 1

    def test_all_fail_exits_1(self):
        checks = [
            ("arXiv API", False, "Timeout"),
            ("Semantic Scholar API", False, "Timeout"),
        ]
        with patch(
            "orbitr.commands.doctor._check_url", new_callable=AsyncMock
        ) as mock_check:
            mock_check.side_effect = checks
            result = _invoke("doctor")
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Credential checks
# ---------------------------------------------------------------------------


class TestDoctorCredentials:
    def test_unset_credentials_shown(self):
        checks = [
            ("arXiv API", True, "HTTP 200"),
            ("Semantic Scholar API", True, "HTTP 200"),
        ]
        with patch(
            "orbitr.commands.doctor._check_url", new_callable=AsyncMock
        ) as mock_check:
            mock_check.side_effect = checks
            result = _invoke("doctor", config=_test_config())
        # All three optional credentials are unset
        assert "not set" in result.output

    def test_set_credentials_shown(self):
        creds = Credentials(
            semantic_scholar_api_key="sk-test",
            zotero_user_id="123",
            zotero_api_key="zot-key",
        )
        checks = [
            ("arXiv API", True, "HTTP 200"),
            ("Semantic Scholar API", True, "HTTP 200"),
            ("Zotero API", True, "HTTP 200"),
        ]
        with patch(
            "orbitr.commands.doctor._check_url", new_callable=AsyncMock
        ) as mock_check:
            mock_check.side_effect = checks
            result = _invoke("doctor", config=_test_config(credentials=creds))
        assert "set" in result.output

    def test_zotero_checked_when_credentials_set(self):
        creds = Credentials(
            semantic_scholar_api_key="",
            zotero_user_id="123",
            zotero_api_key="zot-key",
        )
        checks = [
            ("arXiv API", True, "HTTP 200"),
            ("Semantic Scholar API", True, "HTTP 200"),
            ("Zotero API", True, "HTTP 200"),
        ]
        with patch(
            "orbitr.commands.doctor._check_url", new_callable=AsyncMock
        ) as mock_check:
            mock_check.side_effect = checks
            _invoke("doctor", config=_test_config(credentials=creds))
        # Should have been called 3 times (including Zotero)
        assert mock_check.call_count == 3

    def test_zotero_skipped_without_credentials(self):
        checks = [
            ("arXiv API", True, "HTTP 200"),
            ("Semantic Scholar API", True, "HTTP 200"),
        ]
        with patch(
            "orbitr.commands.doctor._check_url", new_callable=AsyncMock
        ) as mock_check:
            mock_check.side_effect = checks
            _invoke("doctor", config=_test_config())
        # Only 2 checks — Zotero skipped
        assert mock_check.call_count == 2


# ---------------------------------------------------------------------------
# Config file check
# ---------------------------------------------------------------------------


class TestDoctorConfigFile:
    def test_config_file_path_shown(self):
        checks = [
            ("arXiv API", True, "HTTP 200"),
            ("Semantic Scholar API", True, "HTTP 200"),
        ]
        with patch(
            "orbitr.commands.doctor._check_url", new_callable=AsyncMock
        ) as mock_check:
            mock_check.side_effect = checks
            result = _invoke("doctor")
        assert "Config file" in result.output
