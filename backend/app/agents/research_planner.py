import json
from collections.abc import Callable

from app.chains.research_chains import research_chains


class ResearchPlanner:
    """研究计划制定模块 - 负责根据用户查询生成研究计划"""

    def __init__(self) -> None:
        pass

    async def plan_research(
        self, query: str, callback: Callable | None = None
    ) -> list[dict[str, object]]:
        """使用链制定研究计划，支持进度回调

        Args:
            query: 研究查询
            callback: 进度回调函数，用于实时反馈计划制定进度

        Returns:
            研究计划列表，每个计划包含步骤、标题、描述、工具、搜索查询等信息

        为什么需要进度回调：
        - 计划制定可能耗时较长，需要给用户实时反馈
        - 提升用户体验，避免长时间等待时的焦虑
        """
        if callback:
            await callback(
                {
                    "type": "planning_step",
                    "message": "🔍 分析研究主题...",
                    "data": {"step": "analyzing_topic"},
                }
            )

        try:
            if callback:
                await callback(
                    {
                        "type": "planning_step",
                        "message": "🧠 调用AI生成研究计划...",
                        "data": {"step": "calling_ai"},
                    }
                )

            planning_chain = research_chains.create_planning_chain()
            result = await planning_chain.ainvoke({"query": query})
            response = (
                result.get("research_plan", result)
                if isinstance(result, dict)
                else result
            )

            if callback:
                await callback(
                    {
                        "type": "planning_step",
                        "message": "📋 解析研究计划结构...",
                        "data": {"step": "parsing_plan"},
                    }
                )

            # 解析JSON响应
            plan = self._parse_plan_response(response)

            if callback:
                await callback(
                    {
                        "type": "planning_step",
                        "message": f"✅ 成功生成{len(plan)}个研究步骤",
                        "data": {"step": "plan_ready", "plan_preview": plan},
                    }
                )

            return plan
        except Exception as e:
            print(f"Research planning error: {e}")

            if callback:
                await callback(
                    {
                        "type": "planning_step",
                        "message": "⚠️ AI计划生成失败，使用默认计划",
                        "data": {"step": "fallback_plan"},
                    }
                )

            # 返回默认计划 - 为什么需要默认计划：确保系统在AI服务不可用时仍能正常工作
            default_plan = self._get_default_plan(query)

            if callback:
                await callback(
                    {
                        "type": "planning_step",
                        "message": "📋 默认计划准备完成",
                        "data": {"step": "default_ready", "plan_preview": default_plan},
                    }
                )

            return default_plan

    def _parse_plan_response(self, response: str) -> list[dict[str, object]]:
        """解析AI生成的计划响应

        为什么需要这个方法：
        - AI返回的格式可能不一致，需要统一解析逻辑
        - 提高代码复用性，避免重复的解析代码
        """
        if "```json" in str(response):
            json_str = response.split("```json")[1].split("```")[0].strip()
        else:
            json_str = response

        plan_data = json.loads(json_str)
        return plan_data.get("research_plan", [])

    def _get_default_plan(self, query: str) -> list[dict[str, object]]:
        """获取默认研究计划

        为什么需要默认计划：
        - 作为AI服务失败时的兜底方案
        - 确保用户始终能得到研究服务，提高系统可靠性
        """
        return [
            {
                "step": 1,
                "title": "背景调研",
                "description": "使用综合搜索收集基本信息",
                "tool": "comprehensive_search",
                "search_queries": [query, f"{query} 背景"],
                "expected_outcome": "了解基本概念和背景",
            },
            {
                "step": 2,
                "title": "深入分析",
                "description": "使用Tavily搜索获取最新信息",
                "tool": "comprehensive_search",
                "search_queries": [f"{query} 分析", f"{query} 最新"],
                "expected_outcome": "获得详细分析和当前状况",
            },
            {
                "step": 3,
                "title": "综合评估",
                "description": "全面搜索相关资料进行综合分析",
                "tool": "comprehensive_search",
                "search_queries": [f"{query} 评估", f"{query} 总结"],
                "expected_outcome": "获得全面的分析结论",
            },
        ]
