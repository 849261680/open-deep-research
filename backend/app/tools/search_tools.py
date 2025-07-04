from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field
from typing import Optional, Type, List, Dict, Any
import json
from app.services.search_tools import search_tools


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


class ComprehensiveSearchInput(BaseModel):
    """Input for Comprehensive Search tool."""
    query: str = Field(description="Search query to look up")


class GoogleSearchTool(BaseTool):
    """Tool for searching Google using SerpAPI or DuckDuckGo fallback."""
    
    name: str = "google_search"
    description: str = "Search Google for current information about a topic. Returns title, link, and snippet for each result."
    args_schema: Type[BaseModel] = GoogleSearchInput
    
    async def _arun(self, query: str, num_results: int = 10) -> str:
        """Search Google asynchronously."""
        results = await search_tools.google_search(query, num_results)
        return json.dumps(results, ensure_ascii=False, indent=2)
    
    def _run(self, query: str, num_results: int = 10) -> str:
        """Search Google synchronously."""
        import asyncio
        return asyncio.run(self._arun(query, num_results))


class DuckDuckGoSearchTool(BaseTool):
    """Tool for searching DuckDuckGo."""
    
    name: str = "duckduckgo_search"
    description: str = "Search DuckDuckGo for current information about a topic. Returns title, link, and snippet for each result."
    args_schema: Type[BaseModel] = DuckDuckGoSearchInput
    
    async def _arun(self, query: str, num_results: int = 10) -> str:
        """Search DuckDuckGo asynchronously."""
        results = await search_tools.duckduckgo_search(query, num_results)
        return json.dumps(results, ensure_ascii=False, indent=2)
    
    def _run(self, query: str, num_results: int = 10) -> str:
        """Search DuckDuckGo synchronously."""
        import asyncio
        return asyncio.run(self._arun(query, num_results))


class WikipediaSearchTool(BaseTool):
    """Tool for searching Wikipedia."""
    
    name: str = "wikipedia_search"
    description: str = "Search Wikipedia for encyclopedic information about a topic. Returns title, link, and summary for each result."
    args_schema: Type[BaseModel] = WikipediaSearchInput
    
    async def _arun(self, query: str, num_results: int = 5) -> str:
        """Search Wikipedia asynchronously."""
        results = await search_tools.wikipedia_search(query, num_results)
        return json.dumps(results, ensure_ascii=False, indent=2)
    
    def _run(self, query: str, num_results: int = 5) -> str:
        """Search Wikipedia synchronously."""
        import asyncio
        return asyncio.run(self._arun(query, num_results))


class ComprehensiveSearchTool(BaseTool):
    """Tool for comprehensive search using multiple sources."""
    
    name: str = "comprehensive_search"
    description: str = "Search multiple sources (Google, Wikipedia, Academic) for comprehensive information about a topic."
    args_schema: Type[BaseModel] = ComprehensiveSearchInput
    
    async def _arun(self, query: str) -> str:
        """Perform comprehensive search asynchronously."""
        results = await search_tools.comprehensive_search(query)
        return json.dumps(results, ensure_ascii=False, indent=2)
    
    def _run(self, query: str) -> str:
        """Perform comprehensive search synchronously."""
        import asyncio
        return asyncio.run(self._arun(query))


# 导出所有工具
research_tools = [
    GoogleSearchTool(),
    DuckDuckGoSearchTool(),
    WikipediaSearchTool(),
    ComprehensiveSearchTool()
]