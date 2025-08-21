from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from app.chains.base_chains import base_chain_manager


class ReportChains:
    """报告生成链管理器"""
    
    def __init__(self):
        self.llm = base_chain_manager.llm
    
    def create_report_generation_chain(self) -> LLMChain:
        """创建报告生成链"""
        report_prompt = PromptTemplate(
            input_variables=["query", "research_plan", "step_analyses", "synthesis"],
            template="""
基于完整的研究过程，生成一份专业的研究报告：

原始问题：{query}
研究计划：{research_plan}
步骤分析：{step_analyses}
综合分析：{synthesis}

请生成一份结构化的研究报告，包含：

# {query} - 深度研究报告

## 执行摘要
（简要概述主要发现和结论）

## 研究方法
（说明研究方法和步骤）

## 主要发现
（按重要性列出关键发现）

## 详细分析
（深入分析各个方面）

## 综合观点
（整合性分析和见解）

## 结论与建议
（总结性结论和实用建议）

## 研究限制
（说明研究的局限性）

要求：
1. 报告应该专业、客观
2. 引用具体数据和来源
3. 结构清晰，逻辑严密
4. 提供实用的见解和建议
5. 使用中文撰写
"""
        )
        
        return LLMChain(
            llm=self.llm,
            prompt=report_prompt,
            output_key="final_report"
        )


# 全局实例
report_chains = ReportChains()