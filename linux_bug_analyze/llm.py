"""OpenAI 兼容接口适配与重试策略。"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from .prompting import SYSTEM_PROMPT


class LLMError(RuntimeError):
    """模型在重试后仍未返回有效内容。"""


def is_retryable_error(error: Exception) -> bool:
    status = getattr(error, "status_code", None)
    if status is not None:
        return status in (408, 409, 429) or 500 <= status < 600
    text = str(error).lower()
    return any(
        token in text
        for token in ("429", "rate limit", "timeout", "connection", "http 5")
    )


def create_openai_client(api_key: str, base_url: str) -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LLMError("未安装 openai 库；请先安装项目依赖。") from exc
    # 只使用本模块的显式重试，避免 SDK 默认重试与外层重试相乘。
    return OpenAI(api_key=api_key, base_url=base_url, max_retries=0)


class ChatAnalyzer:
    """将具体 SDK 封装为可注入、可测试的分析器。"""

    def __init__(
        self,
        client: Any,
        model: str,
        *,
        max_tokens: int = 8192,
        max_retries: int = 4,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.sleep = sleep

    def analyze(self, prompt: str) -> str:
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=self.max_tokens,
                )
                content = response.choices[0].message.content
                if not content or not content.strip():
                    raise LLMError("模型返回了空内容。")
                return content.strip()
            except Exception as exc:
                if attempt < self.max_retries and is_retryable_error(exc):
                    wait_seconds = 2**attempt
                    print(
                        f"[重试] 临时 API 错误，{wait_seconds}s 后进行第 {attempt + 2} 次请求。",
                        flush=True,
                    )
                    self.sleep(wait_seconds)
                    continue
                if isinstance(exc, LLMError):
                    raise
                raise LLMError(f"模型调用失败：{exc}") from exc
        raise AssertionError("unreachable")
