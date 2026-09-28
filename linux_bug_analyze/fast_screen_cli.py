"""Budgeted DeepSeek-only screening entry point."""
import argparse
from contextlib import contextmanager
from datetime import datetime
import os
from pathlib import Path
import subprocess

from .config import load_settings, resolve_api_key
from .fast_screening import FastScreener, save
from .git_repository import GitRepository, read_hashes
from .llm import create_openai_client


@contextmanager
def run_lock(output):
    output.mkdir(parents=True,exist_ok=True)
    with (output/'run.lock').open('a+b') as lock:
        if os.name=='nt':
            import msvcrt
            lock.write(b'0');lock.flush();lock.seek(0)
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:yield
        finally:
            if os.name=='nt':
                lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)


def main(argv=None):
    p=argparse.ArgumentParser(description='并发分级初筛；不会调用GLM/Gemini或生成详细报告')
    p.add_argument('--settings',type=Path,default=Path('settings.toml'))
    p.add_argument('--hashes-file',type=Path)
    p.add_argument('--outdir',type=Path)
    p.add_argument('--model',default='DeepSeek-V4.1-Flash')
    p.add_argument('--max-items',type=int,default=500)
    p.add_argument('--max-requests',type=int,default=100)
    p.add_argument('--token-budget',type=int,default=2000000)
    p.add_argument('--workers',type=int,default=4)
    p.add_argument('--compact-chars',type=int,default=6000)
    p.add_argument('--full-chars',type=int,default=20000)
    p.add_argument('--max-tokens',type=int,default=1200)
    p.add_argument('--format-retries',type=int,default=0)
    p.add_argument('--transport-retries',type=int,default=1)
    p.add_argument('--plan-only',action='store_true')
    a=p.parse_args(argv)
    if min(a.max_items,a.max_requests,a.token_budget,a.workers,a.compact_chars,a.full_chars,a.max_tokens)<1:
        p.error('运行上限必须为正整数')
    if a.full_chars<a.compact_chars or min(a.format_retries,a.transport_retries)<0 or a.workers>16:
        p.error('full-chars必须不小于compact-chars；重试非负；并发不超过16')
    s=load_settings(a.settings,required=True)
    if not s.linux_dir or not (a.hashes_file or s.hashes_file) or not s.api_key_file:
        p.error('需要linux_dir、hashes_file和仓库外api_key_file')
    output=a.outdir or Path('analysis_out')/('fast-screen-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    with run_lock(output):
        repo=GitRepository(s.linux_dir);repo.validate()
        commits=[];seen=set();aliases={};groups={}
        for h in read_hashes(a.hashes_file or s.hashes_file)[:a.max_items]:
            canonical=repo.resolve_hash(h);aliases[h]=canonical
            if canonical in seen:continue
            seen.add(canonical);c=repo.get_commit(canonical,0);commits.append(c)
            # Stable patch-id groups are leads, NOT proof of equivalent version semantics.
            result=subprocess.run(['git','patch-id','--stable'],input=c.diff,text=True,
                                  capture_output=True,check=True)
            if result.stdout.strip():
                key=result.stdout.split()[0];groups.setdefault(key,[]).append(c.hash)
        save(output/'dedup.json',dict(aliases=aliases,canonical_duplicates=len(aliases)-len(commits),
            patch_groups=[v for v in groups.values() if len(v)>1],
            policy='canonical duplicates skipped; cross-version patch groups retained independently'))
        if a.plan_only:
            print(f'计划：{len(commits)}条独立提交，{a.workers}并发，{a.model}；未调用模型。')
            return 0
        client=create_openai_client(resolve_api_key(None,s.api_key_file),s.base_url or 'https://llmapi.isrc.ac.cn/v1')
        runner=FastScreener(client,output,model=a.model,endpoint=s.base_url or 'https://llmapi.isrc.ac.cn/v1',
            context=s.context_md.read_text(encoding='utf-8') if s.context_md else '',
            workers=a.workers,max_requests=a.max_requests,token_budget=a.token_budget,
            compact_chars=a.compact_chars,full_chars=a.full_chars,max_tokens=a.max_tokens,
            format_retries=a.format_retries,transport_retries=a.transport_retries)
        start=__import__('time').monotonic()
        try:runner.run(commits)
        except KeyboardInterrupt:
            print('已停止派发，已保存停点。');return 130
        finally:
            save(output/'last_run.json',dict(wall_seconds=__import__('time').monotonic()-start,
                workers=a.workers,model=a.model,requests_cumulative=runner.budget.data['requests']))
        print(f'初筛已结束：{output}；累计请求{runner.budget.data["requests"]}；未启动详细分析。')
        return 3 if runner.budget.stopped.is_set() else 0
