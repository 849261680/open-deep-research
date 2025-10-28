from collections.abc import AsyncGenerator
from datetime import datetime
from datetime import timezone
from typing import Any

from ..chains.research_chains import research_chains
from ..services.search_tools import search_tools


class ResearchExecutor:
    """研究步骤执行模块 - 负责执行具体的研究步骤"""

    def __init__(self) -> None:
        pass

    async def execute_research_step_with_updates(
        self, step: dict[str, Any], query: str
    ) -> AsyncGenerator[dict[str, Any], None]:
        """带进度更新的研究步骤执行

        为什么需要进度更新：
        - 研究步骤执行时间较长，需要给用户实时反馈
        - 让用户了解当前执行状态，提升用户体验
        """
        step_result = {
            "step": step["step"],
            "title": step["title"],
            "status": "executing",
            "search_results": {},
            "search_sources": [],  # 新增：搜索来源信息
            "analysis": "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # 1. 执行搜索 - 显示搜索进度
            search_results: dict[str, dict[str, list[dict[str, Any]]]] = {}
            all_search_sources: list[dict[str, Any]] = []

            search_queries = step.get("search_queries")
            if search_queries and isinstance(search_queries, list):
                for i, search_query in enumerate(search_queries):
                    if isinstance(search_query, str):
                        yield {
                            "type": "search_progress",
                            "message": f"正在搜索：{search_query}",
                            "data": {
                                "query": search_query,
                                "step": i + 1,
                                "total": len(search_queries),
                            },
                        }

                        # 根据工具类型执行不同的搜索 - 为什么需要不同工具：不同来源提供不同类型的信息
                        tool = step.get("tool")
                        if isinstance(tool, str):
                            search_result = await self._execute_search_by_tool(
                                tool, search_query
                            )
                        else:
                            search_result = await self._execute_search_by_tool(
                                "comprehensive_search", search_query
                            )
                        search_results[search_query] = search_result

                        # 收集搜索来源信息 - 为什么收集来源：用户需要了解信息的可信度和出处
                        sources = self._extract_search_sources(
                            search_result, search_query
                        )
                        all_search_sources.extend(sources)

                        yield {
                            "type": "search_result",
                            "message": f"找到 {sum(len(items) for items in search_result.values())} 个结果",
                            "data": {"query": search_query, "sources": sources},
                        }

            step_result["search_results"] = search_results
            step_result["search_sources"] = all_search_sources

            # 2. 分析搜索结果
            yield {
                "type": "analysis_progress",
                "message": "正在分析搜索结果...",
                "data": None,
            }

            if search_results:
                # 合并所有搜索结果 - 为什么合并：提供更全面的分析基础
                combined_results = self._combine_search_results(search_results)

                # 使用链进行分析
                step_title = step["title"]
                if isinstance(step_title, str):
                    analysis = await research_chains.analyze_search_results_with_chain(
                        step_title, combined_results
                    )
                else:
                    analysis = "步骤标题格式错误"
                step_result["analysis"] = analysis
            else:
                step_result["analysis"] = "没有找到相关搜索结果"

            step_result["status"] = "completed"
            yield {
                "type": "step_complete",
                "message": f"完成：{step['title']}",
                "data": step_result,
            }

        except Exception as e:
            step_result["analysis"] = f"执行错误: {str(e)}"
            step_result["status"] = "failed"
            yield {
                "type": "step_complete",
                "message": f"步骤失败：{step['title']}",
                "data": step_result,
            }

    async def execute_research_step(
        self, step: dict[str, Any], query: str
    ) -> dict[str, Any]:
        """执行单个研究步骤（非流式版本）

        为什么需要非流式版本：
        - 某些场景下不需要实时反馈，只需要最终结果
        - 提供更简单的调用接口
        """
        step_result = {
            "step": step["step"],
            "title": step["title"],
            "status": "executing",
            "search_results": {},
            "analysis": "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # 1. 执行搜索
            search_results: dict[str, dict[str, list[dict[str, Any]]]] = {}
            search_queries = step.get("search_queries")
            if search_queries and isinstance(search_queries, list):
                for search_query in search_queries:
                    if isinstance(search_query, str):
                        tool = step.get("tool")
                        if isinstance(tool, str):
                            search_result = await self._execute_search_by_tool(
                                tool, search_query
                            )
                        else:
                            search_result = await self._execute_search_by_tool(
                                "comprehensive_search", search_query
                            )
                        search_results[search_query] = search_result

            step_result["search_results"] = search_results

            # 2. 使用链分析搜索结果
            if search_results:
                combined_results = self._combine_search_results(search_results)
                step_title = step["title"]
                if isinstance(step_title, str):
                    analysis = await research_chains.analyze_search_results_with_chain(
                        step_title, combined_results
                    )
                else:
                    analysis = "步骤标题格式错误"
                step_result["analysis"] = analysis
            else:
                step_result["analysis"] = "没有找到相关搜索结果"

            step_result["status"] = "completed"
        except Exception as e:
            step_result["analysis"] = f"执行错误: {str(e)}"
            step_result["status"] = "failed"

        return step_result

    async def _execute_search_by_tool(
        self, tool: str, search_query: str
    ) -> dict[str, list[dict[str, Any]]]:
        """根据工具类型执行搜索

        为什么需要这个方法：
        - 统一搜索逻辑，避免重复代码
        - 便于扩展新的搜索工具
        """
        if tool == "comprehensive_search":
            return await search_tools.comprehensive_search(search_query)
        if tool == "google_search":
            return {"web": await search_tools.google_search(search_query)}
        if tool == "wikipedia_search":
            return {"wikipedia": await search_tools.wikipedia_search(search_query)}
        # 默认使用综合搜索 - 为什么使用默认：确保即使工具配置错误也能正常工作
        return await search_tools.comprehensive_search(search_query)

    def _extract_search_sources(
        self, search_result: dict[str, list[dict[str, Any]]], search_query: str
    ) -> list[dict[str, Any]]:
        """提取搜索来源信息

        为什么需要提取来源：
        - 用户需要了解信息的来源和可信度
        - 便于后续的引用和验证
        """
        sources: list[dict[str, Any]] = []
        for source_type, items in search_result.items():
            for item in items[
                :3
            ]:  # 只取前3个结果 - 为什么限制数量：避免信息过载，提高性能
                if "title" in item and "link" in item:
                    sources.append(
                        {
                            "title": item["title"],
                            "link": item["link"],
                            "source": source_type,
                            "query": search_query,
                        }
                    )
        return sources

    def _combine_search_results(
        self, search_results: dict[str, dict[str, list[dict[str, Any]]]]
    ) -> dict[str, list[dict[str, Any]]]:
        """合并所有搜索结果

        为什么需要合并：
        - 为分析提供更全面的数据基础
        - 统一数据格式，便于后续处理
        """
        combined_results: dict[str, list[dict[str, Any]]] = {}
        for query_results in search_results.values():
            for source, items in query_results.items():
                if source not in combined_results:
                    combined_results[source] = []
                combined_results[source].extend(items)
        return combined_results
