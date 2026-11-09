"""LangChain tools backed by the Outcrawl search and scrape APIs."""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from langchain_core.utils import secret_from_env
from pydantic import BaseModel, Field, SecretStr

from langchain_outcrawl import _client


class OutcrawlSearchInput(BaseModel):
    """Input for the Outcrawl search tool."""

    query: str = Field(description="The web search query.")
    limit: int | None = Field(
        default=None,
        description="Maximum number of results to return. Uses the tool's default when omitted.",
    )


class OutcrawlScrapeInput(BaseModel):
    """Input for the Outcrawl scrape tool."""

    url: str = Field(description="The full URL of the page to load, including https://.")


class _OutcrawlTool(BaseTool):
    outcrawl_api_key: SecretStr = Field(
        default_factory=secret_from_env("OUTCRAWL_API_KEY", default=""),
        description="Outcrawl API key. Read from the OUTCRAWL_API_KEY environment variable by default.",
    )
    timeout: float = Field(default=_client.DEFAULT_TIMEOUT, description="Request timeout in seconds.")
    extra_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra request fields passed through to the Outcrawl API as they are.",
    )

    def _key(self) -> str:
        key = self.outcrawl_api_key.get_secret_value()
        if not key:
            raise _client.OutcrawlError("No Outcrawl API key. Set OUTCRAWL_API_KEY or pass outcrawl_api_key.")
        return key


class OutcrawlSearchTool(_OutcrawlTool):
    """Search the web with the Outcrawl search API.

    Returns a list of results, each with `url`, `title`, `snippet` and `rank`.

    Setup:
        Install `langchain-outcrawl` and set `OUTCRAWL_API_KEY`. The free plan includes
        credits every month, see https://outcrawl.ai.

    Example:
        ```python
        from langchain_outcrawl import OutcrawlSearchTool

        tool = OutcrawlSearchTool(limit=5)
        tool.invoke({"query": "Model Context Protocol specification"})
        ```
    """

    name: str = "outcrawl_search"
    description: str = (
        "Search the web. Input is a search query. Returns a list of results with url, title, "
        "snippet and rank. Use outcrawl_scrape to read a page in full."
    )
    args_schema: type[BaseModel] = OutcrawlSearchInput
    limit: int | None = Field(default=None, description="Default maximum number of results per search.")

    def _run(
        self,
        query: str,
        limit: int | None = None,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> list[dict[str, Any]]:
        body = _client.search_body(query, limit if limit is not None else self.limit, self.extra_params)
        return _client.parse_hits(_client.post(self._key(), "/search", body, self.timeout))

    async def _arun(
        self,
        query: str,
        limit: int | None = None,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> list[dict[str, Any]]:
        body = _client.search_body(query, limit if limit is not None else self.limit, self.extra_params)
        return _client.parse_hits(await _client.apost(self._key(), "/search", body, self.timeout))


class OutcrawlScrapeTool(_OutcrawlTool):
    """Load a web page with the Outcrawl scrape API and return it as Markdown.

    Returns a dict with `url`, `title`, `status_code`, `markdown` and the API `metadata`.

    Setup:
        Install `langchain-outcrawl` and set `OUTCRAWL_API_KEY`.

    Example:
        ```python
        from langchain_outcrawl import OutcrawlScrapeTool

        tool = OutcrawlScrapeTool()
        tool.invoke({"url": "https://example.com"})
        ```
    """

    name: str = "outcrawl_scrape"
    description: str = (
        "Load a web page by URL and return its content as Markdown, with the page title and "
        "HTTP status code. Input is a full URL."
    )
    args_schema: type[BaseModel] = OutcrawlScrapeInput

    def _run(self, url: str, run_manager: CallbackManagerForToolRun | None = None) -> dict[str, Any]:
        body = _client.scrape_body(url, self.extra_params)
        return _client.parse_page(_client.post(self._key(), "/scrape", body, self.timeout))

    async def _arun(self, url: str, run_manager: AsyncCallbackManagerForToolRun | None = None) -> dict[str, Any]:
        body = _client.scrape_body(url, self.extra_params)
        return _client.parse_page(await _client.apost(self._key(), "/scrape", body, self.timeout))
