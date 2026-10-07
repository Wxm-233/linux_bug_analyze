"""Loopback-only workbench. One writer, token authentication, no shell execution."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from urllib.parse import urlsplit, parse_qs


class ReviewApplication:
    def __init__(self, workflow):
        self.workflow = workflow
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.thread = None
        self.busy = False
        self.error = None

    def dispatch(self, action, values):
        w = self.workflow
        if action == 'stop':
            w.cancel.set()
            if w.runner:
                w.runner.budget.stopped.set()
            return
        actions = {
            'prepare': w.prepare, 'freeze': w.freeze, 'screen': w.screen,
            'sample': w.sample, 'export': w.export, 'retrain': w.train,
            'label': lambda: w.label(values['hash'], values['role'], values['label'], values.get('note', '')),
            'select': lambda: w.select(values['threshold']),
        }
        if action not in actions:
            raise ValueError('未知操作')
        with self.lock:
            if self.busy:
                raise ValueError('已有任务运行，请等待或停止 LLM 派发。')
            self.busy = True
            self.error = None
            w.cancel.clear()
            w.progress = '正在执行：' + action

        def execute():
            try:
                actions[action]()
                w.progress = '操作完成：' + action
            except (ValueError, OSError) as exc:
                self.error = str(exc)
            except Exception as exc:
                # Never expose transport errors/API headers/credentials to the page.
                self.error = f'{type(exc).__name__}：操作失败，进度已保留。请检查配置、依赖和输出文件。'
            finally:
                self.busy = False
        self.thread = threading.Thread(target=execute, name='review-worker')
        self.thread.start()


def make_server(application, port):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Do not log access tokens or commit text.

        def reply(self, data, content_type='application/json; charset=utf-8', status=200):
            payload = json.dumps(data, ensure_ascii=False).encode('utf-8') if content_type.startswith('application/json') else data
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def authorized(self, api=True):
            host = self.headers.get('Host', '')
            # A forwarded local port can differ from the listening server port.
            if host.split(':')[0] not in ('127.0.0.1', 'localhost'):
                self.reply({'error': '仅允许 localhost/127.0.0.1'}, status=403)
                return False
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + host:
                self.reply({'error': '不允许跨站请求'}, status=403)
                return False
            if api and not secrets.compare_digest(self.headers.get('X-Review-Token', ''), application.token):
                self.reply({'error': '请使用终端输出的带 #token 链接打开页面。'}, status=403)
                return False
            return True

        def do_GET(self):
            parsed = urlsplit(self.path)
            path, params = parsed.path, parse_qs(parsed.query)
            if not self.authorized(api=path not in ('/', '/app.js')):
                return
            try:
                if path in ('/', '/app.js'):
                    filename = 'review_web.html' if path == '/' else 'review_web.js'
                    kind = 'text/html; charset=utf-8' if path == '/' else 'text/javascript; charset=utf-8'
                    return self.reply(Path(__file__).with_name(filename).read_bytes(), kind)
                w = application.workflow
                if path == '/api/status':
                    live = None
                    usage = {}
                    p = w.output / 'llm' / 'summary.json'
                    if p.exists():
                        live = json.loads(p.read_text(encoding='utf-8'))
                    usage_path = w.output / 'llm' / 'usage.json'
                    if usage_path.exists():
                        ledger = json.loads(usage_path.read_text(encoding='utf-8'))
                        usage = {k: ledger.get(k, 0) for k in ('requests','charged_tokens','reported_tokens')}
                    return self.reply(dict(busy=application.busy, error=application.error,
                                           progress=w.progress, summary=w.summary(), live_llm=live,
                                           budget=dict(max_requests=w.options.max_requests,
                                                       token_budget=w.options.token_budget, **usage),
                                           configured_model=w.settings.model or 'deepseek-v4-flash'))
                if application.busy:
                    return self.reply({'error': '任务运行中，请稍后。'}, status=409)
                if path == '/api/next':
                    role = params.get('role', ['train'])[0]
                    h = w.next_record(role)
                    return self.reply(w.material(h) if h else None)
                if path == '/api/material':
                    return self.reply(w.material(params['hash'][0]))
                if path == '/api/history':
                    return self.reply(list(w.store.labels(params.get('role', ['train'])[0]).values()))
                if path == '/api/search':
                    query = params.get('q', [''])[0].strip().lower()
                    return self.reply([dict(hash=r['hash'], subject=r['subject']) for r in w.store.records(True)
                                       if query and (query in r['subject'].lower() or query in r['hash'])][:30])
                if path == '/api/preview':
                    result = w.threshold_preview(float(params['threshold'][0]))
                    result.pop('hashes')
                    return self.reply(result)
                if path == '/api/download':
                    name = params.get('name', ['summary.md'])[0]
                    allowed = {'summary.md','summary.json','results.csv','labels.csv','label_events.csv',
                               'confirmed_related_hashes.txt','provisional_related_hashes.txt',
                               'llm_hashes.txt','asreview_dataset.csv','audit_plan.json','model_snapshot.json'}
                    if name not in allowed:
                        raise ValueError('不允许下载此文件')
                    return self.reply((w.output / name).read_bytes(), 'application/octet-stream')
                self.reply({'error': '未找到'}, status=404)
            except (ValueError, KeyError, OSError) as exc:
                self.reply({'error': str(exc)}, status=400)

        def do_POST(self):
            if not self.authorized():
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 65536 or self.headers.get_content_type() != 'application/json':
                    raise ValueError('需要不超过 64 KB 的 JSON 请求')
                values = json.loads(self.rfile.read(length))
                if not isinstance(values, dict):
                    raise ValueError('请求必须为对象')
                if self.path != '/api/action':
                    raise ValueError('未知接口')
                application.dispatch(values.pop('action'), values)
                self.reply({'accepted': True})
            except (ValueError, KeyError) as exc:
                self.reply({'error': str(exc)}, status=400)

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)
