# langchain-outcrawl

[![PyPI - Version](https://img.shields.io/pypi/v/langchain-outcrawl.svg)](https://pypi.org/project/langchain-outcrawl)

[LangChain](https://www.langchain.com/) tools and a document loader for [Outcrawl](https://outcrawl.ai), web infrastructure for AI agents.

- `OutcrawlSearchTool`: web search through the Outcrawl search API. Returns results with `url`, `title`, `snippet` and `rank`.
- `OutcrawlScrapeTool`: loads a page by URL through the Outcrawl scrape API and returns it as Markdown, with the page title and HTTP status code.
- `OutcrawlLoader`: a `BaseLoader` that does the same for a list of URLs and returns LangChain `Document`s.

All three have async versions (`ainvoke`, `alazy_load`).

## Installation

```bash
pip install langchain-outcrawl
```

You need an Outcrawl API key, which you create at [outcrawl.ai/console](https://outcrawl.ai/console). The free plan includes credits every month and needs no card (see [pricing](https://outcrawl.ai/pricing)). Set it as an environment variable:

```bash
export OUTCRAWL_API_KEY="..."
```

or pass `outcrawl_api_key=` to the tool or loader.

## Usage

### Search

```python
from langchain_outcrawl import OutcrawlSearchTool

search = OutcrawlSearchTool(limit=5)
results = search.invoke({"query": "Model Context Protocol specification"})
for r in results:
    print(r["rank"], r["url"], r["title"])
```

### Scrape a page

```python
from langchain_outcrawl import OutcrawlScrapeTool

page = OutcrawlScrapeTool().invoke({"url": "https://example.com"})
print(page["status_code"], page["title"])
print(page["markdown"])
```

### Load pages as documents

```python
from langchain_outcrawl import OutcrawlLoader

docs = OutcrawlLoader(urls=["https://example.com"]).load()
print(docs[0].metadata["source"], docs[0].metadata["title"])
print(docs[0].page_content)
```

### In an agent

The tools are ordinary LangChain tools, so you can hand them to any agent that takes a list of tools:

```python
from langchain_outcrawl import OutcrawlScrapeTool, OutcrawlSearchTool

tools = [OutcrawlSearchTool(limit=5), OutcrawlScrapeTool()]
```

## Options

- `timeout`: request timeout in seconds (default 60).
- `extra_params`: a dict of extra request fields sent to the Outcrawl API as they are. See the [Outcrawl docs](https://outcrawl.ai/docs) for what the API accepts.
- Errors: a rejected key (401), an empty balance (402) and other failures raise `OutcrawlError` with a readable message.

## Development

```bash
pip install -e . pytest pytest-asyncio respx
pytest tests/unit_tests
```

The tests in `tests/integration_tests` call the real API and run only when `OUTCRAWL_API_KEY` is set.

## License

Apache-2.0, see [LICENSE](LICENSE).
