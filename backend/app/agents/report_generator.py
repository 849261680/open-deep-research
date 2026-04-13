import logging
from datetime import datetime
from datetime import timezone

from ..chains.research_chains import research_chains

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成模块 - 负责根据研究结果生成最终报告"""

    def __init__(self) -> None:
        pass

    async def generate_final_report(
        self, research_results: list[dict[str, object]], original_query: str
    ) -> str:
        """生成最终研究报告，使用统一的 chains 架构

        为什么使用 chains 架构：
        - 保持系统架构一致性，避免"两套系统并存"
        - 统一的提示词管理，便于维护和优化
        - 遵循 LangChain 最佳实践
        """
        logger.debug("开始生成最终报告...")
        try:
            step_analyses = self._collect_step_analyses(research_results)
            logger.debug("收集到 %d 个步骤分析", len(step_analyses))

            all_analyses_text = self._format_analyses_text(step_analyses)
            all_analyses_text = self._limit_input_length(all_analyses_text)

            self._log_report_statistics(
                original_query, all_analyses_text, step_analyses
            )

            report_chain = research_chains.create_report_generation_chain()

            chain_input = {
                "query": original_query,
                "research_plan": "基于多步骤研究计划",
                "step_analyses": all_analyses_text,
                "synthesis": f"针对'{original_query}'的综合分析",
            }

            result = await report_chain.ainvoke(chain_input)

            final_report = (
                result.get("final_report", result)
                if isinstance(result, dict)
                else result
            )

            logger.debug("最终报告长度: %d 字符", len(final_report))
            return final_report

        except Exception as e:
            logger.exception("报告生成失败: %s", e)
            logger.info("回退到简单报告生成...")

            # 回退到简单报告生成 - 为什么需要回退：确保即使主要逻辑失败也能提供基本服务
            simple_report = self._generate_simple_report(
                research_results, original_query
            )
            return simple_report

    def _collect_step_analyses(
        self, research_results: list[dict[str, object]]
    ) -> list[dict[str, str]]:
        """收集所有分析结果

        为什么需要单独的方法：
        - 提高代码可读性和可维护性
        - 便于后续扩展和修改收集逻辑
        """
        step_analyses = []
        for result in research_results:
            if result["status"] == "completed":
                citations = result.get("citations", [])
                citation_lines = []
                if isinstance(citations, list):
                    for citation in citations[:5]:
                        if isinstance(citation, dict):
                            title = citation.get("title", "")
                            link = citation.get("link", "")
                            if title and link:
                                citation_lines.append(f"- {title}: {link}")

                analysis_text = str(result["analysis"])
                if citation_lines:
                    analysis_text = (
                        f"{analysis_text}\n\n参考来源:\n" + "\n".join(citation_lines)
                    )
                step_analyses.append(
                    {"title": result["title"], "analysis": analysis_text}
                )
        return step_analyses

    def _format_analyses_text(self, step_analyses: list[dict[str, str]]) -> str:
        """格式化分析文本

        为什么需要格式化：
        - 为AI提供结构化的输入，提高生成质量
        - 统一文本格式，便于处理
        """
        return "\n\n".join(
            [
                f"**{analysis['title']}**:\n{analysis['analysis']}"
                for analysis in step_analyses
            ]
        )

    def _limit_input_length(self, text: str, max_length: int = 8000) -> str:
        """限制输入长度

        为什么需要限制长度：
        - 避免API调用超时
        - 控制成本，避免过长的输入导致高额费用
        - 确保服务稳定性
        """
        if len(text) > max_length:
            text = text[:max_length] + "...\n\n[内容已截断]"
            logger.warning("研究结果过长，已截断至 %d 字符", max_length)
        return text

    def _log_report_statistics(
        self,
        original_query: str,
        all_analyses_text: str,
        step_analyses: list[dict[str, str]],
    ) -> None:
        """记录报告统计信息

        为什么需要记录统计：
        - 便于调试和性能优化
        - 了解系统使用情况
        """
        logger.debug(
            "最终报告输入统计 — 查询: %s，分析文本: %d 字符，完成步骤: %d",
            original_query, len(all_analyses_text), len(step_analyses),
        )

    def _generate_simple_report(
        self, research_results: list[dict[str, object]], original_query: str
    ) -> str:
        """生成简单报告（回退方案）

        为什么需要回退方案：
        - 确保系统在主要逻辑失败时仍能提供基本服务
        - 提高系统可靠性和用户体验
        """
        all_findings = []
        for result in research_results:
            if result["status"] == "completed":
                all_findings.append(f"**{result['title']}**: {result['analysis']}")

        findings_text = "\n\n".join(all_findings)

        return f"""
# {original_query} - 研究报告

## 主要发现

{findings_text}

## 结论

基于以上研究，我们对"{original_query}"进行了多方面的分析和调研。

*报告生成时间: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}*
"""
