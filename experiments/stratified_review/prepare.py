"""Freeze a no-LLM, signal-stratified source-review pilot.

This ranks evidence leads for sampling. It never changes the production filter or
automatically excludes a commit from DeepSeek screening.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import heapq
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from linux_bug_analyze.commit_source import iter_mainline_commits
from linux_bug_analyze.git_repository import GitRepository
from linux_bug_analyze.hash_filter import DEFAULT_CROSS_ARCH_INCLUDE
from linux_bug_analyze.models import CommitInfo
from linux_bug_analyze.reporting import write_text_atomic


DEFECT = re.compile(
    r'\b(?:fix(?:es|ed|ing)?|regress(?:ion|ed)?|bug|broken|fail(?:s|ed|ure)?|'
    r'crash(?:es|ed)?|hang(?:s|ing)?|deadlock|incorrect|wrong|corrupt(?:ion)?|'
    r'overflow|underflow|race|use.after.free|oops|panic|data loss|'
    r'performance regression|slowdown|slower|latency regression)\b', re.I)
PERFORMANCE = re.compile(r'\b(?:performance regression|slowdown|slower|latency regression|throughput regression)\b', re.I)
ARCH_NAME = re.compile(
    r'\b(?:arm64|aarch64|arm32|armv[5-9]|arm|x86(?:[-_]?64)?|i[3-6]86|'
    r'risc[- ]?v|s390|powerpc|ppc|mips|loongarch|sparc|parisc|m68k|'
    r'ia64|xtensa|microblaze|hexagon|csky|openrisc|um|uml)\b', re.I)
ARCH_DIFFERENCE = re.compile(
    r'\b(?:only on|fails? on|broken on|works? on|not on|other architectures?|'
    r'all architectures?|cross[- ]arch(?:itecture)?|arch(?:itecture)?[- ]specific|'
    r'big[- ]endian|little[- ]endian|endianness|byte order|32[- ]bit|64[- ]bit|'
    r'page size|pagesize|word size|compat(?:ibility)? ABI|memory ordering|'
    r'cache coherency|cache maintenance)\b', re.I)
BOUNDARY = re.compile(
    r'\b(?:generic|common code|shared code|architecture callback|arch callback|'
    r'interface contract|callback|platform capability|hardware capability|'
    r'arch(?:itecture)?[- ]specific|fallback|assum(?:e|es|ed|ption)|'
    r'expect(?:s|ed|ation)?|provide(?:s|d|r)?|firmware description|'
    r'cpu hotplug|topology|compat ABI)\b', re.I)
TRAILER = re.compile(r'^(?:Signed-off-by|Reviewed-by|Acked-by|Tested-by|Cc|Link|Reported-by|Suggested-by):', re.I)
REVISION = re.compile(r'^v\d+(?:\.\d+)?:', re.I)
HEX40 = re.compile(r'\b[0-9a-f]{40}\b')
ARCH_PATH = re.compile(DEFAULT_CROSS_ARCH_INCLUDE[0], re.I)


def explanation(commit: CommitInfo, version: str = 'v2') -> str:
    body = []
    for line in commit.body.splitlines():
        if version == 'v2' and REVISION.match(line.strip()):
            break
        if not TRAILER.match(line.strip()):
            body.append(line)
    return '\n'.join([commit.subject, *body])


def signals(commit: CommitInfo, version: str = 'v2') -> dict[str, object]:
    text = explanation(commit, version)
    paths = commit.files
    fixes_tag = bool(re.search(r'(?mi)^Fixes:\s+[0-9a-f]{7,}', commit.body))
    defect = bool(DEFECT.search(text) or fixes_tag)
    difference = bool(ARCH_DIFFERENCE.search(text))
    arch_text = bool(ARCH_NAME.search(text))
    arch_path = any(ARCH_PATH.search(path) for path in paths)
    common_path = any(path.startswith(('kernel/', 'mm/', 'include/linux/', 'block/', 'lib/', 'drivers/')) for path in paths)
    boundary = bool(BOUNDARY.search(text) or (arch_path and common_path))
    performance = bool(PERFORMANCE.search(text))
    return {
        'defect': defect,
        'performance': performance,
        'architecture_text': arch_text,
        'architecture_path': arch_path,
        'architecture_difference': difference,
        'boundary': boundary,
        'crossed_arch_and_common_paths': arch_path and common_path,
        'fixes_tag': fixes_tag,
    }


def selected_stratum(s: dict[str, object], version: str = 'v2') -> str:
    arch = s['architecture_text'] or s['architecture_path']
    if s['defect'] and (s['architecture_difference'] or (arch and s['boundary'])):
        return 'high'
    if (s['defect'] and (arch or s['boundary'])) or (version == 'v1' and ((arch and s['boundary']) or s['performance'])):
        return 'medium'
    return 'low'


def stable_score(seed: int, commit_hash: str) -> int:
    return int(hashlib.sha256(f'{seed}:{commit_hash}'.encode('ascii')).hexdigest(), 16)


class MinHashSample:
    def __init__(self, quota: int, seed: int):
        self.quota, self.seed = quota, seed
        self.heap: list[tuple[int, str, dict]] = []

    def offer(self, row: dict) -> None:
        if self.quota == 0:
            return
        score = stable_score(self.seed, row['hash'])
        entry = (-score, row['hash'], row)
        if len(self.heap) < self.quota:
            heapq.heappush(self.heap, entry)
        elif score < -self.heap[0][0]:
            heapq.heapreplace(self.heap, entry)

    def rows(self) -> list[dict]:
        return [entry[2] for entry in sorted(self.heap, key=lambda item: (-item[0], item[1]))]


def seen_hashes(root: Path) -> set[str]:
    seen: set[str] = set()
    local = root / 'analysis_out'
    if not local.exists():
        return seen
    for path in local.rglob('*'):
        if not path.is_file():
            continue
        if HEX40.fullmatch(path.stem):
            seen.add(path.stem)
        elif path.name in {'hashes.txt', 'selected_hashes.txt', 'input.json', 'manifest.json', 'local-review.json', 'comparison.json'} and path.stat().st_size < 3_000_000:
            seen.update(HEX40.findall(path.read_text(encoding='utf-8', errors='replace')))
    return seen


CELLS = ('high', 'medium', 'low', 'outside_defect', 'outside_other')


def batch_quotas(args: argparse.Namespace) -> dict[str, int]:
    if not args.batch_quotas:
        return {'high': args.per_stratum, 'medium': args.per_stratum,
                'low': args.per_stratum, 'outside_defect': (args.per_stratum + 1) // 2,
                'outside_other': args.per_stratum // 2}
    quotas: dict[str, int] = {}
    for part in args.batch_quotas.split(','):
        name, separator, raw = part.strip().partition('=')
        if not separator or name not in CELLS or name in quotas:
            raise ValueError('batch-quotas 应包含五个唯一层名及非负整数配额')
        try:
            value = int(raw)
        except ValueError as exc:
            raise ValueError(f'{name} 配额不是整数') from exc
        if value < 0:
            raise ValueError('批次配额不能为负数')
        quotas[name] = value
    if set(quotas) != set(CELLS) or not any(quotas.values()):
        raise ValueError('必须指定五个层的配额，且至少一个大于零')
    return {name: quotas[name] for name in CELLS}


def planned_batches(manifest: dict) -> list[list[str]]:
    quotas = manifest['batch_quotas']
    grouped = {name: [row['hash'] for row in manifest['samples'] if row['stratum'] == name]
               for name in CELLS}
    batches = []
    for index in range(manifest['batch_count']):
        batch = []
        for name, quota in quotas.items():
            batch.extend(grouped[name][index * quota:(index + 1) * quota])
        if len(batch) != sum(quotas.values()) or len(set(batch)) != len(batch):
            raise ValueError('批次有缺额或重复')
        batches.append(batch)
    if len(set(hash_ for batch in batches for hash_ in batch)) != sum(map(len, batches)):
        raise ValueError('不同批次之间出现重复提交')
    return batches


def write_batches(outdir: Path, manifest: dict) -> None:
    for index, hashes in enumerate(planned_batches(manifest), 1):
        path = outdir / f'batch-{index:03d}.txt'
        content = ''.join(hash_ + '\n' for hash_ in hashes)
        if path.exists() and path.read_text(encoding='utf-8') != content:
            raise ValueError(f'已存在不同内容的批次文件：{path}')
        write_text_atomic(path, content)


def build(args: argparse.Namespace) -> dict:
    root = Path(__file__).resolve().parents[2]
    audit_path = root / 'candidate_hashes.txt.audit.jsonl'
    selected_path = root / 'candidate_hashes.txt'
    with audit_path.open(encoding='utf-8') as stream:
        audit = json.loads(next(stream))
        indices = {row['hash']: row['input_index'] for row in map(json.loads, stream)}
    selected = {line.strip() for line in selected_path.read_text(encoding='utf-8').splitlines() if line.strip()}
    if len(indices) != audit['selected'] or indices.keys() != selected:
        raise ValueError('候选 hash 文件与旧审计不一致')
    seen = seen_hashes(root)
    quotas = batch_quotas(args)
    limits = {name: quota * args.batches for name, quota in quotas.items()}
    samplers = {key: MinHashSample(limit, args.seed) for key, limit in limits.items()}
    counts = collections.Counter()
    selected_in_scan: set[str] = set()
    head = GitRepository(args.linux_dir)._run(['rev-parse', 'HEAD']).strip()

    for commit in iter_mainline_commits(args.linux_dir, audit['ref'], since=audit['since'],
                                        until=audit['until'], no_merges=audit['no_merges'],
                                        reverse=audit['reverse'], max_count=0):
        original_selected = commit.hash in selected
        if original_selected:
            selected_in_scan.add(commit.hash)
        s = signals(commit, args.signal_version)
        stratum = (selected_stratum(s, args.signal_version) if original_selected else
                   'outside_defect' if s['defect'] else 'outside_other')
        counts[stratum] += 1
        if commit.hash in seen:
            continue
        row = {'hash': commit.hash, 'subject': commit.subject, 'stratum': stratum,
               'original_selected': original_selected, 'signals': s,
               'audit_index': indices.get(commit.hash)}
        samplers[stratum].offer(row)

    # A date string can be interpreted differently by Git on Windows and WSL.
    # Classify any frozen selected hashes absent from this WSL scan individually;
    # do not silently drop them or include them in the unselected population.
    missing = sorted(selected - selected_in_scan)
    repo = GitRepository(args.linux_dir)
    for commit_hash in missing:
        commit = repo.get_commit(commit_hash, 0, include_diff=False)
        s = signals(commit, args.signal_version)
        stratum = selected_stratum(s, args.signal_version)
        counts[stratum] += 1
        if commit_hash not in seen:
            samplers[stratum].offer({'hash': commit_hash, 'subject': commit.subject,
                                     'stratum': stratum, 'original_selected': True,
                                     'signals': s, 'audit_index': indices[commit_hash]})

    if sum(counts[key] for key in ('high', 'medium', 'low')) != audit['selected']:
        raise ValueError('候选分层计数与旧审计不一致')
    samples = [row for key in limits for row in samplers[key].rows()]
    if len(samples) != sum(limits.values()) or len({row['hash'] for row in samples}) != len(samples):
        raise ValueError('某一层样本不足或重复')
    return {
        'version': 'static-strata-' + args.signal_version, 'seed': args.seed, 'per_stratum': args.per_stratum,
        'linux_head': head, 'audit_summary': audit,
        'audit_sha256': hashlib.sha256(audit_path.read_bytes()).hexdigest(),
        'selected_hashes_sha256': hashlib.sha256(selected_path.read_bytes()).hexdigest(),
        'originally_seen_excluded': len(seen),
        'wsl_scan_count': sum(counts.values()) - len(missing),
        'selected_missing_from_wsl_date_window': missing,
        'stratum_sizes': dict(counts), 'quotas': limits,
        'batch_quotas': quotas, 'batch_count': args.batches,
        'sampling_note': 'Within each cell, the smallest SHA256(seed:hash) scores; deterministic without replacement. Outside is split between defect-like and other samples. Nonproportional; not a prevalence estimate.',
        'samples': samples,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--linux-dir', type=Path, required=True)
    parser.add_argument('--outdir', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=20260923)
    parser.add_argument('--signal-version', choices=('v1', 'v2'), default='v2')
    parser.add_argument('--per-stratum', type=int, default=25)
    parser.add_argument('--batch-quotas', help='每批配额，如 high=100,medium=100,low=50,outside_defect=13,outside_other=12')
    parser.add_argument('--batches', type=int, default=1)
    args = parser.parse_args(argv)
    if args.per_stratum < 2 or args.batches < 1:
        parser.error('--per-stratum 至少为 2 且 --batches 至少为 1')
    try:
        quotas = batch_quotas(args)
    except ValueError as exc:
        parser.error(str(exc))
    args.outdir.mkdir(parents=True, exist_ok=True)
    path = args.outdir / 'manifest.json'
    if path.exists():
        old = json.loads(path.read_text(encoding='utf-8'))
        if old['version'] != 'static-strata-' + args.signal_version:
            parser.error('静态信号版本与冻结清单不同')
        if args.batch_quotas and 'batch_quotas' not in old:
            parser.error('旧试验清单不含批次信息，请换一个输出目录')
        if not args.batch_quotas and old.get('per_stratum') != args.per_stratum:
            parser.error('已冻结清单的每层配额不同，请换一个输出目录')
        if (old['seed'] != args.seed or old.get('batch_quotas', quotas) != quotas
                or old.get('batch_count', 1) != args.batches):
            parser.error('已冻结清单的种子或批次配额不同，请换一个输出目录')
        repo = GitRepository(args.linux_dir)
        if repo._run(['rev-parse', 'HEAD']).strip() != old['linux_head']:
            parser.error('Linux Git HEAD 与冻结清单不同')
        root = Path(__file__).resolve().parents[2]
        for name, field in (('candidate_hashes.txt.audit.jsonl', 'audit_sha256'),
                            ('candidate_hashes.txt', 'selected_hashes_sha256')):
            if hashlib.sha256((root / name).read_bytes()).hexdigest() != old[field]:
                parser.error(f'{name} 与冻结清单不同')
        if args.batch_quotas:
            write_batches(args.outdir, old)
        print('使用已冻结 manifest，不重抽样：', path)
        return 0
    result = build(args)
    write_text_atomic(path, json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    if args.batch_quotas:
        write_batches(args.outdir, result)
    print(json.dumps({'scan': result['wsl_scan_count'], 'strata': result['stratum_sizes'],
                      'sampled': len(result['samples']),
                      'date_window_missing_selected': len(result['selected_missing_from_wsl_date_window'])},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
