from __future__ import annotations

import httpx
import pytest
import respx

from orbitr.clients.karakeep import KarakeepClient
from orbitr.exceptions import ConfigError, SourceError

_URL = "https://keep.example.test"
_ENDPOINT = f"{_URL}/api/search-bookmarks"


def _client() -> KarakeepClient:
    return KarakeepClient("secret-token", _URL)


@pytest.mark.asyncio
async def test_search_maps_bookmarks_and_authenticates():
    with respx.mock:
        route = respx.get(_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "total": 1,
                    "data": [
                        {
                            "id": "abc",
                            "title": "Saved paper",
                            "url": "https://example.test/paper",
                            "content": {"text": "Read this"},
                            "tags": [{"name": "research"}],
                            "createdAt": "2024-01-02T03:04:05Z",
                        }
                    ],
                },
            )
        )
        result = await _client().search_bookmarks("paper", 5)
    assert route.calls[0].request.headers["Authorization"] == "Bearer secret-token"
    assert result.total_count == 1
    assert result.papers[0].id == "karakeep:abc"
    assert result.papers[0].abstract == "Read this"
    assert result.papers[0].categories == ["research"]
    assert "secret-token" not in result.papers[0].model_dump_json()


@pytest.mark.asyncio
async def test_empty_results_are_valid():
    with respx.mock:
        respx.get(_ENDPOINT).mock(return_value=httpx.Response(200, json={"data": []}))
        result = await _client().search_bookmarks("nothing")
    assert result.papers == []


@pytest.mark.asyncio
async def test_malformed_envelope_raises_source_error():
    with respx.mock:
        respx.get(_ENDPOINT).mock(return_value=httpx.Response(200, json={"data": {}}))
        with pytest.raises(SourceError, match="invalid bookmark list"):
            await _client().search_bookmarks("x")


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403, 404])
async def test_http_failures_are_normalized(status):
    with respx.mock:
        respx.get(_ENDPOINT).mock(return_value=httpx.Response(status))
        with pytest.raises(SourceError):
            await _client().search_bookmarks("x")


def test_credentials_and_url_are_required():
    with pytest.raises(ConfigError):
        KarakeepClient("", _URL)
    with pytest.raises(ConfigError):
        KarakeepClient("secret", "not-a-url")
    with pytest.raises(ConfigError):
        KarakeepClient("secret", "https://user:pass@example.test")
