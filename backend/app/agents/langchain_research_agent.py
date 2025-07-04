from typing import Dict, List, Any, AsyncGenerator
from datetime import datetime
import json
import asyncio

from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
from langchain.memory import ConversationBufferMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.prompts import PromptTemplate
from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.manager import CallbackManager
from app.tools.search_tools import research_tools
from app.services.deepseek_service import deepseek_service
from app.services.search_tools import search_tools
from app.chains.research_chains import research_chains
from app.llms.deepseek_llm import DeepSeekLLM


class StreamingCallbackHandler(BaseCallbackHandler):
    """Callback handler for streaming responses."""
    
    def __init__(self, callback_func):
        self.callback_func = callback_func
    
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Called when new token is generated."""
        if self.callback_func:
            self.callback_func(token)
    
    def on_agent_action(self, action, **kwargs) -> None:
        """Called when agent takes an action."""
        if self.callback_func:
            self.callback_func(f"🔧 使用工具: {action.tool}")
    
    def on_agent_finish(self, finish, **kwargs) -> None:
        """Called when agent finishes."""
        if self.callback_func:
            self.callback_func("✅ 代理执行完成")


class LangChainResearchAgent:
    """基于LangChain的研究代理"""
    
    def __init__(self):
        self.llm = None
        self.memory = None
        self.tools = research_tools
        self.agent_executor = None
        self.research_history = []
        self._initialized = False
    
    def _ensure_initialized(self):
        """懒加载初始化"""
        if not self._initialized:
            try:
                print("正在初始化LLM...")
                self.llm = DeepSeekLLM()
                print("LLM初始化完成")
                
                print("正在初始化Memory...")
                self.memory = ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=True
                )
                print("Memory初始化完成")
                
                print("正在创建Agent...")
                self.agent_executor = self._create_agent()
                print("Agent创建完成")
                
                self._initialized = True
                print("Agent完全初始化完成")
            except Exception as e:
                print(f"Agent initialization error: {e}")
                import traceback
                traceback.print_exc()
                raise e
    
    def _create_agent(self) -> AgentExecutor:
        """创建ReAct代理"""
        
        # 直接使用简单的prompt，避免hub.pull阻塞
        from langchain.prompts import PromptTemplate
        prompt = PromptTemplate.from_template(
            "Answer the following questions as best you can. You have access to the following tools:\n\n"
            "{tools}\n\n"
            "Use the following format:\n\n"
            "Question: the input question you must answer\n"
            "Thought: you should always think about what to do\n"
            "Action: the action to take, should be one of [{tool_names}]\n"
            "Action Input: the input to the action\n"
            "Observation: the result of the action\n"
            "... (this Thought/Action/Action Input/Observation can repeat N times)\n"
            "Thought: I now know the final answer\n"
            "Final Answer: the final answer to the original input question\n\n"
            "Begin!\n\n"
            "Question: {input}\n"
            "Thought:{agent_scratchpad}"
        )
        
        # 创建ReAct代理
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # 创建代理执行器
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,
            early_stopping_method="generate"
        )
        
        return agent_executor
    
    def _format_tools(self) -> str:
        """格式化工具描述"""
        tool_descriptions = []
        for tool in self.tools:
            tool_descriptions.append(f"- {tool.name}: {tool.description}")
        return "\n".join(tool_descriptions)
    
    def _format_tool_names(self) -> str:
        """格式化工具名称"""
        return ", ".join([tool.name for tool in self.tools])
    
    async def plan_research(self, query: str) -> List[Dict[str, Any]]:
        """使用链制定研究计划"""
        self._ensure_initialized()
        try:
            planning_chain = research_chains.create_planning_chain()
            result = await planning_chain.ainvoke({"query": query})
            response = result.get("research_plan", result) if isinstance(result, dict) else result
            
            # 解析JSON响应
            if "```json" in str(response):
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
                    "description": "使用综合搜索收集基本信息",
                    "tool": "comprehensive_search",
                    "search_queries": [query, f"{query} 背景"],
                    "expected_outcome": "了解基本概念和背景"
                },
                {
                    "step": 2,
                    "title": "深入分析", 
                    "description": "使用Google搜索获取最新信息",
                    "tool": "google_search",
                    "search_queries": [f"{query} 分析", f"{query} 最新"],
                    "expected_outcome": "获得详细分析和当前状况"
                },
                {
                    "step": 3,
                    "title": "权威资料",
                    "description": "使用Wikipedia搜索获取权威信息", 
                    "tool": "wikipedia_search",
                    "search_queries": [query, f"{query} 定义"],
                    "expected_outcome": "获得可靠的参考资料"
                }
            ]
    
    async def execute_research_step(self, step: Dict[str, Any], query: str) -> Dict[str, Any]:
        """执行单个研究步骤"""
        step_result = {
            "step": step["step"],
            "title": step["title"],
            "status": "executing",
            "search_results": {},
            "analysis": "",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # 1. 执行搜索
            search_results = {}
            if step.get("search_queries"):
                for search_query in step["search_queries"]:
                    if step.get("tool") == "comprehensive_search":
                        search_result = await search_tools.comprehensive_search(search_query)
                    elif step.get("tool") == "google_search":
                        search_result = {"web": await search_tools.google_search(search_query)}
                    elif step.get("tool") == "wikipedia_search":
                        search_result = {"wikipedia": await search_tools.wikipedia_search(search_query)}
                    else:
                        search_result = await search_tools.comprehensive_search(search_query)
                    
                    search_results[search_query] = search_result
            
            step_result["search_results"] = search_results
            
            # 2. 使用链分析搜索结果
            if search_results:
                # 合并所有搜索结果
                combined_results = {}
                for query_results in search_results.values():
                    for source, items in query_results.items():
                        if source not in combined_results:
                            combined_results[source] = []
                        combined_results[source].extend(items)
                
                # 使用链进行分析
                analysis = await research_chains.analyze_search_results_with_chain(
                    step["title"], 
                    combined_results
                )
                step_result["analysis"] = analysis
            else:
                step_result["analysis"] = "没有找到相关搜索结果"
            
            step_result["status"] = "completed"
        except Exception as e:
            step_result["analysis"] = f"执行错误: {str(e)}"
            step_result["status"] = "failed"
        
        return step_result
    
    async def generate_final_report(self, research_results: List[Dict[str, Any]], original_query: str) -> str:
        """使用链生成最终研究报告"""
        
        try:
            # 1. 收集所有分析结果
            step_analyses = []
            for result in research_results:
                if result["status"] == "completed":
                    step_analyses.append({
                        "title": result["title"],
                        "analysis": result["analysis"]
                    })
            
            # 2. 使用综合分析链
            synthesis_chain = research_chains.create_synthesis_chain()
            all_analyses_text = "\n\n".join([f"**{analysis['title']}**:\n{analysis['analysis']}" for analysis in step_analyses])
            
            result = await synthesis_chain.ainvoke({
                "query": original_query,
                "all_analyses": all_analyses_text
            })
            synthesis = result.get("synthesis", result) if isinstance(result, dict) else result
            
            # 3. 使用报告生成链
            report_chain = research_chains.create_report_generation_chain()
            
            result = await report_chain.ainvoke({
                "query": original_query,
                "research_plan": json.dumps([{"title": r["title"], "description": r.get("description", "")} for r in research_results], ensure_ascii=False),
                "step_analyses": all_analyses_text,
                "synthesis": synthesis
            })
            final_report = result.get("final_report", result) if isinstance(result, dict) else result
            
            return final_report
            
        except Exception as e:
            # 回退到简单报告生成
            all_findings = []
            for result in research_results:
                if result["status"] == "completed":
                    all_findings.append(f"**{result['title']}**: {result['analysis']}")
            
            findings_text = "\n\n".join(all_findings)
            
            simple_report = f"""
