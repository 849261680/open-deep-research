import asyncio
import logging
import os

import requests

from ..utils.env import load_project_env

load_project_env()

logger = logging.getLogger(__name__)


class SearchTools:
    def __init__(self) -> None:
        self.serpapi_key = os.getenv("SERPAPI_API_KEY")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")

    async def tavily_search(
        self, query: str, num_results: int = 10
    ) -> list[dict[str, object]]:
        """使用Tavily搜索"""
        logger.debug("开始 Tavily 搜索: %s", query)

        if not self.tavily_api_key:
            logger.warning("Tavily API Key 未配置，返回空结果")
            return []

        try:
            result = await asyncio.to_thread(self._sync_tavily_search, query, num_results)
            logger.debug("Tavily 搜索成功，返回 %d 个结果", len(result))
            return result
        except asyncio.TimeoutError:
            logger.warning("Tavily search timeout for query: %s", query)
            return []
        except Exception as e:
            logger.error("Tavily search error: %s", e)
            return []

    def _sync_tavily_search(
        self, query: str, num_results: int = 10
    ) -> list[dict[str, object]]:
        """同步版本的Tavily搜索，优化内容长度"""
        try:
            from tavily import TavilyClient

            tavily = TavilyClient(api_key=self.tavily_api_key)
            response = tavily.search(
                query=query,
                search_depth="basic",
                max_results=min(num_results, 8),
            )

            results = []
            for result in response.get("results", []):
                title = result.get("title", "")
                content = result.get("content", "")

                max_content_length = 300
                if len(content) > max_content_length:
                    content = content[:max_content_length] + "..."

                results.append(
                    {
                        "title": title,
                        "link": result.get("url", ""),
                        "snippet": content,
                        "source": "tavily",
                    }
                )

            return results
        except Exception as e:
            logger.error("Sync Tavily search error: %s", e, exc_info=True)
            return []

    async def google_search(
        self, query: str, num_results: int = 10
    ) -> list[dict[str, object]]:
        """使用SerpAPI进行Google搜索"""
        if not self.serpapi_key:
            return await self.tavily_search(query, num_results)

        try:
            result = await asyncio.to_thread(self._sync_google_search, query, num_results)
            if result:
                return result
            return await self.tavily_search(query, num_results)
        except Exception as e:
            logger.error("Google search error: %s", e)
            return await self.tavily_search(query, num_results)

    def _sync_google_search(
        self, query: str, num_results: int = 10
    ) -> list[dict[str, object]]:
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": self.serpapi_key,
            "num": num_results,
            "engine": "google",
        }

        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            logger.warning(
                "Google search failed with status %d, using Tavily", response.status_code
            )
            return []

        data = response.json()
        results = []
        for result in data.get("organic_results", []):
            results.append(
                {
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "source": "google",
                }
            )
        return results

    async def duckduckgo_search(
        self, query: str, num_results: int = 10
    ) -> list[dict[str, object]]:
        """DuckDuckGo搜索 - 免费备选方案"""
        logger.debug("开始 DuckDuckGo 搜索: %s", query)

        try:
            result = await asyncio.to_thread(
                self._sync_duckduckgo_search, query, num_results
            )
            logger.debug("DuckDuckGo 搜索成功，返回 %d 个结果", len(result))
            return result
        except asyncio.TimeoutError:
            logger.warning("DuckDuckGo search timeout for query: %s", query)
            return []
        except Exception as e:
            logger.error("DuckDuckGo search error: %s", e)
            return []

    def _sync_duckduckgo_search(
        self, query: str, num_results: int = 10
    ) -> list[dict[str, object]]:
        """同步版本的DuckDuckGo搜索 - 免费备选方案"""
        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                results = []
                ddg_results = ddgs.text(query, max_results=min(num_results, 10))

                for result in ddg_results:
                    results.append(
                        {
                            "title": result.get("title", ""),
                            "link": result.get("href", ""),
                            "snippet": result.get("body", ""),
                            "source": "duckduckgo",
                        }
                    )

                return results
        except Exception as e:
            logger.error("DuckDuckGo 同步搜索失败: %s", e)
            return []

    async def wikipedia_search(
        self, query: str, num_results: int = 5
    ) -> list[dict[str, object]]:
        """Wikipedia搜索已禁用，避免超时问题"""
        logger.debug("Wikipedia 搜索已禁用以提高性能，查询: %s", query)
        return []

    def _sync_wikipedia_search(
        self, query: str, num_results: int = 5
    ) -> list[dict[str, object]]:
        """Wikipedia搜索已禁用"""
        return []

    async def academic_search(
        self, query: str, num_results: int = 5
    ) -> list[dict[str, object]]:
        """学术搜索，优先使用 Tavily"""
        if self.tavily_api_key:
            academic_query = f"{query} research academic study paper"
            return await self.tavily_search(academic_query, num_results)
        academic_query = f"site:scholar.google.com OR site:arxiv.org OR site:researchgate.net {query}"
        return await self.google_search(academic_query, num_results)

    async def comprehensive_search(
        self, query: str
    ) -> dict[str, list[dict[str, object]]]:
        """综合搜索，优先使用 Tavily，避免超时问题"""
        results = {}

        if self.tavily_api_key:
            tavily_results = await self.tavily_search(query, 6)
            results["web"] = tavily_results
            results["wikipedia"] = []
            results["academic"] = []
        else:
            logger.warning("Tavily 不可用，使用备用搜索方案")
            try:
                google_results = await self.google_search(query, 8)
                if google_results:
                    results["web"] = google_results
                else:
                    results["web"] = await self.duckduckgo_search(query, 8)
            except Exception as e:
                logger.warning("Google搜索失败 (%s)，使用DuckDuckGo搜索", e)
                results["web"] = await self.duckduckgo_search(query, 8)

            results["wikipedia"] = []
            results["academic"] = []

        return results


# 全局实例
search_tools = SearchTools()
