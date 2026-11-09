"""Small HTTP client for the Outcrawl search and scrape APIs."""

from __future__ import annotations

from typing import Any

import httpx

API_BASE_URL = "https://api.outcrawl.ai/v1"
DEFAULT_TIMEOUT = 60.0


class OutcrawlError(RuntimeError):
    """Raised when the Outcrawl API answers with an error status."""


def _headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _raise_for_status(response: httpx.Response) -> None:
    if response.is_success:
        return
    detail = response.text[:300]
    if response.status_code == 401:
        raise OutcrawlError("Outcrawl rejected the API key (401). Check OUTCRAWL_API_KEY.")
    if response.status_code == 402:
        raise OutcrawlError("Outcrawl account is out of credits (402).")
    raise OutcrawlError(f"Outcrawl request failed with status {response.status_code}: {detail}")


def search_body(query: str, limit: int | None, extra: dict[str, Any] | None) -> dict[str, Any]:
    body: dict[str, Any] = {"query": query}
    if limit is not None:
        body["limit"] = limit
    if extra:
        body.update({k: v for k, v in extra.items() if v is not None})
    return body


def scrape_body(url: str, extra: dict[str, Any] | None) -> dict[str, Any]:
    body: dict[str, Any] = {"url": url, "formats": ["markdown"]}
    if extra:
        body.update({k: v for k, v in extra.items() if v is not None})
    return body


def post(api_key: str, path: str, body: dict[str, Any], timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    with httpx.Client(timeout=timeout) as client:
        response = client.post(f"{API_BASE_URL}{path}", headers=_headers(api_key), json=body)
    _raise_for_status(response)
    payload: dict[str, Any] = response.json()
    return payload


async def apost(api_key: str, path: str, body: dict[str, Any], timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{API_BASE_URL}{path}", headers=_headers(api_key), json=body)
    _raise_for_status(response)
    payload: dict[str, Any] = response.json()
    return payload


def parse_hits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the search hits as plain dicts with url, title, snippet and rank."""
    hits = []
    for hit in payload.get("hits", []):
        item = {
            "url": hit.get("url", ""),
            "title": hit.get("title") or "",
            "snippet": hit.get("snippet") or "",
        }
        if hit.get("rank") is not None:
            item["rank"] = hit["rank"]
        hits.append(item)
    return hits


def parse_page(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the scraped page as url, title, status code, markdown and the API metadata."""
    metadata = payload.get("metadata") or {}
    return {
        "url": payload.get("url", ""),
        "title": metadata.get("title") or "",
        "status_code": payload.get("statusCode"),
        "markdown": payload.get("markdown") or "",
        "metadata": metadata,
    }
