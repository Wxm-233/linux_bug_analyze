"""A single background summary worker with a replaceable two-record window."""
import threading

from .screening import StopRun


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
            if hashes and self.thread is None:
                self.thread = threading.Thread(target=self._run, name='reading-prefetch')
                self.thread.start()
            self.condition.notify_all()

    def snapshot(self):
        with self.condition:
            return dict(role=self.role, targets=list(self.targets), completed=list(self.completed),
                        in_flight=self.in_flight, error=self.error,
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
            try:
                if self.runner is None:
                    self.runner = self.workflow.reading_summarizer()
                commit = self.workflow.repo.get_commit(h, 0)
                # A label or a navigation may have replaced the window while Git ran.
                with self.condition:
                    stale = self.closed or revision != self.revision
                if not stale:
                    self.runner.generate(commit, self._client)
            except StopRun:
                error = '摘要预算不足，请提高摘要预算并重启服务；已有摘要仍可使用。'
            except Exception as exc:
                error = f'摘要生成失败（{type(exc).__name__}）。请检查接口/配置，重新开启自动摘要可重试；仍可按原始材料标注。'
            finally:
                with self.condition:
                    self.in_flight = None
                    if revision == self.revision:
                        if error:
                            self.error = error
                            self.pending = []  # Do not spend the remaining budget on automatic retries.
                        else:
                            self.completed.append(h)
                    self.condition.notify_all()

    def close(self):
        with self.condition:
            self.closed = True
            self.pending = []
            self.condition.notify_all()
        if self.thread:
            self.thread.join()  # Let an already sent request finish and persist its budget/cache.
