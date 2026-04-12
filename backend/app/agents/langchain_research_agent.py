from collections.abc import AsyncGenerator
from collections.abc import Callable

from langchain.agents import AgentExecutor
from langchain.agents import create_react_agent
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate

from ..core.orchestrator import research_orchestrator
from ..llms.deepseek_llm import DeepSeekLLM
from ..tools.search_tools import research_tools
from .report_generator import ReportGenerator
from .research_executor import ResearchExecutor
from .research_planner import ResearchPlanner
from .streaming_handler import StreamingManager


class LangChainResearchAgent:
    """基于LangChain的研究代理 - 主要协调各个功能模块

    为什么采用模块化设计：
    - 遵循单一职责原则，每个模块负责特定功能
    - 提高代码可维护性和可测试性
    - 便于功能扩展和修改
    """

    def __init__(self) -> None:
        self.llm: DeepSeekLLM | None = None
        self.memory: ConversationBufferMemory | None = None
        self.tools = research_tools
        self.agent_executor: AgentExecutor | None = None
        self.research_history: list[dict[str, object]] = []
        self._initialized = False

        # 初始化功能模块 - 为什么使用组合模式：降低耦合度，提高代码复用性
        self.planner = ResearchPlanner()
        self.executor = ResearchExecutor()
        self.report_generator = ReportGenerator()
        self.streaming_manager = StreamingManager()

    def _ensure_initialized(self) -> None:
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
                    memory_key="chat_history", return_messages=True
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
        if self.llm is None:
            raise ValueError("LLM must be initialized before creating agent")
        agent = create_react_agent(llm=self.llm, tools=self.tools, prompt=prompt)

        # 创建代理执行器
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,
            early_stopping_method="generate",
        )

    def _format_tools(self) -> str:
        """格式化工具描述"""
        tool_descriptions = []
        for tool in self.tools:
            tool_descriptions.append(f"- {tool.name}: {tool.description}")
        return "\n".join(tool_descriptions)

    def _format_tool_names(self) -> str:
        """格式化工具名称"""
        return ", ".join([tool.name for tool in self.tools])

    async def plan_research(
        self, query: str, callback: Callable | None = None
    ) -> list[dict[str, object]]:
        """使用链制定研究计划，支持进度回调

        为什么委托给专门的模块：
        - 遵循单一职责原则，计划制定有专门的模块处理
        - 降低主类的复杂度，提高可维护性
        """
        self._ensure_initialized()
        return await self.planner.plan_research(query, callback)

    async def _plan_research_with_updates(
        self, query: str
    ) -> AsyncGenerator[dict[str, object], None]:
        """带进度更新的研究计划制定

        为什么委托给流式管理器：
        - 流式处理有专门的模块管理，避免代码重复
        - 统一流式处理逻辑，便于维护
        """
        async for update in self.streaming_manager.handle_planning_updates(
            query, self.planner
        ):
            yield update

    async def _execute_research_step_with_updates(
        self, step: dict[str, object], query: str
    ) -> AsyncGenerator[dict[str, object], None]:
        """带进度更新的研究步骤执行

        为什么委托给执行器：
        - 步骤执行逻辑复杂，需要专门的模块处理
        - 提高代码复用性和可维护性
        """
        async for update in self.executor.execute_research_step_with_updates(
            step, query
        ):
            yield update

    async def execute_research_step(
        self, step: dict[str, object], query: str
    ) -> dict[str, object]:
        """执行单个研究步骤

        为什么委托给执行器：
        - 遵循单一职责原则，执行逻辑由专门模块处理
        - 降低主类复杂度
        """
        return await self.executor.execute_research_step(step, query)

    async def generate_final_report(
        self, research_results: list[dict[str, object]], original_query: str
    ) -> str:
        """生成最终研究报告

        为什么委托给报告生成器：
        - 报告生成有复杂的格式化和优化逻辑
        - 专门的模块便于功能扩展和维护
        """
        return await self.report_generator.generate_final_report(
            research_results, original_query
        )

    async def conduct_research(
        self, query: str, user_id: int | None = None
    ) -> AsyncGenerator[dict[str, object], None]:
        """执行完整的研究流程。

        当前主流程已迁移到 orchestrator，这里保留兼容层给 API 使用。
        """
        async for update in research_orchestrator.run(query, user_id=user_id):
            if update.get("type") == "report_complete":
                payload = update.get("data")
                if isinstance(payload, dict):
                    self.research_history.append(payload)
            yield update

    def get_research_history(self, user_id: int | None = None) -> list[dict[str, object]]:
        """获取研究历史

        为什么需要这个方法：
        - 用户可能需要查看之前的研究结果
        - 提供完整的用户体验
        """
        history = research_orchestrator.get_history(user_id=user_id)
        return history if history else self.research_history

    def clear_memory(self) -> None:
        """清空记忆

        为什么需要清空记忆：
        - 避免内存占用过多
        - 用户可能需要开始全新的研究会话
        """
        if self.memory:
            self.memory.clear()
        self.research_history = []
        research_orchestrator.clear()


# 全局实例
langchain_research_agent = LangChainResearchAgent()
