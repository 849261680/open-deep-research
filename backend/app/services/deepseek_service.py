import asyncio
import os
import time
from collections.abc import AsyncGenerator

import requests
from dotenv import load_dotenv
from requests.exceptions import Timeout

load_dotenv()


class DeepSeekService:
    def __init__(self) -> None:
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, prompt: str, max_tokens: int, stream: bool) -> dict[str, object]:
        return {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": min(max_tokens, 2000),
            "temperature": 0.7,
            "stream": stream,
        }

    def _truncate_prompt(self, prompt: str) -> str:
        max_prompt_length = 2000
        if len(prompt) > max_prompt_length:
            prompt = prompt[:max_prompt_length] + "...\n\n请基于以上内容生成简洁摘要。"
            print(f"⚠️ [DeepSeek调试] 提示词过长，已截断至 {max_prompt_length} 字符")
        return prompt

    def generate_response_sync(self, prompt: str, max_tokens: int = 2000) -> str:
        """同步调用 DeepSeek，供同步 LangChain 路径和线程池包装使用。"""
        print(f"🚀 [DeepSeek调试] 开始生成响应，提示词长度: {len(prompt)}")

        if not self.api_key:
            print("❌ [DeepSeek调试] API密钥未找到")
            raise ValueError("DeepSeek API key not found")

        prompt = self._truncate_prompt(prompt)
        payload = self._build_payload(prompt, max_tokens, stream=False)

        print("📝 [DeepSeek调试] API 请求详情:")
        print(f"   - 输入长度: {len(prompt)} 字符")
        print(f"   - 最大输出: {payload['max_tokens']} tokens")
        print(f"   - 模型: {payload['model']}")
        print(f"   - 提示词预览: {prompt[:100]}...")

        max_retries = 2
        response: requests.Response | None = None
        for attempt in range(max_retries + 1):
            try:
                print(f"🔄 [DeepSeek调试] API 调用尝试 {attempt + 1}/{max_retries + 1}")
                start_time = time.time()
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=90,
                )
                end_time = time.time()
                print(f"⏱️ [DeepSeek调试] API 响应时间: {end_time - start_time:.2f} 秒")
                print(f"📊 [DeepSeek调试] 响应状态码: {response.status_code}")

                if response.status_code != 200:
                    print(f"❌ [DeepSeek调试] API 错误响应: {response.text}")
                    if attempt == max_retries:
                        break
                    time.sleep(2)
                    continue

                result = response.json()
                response_content = result["choices"][0]["message"]["content"]
                print(
                    f"✅ [DeepSeek调试] API 调用成功，响应长度: {len(response_content)} 字符"
                )
                print(f"📝 [DeepSeek调试] 响应预览: {response_content[:100]}...")
                return response_content
            except Timeout:
                if attempt == max_retries:
                    print("⏰ [DeepSeek调试] API 请求超时，已重试多次")
                    raise Timeout("DeepSeek API request timed out")
                print(
                    f"⏰ [DeepSeek调试] 请求超时，将重试... ({attempt + 1}/{max_retries})"
                )
                time.sleep(2)
            except Exception as e:
                if attempt == max_retries:
                    print(f"❌ [DeepSeek调试] API 连接失败: {e}")
                    raise
                print(
                    f"⚠️ [DeepSeek调试] 连接失败，将重试... ({attempt + 1}/{max_retries})"
                )
                time.sleep(2)

        if response is None:
            raise RuntimeError("DeepSeek API request failed before receiving a response")

        raise Exception(f"DeepSeek API error: {response.status_code} - {response.text}")

    async def generate_response(self, prompt: str, max_tokens: int = 2000) -> str:
        """异步包装，避免阻塞事件循环。"""
        return await asyncio.to_thread(self.generate_response_sync, prompt, max_tokens)

    async def stream_response(
        self, prompt: str, max_tokens: int = 4000
    ) -> AsyncGenerator[str, None]:
        """流式生成回复"""
        if not self.api_key:
            raise ValueError("DeepSeek API key not found")

        prompt = self._truncate_prompt(prompt)
        payload = self._build_payload(prompt, max_tokens, stream=True)

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
