import asyncio
import json
import logging

from langchain.tools import BaseTool
from pydantic import BaseModel
from pydantic import Field

from ..services.search_tools import search_tools

logger = logging.getLogger(__name__)


class GoogleSearchInput(BaseModel):
    """Input for Google Search tool."""

    query: str = Field(description="Search query to look up")
    num_results: int = Field(default=10, description="Number of results to return")


class DuckDuckGoSearchInput(BaseModel):
    """Input for DuckDuckGo Search tool."""

    query: str = Field(description="Search query to look up")
    num_results: int = Field(default=10, description="Number of results to return")


class WikipediaSearchInput(BaseModel):
    """Input for Wikipedia Search tool."""

    query: str = Field(description="Search query to look up")
    num_results: int = Field(default=5, description="Number of results to return")


class TavilySearchInput(BaseModel):
    """Input for Tavily Search tool."""

    query: str = Field(description="Search query to look up")
    num_results: int = Field(default=10, description="Number of results to return")


class ComprehensiveSearchInput(BaseModel):
    """Input for Comprehensive Search tool."""

    query: str = Field(description="Search query to look up")


class GoogleSearchTool(BaseTool):
    """Tool for searching Google using SerpAPI or DuckDuckGo fallback."""

    name: str = "google_search"
    description: str = "Search Google for current information about a topic. Returns title, link, and snippet for each result."
    args_schema: type[BaseModel] = GoogleSearchInput

    async def _arun(self, query: str, num_results: int = 10) -> str:
        results = await search_tools.google_search(query, num_results)
        return json.dumps(results, ensure_ascii=False, indent=2)

    def _run(self, query: str, num_results: int = 10) -> str:
        return asyncio.run(self._arun(query, num_results))


class TavilySearchTool(BaseTool):
    """Tool for searching Tavily - AI-optimized search."""

    name: str = "tavily_search"
    description: str = "Search Tavily for AI-optimized, high-quality information about a topic. Best for current events and comprehensive research."
    args_schema: type[BaseModel] = TavilySearchInput

    async def _arun(self, query: str, num_results: int = 10) -> str:
        results = await search_tools.tavily_search(query, num_results)
        return json.dumps(results, ensure_ascii=False, indent=2)

    def _run(self, query: str, num_results: int = 10) -> str:
        return asyncio.run(self._arun(query, num_results))


class DuckDuckGoSearchTool(BaseTool):
    """Tool for searching DuckDuckGo."""

    name: str = "duckduckgo_search"
    description: str = "Search DuckDuckGo for current information about a topic. Returns title, link, and snippet for each result."
    args_schema: type[BaseModel] = DuckDuckGoSearchInput

    async def _arun(self, query: str, num_results: int = 10) -> str:
        results = await search_tools.duckduckgo_search(query, num_results)
        return json.dumps(results, ensure_ascii=False, indent=2)

    def _run(self, query: str, num_results: int = 10) -> str:
        return asyncio.run(self._arun(query, num_results))


class WikipediaSearchTool(BaseTool):
    """Tool for searching Wikipedia."""

    name: str = "wikipedia_search"
    description: str = "Search Wikipedia for encyclopedic information about a topic. Returns title, link, and summary for each result."
    args_schema: type[BaseModel] = WikipediaSearchInput

    async def _arun(self, query: str, num_results: int = 5) -> str:
        results = await search_tools.wikipedia_search(query, num_results)
        return json.dumps(results, ensure_ascii=False, indent=2)

    def _run(self, query: str, num_results: int = 5) -> str:
        return asyncio.run(self._arun(query, num_results))


class ComprehensiveSearchTool(BaseTool):
    """Tool for comprehensive search using multiple sources."""

    name: str = "comprehensive_search"
    description: str = "Search multiple sources (Google, Wikipedia, Academic) for comprehensive information about a topic."
    args_schema: type[BaseModel] = ComprehensiveSearchInput

    async def _arun(self, query: str) -> str:
        results = await search_tools.comprehensive_search(query)
        return json.dumps(results, ensure_ascii=False, indent=2)

    def _run(self, query: str) -> str:
        return asyncio.run(self._arun(query))


# 导出所有工具，只保留高性能工具
research_tools = [
    TavilySearchTool(),
    ComprehensiveSearchTool(),
    GoogleSearchTool(),  # 作为备用
]
