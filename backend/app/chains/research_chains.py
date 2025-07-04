from langchain.chains import LLMChain, SequentialChain, MapReduceChain
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import Dict, List, Any
import json

from app.llms.deepseek_llm import DeepSeekLLM


class ResearchChains:
    """研究链集合"""
    
    def __init__(self):
        self.llm = DeepSeekLLM()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
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
"""
        )
        
        return LLMChain(
            llm=self.llm,
            prompt=analysis_prompt,
            output_key="analysis"
        )
    
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
"""
        )
        
        return LLMChain(
            llm=self.llm,
            prompt=synthesis_prompt,
            output_key="synthesis"
        )
    
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
    
    def create_research_pipeline(self) -> SequentialChain:
        """创建完整的研究流水线"""
        
        # 创建各个链
        planning_chain = self.create_planning_chain()
        synthesis_chain = self.create_synthesis_chain()
        report_chain = self.create_report_generation_chain()
        
        # 创建顺序链
        research_pipeline = SequentialChain(
            chains=[planning_chain, synthesis_chain, report_chain],
            input_variables=["query"],
            output_variables=["research_plan", "synthesis", "final_report"],
            verbose=True
        )
        
        return research_pipeline
    
    def create_summarization_chain(self) -> MapReduceChain:
        """创建文档摘要链"""
        map_prompt = PromptTemplate(
            input_variables=["text"],
            template="请对以下文本进行摘要，保留关键信息：\n\n{text}\n\n摘要："
        )
        
        reduce_prompt = PromptTemplate(
            input_variables=["text"],
            template="请将以下摘要合并为一个连贯的总结：\n\n{text}\n\n最终摘要："
        )
        
        return load_summarize_chain(
            llm=self.llm,
            chain_type="map_reduce",
            map_prompt=map_prompt,
            combine_prompt=reduce_prompt,
            verbose=True
        )
    
    def process_search_results(self, results: Dict[str, List[Dict[str, Any]]]) -> List[Document]:
        """处理搜索结果为文档"""
        documents = []
        
        for source, items in results.items():
            for item in items:
                content = f"标题: {item.get('title', '')}\n"
                content += f"来源: {source}\n"
                content += f"链接: {item.get('link', '')}\n"
                content += f"内容: {item.get('snippet', '')}\n"
                
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": source,
                        "title": item.get('title', ''),
                        "link": item.get('link', '')
                    }
                )
                documents.append(doc)
        
        return documents
    
    async def analyze_search_results_with_chain(self, step_title: str, search_results: Dict[str, List[Dict[str, Any]]]) -> str:
        """使用链分析搜索结果"""
        # 处理搜索结果
        documents = self.process_search_results(search_results)
        
        # 如果文档太多，先进行摘要
        if len(documents) > 10:
            summarization_chain = self.create_summarization_chain()
            result = await summarization_chain.ainvoke({"input_documents": documents})
            search_results_text = result.get("output_text", result) if isinstance(result, dict) else result
        else:
            search_results_text = "\n\n".join([doc.page_content for doc in documents])
        
        # 使用分析链
        analysis_chain = self.create_search_analysis_chain()
        result = await analysis_chain.ainvoke({
            "step_title": step_title,
            "search_results": search_results_text
        })
        analysis = result.get("analysis", result) if isinstance(result, dict) else result
        
        return analysis


# 全局实例
research_chains = ResearchChains()