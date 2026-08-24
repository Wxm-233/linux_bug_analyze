"""OpenAI 兼容接口适配与重试策略。"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from .analysis_protocol import AnalysisFormatError, parse_model_output
from .models import ModelAnalysis
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
        format_retries: int = 1,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.format_retries = format_retries
        self.sleep = sleep

    def analyze(self, prompt: str) -> ModelAnalysis:
        transport_failures = 0
        format_failures = 0
        request_prompt = prompt
        while True:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": request_prompt},
                    ],
                    temperature=0.2,
                    max_tokens=self.max_tokens,
                )
            except Exception as exc:
                if (
                    transport_failures < self.max_retries
                    and is_retryable_error(exc)
                ):
                    wait_seconds = 2**transport_failures
                    transport_failures += 1
                    print(
                        f"[重试] 临时 API 错误，{wait_seconds}s 后重新请求。",
                        flush=True,
                    )
                    self.sleep(wait_seconds)
                    continue
                if isinstance(exc, LLMError):
                    raise
                raise LLMError(f"模型调用失败：{exc}") from exc

            try:
                choice = response.choices[0]
                finish_reason = getattr(choice, "finish_reason", None)
                if finish_reason not in (None, "stop"):
                    raise AnalysisFormatError(
                        f"模型输出未完整结束（finish_reason={finish_reason!r}）。"
                    )
                content = choice.message.content
                if not isinstance(content, str) or not content.strip():
                    raise AnalysisFormatError("模型返回了空内容。")
                parsed = parse_model_output(content)
                return ModelAnalysis(parsed.classification, parsed.markdown, self.model)
            except (AttributeError, IndexError, AnalysisFormatError) as exc:
                format_error = (
                    exc
                    if isinstance(exc, AnalysisFormatError)
                    else AnalysisFormatError(f"模型响应结构无效：{exc}")
                )
                if format_failures >= self.format_retries:
                    raise LLMError(f"模型输出格式校验失败：{format_error}") from exc
                format_failures += 1
                request_prompt = (
                    prompt
                    + "\n\n上一次响应未通过格式校验："
                    + str(format_error)
                    + "\n请重新完成分析并严格遵守输出协议。若上次因长度被截断，"
                    "请压缩措辞，但不得省略要求的二级标题。"
                )
                print(
                    f"[重试] 模型输出格式无效，进行第 {format_failures} 次格式重试："
                    f"{format_error}",
                    flush=True,
                )
