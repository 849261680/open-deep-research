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
    args_schema: Type[BaseModel] = GoogleSearchInput
    
    async def _arun(self, query: str, num_results: int = 10) -> str:
        """Search Google asynchronously."""
        results = await search_tools.google_search(query, num_results)
        return json.dumps(results, ensure_ascii=False, indent=2)
    
    def _run(self, query: str, num_results: int = 10) -> str:
        """Search Google synchronously."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环已经在运行，返回一个简单的结果
                return json.dumps([{"title": "搜索功能暂时不可用", "link": "", "snippet": "请使用异步调用", "source": "google"}], ensure_ascii=False)
            else:
                return loop.run_until_complete(self._arun(query, num_results))
        except RuntimeError:
            return json.dumps([{"title": "搜索功能暂时不可用", "link": "", "snippet": "请使用异步调用", "source": "google"}], ensure_ascii=False)


class TavilySearchTool(BaseTool):
    """Tool for searching Tavily - AI-optimized search."""
    
    name: str = "tavily_search"
    description: str = "Search Tavily for AI-optimized, high-quality information about a topic. Best for current events and comprehensive research."
    args_schema: Type[BaseModel] = TavilySearchInput
    
    async def _arun(self, query: str, num_results: int = 10) -> str:
        """Search Tavily asynchronously."""
        results = await search_tools.tavily_search(query, num_results)
        return json.dumps(results, ensure_ascii=False, indent=2)
    
    def _run(self, query: str, num_results: int = 10) -> str:
        """Search Tavily synchronously."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环已经在运行，返回一个简单的结果
                return json.dumps([{"title": "搜索功能暂时不可用", "link": "", "snippet": "请使用异步调用", "source": "tavily"}], ensure_ascii=False)
            else:
                return loop.run_until_complete(self._arun(query, num_results))
        except RuntimeError:
            return json.dumps([{"title": "搜索功能暂时不可用", "link": "", "snippet": "请使用异步调用", "source": "tavily"}], ensure_ascii=False)


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
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环已经在运行，返回一个简单的结果
                return json.dumps([{"title": "搜索功能暂时不可用", "link": "", "snippet": "请使用异步调用", "source": "duckduckgo"}], ensure_ascii=False)
            else:
                return loop.run_until_complete(self._arun(query, num_results))
        except RuntimeError:
            return json.dumps([{"title": "搜索功能暂时不可用", "link": "", "snippet": "请使用异步调用", "source": "duckduckgo"}], ensure_ascii=False)


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
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环已经在运行，返回一个简单的结果
                return json.dumps([{"title": "搜索功能暂时不可用", "link": "", "snippet": "请使用异步调用", "source": "wikipedia"}], ensure_ascii=False)
            else:
                return loop.run_until_complete(self._arun(query, num_results))
        except RuntimeError:
            return json.dumps([{"title": "搜索功能暂时不可用", "link": "", "snippet": "请使用异步调用", "source": "wikipedia"}], ensure_ascii=False)


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
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环已经在运行，返回一个简单的结果
                return json.dumps({"web": [], "wikipedia": [], "academic": []}, ensure_ascii=False)
            else:
                return loop.run_until_complete(self._arun(query))
        except RuntimeError:
            return json.dumps({"web": [], "wikipedia": [], "academic": []}, ensure_ascii=False)


# 导出所有工具，只保留高性能工具
research_tools = [
    TavilySearchTool(),
    ComprehensiveSearchTool(),
    GoogleSearchTool()  # 作为备用
]