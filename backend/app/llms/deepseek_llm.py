from langchain.llms.base import LLM
from pydantic import BaseModel, Field
from typing import List
import asyncio
from app.services.deepseek_service import deepseek_service


class DeepSeekLLM(LLM):
    """Custom LLM wrapper for DeepSeek API，优化性能."""
    
    model_name: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 2000  # 减少最大 tokens 以提高速度
    
    @property
    def _llm_type(self) -> str:
        return "deepseek"
    
    def _call(self, prompt: str, stop: List[str] = None) -> str:
        """Call the DeepSeek API."""
        try:
            response = asyncio.run(deepseek_service.generate_response(prompt, self.max_tokens))
            return response
        except Exception as e:
            return f"Error calling DeepSeek API: {str(e)}"
    
    async def _acall(self, prompt: str, stop: List[str] = None) -> str:
        """Call the DeepSeek API asynchronously."""
        try:
            response = await deepseek_service.generate_response(prompt, self.max_tokens)
            return response
        except Exception as e:
            return f"Error calling DeepSeek API: {str(e)}"