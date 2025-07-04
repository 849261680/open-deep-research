import json
from typing import Dict, List, Any, AsyncGenerator
from datetime import datetime
from app.services.deepseek_service import deepseek_service
from app.services.search_tools import search_tools

class ResearchAgent:
    def __init__(self):
        self.deepseek = deepseek_service
        self.search = search_tools
        self.research_steps = []
    
    async def plan_research(self, query: str) -> List[Dict[str, Any]]:
        """根据用户查询制定研究计划"""
        planning_prompt = f"""
作为一个专业的研究助手，请为以下研究主题制定详细的研究计划：

研究主题：{query}

请按照以下格式制定研究计划，返回JSON格式：
{{
    "research_plan": [
        {{
            "step": 1,
            "title": "步骤标题",
            "description": "详细描述",
            "search_queries": ["搜索关键词1", "搜索关键词2"],
            "expected_outcome": "预期结果"
        }}
    ]
}}

要求：
1. 计划应包含3-5个主要步骤
2. 每个步骤应有明确的搜索关键词
3. 步骤之间应该有逻辑关系
4. 最后一步应该是综合分析和结论
"""
        
        try:
            response = await self.deepseek.generate_response(planning_prompt)
            
            # 尝试解析JSON响应
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response
            
            plan_data = json.loads(json_str)
            return plan_data.get("research_plan", [])
        except Exception as e:
            print(f"Research planning error: {e}")
            # 返回默认计划
            return [
                {
                    "step": 1,
                    "title": "背景调研",
                    "description": "收集基本信息和背景资料",
                    "search_queries": [query, f"{query} 背景", f"{query} 概述"],
                    "expected_outcome": "了解基本概念和背景"
                },
                {
                    "step": 2,
                    "title": "深入分析",
                    "description": "深入研究相关细节和数据",
                    "search_queries": [f"{query} 分析", f"{query} 数据", f"{query} 研究"],
                    "expected_outcome": "获得详细分析和数据支持"
                },
                {
                    "step": 3,
                    "title": "综合总结",
                    "description": "综合所有信息形成结论",
                    "search_queries": [f"{query} 总结", f"{query} 结论", f"{query} 趋势"],
                    "expected_outcome": "形成完整的研究报告"
                }
            ]
    
    async def execute_research_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个研究步骤"""
        step_result = {
            "step": step["step"],
            "title": step["title"],
            "status": "executing",
            "search_results": [],
            "analysis": "",
            "timestamp": datetime.now().isoformat()
        }
        
        # 执行搜索
        all_results = {}
        for query in step["search_queries"]:
            search_result = await self.search.comprehensive_search(query)
            all_results[query] = search_result
        
        step_result["search_results"] = all_results
        step_result["status"] = "completed"
        
        # 分析搜索结果
        analysis_prompt = f"""
基于以下搜索结果，为研究步骤"{step['title']}"提供详细分析：

搜索结果：
{json.dumps(all_results, ensure_ascii=False, indent=2)}

请提供：
1. 关键发现
2. 重要数据和事实
3. 相关观点和分析
4. 这一步骤的小结

分析要求：
- 客观、准确
- 引用具体来源
- 突出重点信息
- 中文回复
"""
        
        try:
            analysis = await self.deepseek.generate_response(analysis_prompt)
            step_result["analysis"] = analysis
        except Exception as e:
            print(f"Analysis error: {e}")
            step_result["analysis"] = "分析生成失败，请查看原始搜索结果。"
        
        return step_result
    
    async def generate_final_report(self, research_results: List[Dict[str, Any]], original_query: str) -> str:
        """生成最终研究报告"""
        report_prompt = f"""
基于以下完整的研究过程和结果，生成一份专业的研究报告：

原始研究问题：{original_query}

研究过程和结果：
{json.dumps(research_results, ensure_ascii=False, indent=2)}

请生成一份结构化的研究报告，包含：

# {original_query} - 深度研究报告

## 执行摘要
（简要概述主要发现和结论）

## 研究背景
（问题背景和研究意义）

## 主要发现
（按重要性列出关键发现）

## 详细分析
（深入分析各个方面）

## 数据支持
（引用具体数据和来源）

## 结论与建议
（总结性结论和实用建议）

## 信息来源
（列出主要参考来源）

要求：
1. 报告应该专业、客观
2. 引用具体数据和来源
3. 结构清晰，逻辑严密
4. 提供实用的见解和建议
5. 使用中文撰写
"""
        
        try:
            report = await self.deepseek.generate_response(report_prompt, max_tokens=6000)
            return report
        except Exception as e:
            print(f"Report generation error: {e}")
            return "报告生成失败，请检查研究结果。"
    
    async def conduct_research(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """执行完整的研究流程"""
        self.research_steps = []
        
        # 1. 制定研究计划
        yield {"type": "planning", "message": "正在制定研究计划...", "data": None}
        
        research_plan = await self.plan_research(query)
        yield {"type": "plan", "message": "研究计划制定完成", "data": research_plan}
        
        # 2. 执行研究步骤
        research_results = []
        for step in research_plan:
            yield {"type": "step_start", "message": f"开始执行：{step['title']}", "data": step}
            
            step_result = await self.execute_research_step(step)
            research_results.append(step_result)
            self.research_steps.append(step_result)
            
            yield {"type": "step_complete", "message": f"完成：{step['title']}", "data": step_result}
        
        # 3. 生成最终报告
        yield {"type": "report_generating", "message": "正在生成最终研究报告...", "data": None}
        
        final_report = await self.generate_final_report(research_results, query)
        
        yield {"type": "report_complete", "message": "研究完成", "data": {
            "query": query,
            "plan": research_plan,
            "results": research_results,
            "report": final_report,
            "timestamp": datetime.now().isoformat()
        }}

# 全局实例
research_agent = ResearchAgent()