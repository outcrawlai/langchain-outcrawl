"""LangChain document loader backed by the Outcrawl scrape API."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from langchain_core.utils import secret_from_env
from pydantic import SecretStr

from langchain_outcrawl import _client


class OutcrawlLoader(BaseLoader):
    """Load web pages as Markdown documents with the Outcrawl scrape API.

    One request is made per URL, in order. Each document has the page Markdown as
    `page_content` and `source`, `title`, `status_code` and the API metadata in `metadata`.

    Setup:
        Install `langchain-outcrawl` and set `OUTCRAWL_API_KEY`.

    Example:
        ```python
        from langchain_outcrawl import OutcrawlLoader

        docs = OutcrawlLoader(urls=["https://example.com"]).load()
        ```
    """

    def __init__(
        self,
        urls: Sequence[str],
        *,
        outcrawl_api_key: SecretStr | str | None = None,
        timeout: float = _client.DEFAULT_TIMEOUT,
        extra_params: dict[str, Any] | None = None,
    ) -> None:
        self.urls = list(urls)
        if outcrawl_api_key is None:
            outcrawl_api_key = secret_from_env("OUTCRAWL_API_KEY", default="")()
        self._key = outcrawl_api_key.get_secret_value() if isinstance(outcrawl_api_key, SecretStr) else outcrawl_api_key
        self.timeout = timeout
        self.extra_params = extra_params or {}

    def _check_key(self) -> str:
        if not self._key:
            raise _client.OutcrawlError("No Outcrawl API key. Set OUTCRAWL_API_KEY or pass outcrawl_api_key.")
        return self._key

    @staticmethod
    def _to_document(page: dict[str, Any]) -> Document:
        metadata = {
            "source": page["url"],
            "title": page["title"],
            "status_code": page["status_code"],
            **{k: v for k, v in page["metadata"].items() if k != "title"},
        }
        return Document(page_content=page["markdown"], metadata=metadata)

    def lazy_load(self) -> Iterator[Document]:
        key = self._check_key()
        for url in self.urls:
            body = _client.scrape_body(url, self.extra_params)
            yield self._to_document(_client.parse_page(_client.post(key, "/scrape", body, self.timeout)))

    async def alazy_load(self) -> AsyncIterator[Document]:
        key = self._check_key()
        for url in self.urls:
            body = _client.scrape_body(url, self.extra_params)
            yield self._to_document(_client.parse_page(await _client.apost(key, "/scrape", body, self.timeout)))
