from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.schema import Document

from app.chains.base_chains import base_chain_manager


class AnalysisChains:
    """分析链管理器"""

    def __init__(self) -> None:
        self.llm = base_chain_manager.llm

    def create_search_analysis_chain(self) -> LLMChain:
        """创建搜索结果分析链"""
        analysis_prompt = PromptTemplate(
            input_variables=["step_title", "search_results"],
            template="""
基于以下搜索结果，为研究步骤"{step_title}"提供详细分析：

搜索结果：
{search_results}

请提供：
1. 关键发现和要点
2. 重要数据和事实
3. 相关观点和分析
4. 这一步骤的小结

分析要求：
- 客观、准确
- 引用具体来源
- 突出重点信息
- 中文回复
- 结构化输出
""",
        )

        return LLMChain(llm=self.llm, prompt=analysis_prompt, output_key="analysis")

    def create_synthesis_chain(self) -> LLMChain:
        """创建综合分析链"""
        synthesis_prompt = PromptTemplate(
            input_variables=["query", "all_analyses"],
            template="""
基于以下所有研究分析，为原始问题"{query}"提供综合性的深度分析：

研究分析结果：
{all_analyses}

请提供：
1. 综合性观点
2. 深层次见解
3. 关键结论
4. 实用建议
5. 潜在影响

要求：
- 整合所有信息
- 提供新的见解
- 逻辑清晰
- 中文回复
""",
        )

        return LLMChain(llm=self.llm, prompt=synthesis_prompt, output_key="synthesis")

    async def analyze_search_results_with_chain(
        self, step_title: str, search_results: dict[str, list[dict[str, object]]]
    ) -> str:
        """使用链分析搜索结果"""
        documents = base_chain_manager.process_search_results(search_results)

        # 限制文档数量
        if len(documents) > 5:
            documents = documents[:5]

        if len(documents) > 0:
            return await self._simple_summarize_documents(step_title, documents)
        return "未找到相关搜索结果"

    async def _simple_summarize_documents(
        self, step_title: str, documents: list[Document]
    ) -> str:
        """简化的文档摘要方法"""
        combined_content = ""
        max_total_length = 2500

        for doc in documents:
            if len(combined_content) + len(doc.page_content) > max_total_length:
                remaining_space = max_total_length - len(combined_content)
                if remaining_space > 100:
                    combined_content += doc.page_content[:remaining_space] + "...\n\n"
                break
            combined_content += doc.page_content + "\n\n"

        analysis_prompt = f"""
请为研究步骤'{step_title}'分析以下搜索结果，提供简洁的摘要：

{combined_content}

请提供：
1. 关键发现（2-3点）
2. 重要信息总结
3. 这一步骤的结论

要求：简洁明了，重点突出，中文回复。
"""

        try:
            return await self.llm._acall(analysis_prompt)
        except Exception as e:  # noqa: BLE001
            print(f"简化摘要生成失败: {e}")
            return f"无法生成步骤'{step_title}'的分析摘要，但搜索到了 {len(documents)} 个相关结果。"


# 全局实例
analysis_chains = AnalysisChains()
