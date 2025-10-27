"""研究链集合 - 兼容性包装器"""

from langchain.chains import SequentialChain
from langchain.schema import Document

from .analysis_chains import analysis_chains
from .base_chains import base_chain_manager
from .planning_chains import planning_chains
from .report_chains import report_chains


class ResearchChains:
    """研究链集合 - 兼容性包装器"""

    def __init__(self) -> None:
        self.llm = base_chain_manager.llm
        self.text_splitter = base_chain_manager.text_splitter

    def create_planning_chain(self) -> SequentialChain:
        """创建研究计划链"""
        return planning_chains.create_planning_chain()

    def create_search_analysis_chain(self) -> SequentialChain:
        """创建搜索结果分析链"""
        return analysis_chains.create_search_analysis_chain()

    def create_synthesis_chain(self) -> SequentialChain:
        """创建综合分析链"""
        return analysis_chains.create_synthesis_chain()

    def create_report_generation_chain(self) -> SequentialChain:
        """创建报告生成链"""
        return report_chains.create_report_generation_chain()

    def create_research_pipeline(self) -> SequentialChain:
        """创建完整的研究流水线"""
        planning_chain = self.create_planning_chain()
        synthesis_chain = self.create_synthesis_chain()
        report_chain = self.create_report_generation_chain()

        return SequentialChain(
            chains=[planning_chain, synthesis_chain, report_chain],
            input_variables=["query"],
            output_variables=["research_plan", "synthesis", "final_report"],
            verbose=True,
        )

    def process_search_results(
        self, results: dict[str, list[dict[str, object]]]
    ) -> list[Document]:
        """处理搜索结果为文档"""
        return base_chain_manager.process_search_results(results)

    async def analyze_search_results_with_chain(
        self, step_title: str, search_results: dict[str, list[dict[str, object]]]
    ) -> str:
        """使用链分析搜索结果"""
        return await analysis_chains.analyze_search_results_with_chain(
            step_title, search_results
        )


# 全局实例
research_chains = ResearchChains()
