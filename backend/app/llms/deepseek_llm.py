import asyncio

from langchain_core.language_models.llms import BaseLLM
from langchain_core.outputs import Generation
from langchain_core.outputs import LLMResult

from app.services.deepseek_service import deepseek_service


class DeepSeekLLM(BaseLLM):
    """Custom LLM wrapper for DeepSeek API，优化性能."""

    model_name: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 2000  # 减少最大 tokens 以提高速度

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    @property
    def _llm_type(self) -> str:
        return "deepseek"

    def _generate(
        self,
        prompts: list[str],
        stop: list[str] | None = None,
        run_manager: object | None = None,
        **kwargs: object,
    ) -> LLMResult:
        """Generate text from DeepSeek API."""
        try:
            # For simplicity, we'll just handle the first prompt
            prompt = prompts[0]
            response = asyncio.run(
                deepseek_service.generate_response(prompt, self.max_tokens)
            )
            generation = Generation(text=response)
            return LLMResult(generations=[[generation]])
        except Exception as e:
            generation = Generation(text=f"Error calling DeepSeek API: {str(e)}")
            return LLMResult(generations=[[generation]])

    async def _agenerate(
        self,
        prompts: list[str],
        stop: list[str] | None = None,
        run_manager: object | None = None,
        **kwargs: object,
    ) -> LLMResult:
        """Generate text from DeepSeek API asynchronously."""
        try:
            # For simplicity, we'll just handle the first prompt
            prompt = prompts[0]
            response = await deepseek_service.generate_response(prompt, self.max_tokens)
            generation = Generation(text=response)
            return LLMResult(generations=[[generation]])
        except Exception as e:
            generation = Generation(text=f"Error calling DeepSeek API: {str(e)}")
            return LLMResult(generations=[[generation]])

    def _call(
        self,
        prompt: str,
        stop: list[str] | None = None,
        run_manager: object | None = None,
        **kwargs: object,
    ) -> str:
        """Call DeepSeek API."""
        result = self._generate([prompt], stop, run_manager, **kwargs)
        return result.generations[0][0].text

    async def _acall(
        self,
        prompt: str,
        stop: list[str] | None = None,
        run_manager: object | None = None,
        **kwargs: object,
    ) -> str:
        """Call DeepSeek API asynchronously."""
        result = await self._agenerate([prompt], stop, run_manager, **kwargs)
        return result.generations[0][0].text

    @property
    def _identifying_params(self) -> dict[str, object]:
        """Get identifying parameters."""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