# {original_query} - 研究报告

## 主要发现

{findings_text}

## 结论

基于以上研究，我们对"{original_query}"进行了多方面的分析和调研。

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            return simple_report
    
    async def conduct_research(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """执行完整的研究流程"""
        self._ensure_initialized()
        
        # 1. 制定研究计划
        yield {"type": "planning", "message": "正在制定研究计划...", "data": None}
        
        research_plan = await self.plan_research(query)
        yield {"type": "plan", "message": "研究计划制定完成", "data": research_plan}
        
        # 2. 执行研究步骤
        research_results = []
        for step in research_plan:
            yield {"type": "step_start", "message": f"开始执行：{step['title']}", "data": step}
            
            step_result = await self.execute_research_step(step, query)
            research_results.append(step_result)
            
            yield {"type": "step_complete", "message": f"完成：{step['title']}", "data": step_result}
        
        # 3. 生成最终报告
        yield {"type": "report_generating", "message": "正在生成最终研究报告...", "data": None}
        
        final_report = await self.generate_final_report(research_results, query)
        
        # 保存到历史记录
        research_record = {
            "query": query,
            "plan": research_plan,
            "results": research_results,
            "report": final_report,
            "timestamp": datetime.now().isoformat()
        }
        self.research_history.append(research_record)
        
        yield {"type": "report_complete", "message": "研究完成", "data": research_record}
    
    def get_research_history(self) -> List[Dict[str, Any]]:
        """获取研究历史"""
        return self.research_history
    
    def clear_memory(self):
        """清空记忆"""
        if self.memory:
            self.memory.clear()
        self.research_history = []


# 全局实例
langchain_research_agent = LangChainResearchAgent()