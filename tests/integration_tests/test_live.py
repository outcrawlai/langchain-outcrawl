"""Live checks against the real Outcrawl API. Skipped unless OUTCRAWL_API_KEY is set."""

import os

import pytest

from langchain_outcrawl import OutcrawlLoader, OutcrawlScrapeTool, OutcrawlSearchTool

pytestmark = pytest.mark.skipif(not os.environ.get("OUTCRAWL_API_KEY"), reason="OUTCRAWL_API_KEY not set")


def test_search_live() -> None:
    hits = OutcrawlSearchTool(limit=3).invoke({"query": "Model Context Protocol specification"})
    assert hits
    assert all(h["url"].startswith("http") for h in hits)


def test_scrape_and_loader_live() -> None:
    page = OutcrawlScrapeTool().invoke({"url": "https://example.com"})
    assert page["status_code"] == 200
    assert "documentation examples" in page["markdown"]
    docs = OutcrawlLoader(["https://example.com"]).load()
    assert docs[0].metadata["source"].startswith("https://example.com")
