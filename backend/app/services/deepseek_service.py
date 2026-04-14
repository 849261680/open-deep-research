import asyncio
import logging
import os
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import requests
from requests.exceptions import Timeout

from ..utils.env import load_project_env

load_project_env()

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid integer env %s=%r, using default %d", name, raw, default)
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid float env %s=%r, using default %.2f", name, raw, default)
        return default


@dataclass(frozen=True)
class DeepSeekConfig:
    model: str
    temperature: float
    max_output_tokens: int
    max_prompt_chars: int

    @classmethod
    def from_env(cls) -> "DeepSeekConfig":
        return cls(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            temperature=_env_float("DEEPSEEK_TEMPERATURE", 0.7),
            max_output_tokens=_env_int("DEEPSEEK_MAX_OUTPUT_TOKENS", 4_000),
            max_prompt_chars=_env_int("DEEPSEEK_MAX_PROMPT_CHARS", 24_000),
        )


class DeepSeekService:
    def __init__(self, config: DeepSeekConfig | None = None) -> None:
        self.config = config or DeepSeekConfig.from_env()
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        prompt: str,
        max_tokens: int | None,
        stream: bool,
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> dict[str, object]:
        requested_max_tokens = max_tokens or self.config.max_output_tokens
        return {
            "model": model or self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": min(requested_max_tokens, self.config.max_output_tokens),
            "temperature": (
                self.config.temperature if temperature is None else temperature
            ),
            "stream": stream,
        }

    def _truncate_prompt(self, prompt: str) -> str:
        if self.config.max_prompt_chars <= 0:
            return prompt
        if len(prompt) > self.config.max_prompt_chars:
            prompt = prompt[:self.config.max_prompt_chars] + "...\n\n请基于以上内容生成简洁摘要。"
            logger.warning("提示词过长，已截断至 %d 字符", self.config.max_prompt_chars)
        return prompt

    def generate_response_sync(
        self,
        prompt: str,
        max_tokens: int | None = None,
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """同步调用 DeepSeek，供同步 LangChain 路径和线程池包装使用。"""
        logger.debug("开始生成响应，提示词长度: %d", len(prompt))

        if not self.api_key:
            raise ValueError("DeepSeek API key not found")

        prompt = self._truncate_prompt(prompt)
        payload = self._build_payload(
            prompt,
            max_tokens,
            stream=False,
            model=model,
            temperature=temperature,
        )

        max_retries = 2
        response: requests.Response | None = None
        for attempt in range(max_retries + 1):
            try:
                logger.debug("API 调用尝试 %d/%d", attempt + 1, max_retries + 1)
                start_time = time.time()
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=90,
                )
                elapsed = time.time() - start_time
                logger.debug("API 响应时间: %.2f 秒，状态码: %d", elapsed, response.status_code)

                if response.status_code != 200:
                    logger.error("API 错误响应: %s", response.text)
                    if attempt == max_retries:
                        break
                    time.sleep(2)
                    continue

                result = response.json()
                response_content = result["choices"][0]["message"]["content"]
                logger.debug("API 调用成功，响应长度: %d 字符", len(response_content))
                return response_content
            except Timeout:
                if attempt == max_retries:
                    logger.error("API 请求超时，已重试多次")
                    raise Timeout("DeepSeek API request timed out")
                logger.warning("请求超时，将重试... (%d/%d)", attempt + 1, max_retries)
                time.sleep(2)
            except Exception as e:
                if attempt == max_retries:
                    logger.error("API 连接失败: %s", e)
                    raise
                logger.warning("连接失败，将重试... (%d/%d)", attempt + 1, max_retries)
                time.sleep(2)

        if response is None:
            raise RuntimeError("DeepSeek API request failed before receiving a response")

        raise Exception(f"DeepSeek API error: {response.status_code} - {response.text}")

    async def generate_response(
        self,
        prompt: str,
        max_tokens: int | None = None,
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """异步包装，避免阻塞事件循环。"""
        return await asyncio.to_thread(
            self.generate_response_sync,
            prompt,
            max_tokens,
            model=model,
            temperature=temperature,
        )

    async def stream_response(
        self,
        prompt: str,
        max_tokens: int | None = None,
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式生成回复"""
        if not self.api_key:
            raise ValueError("DeepSeek API key not found")

        prompt = self._truncate_prompt(prompt)
        payload = self._build_payload(
            prompt,
            max_tokens,
            stream=True,
            model=model,
            temperature=temperature,
        )

        def _stream_lines() -> list[str]:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                stream=True,
                timeout=90,
            )
            if response.status_code != 200:
                raise Exception(
                    f"DeepSeek API error: {response.status_code} - {response.text}"
                )
            return [line.decode("utf-8") for line in response.iter_lines() if line]

        for line in await asyncio.to_thread(_stream_lines):
            yield line


# 全局实例
deepseek_service = DeepSeekService()
