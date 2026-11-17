"""Budgeted DeepSeek-only screening entry point."""
import argparse
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from .config import load_settings, resolve_api_key
from .fast_screening import FastScreener, save
from .git_repository import GitRepository, GitRepositoryError, read_hashes
from .llm import create_openai_client


def load_batch_selection(path: Path, number: int) -> tuple[Path, dict]:
    """Resolve a frozen stratified batch and verify its hash file."""
    manifest = json.loads(path.read_text(encoding='utf-8'))
    if number < 1 or number > manifest['batch_count']:
        raise ValueError('批次编号不在冻结计划范围内')
    quotas = manifest['batch_quotas']
    grouped = {name: [row['hash'] for row in manifest['samples'] if row['stratum'] == name]
               for name in quotas}
    expected = []
    for name, quota in quotas.items():
        expected.extend(grouped[name][(number-1)*quota:number*quota])
    if len(expected) != sum(quotas.values()) or len(set(expected)) != len(expected):
        raise ValueError('冻结清单中的批次有缺额或重复')
    expected_set = set(expected)
    hashes_path = path.parent / f'batch-{number:03d}.txt'
    if read_hashes(hashes_path) != expected:
        raise ValueError('批次哈希文件与冻结清单不一致')
    provenance = {
        'plan_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'batch_sha256': hashlib.sha256(hashes_path.read_bytes()).hexdigest(),
        'batch_number': number, 'seed': manifest['seed'],
        'linux_head': manifest['linux_head'],
        'audit_sha256': manifest['audit_sha256'],
        'stratum_sizes': manifest['stratum_sizes'], 'batch_quotas': quotas,
        'sample_strata': {row['hash']: row['stratum'] for row in manifest['samples']
                          if row['hash'] in expected_set},
        'nominal_sampling_fraction': {name: quota / manifest['stratum_sizes'][name]
                                      for name, quota in quotas.items()},
        'sampling_note': 'Nominal fractions use the full cell sizes; previously seen commits were excluded before drawing. This is a nonproportional pilot, not a prevalence estimate.',
        'execution_order': 'round_robin_by_stratum',
    }
    if len(provenance['sample_strata']) != len(expected):
        raise ValueError('批次缺少逐条分层记录')
    return hashes_path, provenance


