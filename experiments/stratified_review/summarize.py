"""Validate the frozen assistant source review and write a compact summary."""

from __future__ import annotations

import collections
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LABELS = {'related', 'unrelated', 'uncertain'}


def load_review() -> tuple[dict, list[dict]]:
    manifest = json.loads((ROOT / 'pilot_manifest.json').read_text(encoding='utf-8'))
    with (ROOT / 'review_notes.tsv').open(encoding='utf-8', newline='') as stream:
        notes = list(csv.DictReader(stream, delimiter='\t'))
    if len(manifest['samples']) != 100 or len(notes) != 100:
        raise ValueError('pilot must contain 100 samples and 100 reviews')
    if [int(row['index']) for row in notes] != list(range(1, 101)):
        raise ValueError('review indices must be exactly 1..100')
    if any(row['label'] not in LABELS or not row['reason'].strip() for row in notes):
        raise ValueError('invalid label or missing reason')
    rows = []
    for note, sample in zip(notes, manifest['samples']):
        rows.append({
            'index': int(note['index']), 'hash': sample['hash'],
            'stratum': sample['stratum'], 'label': note['label'],
            'reason': note['reason'], 'subject': sample['subject'],
        })
    return manifest, rows


def summary() -> str:
    manifest, rows = load_review()
    counts = collections.defaultdict(collections.Counter)
    for row in rows:
        counts[row['stratum']][row['label']] += 1
    lines = [
        '# 2026-09-23 静态三信号分层抽样复核', '',
        '此结果是助手阅读本地 Git 提交说明及补丁片段后的初步源码复核，',
        '不是领域专家金标准，也没有运行复现；`uncertain` 不按负例计算。',
        '本地材料包含完整提交说明、路径和最多 10,000 字符的补丁首尾；7 条补丁被截断，',
        '其中第 43 条初步判为相关，后续确认需回到完整补丁和调用链。', '',
        f"总体：旧审计扫描 {manifest['audit_summary']['scanned']:,} 条、保留 {manifest['audit_summary']['selected']:,} 条；",
        f"本次 WSL 重建日期窗口扫描 {manifest['wsl_scan_count']:,} 条，冻结旧候选中有 {len(manifest['selected_missing_from_wsl_date_window'])} 条不在该窗口。",
        '候选仍以旧审计列表为准；未入选对照来自本次 WSL 重扫，两个总体不完全相同。', '',
        '| 层 | 总量 | 抽样 | 初步相关 | 不相关 | 待定 |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for cell in ('high', 'medium', 'low', 'outside_defect', 'outside_other'):
        c = counts[cell]
        lines.append(f"| {cell} | {manifest['stratum_sizes'][cell]:,} | {sum(c.values())} | {c['related']} | {c['unrelated']} | {c['uncertain']} |")
    lines += [
        '',
        '分层是研究线索的排序，不是自动排除规则。各层采用固定种子、按 SHA-256 最小值抽样，',
        '且主动排除了本地已见哈希；各层抽样数不按总体比例分配，因此表中的相关比例',
        '不能推断全量相关率、召回率、漏检率或模型准确率。', '',
        '## 值得继续核查的线索', '',
        '- 高层：S0ix/S3 睡眠结果、64 位符号扩展、SWIOTLB 对齐、arm32 字节 xchg、兼容系统调用、s390 PSW、IOMMU fwspec、32 位构建与页表能力。',
        '- 中层：PowerPC 文本区与 KASAN、KVM/VMX 条件、f2fs arm32 对齐、LoongArch BPF JIT。',
        '- 低层：PCI ACS 在 OF 平台上的请求与启用顺序，提示不能把低层全丢弃。',
        '- 未入选对照：AMD 无显示芯片的能力报告、WiFi 7 描述格式差异仍待确认是否属于当前研究范围。', '',
        '## 静态规则暴露的问题', '',
        '- 位宽词可能指设备参数而非 CPU 位宽；高层出现 32 个音频时隙以及提交历史里的 64-bit 字段。',
        '- 架构路径与缺陷词会吸收 DTS/schema、文档和自测修补；单一层级不能当作相关性判断。',
        '- 真实跨层问题可能没有明显架构词；需要识别接口提供者、调用者及能力/生命周期条件。',
        '- 下一轮应先请领域人员裁定待定项与研究边界，然后再用独立样本比较调整前后的排序效果。',
        '- 现有 DeepSeek-V4.1-Flash `screen_fast.py` 短判定流程未改，当前试验没有外部模型调用。',
        '',
        '## 逐条复核', '',
        '| # | 层 | 结论 | 提交 | 依据 |',
        '|---:|---|---|---|---|',
    ]
    for row in rows:
        subject = row['subject'].replace('|', '\\|')
        reason = row['reason'].replace('|', '\\|')
        lines.append(f"| {row['index']} | {row['stratum']} | {row['label']} | `{row['hash'][:12]}` {subject} | {reason} |")
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    path = ROOT / 'RESULTS.md'
    path.write_text(summary(), encoding='utf-8')
    print(path)
