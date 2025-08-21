from typing import Dict, List, Any
from datetime import datetime
from app.services.deepseek_service import deepseek_service


class ReportGenerator:
    """报告生成模块 - 负责根据研究结果生成最终报告"""
    
    def __init__(self):
        pass
    
    async def generate_final_report(self, research_results: List[Dict[str, Any]], original_query: str) -> str:
        """生成最终研究报告，优化为单次API调用
        
        为什么优化为单次API调用：
        - 减少API调用次数，提高性能和降低成本
        - 避免多次调用可能导致的一致性问题
        """
        try:
            # 1. 收集所有分析结果
            step_analyses = self._collect_step_analyses(research_results)
            
            # 2. 直接生成最终报告，避免多次API调用
            all_analyses_text = self._format_analyses_text(step_analyses)
            
            # 限制输入长度，确保不超时 - 为什么限制：避免API超时，确保服务稳定性
            all_analyses_text = self._limit_input_length(all_analyses_text)
            
            # 创建简化的报告生成提示
            self._log_report_statistics(original_query, all_analyses_text, step_analyses)
            
            report_prompt = self._create_report_prompt(original_query, all_analyses_text)
            
            # 直接调用LLM，避免复杂链式处理 - 为什么避免复杂链式：提高性能，减少出错概率
            final_report = await deepseek_service.generate_response(report_prompt, max_tokens=1500)
            
            return final_report
            
        except Exception as e:
            # 回退到简单报告生成 - 为什么需要回退：确保即使主要逻辑失败也能提供基本服务
            return self._generate_simple_report(research_results, original_query)
    
    def _collect_step_analyses(self, research_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """收集所有分析结果
        
        为什么需要单独的方法：
        - 提高代码可读性和可维护性
        - 便于后续扩展和修改收集逻辑
        """
        step_analyses = []
        for result in research_results:
            if result["status"] == "completed":
                step_analyses.append({
                    "title": result["title"],
                    "analysis": result["analysis"]
                })
        return step_analyses
    
    def _format_analyses_text(self, step_analyses: List[Dict[str, str]]) -> str:
        """格式化分析文本
        
        为什么需要格式化：
        - 为AI提供结构化的输入，提高生成质量
        - 统一文本格式，便于处理
        """
        return "\n\n".join([f"**{analysis['title']}**:\n{analysis['analysis']}" for analysis in step_analyses])
    
    def _limit_input_length(self, text: str, max_length: int = 1500) -> str:
        """限制输入长度
        
        为什么需要限制长度：
        - 避免API调用超时
        - 控制成本，避免过长的输入导致高额费用
        - 确保服务稳定性
        """
        if len(text) > max_length:
            text = text[:max_length] + "...\n\n[内容已截断]"
            print(f"⚠️ 研究结果过长，已截断至 {max_length} 字符")
        return text
    
    def _log_report_statistics(self, original_query: str, all_analyses_text: str, step_analyses: List[Dict[str, str]]):
        """记录报告统计信息
        
        为什么需要记录统计：
        - 便于调试和性能优化
        - 了解系统使用情况
        """
        print(f"📊 最终报告输入统计:")
        print(f"   - 查询: {original_query}")
        print(f"   - 分析文本长度: {len(all_analyses_text)} 字符")
        print(f"   - 完成的步骤数: {len(step_analyses)}")
    
    def _create_report_prompt(self, original_query: str, all_analyses_text: str) -> str:
        """创建报告生成提示
        
        为什么需要单独的方法：
        - 提示词是核心逻辑，需要独立管理
        - 便于调整和优化提示词
        """
        return f"""
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
    
    def _generate_simple_report(self, research_results: List[Dict[str, Any]], original_query: str) -> str:
        """生成简单报告（回退方案）
        
        为什么需要回退方案：
        - 确保系统在主要逻辑失败时仍能提供基本服务
        - 提高系统可靠性和用户体验
        """
        all_findings = []
        for result in research_results:
            if result["status"] == "completed":
                all_findings.append(f"**{result['title']}**: {result['analysis']}")
        
        findings_text = "\n\n".join(all_findings)
        
        return f"""
# {original_query} - 研究报告

## 主要发现

{findings_text}

## 结论

基于以上研究，我们对"{original_query}"进行了多方面的分析和调研。

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