def interleave_batch(commits, provenance):
    """Visit every frozen stratum early, even if the budget stops the batch."""
    if provenance is None:
        return commits
    cells = {name: [] for name in provenance['batch_quotas']}
    for commit in commits:
        cells[provenance['sample_strata'][commit.hash]].append(commit)
    return [commit for index in range(max(map(len, cells.values())))
            for group in cells.values() for commit in group[index:index + 1]]


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
    p.add_argument('--batch-manifest',type=Path,help='静态分层冻结清单；使用该批次的 hash 文件')
    p.add_argument('--batch-number',type=int,default=1)
    p.add_argument('--outdir',type=Path)
    p.add_argument('--model',default='DeepSeek-V4.1-Flash')
    p.add_argument('--context-mode',choices=('full','task-only'),default='full',
                   help='实验选项：task-only 不重复附加研究文档；默认保持原行为')
    p.add_argument('--context-file',type=Path,
                   help='实验选项：覆盖默认研究文档；与 task-only 不可同时使用')
    p.add_argument('--material-mode',choices=('original','key-hunks'),default='original',
                   help='实验选项：key-hunks 在首轮保留所有修改行并压缩未修改上下文')
    p.add_argument('--max-items',type=int,default=500)
    p.add_argument('--max-requests',type=int,default=100)
    p.add_argument('--token-budget',type=int,default=2000000)
    p.add_argument('--workers',type=int,default=16)
    p.add_argument('--compact-chars',type=int,default=6000)
    p.add_argument('--full-chars',type=int,default=20000)
    p.add_argument('--max-tokens',type=int,default=1200)
    p.add_argument('--format-retries',type=int,default=0)
    p.add_argument('--transport-retries',type=int,default=1)
    p.add_argument('--plan-only',action='store_true')
    a=p.parse_args(argv)
    if a.batch_manifest and a.hashes_file:
        p.error('--batch-manifest 与 --hashes-file 只能使用一个')
    if not a.batch_manifest and a.batch_number != 1:
        p.error('--batch-number 需要 --batch-manifest')
    if a.context_mode=='task-only' and a.context_file:
        p.error('--context-file 与 task-only 不能同时使用')
    if min(a.max_items,a.max_requests,a.token_budget,a.workers,a.compact_chars,a.full_chars,a.max_tokens)<1:
        p.error('运行上限必须为正整数')
    if a.full_chars<a.compact_chars or min(a.format_retries,a.transport_retries)<0 or a.workers>16:
        p.error('full-chars必须不小于compact-chars；重试非负；并发不超过16')
    s=load_settings(a.settings,required=True)
    if not s.linux_dir or not (a.batch_manifest or a.hashes_file or s.hashes_file) or not s.api_key_file:
        p.error('需要linux_dir、hashes_file和仓库外api_key_file')
    output=a.outdir or Path('analysis_out')/('fast-screen-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    with run_lock(output):
        total_start=time.monotonic()
        repo=GitRepository(s.linux_dir);repo.validate()
        provenance=None
        hashes_path=a.hashes_file or s.hashes_file
        if a.batch_manifest:
            try:
                hashes_path,provenance=load_batch_selection(a.batch_manifest,a.batch_number)
            except (OSError,ValueError,KeyError,TypeError,GitRepositoryError) as exc:
                p.error(f'无法读取分层批次：{exc}')
            if repo._run(['rev-parse','HEAD']).strip()!=provenance['linux_head']:
                p.error('Linux Git HEAD 与分层清单不同')
            batch_size=sum(provenance['batch_quotas'].values())
            if a.max_items<batch_size:
                p.error(f'--max-items 至少为 {batch_size}，避免截断批次配额')
            provenance_path=output/'batch_source.json'
            if provenance_path.exists() and json.loads(provenance_path.read_text(encoding='utf-8'))!=provenance:
                p.error('输出目录已属于另一个批次计划')
            save(provenance_path,provenance)
        commits=[];seen=set();aliases={};groups={}
        for h in read_hashes(hashes_path)[:a.max_items]:
            canonical=repo.resolve_hash(h);aliases[h]=canonical
            if canonical in seen:continue
            seen.add(canonical);c=repo.get_commit(canonical,0);commits.append(c)
            # Stable patch-id groups are leads, NOT proof of equivalent version semantics.
            result=subprocess.run(['git','patch-id','--stable'],input=c.diff,text=True,
                                  capture_output=True,check=True)
            if result.stdout.strip():
                key=result.stdout.split()[0];groups.setdefault(key,[]).append(c.hash)
        commits=interleave_batch(commits,provenance)
        save(output/'dedup.json',dict(aliases=aliases,canonical_duplicates=len(aliases)-len(commits),
            patch_groups=[v for v in groups.values() if len(v)>1],
            policy='canonical duplicates skipped; cross-version patch groups retained independently'))
        preparation_seconds=time.monotonic()-total_start
        save(output/'preparation.json',dict(wall_seconds=preparation_seconds,
            commits=len(commits),includes='git resolution, commit/diff extraction, stable patch-id'))
        if a.plan_only:
            print(f'计划：{len(commits)}条独立提交，{a.workers}并发，{a.model}；未调用模型。')
            return 0
        client=create_openai_client(resolve_api_key(None,s.api_key_file),s.base_url or 'https://llmapi.isrc.ac.cn/v1')
        context_path=a.context_file or (s.context_md if a.context_mode=='full' else None)
        runner=FastScreener(client,output,model=a.model,endpoint=s.base_url or 'https://llmapi.isrc.ac.cn/v1',
            context=context_path.read_text(encoding='utf-8') if context_path else '',
            workers=a.workers,max_requests=a.max_requests,token_budget=a.token_budget,
            compact_chars=a.compact_chars,full_chars=a.full_chars,max_tokens=a.max_tokens,
            format_retries=a.format_retries,transport_retries=a.transport_retries,
            material_mode=a.material_mode)
        start=time.monotonic()
        try:runner.run(commits)
        except KeyboardInterrupt:
            print('已停止派发，已保存停点。');return 130
        finally:
            ended=time.monotonic()
            save(output/'last_run.json',dict(wall_seconds=ended-start,
                preparation_seconds=preparation_seconds,total_seconds=ended-total_start,
                workers=a.workers,model=a.model,requests_cumulative=runner.budget.data['requests']))
        print(f'初筛已结束：{output}；累计请求{runner.budget.data["requests"]}；未启动详细分析。')
        return 3 if runner.budget.stopped.is_set() else 0
