import json

import httpx
import pytest
import respx

from langchain_outcrawl import OutcrawlError, OutcrawlLoader, OutcrawlScrapeTool, OutcrawlSearchTool

SEARCH = {
    "hits": [
        {"url": "https://a.example/1", "title": "One", "snippet": "first", "rank": 1},
        {"url": "https://a.example/2", "title": None, "snippet": None},
    ],
    "usage": {"credits": "5"},
}
PAGE = {
    "url": "https://example.com/",
    "statusCode": 200,
    "markdown": "# Example\n\nBody",
    "metadata": {"title": "Example Domain", "language": "en"},
    "usage": {"credits": "1"},
}


@respx.mock
def test_search_sends_query_limit_and_bearer_key() -> None:
    route = respx.post("https://api.outcrawl.ai/v1/search").mock(return_value=httpx.Response(200, json=SEARCH))
    tool = OutcrawlSearchTool(outcrawl_api_key="k-123", limit=2)
    result = tool.invoke({"query": "mcp"})
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer k-123"
    assert json.loads(request.content) == {"query": "mcp", "limit": 2}
    assert result == [
        {"url": "https://a.example/1", "title": "One", "snippet": "first", "rank": 1},
        {"url": "https://a.example/2", "title": "", "snippet": ""},
    ]


@respx.mock
def test_search_call_limit_overrides_default_and_extra_params_pass_through() -> None:
    route = respx.post("https://api.outcrawl.ai/v1/search").mock(return_value=httpx.Response(200, json=SEARCH))
    tool = OutcrawlSearchTool(outcrawl_api_key="k", limit=2, extra_params={"country": "us", "skip": None})
    tool.invoke({"query": "q", "limit": 7})
    assert json.loads(route.calls.last.request.content) == {"query": "q", "limit": 7, "country": "us"}


@respx.mock
def test_scrape_requests_markdown_and_returns_page() -> None:
    route = respx.post("https://api.outcrawl.ai/v1/scrape").mock(return_value=httpx.Response(200, json=PAGE))
    page = OutcrawlScrapeTool(outcrawl_api_key="k").invoke({"url": "https://example.com"})
    assert json.loads(route.calls.last.request.content) == {"url": "https://example.com", "formats": ["markdown"]}
    assert page["markdown"].startswith("# Example")
    assert page["title"] == "Example Domain"
    assert page["status_code"] == 200


@respx.mock
def test_loader_makes_one_request_per_url_and_maps_metadata() -> None:
    respx.post("https://api.outcrawl.ai/v1/scrape").mock(return_value=httpx.Response(200, json=PAGE))
    docs = OutcrawlLoader(["https://example.com", "https://example.com/b"], outcrawl_api_key="k").load()
    assert len(docs) == 2
    assert docs[0].page_content == "# Example\n\nBody"
    assert docs[0].metadata == {
        "source": "https://example.com/",
        "title": "Example Domain",
        "status_code": 200,
        "language": "en",
    }


@respx.mock
async def test_async_paths() -> None:
    respx.post("https://api.outcrawl.ai/v1/search").mock(return_value=httpx.Response(200, json=SEARCH))
    respx.post("https://api.outcrawl.ai/v1/scrape").mock(return_value=httpx.Response(200, json=PAGE))
    assert len(await OutcrawlSearchTool(outcrawl_api_key="k").ainvoke({"query": "q"})) == 2
    page = await OutcrawlScrapeTool(outcrawl_api_key="k").ainvoke({"url": "https://example.com"})
    assert page["status_code"] == 200
    docs = [d async for d in OutcrawlLoader(["https://example.com"], outcrawl_api_key="k").alazy_load()]
    assert docs[0].metadata["title"] == "Example Domain"


@pytest.mark.parametrize(
    ("status", "text"),
    [(401, "rejected the API key"), (402, "out of credits"), (500, "status 500")],
)
@respx.mock
def test_error_statuses_raise_readable_errors(status: int, text: str) -> None:
    respx.post("https://api.outcrawl.ai/v1/search").mock(return_value=httpx.Response(status, text="boom"))
    with pytest.raises(OutcrawlError, match=text):
        OutcrawlSearchTool(outcrawl_api_key="k")._run("q")


def test_missing_key_is_reported_before_any_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OUTCRAWL_API_KEY", raising=False)
    with pytest.raises(OutcrawlError, match="No Outcrawl API key"):
        OutcrawlSearchTool()._run("q")
    with pytest.raises(OutcrawlError, match="No Outcrawl API key"):
        list(OutcrawlLoader(["https://example.com"]).lazy_load())


def test_key_is_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OUTCRAWL_API_KEY", "env-key")
    assert OutcrawlScrapeTool().outcrawl_api_key.get_secret_value() == "env-key"
    assert "env-key" not in repr(OutcrawlScrapeTool())
