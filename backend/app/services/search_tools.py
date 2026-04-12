import asyncio
import os

import requests
import urllib3

from ..utils.env import load_project_env

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_project_env()


class SearchTools:
    def __init__(self) -> None:
        self.serpapi_key = os.getenv("SERPAPI_API_KEY")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")

    async def tavily_search(
        self, query: str, num_results: int = 10
    ) -> list[dict[str, object]]:
        """使用Tavily搜索"""
        print(f"🔍 开始 Tavily 搜索: {query}")

        if not self.tavily_api_key:
            print("❌ Tavily API Key 未配置，返回空结果")
            return []

        print("✅ Tavily API Key 已配置，执行搜索...")

        try:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._sync_tavily_search, query, num_results)
                result = await asyncio.wait_for(
                    asyncio.wrap_future(future), timeout=10.0
                )
                print(f"✅ Tavily 搜索成功，返回 {len(result)} 个结果")
                return result
        except asyncio.TimeoutError:
            print(f"⏰ Tavily search timeout for query: {query}")
            return []
        except Exception as e:
            print(f"❌ Tavily search error: {e}")
            print("🔄 Tavily 搜索失败，返回空结果")
            return []

    def _sync_tavily_search(
        self, query: str, num_results: int = 10
    ) -> list[dict[str, object]]:
        """同步版本的Tavily搜索，优化内容长度"""
        print(f"🔄 执行同步 Tavily 搜索: {query}")
        try:
            from tavily import TavilyClient

            print("📡 创建 Tavily 客户端...")
            tavily = TavilyClient(api_key=self.tavily_api_key)

            print(f"🚀 发送搜索请求: {query} (最多 {min(num_results, 8)} 个结果)")
            # 执行搜索，限制结果数量以提高性能
            response = tavily.search(
                query=query,
                search_depth="basic",
                max_results=min(num_results, 8),  # 减少结果数量
            )

            print(f"📥 收到搜索响应: {type(response)}")

            results = []
            for i, result in enumerate(response.get("results", [])):
                title = result.get("title", "")
                content = result.get("content", "")

                # 限制内容长度，避免 token 超限
                max_content_length = 300  # 约 200-400 tokens
                if len(content) > max_content_length:
                    content = content[:max_content_length] + "..."

                print(
                    f"  📄 处理结果 {i + 1}: {title[:50]}... (内容长度: {len(content)})"
                )
                results.append(
                    {
                        "title": title,
                        "link": result.get("url", ""),
                        "snippet": content,
                        "source": "tavily",
                    }
                )

            print(f"✅ Tavily 同步搜索完成，返回 {len(results)} 个结果")
            return results
        except Exception as e:
            print(f"❌ Sync Tavily search error: {e}")
            import traceback

            print(f"📋 错误详情: {traceback.format_exc()}")
            return []

    async def google_search(
        self, query: str, num_results: int = 10
    ) -> list[dict[str, object]]:
        """使用SerpAPI进行Google搜索"""
        if not self.serpapi_key:
            # 如果没有SerpAPI密钥，使用Tavily作为替代
            return await self.tavily_search(query, num_results)

        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": self.serpapi_key,
            "num": num_results,
            "engine": "google",
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
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
            # 如果Google搜索失败，回退到Tavily
            print(
                f"Google search failed with status {response.status_code}, using Tavily"
            )
            return await self.tavily_search(query, num_results)
        except Exception as e:
            print(f"Google search error: {e}")
            return await self.tavily_search(query, num_results)

    async def duckduckgo_search(
        self, query: str, num_results: int = 10
    ) -> list[dict[str, object]]:
        """DuckDuckGo搜索 - 免费备选方案"""
        print(f"🔍 开始 DuckDuckGo 搜索: {query}")

        try:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    self._sync_duckduckgo_search, query, num_results
                )
                result = await asyncio.wait_for(
                    asyncio.wrap_future(future), timeout=15.0
                )
                print(f"✅ DuckDuckGo 搜索成功，返回 {len(result)} 个结果")
                return result
        except asyncio.TimeoutError:
            print(f"⏰ DuckDuckGo search timeout for query: {query}")
            return []
        except Exception as e:
            print(f"❌ DuckDuckGo search error: {e}")
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
            print(f"❌ DuckDuckGo 同步搜索失败: {e}")
            return []

    async def wikipedia_search(
        self, query: str, num_results: int = 5
    ) -> list[dict[str, object]]:
        """Wikipedia搜索已禁用，避免超时问题"""
        print(f"⚠️ Wikipedia 搜索已禁用以提高性能，查询: {query}")
        return []

    def _sync_wikipedia_search(
        self, query: str, num_results: int = 5
    ) -> list[dict[str, object]]:
        """Wikipedia搜索已禁用"""
        print(f"⚠️ 同步 Wikipedia 搜索已禁用，查询: {query}")
        return []

    async def academic_search(
        self, query: str, num_results: int = 5
    ) -> list[dict[str, object]]:
        """学术搜索，优先使用 Tavily"""
        if self.tavily_api_key:
            print(f"🎓 使用 Tavily 进行学术搜索: {query}")
            # 为学术搜索优化查询
            academic_query = f"{query} research academic study paper"
            return await self.tavily_search(academic_query, num_results)
        # 回退到Google学术搜索
        academic_query = f"site:scholar.google.com OR site:arxiv.org OR site:researchgate.net {query}"
        return await self.google_search(academic_query, num_results)

    async def comprehensive_search(
        self, query: str
    ) -> dict[str, list[dict[str, object]]]:
        """综合搜索，优先使用 Tavily，避免超时问题"""
        results = {}

        # 如果有 Tavily API Key，只使用 Tavily 搜索
        if self.tavily_api_key:
            print(f"🎯 使用 Tavily 进行综合搜索: {query}")
            # 减少结果数量以提高性能，避免 token 超限
            tavily_results = await self.tavily_search(query, 6)  # 从10减少到6
            results["web"] = tavily_results
            results["wikipedia"] = []  # 不使用 Wikipedia 避免超时
            results["academic"] = []  # 不使用学术搜索避免复杂性
        else:
            print("⚠️ Tavily 不可用，使用备用搜索方案")
            # 回退方案：尝试 Google 搜索，如果失败则使用 DuckDuckGo
            try:
                google_results = await self.google_search(query, 8)
                if google_results:
                    results["web"] = google_results
                else:
                    print("🔄 Google搜索无结果，尝试DuckDuckGo搜索")
                    results["web"] = await self.duckduckgo_search(query, 8)
            except Exception as e:
                print(f"⚠️ Google搜索失败 ({e})，使用DuckDuckGo搜索")
                results["web"] = await self.duckduckgo_search(query, 8)

            results["wikipedia"] = []
            results["academic"] = []

        return results


# 全局实例
search_tools = SearchTools()
