"""A single background summary worker with a replaceable two-record window."""
import threading
import math
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .screening import StopRun
from .llm import is_retryable_error
from .review_reading import ReadingFormatError


def retry_delay(exc, retry_number):
    """Respect server delays; defer instead of retrying too soon for long hints."""
    headers = getattr(getattr(exc, 'response', None), 'headers', {}) or {}
    hint = headers.get('retry-after')
    delay = 0
    if hint is not None:
        try:
            delay = float(hint)
        except (TypeError, ValueError):
            try:
                delay = (parsedate_to_datetime(hint) - datetime.now(timezone.utc)).total_seconds()
            except (TypeError, ValueError, OverflowError):
                delay = 0
    if not math.isfinite(delay):
        delay = 0
    delay = max(delay, min(2 ** retry_number, 30))
    return delay + random.uniform(0, .5) if delay <= 60 else None


def retryable(exc):
    # A quota/billing error may also use HTTP 429, but needs operator action.
    if getattr(exc, 'code', None) in ('insufficient_quota', 'billing_hard_limit_reached'):
        return False
    return isinstance(exc, (ReadingFormatError, TimeoutError, ConnectionError)) or is_retryable_error(exc)


def failure_reason(exc):
    if isinstance(exc, ReadingFormatError):
        return str(exc)  # Only locally constructed messages, never a raw API error.
    status = getattr(exc, 'status_code', None)
    return type(exc).__name__ + (f'，HTTP {status}' if type(status) is int else '')


class ReadingPrefetch:
    def __init__(self, workflow, client_factory=None):
        self.workflow = workflow
        self.client_factory = client_factory or workflow.reading_client
        self.condition = threading.Condition()
        self.thread = None
        self.runner = None
        self.client = None
        self.closed = False
        self.revision = 0
        self.role = None
        self.targets = []
        self.pending = []
        self.completed = []
        self.in_flight = None
        self.error = None
        self.retry = None
        self.failed = {}

    def request(self, role=None, hashes=()):
        hashes = list(dict.fromkeys(hashes))
        if len(hashes) > 2:
            raise ValueError('摘要预取最多包含当前与下一篇')
        with self.condition:
            if self.closed:
                raise ValueError('摘要服务已关闭')
            if (self.role, self.targets) == (role, hashes):
                return
            self.revision += 1
            self.role, self.targets = role, hashes
            self.pending, self.completed, self.error = list(hashes), [], None
            self.retry, self.failed = None, {}
            if hashes and self.thread is None:
                self.thread = threading.Thread(target=self._run, name='reading-prefetch')
                self.thread.start()
            self.condition.notify_all()

    def snapshot(self):
        with self.condition:
            return dict(role=self.role, targets=list(self.targets), completed=list(self.completed),
                        in_flight=self.in_flight, error=self.error,
                        retry=dict(self.retry) if self.retry else None, failed=dict(self.failed),
                        busy=bool(self.pending or self.in_flight), revision=self.revision)

    def _client(self):
        if self.client is None:
            self.client = self.client_factory()
        return self.client

    def _run(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda: self.closed or self.pending)
                if self.closed:
                    return
                h = self.pending.pop(0)
                revision = self.revision
                self.in_flight = h
            error = None
            fatal = False
            success = False
            try:
                if self.runner is None:
                    self.runner = self.workflow.reading_summarizer()
                commit = self.workflow.repo.get_commit(h, 0)
                correction = None
                retries = self.workflow.options.summary_retries
                for attempt in range(retries + 1):
                    with self.condition:
                        if self.closed or revision != self.revision:
                            break
                    try:
                        self.runner.generate(commit, self._client, correction=correction)
                        success = True
                        break
                    except StopRun:
                        raise
                    except Exception as exc:
                        reason = failure_reason(exc)
                        can_retry = retryable(exc)
                        if not can_retry or attempt == retries:
                            fatal = not can_retry
                            error = (f'{h[:12]} 摘要生成失败：{reason}。' +
                                     (f'已用完 {retries} 次自动重试，本轮跳过该篇；自动摘要保持开启。'
                                      if can_retry else '已暂停本轮派发，请检查接口/配置；自动摘要开关保持开启。'))
                            break
                        delay = retry_delay(exc, attempt + 1)
                        if delay is None:
                            fatal = True
                            error = f'{h[:12]}：服务端要求较长等待，已暂停本轮派发，请稍后重试。'
                            break
                        if isinstance(exc, ReadingFormatError):
                            correction = reason
                        with self.condition:
                            if self.closed or revision != self.revision:
                                break
                            self.retry = dict(hash=h, attempt=attempt+1, max_retries=retries,
                                              delay=round(delay,1), reason=reason)
                            self.condition.notify_all()
                            if self.condition.wait_for(lambda:self.closed or revision != self.revision,
                                                       timeout=delay):
                                break
            except StopRun:
                fatal = True
                error = '摘要预算不足，请提高摘要预算并重启服务；已有摘要仍可使用。'
            except Exception as exc:
                fatal = True
                error = f'摘要准备失败（{failure_reason(exc)}）。请检查本地仓库/配置；未自动重试。'
            finally:
                with self.condition:
                    self.in_flight = None
                    if revision == self.revision:
                        self.retry = None
                        if error:
                            self.failed[h] = error
                            self.error = '\n'.join(self.failed.values())
                            if fatal:
                                self.pending = []
                        elif success:
                            self.completed.append(h)
                    self.condition.notify_all()

    def close(self):
        with self.condition:
            self.closed = True
            self.pending = []
            self.condition.notify_all()
        if self.thread:
            self.thread.join()  # Let an already sent request finish and persist its budget/cache.
