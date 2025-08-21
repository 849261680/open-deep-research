from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from app.chains.base_chains import base_chain_manager


class PlanningChains:
    """研究计划链管理器"""
    
    def __init__(self):
        self.llm = base_chain_manager.llm
    
    def create_planning_chain(self) -> LLMChain:
        """创建研究计划链"""
        planning_prompt = PromptTemplate(
            input_variables=["query"],
            template="""
作为一个专业的研究助手，请为以下研究主题制定详细的研究计划：

研究主题：{query}

请按照以下JSON格式制定研究计划：
{{
    "research_plan": [
        {{
            "step": 1,
            "title": "步骤标题",
            "description": "详细描述",
            "tool": "推荐工具",
            "search_queries": ["关键词1", "关键词2"],
            "expected_outcome": "预期结果"
        }}
    ]
}}

要求：
1. 计划应包含3-5个主要步骤
2. 每个步骤应有明确的搜索关键词
3. 步骤之间应该有逻辑关系
4. 最后一步应该是综合分析和结论
5. 只返回JSON格式，不要其他文字
"""
        )
        
        return LLMChain(
            llm=self.llm,
            prompt=planning_prompt,
            output_key="research_plan"
        )


# 全局实例
planning_chains = PlanningChains()