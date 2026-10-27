"""Summarize which broad legacy rules admitted the frozen candidate list."""

from __future__ import annotations

import collections
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / 'candidate_hashes.txt.audit.jsonl'
OUT = Path(__file__).with_name('AUDIT.md')
NAMES = ('architecture_path_pattern', 'architecture_name',
         'cross_arch_wording', 'generic_boundary_word')


def summarize(path: Path) -> str:
    counts = collections.Counter()
    alone_fields = {name: collections.Counter() for name in NAMES}
    with path.open(encoding='utf-8') as stream:
        meta = json.loads(next(stream))
        patterns = tuple(meta['include'])
        for line in stream:
            row = json.loads(line)
            hits = {m['pattern']: set(m['fields']) for m in row['include_matches']}
            mask = tuple(i for i, pattern in enumerate(patterns) if pattern in hits)
            counts['rows'] += 1
            for i in mask:
                counts[f'hit_{i}'] += 1
            if len(mask) == 1:
                i = mask[0]
                counts[f'alone_{i}'] += 1
                fields = hits[patterns[i]]
                alone_fields[NAMES[i]][','.join(sorted(fields))] += 1
    if counts['rows'] != meta['selected']:
        raise ValueError('Audit count does not match selected count')
    lines = [
        '# 旧候选规则命中贡献审计', '',
        f"冻结审计扫描 {meta['scanned']:,} 条、保留 {meta['selected']:,} 条（{meta['selected']/meta['scanned']:.2%}）。",
        '四条默认正则在 subject/body/files 中命中任意一条即保留；下表中的“独中”只说明',
        '其他三条规则未命中，**不表示提交与研究目标无关**。路径正则原来也会搜索 body。', '',
        '| 旧规则 | 命中条数（可重叠） | 仅此规则命中 |',
        '|---|---:|---:|',
    ]
    for i, name in enumerate(NAMES):
        lines.append(f"| {name} | {counts[f'hit_{i}']:,} | {counts[f'alone_{i}']:,} |")
    lines.extend(['', '仅规则命中的字段分布：', '', '| 旧规则 | 字段组合 | 条数 |', '|---|---|---:|'])
    for name in NAMES:
        for fields, total in sorted(alone_fields[name].items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f'| {name} | {fields} | {total:,} |')
    lines.extend(['',
                  '这是条件收紧前的命中结构审计，不能从只有入选项的审计文件直接计算漏检率。',
                  '后续以组合信号分层和低层/原未入选对照抽样检查，不把单一信号自动作为排除依据。', ''])
    return '\n'.join(lines)


if __name__ == '__main__':
    OUT.write_text(summarize(AUDIT), encoding='utf-8')
    print(OUT)
