from typing import Dict, List, Any, AsyncGenerator
from datetime import datetime
import asyncio

from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from app.tools.search_tools import research_tools
from app.llms.deepseek_llm import DeepSeekLLM
from app.agents.research_planner import ResearchPlanner
from app.agents.research_executor import ResearchExecutor
from app.agents.report_generator import ReportGenerator
from app.agents.streaming_handler import StreamingManager


class LangChainResearchAgent:
    """基于LangChain的研究代理 - 主要协调各个功能模块
    
    为什么采用模块化设计：
    - 遵循单一职责原则，每个模块负责特定功能
    - 提高代码可维护性和可测试性
    - 便于功能扩展和修改
    """
    
    def __init__(self):
        self.llm = None
        self.memory = None
        self.tools = research_tools
        self.agent_executor = None
        self.research_history = []
        self._initialized = False
        
        # 初始化功能模块 - 为什么使用组合模式：降低耦合度，提高代码复用性
        self.planner = ResearchPlanner()
        self.executor = ResearchExecutor()
        self.report_generator = ReportGenerator()
        self.streaming_manager = StreamingManager()
    
    def _ensure_initialized(self):
        """懒加载初始化
        
        为什么使用懒加载：
        - 避免启动时的性能开销
        - 只有在实际使用时才初始化资源
        """
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
        """创建ReAct代理
        
        为什么使用ReAct模式：
        - 结合推理和行动，提供更好的问题解决能力
        - LangChain的标准模式，便于集成各种工具
        """
        # 直接使用简单的prompt，避免hub.pull阻塞
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
        """使用链制定研究计划，支持进度回调
        
        为什么委托给专门的模块：
        - 遵循单一职责原则，计划制定有专门的模块处理
        - 降低主类的复杂度，提高可维护性
        """
        self._ensure_initialized()
        return await self.planner.plan_research(query, callback)
    
    async def _plan_research_with_updates(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """带进度更新的研究计划制定
        
        为什么委托给流式管理器：
        - 流式处理有专门的模块管理，避免代码重复
        - 统一流式处理逻辑，便于维护
        """
        async for update in self.streaming_manager.handle_planning_updates(query, self.planner):
            yield update
    
    async def _execute_research_step_with_updates(self, step: Dict[str, Any], query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """带进度更新的研究步骤执行
        
        为什么委托给执行器：
        - 步骤执行逻辑复杂，需要专门的模块处理
        - 提高代码复用性和可维护性
        """
        async for update in self.executor.execute_research_step_with_updates(step, query):
            yield update
    
    async def execute_research_step(self, step: Dict[str, Any], query: str) -> Dict[str, Any]:
        """执行单个研究步骤
        
        为什么委托给执行器：
        - 遵循单一职责原则，执行逻辑由专门模块处理
        - 降低主类复杂度
        """
        return await self.executor.execute_research_step(step, query)
    
    async def generate_final_report(self, research_results: List[Dict[str, Any]], original_query: str) -> str:
        """生成最终研究报告
        
        为什么委托给报告生成器：
        - 报告生成有复杂的格式化和优化逻辑
        - 专门的模块便于功能扩展和维护
        """
        return await self.report_generator.generate_final_report(research_results, original_query)
    
    async def conduct_research(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """执行完整的研究流程
        
        为什么这个方法保留在主类：
        - 作为总体协调方法，负责调度各个模块
        - 管理整个研究流程的状态和历史记录
        """
        self._ensure_initialized()
        
        # 1. 制定研究计划 - 显示详细过程
        yield {"type": "planning", "message": "正在制定研究计划...", "data": None}
        
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
        
        # 保存到历史记录 - 为什么保存历史：便于用户查看和管理之前的研究
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
        """获取研究历史
        
        为什么需要这个方法：
        - 用户可能需要查看之前的研究结果
        - 提供完整的用户体验
        """
        return self.research_history
    
    def clear_memory(self):
        """清空记忆
        
        为什么需要清空记忆：
        - 避免内存占用过多
        - 用户可能需要开始全新的研究会话
        """
        if self.memory:
            self.memory.clear()
        self.research_history = []


# 全局实例
langchain_research_agent = LangChainResearchAgent()