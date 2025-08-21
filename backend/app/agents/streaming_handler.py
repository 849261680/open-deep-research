from typing import Dict, List, Any, AsyncGenerator
from langchain.callbacks.base import BaseCallbackHandler


class StreamingCallbackHandler(BaseCallbackHandler):
    """流式回调处理器 - 处理LangChain的流式响应"""
    
    def __init__(self, callback_func):
        """初始化回调处理器
        
        Args:
            callback_func: 回调函数，用于处理流式数据
            
        为什么需要回调函数：
        - 实现异步的流式数据传输
        - 让调用者能够实时处理生成的内容
        """
        self.callback_func = callback_func
    
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """当生成新token时调用
        
        为什么需要这个方法：
        - LangChain的标准接口，用于处理流式生成的token
        - 实现实时的内容展示
        """
        if self.callback_func:
            self.callback_func(token)
    
    def on_agent_action(self, action, **kwargs) -> None:
        """当代理执行动作时调用
        
        为什么需要这个方法：
        - 让用户了解代理当前正在执行的操作
        - 提升用户体验，增加透明度
        """
        if self.callback_func:
            self.callback_func(f"🔧 使用工具: {action.tool}")
    
    def on_agent_finish(self, finish, **kwargs) -> None:
        """当代理完成时调用
        
        为什么需要这个方法：
        - 通知用户代理已完成所有操作
        - 提供明确的结束信号
        """
        if self.callback_func:
            self.callback_func("✅ 代理执行完成")


class StreamingManager:
    """流式处理管理器 - 管理研究过程中的流式更新"""
    
    def __init__(self):
        pass
    
    async def handle_planning_updates(self, query: str, planner) -> AsyncGenerator[Dict[str, Any], None]:
        """处理计划制定的流式更新
        
        为什么需要流式更新：
        - 计划制定可能耗时较长，需要给用户实时反馈
        - 提升用户体验，避免长时间的空白等待
        """
        try:
            # 直接调用AI生成计划，不显示中间步骤
            from app.chains.research_chains import research_chains
            import json
            
            planning_chain = research_chains.create_planning_chain()
            result = await planning_chain.ainvoke({"query": query})
            response = result.get("research_plan", result) if isinstance(result, dict) else result
            
            # 解析JSON响应
            plan = self._parse_plan_response(response)
            
            # 直接发送完整计划
            yield {"type": "plan", "message": "研究计划制定完成", "data": plan}
            
        except Exception as e:
            print(f"Research planning error: {e}")
            
            # AI生成失败，使用默认计划 - 为什么需要默认计划：确保服务的可靠性
            default_plan = self._get_default_plan(query)
            yield {"type": "plan", "message": "研究计划制定完成", "data": default_plan}
    
    def _parse_plan_response(self, response: str) -> List[Dict[str, Any]]:
        """解析计划响应
        
        为什么需要这个方法：
        - 统一解析逻辑，避免重复代码
        - 处理AI返回格式的不一致性
        """
        import json
        
        if "```json" in str(response):
            json_str = response.split("```json")[1].split("```")[0].strip()
        else:
            json_str = response
        
        plan_data = json.loads(json_str)
        return plan_data.get("research_plan", [])
    
    def _get_default_plan(self, query: str) -> List[Dict[str, Any]]:
        """获取默认计划
        
        为什么需要默认计划：
        - 作为AI服务失败时的兜底方案
        - 确保用户始终能得到研究服务
        """
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
