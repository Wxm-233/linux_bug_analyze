"""One command to start/resume the local screening workbench."""
import argparse
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .config import load_settings, ConfigurationError
from .fast_screen_cli import run_lock
from .review_workflow import ReviewWorkflow
from .review_web import ReviewApplication, make_server


def main(argv=None):
    parser = argparse.ArgumentParser(description='启动人机协同 commit 筛选工作台（默认不调用 LLM）')
    parser.add_argument('--settings', type=Path, default=Path('settings.toml'))
    parser.add_argument('--port', type=int)
    parser.add_argument('--export-only', action='store_true', help='更新 CSV/Markdown 后退出；不启动服务或调用模型')
    args = parser.parse_args(argv)
    try:
        settings = load_settings(args.settings, required=True)
        if not args.export_only:
            try:
                installed = version('asreview')
            except PackageNotFoundError:
                raise ConfigurationError('缺少 ASReview。请先运行：python -m pip install -e ".[review]"') from None
            if installed != '3.0.8':
                raise ConfigurationError(f'ASReview 当前为 {installed}，本版本验证使用 3.0.8；请安装项目的 [review] 依赖。')
        port = args.port if args.port is not None else settings.review.port
        if not 1 <= port <= 65535:
            raise ConfigurationError('端口必须在 1–65535 内')
        output = settings.review.output_dir or settings.source.parent / 'review_workspace'
        with run_lock(output):
            workflow = ReviewWorkflow(settings, output)
            if args.export_only:
                workflow.require_ready()
                workflow.export()
                print(f'已导出：{output / "summary.md"}')
                return 0
            app = ReviewApplication(workflow)
            server = make_server(app, port)
            print(f'筛选工作台：http://127.0.0.1:{port}/#{app.token}', flush=True)
            print(f'远程服务器：先在本机运行 ssh -N -L {port}:127.0.0.1:{port} 用户@服务器，再打开上述链接。', flush=True)
            print('Ctrl+C 停止服务；标注自动保存。仅点击网页中“启动短判断”才调用 LLM。', flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print('正在停止派发并保存已发出请求的结果…', flush=True)
            finally:
                workflow.cancel.set()
                if workflow.runner:
                    workflow.runner.budget.stopped.set()
                if app.thread:
                    app.thread.join()
                server.server_close()
        return 0
    except (ValueError, OSError) as exc:
        print(f'[错误] {exc}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
