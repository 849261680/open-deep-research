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
    
    async def plan_research(self, query: str, callback=None) -> List[Dict[str, Any]]:
        """使用链制定研究计划，支持进度回调"""
        self._ensure_initialized()
        
        if callback:
            await callback({"type": "planning_step", "message": "🔍 分析研究主题...", "data": {"step": "analyzing_topic"}})
        
        try:
            if callback:
                await callback({"type": "planning_step", "message": "🧠 调用AI生成研究计划...", "data": {"step": "calling_ai"}})
            
            planning_chain = research_chains.create_planning_chain()
            result = await planning_chain.ainvoke({"query": query})
            response = result.get("research_plan", result) if isinstance(result, dict) else result
            
            if callback:
                await callback({"type": "planning_step", "message": "📋 解析研究计划结构...", "data": {"step": "parsing_plan"}})
            
            # 解析JSON响应
            if "```json" in str(response):
                json_str = response.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response
            
            plan_data = json.loads(json_str)
            plan = plan_data.get("research_plan", [])
            
            if callback:
                await callback({"type": "planning_step", "message": f"✅ 成功生成{len(plan)}个研究步骤", "data": {"step": "plan_ready", "plan_preview": plan}})
            
            return plan
        except Exception as e:
            print(f"Research planning error: {e}")
            
            if callback:
                await callback({"type": "planning_step", "message": "⚠️ AI计划生成失败，使用默认计划", "data": {"step": "fallback_plan"}})
            
            # 返回默认计划
            default_plan = [
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
                    "description": "使用Tavily搜索获取最新信息",
                    "tool": "comprehensive_search",
                    "search_queries": [f"{query} 分析", f"{query} 最新"],
                    "expected_outcome": "获得详细分析和当前状况"
                },
                {
                    "step": 3,
                    "title": "综合评估",
                    "description": "全面搜索相关资料进行综合分析", 
                    "tool": "comprehensive_search",
                    "search_queries": [f"{query} 评估", f"{query} 总结"],
                    "expected_outcome": "获得全面的分析结论"
                }
            ]
            
            if callback:
                await callback({"type": "planning_step", "message": "📋 默认计划准备完成", "data": {"step": "default_ready", "plan_preview": default_plan}})
            
            return default_plan
    
    async def _plan_research_with_updates(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """带进度更新的研究计划制定"""
        
        try:
            # 直接调用AI生成计划，不显示中间步骤
            planning_chain = research_chains.create_planning_chain()
            result = await planning_chain.ainvoke({"query": query})
            response = result.get("research_plan", result) if isinstance(result, dict) else result
            
            # 解析JSON响应
            if "```json" in str(response):
                json_str = response.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response
            
            plan_data = json.loads(json_str)
            plan = plan_data.get("research_plan", [])
            
            # 直接发送完整计划
            yield {"type": "plan", "message": "研究计划制定完成", "data": plan}
            
        except Exception as e:
            print(f"Research planning error: {e}")
            
            # AI生成失败，使用默认计划
            default_plan = [
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
                    "description": "使用Tavily搜索获取最新信息",
                    "tool": "comprehensive_search",
                    "search_queries": [f"{query} 分析", f"{query} 最新"],
                    "expected_outcome": "获得详细分析和当前状况"
                },
                {
                    "step": 3,
                    "title": "综合评估",
                    "description": "全面搜索相关资料进行综合分析", 
                    "tool": "comprehensive_search",
                    "search_queries": [f"{query} 评估", f"{query} 总结"],
                    "expected_outcome": "获得全面的分析结论"
                }
            ]
            
            yield {"type": "plan", "message": "研究计划制定完成", "data": default_plan}
    
    async def _execute_research_step_with_updates(self, step: Dict[str, Any], query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """带进度更新的研究步骤执行"""
        step_result = {
            "step": step["step"],
            "title": step["title"],
            "status": "executing",
            "search_results": {},
            "search_sources": [],  # 新增：搜索来源信息
            "analysis": "",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # 1. 执行搜索 - 显示搜索进度
            search_results = {}
            all_search_sources = []
            
            if step.get("search_queries"):
                for i, search_query in enumerate(step["search_queries"]):
                    yield {"type": "search_progress", "message": f"正在搜索：{search_query}", "data": {"query": search_query, "step": i+1, "total": len(step["search_queries"])}}
                    
                    if step.get("tool") == "comprehensive_search":
                        search_result = await search_tools.comprehensive_search(search_query)
                    elif step.get("tool") == "google_search":
                        search_result = {"web": await search_tools.google_search(search_query)}
                    elif step.get("tool") == "wikipedia_search":
                        search_result = {"wikipedia": await search_tools.wikipedia_search(search_query)}
                    else:
                        search_result = await search_tools.comprehensive_search(search_query)
                    
                    search_results[search_query] = search_result
                    
                    # 收集搜索来源信息
                    for source_type, items in search_result.items():
                        for item in items[:3]:  # 只取前3个结果
                            if 'title' in item and 'link' in item:
                                all_search_sources.append({
                                    "title": item['title'],
                                    "link": item['link'],
                                    "source": source_type,
                                    "query": search_query
                                })
                    
                    yield {"type": "search_result", "message": f"找到 {sum(len(items) for items in search_result.values())} 个结果", "data": {"query": search_query, "sources": [{"title": item['title'], "link": item['link'], "source": source_type} for source_type, items in search_result.items() for item in items[:3] if 'title' in item and 'link' in item]}}
            
            step_result["search_results"] = search_results
            step_result["search_sources"] = all_search_sources
            
            # 2. 分析搜索结果
            yield {"type": "analysis_progress", "message": "正在分析搜索结果...", "data": None}
            
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
            yield {"type": "step_complete", "message": f"完成：{step['title']}", "data": step_result}
            
        except Exception as e:
            step_result["analysis"] = f"执行错误: {str(e)}"
            step_result["status"] = "failed"
            yield {"type": "step_complete", "message": f"步骤失败：{step['title']}", "data": step_result}
    
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
        """生成最终研究报告，优化为单次API调用"""
        
        try:
            # 1. 收集所有分析结果
            step_analyses = []
            for result in research_results:
                if result["status"] == "completed":
                    step_analyses.append({
                        "title": result["title"],
                        "analysis": result["analysis"]
                    })
            
            # 2. 直接生成最终报告，避免多次API调用
            all_analyses_text = "\n\n".join([f"**{analysis['title']}**:\n{analysis['analysis']}" for analysis in step_analyses])
            
            # 限制输入长度，确保不超时
            max_input_length = 1500
            if len(all_analyses_text) > max_input_length:
                all_analyses_text = all_analyses_text[:max_input_length] + "...\n\n[内容已截断]"
                print(f"⚠️ 研究结果过长，已截断至 {max_input_length} 字符")
            
            # 创建简化的报告生成提示
            print(f"📊 最终报告输入统计:")
            print(f"   - 查询: {original_query}")
            print(f"   - 分析文本长度: {len(all_analyses_text)} 字符")
            print(f"   - 完成的步骤数: {len(step_analyses)}")
            
            report_prompt = f"""
请基于以下研究结果，为"{original_query}"生成一份简洁的研究报告：

研究结果：
{all_analyses_text}

请按以下格式生成报告：

# {original_query} - 研究报告

## 核心发现
（列出3-5个关键发现）

## 详细分析  
（基于研究结果的深入分析）

## 结论与建议
（总结性结论和实用建议）

要求：
1. 内容简洁但有深度
2. 突出重点信息
3. 逻辑清晰
4. 中文撰写
"""
            
            # 直接调用LLM，避免复杂链式处理
            from app.services.deepseek_service import deepseek_service
            final_report = await deepseek_service.generate_response(report_prompt, max_tokens=1500)
            
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
        
        # 1. 制定研究计划 - 显示详细过程
        yield {"type": "planning", "message": "正在制定研究计划...", "data": None}
        
        # 定义回调函数来实时发送计划制定进度
        async def planning_callback(update):
            yield update
        
        # 使用生成器来捕获计划制定的进度
        planning_updates = []
        
        async def capture_planning_updates(update):
            planning_updates.append(update)
            yield update
        
        # 调用带回调的计划制定方法
        research_plan = None
        async for update in self._plan_research_with_updates(query):
            yield update
            if update.get("type") == "plan" and update.get("data"):
                research_plan = update["data"]
        
        if not research_plan:
            # 如果没有获得计划，使用备用方法
            research_plan = await self.plan_research(query)
            yield {"type": "plan", "message": "研究计划制定完成", "data": research_plan}
        
        # 2. 执行研究步骤
        research_results = []
        for step in research_plan:
            yield {"type": "step_start", "message": f"开始执行：{step['title']}", "data": step}
            
            # 执行带进度更新的研究步骤
            step_result = None
            async for update in self._execute_research_step_with_updates(step, query):
                yield update
                if update.get("type") == "step_complete":
                    step_result = update["data"]
                    research_results.append(step_result)
        
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