"""Assemble reviewed provenance conclusions from prior JSON/MD records only."""
from pathlib import Path
import hashlib
import json

OUT = Path(__file__).resolve().parent
STAGE = OUT.parent
BASE = STAGE.parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def quote(path, line):
    p = BASE / path
    text = p.read_text(encoding='utf-8').splitlines()[line - 1]
    return {'path': path, 'sha256': sha(p), 'line': line, 'text': text, 'kind': 'prior_source_review_or_development_record'}

def main():
    scope_path = OUT / 'scope_search.json'
    scope = json.loads(scope_path.read_text(encoding='utf-8'))
    pool_path = STAGE / 'metadata_pool.json'
    pool = json.loads(pool_path.read_text(encoding='utf-8'))['records']
    assert sha(pool_path) == scope['metadata_pool_sha256']
    manifest_path = BASE / 'cross_subsystem_facts_20261003/ocfs2/source_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    oc_provenance = []
    for index, entry in enumerate(manifest):
        if entry['revision'].endswith('^') and entry['path'] in ('fs/ocfs2/inode.c', 'fs/ocfs2/ocfs2_fs.h'):
            oc_provenance.append({'record_path': manifest_path.relative_to(BASE).as_posix(), 'record_sha256': sha(manifest_path), 'json_pointer': '/' + str(index), 'source_identity_as_recorded': entry})
    assert len(oc_provenance) == 2
    result_path = BASE / 'bcachefs_auto_layout_result.json'
    result = json.loads(result_path.read_text(encoding='utf-8'))
    assert result['source']['fixed_revision'].startswith('3f3ae125')
    bc_provenance = {'record_path': result_path.relative_to(BASE).as_posix(), 'record_sha256': sha(result_path), 'json_pointer': '/source', 'source_identity_as_recorded': result['source'], 'extraction_result_summary': {'candidate_records': len(result['candidates']), 'method': result['method'], 'verdict_scope': result['verdict_scope']}}
    actual = {
        'c9dff86eb78a4b6b02b1e407993c946ccaf9bfb4': [quote('representation_holdout_review.md', 20), quote('cross_subsystem_facts_20261003/ocfs2/review.md', 3), quote('cross_subsystem_facts_20261003/ocfs2/review.md', 5), quote('cross_subsystem_facts_20261003/ocfs2/review.md', 9), *oc_provenance],
        '3f3ae1250e739fb446639efad0ba916ba0a012f0': [quote('bcachefs_auto_layout_review.md', 3), quote('bcachefs_auto_layout_review.md', 17), bc_provenance],
    }
    metadata_names = {'2026-09-28_holdout_metadata_pre.json', 'bcachefs_auto_holdout_protocol_pre.md', 'bounded_interface_holdout_20261003/pool_metadata.json', 'next_stage_selection_pre.json', 'representation_single_holdout_protocol_pre.json', 'scalar_read_holdout_20261008/metadata_snapshot.json'}
    records = []
    for r in pool:
        hits = [h for h in scope['matching_references'] if h['commit'] == r['commit']]
        evidence = actual.get(r['commit'], [])
        meta = [h for h in hits if h['path'] in metadata_names]
        record = {'pool_order': r['pool_order'], 'representation_order': r['representation_order'], 'commit': r['commit'], 'subject_metadata_only': r['subject'], 'status': 'prior_source_review_and_development_exposure' if evidence else ('metadata_only' if hits else 'no_evidence_in_defined_scope'), 'source_exposure_confirmed': bool(evidence), 'actual_source_evidence': evidence, 'matching_reference_count': len(hits), 'matching_reference_paths': sorted({h['path'] for h in hits}), 'metadata_or_preselection_references_not_used_as_exposure_proof': meta, 'filename_prefix_matches': [f['path'] for f in scope['searched_files'] if r['commit'][:8] in f['path']], 'conclusion_scope': 'bounded prior local study and rule-development records only; no global blindness claim'}
        records.append(record)
    assert sum(r['source_exposure_confirmed'] for r in records) == 2
    audit = {'schema_version': 1, 'date': '2026-10-09', 'auditor': '/root/encoded_count_exposure', 'metadata_pool_sha256': sha(pool_path), 'scope_search_sha256': sha(scope_path), 'pool_count': 16, 'searched_file_count': len(scope['searched_files']), 'searched_files': scope['searched_files'], 'search_method': {'scope': scope['scope'], 'enumeration_argv': scope['enumeration_argv'], 'search_argv': scope['search_argv'], 'cwd': scope['cwd'], 'content_match_count': len(scope['matching_references']), 'minimum_fix_prefix_length': 8, 'filename_prefix_check': 'Also checked the enumerated record filenames; no additional prefix matches.'}, 'records': records, 'counts': {'prior_source_review_and_development_exposure': 2, 'metadata_only': 0, 'no_evidence_in_defined_scope': 14}, 'new_source_or_patch_read': False, 'actual_saved_c_or_header_bytes_read': False, 'git_commands': 0, 'network_calls': 0, 'project_model_calls': 0, 'detector_or_gate_runs': 0, 'candidate_selection_made': False, 'limitations': ['Search covers the recorded prior case_taxonomy MD/JSON/TSV scope only. No matching reference is not global blindness or an assertion that a person or model never read the patch.', 'Historical fixed-500 short judgments may already have read related materials; this audit addresses only local study and rule-development exposure.', 'Title, metadata, preselection and protocol references alone do not establish source exposure. A previous selection becomes exposed only if a source review/result or extraction provenance corroborates actual use.', 'Prior review statements and source/result provenance were read; the saved C/H source bytes and any raw patch text were not opened or independently rehashed here. Recorded source hashes identify the former extraction; they are not a new verification of historical source semantics.', 'Initial exploratory rg used the repository-qualified search root and returned this new stage metadata as well; those already-known metadata mentions are excluded from the definitive saved scope snapshot and all exposure conclusions.', 'Only full or at least 8-character fix SHA and record filenames were searched. Untagged notes, differently abbreviated identifiers, renamed paths, external conversations, analysis_out model responses or records outside this scope can be missed.', 'This audit does not rank candidates, interpret their bug relevance, choose a sample, run old rules/gates or modify any previous stage.']}
    target = OUT / 'exposure_audit.json'
    target.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    rows = []
    for r in records:
        status = '已读源码并参与开发' if r['source_exposure_confirmed'] else '定义范围内无证据'
        refs = '旧 inode.c/格式字段审阅；开发回放；父版来源清单' if r['commit'].startswith('c9dff86e') else ('旧/新格式头及布局提取结果；明确开发说明' if r['commit'].startswith('3f3ae125') else '未匹配至少8位fix标识或记录文件名')
        rows.append(f"| {r['pool_order']} | `{r['commit'][:12]}` | {status} | {refs} |")
    md = '# 固定16项的独立本地曝光审计\n\n日期2026-10-09。本审计仅检查旧研究记录中的源码审阅/规则开发曝光，不判断相关性、不选样。固定池来自 representation 第17–32项；元数据池 SHA-256 `' + sha(pool_path) + '`。\n\n以 `rg --files --hidden --no-ignore` 枚举旧 case_taxonomy 所有 `.md/.json/.tsv`，排除本轮完整目录；以大小写不敏感8位fix前缀联合表达式搜索。共搜索 ' + str(len(scope['searched_files'])) + ' 份记录，得到502条引用；另外检查记录文件名，无额外SHA前缀线索。完整文件清单/哈希与原命令在 `scope_search.json`，逐项结论在 `exposure_audit.json`。标题/metadata/preselection命中不自动升级为源码曝光。\n\n| 池顺序 | fix | 结论 | 支持 |\n|---:|---|---|---|\n' + '\n'.join(rows) + '\n\n实际曝光两项：\n\n- `c9dff86e`：`representation_holdout_review.md:20` 记录父版 `inode.c:203–218` 与 `ocfs2_fs.h:672–693` 的具体字段、消费者和补丁后解释。`cross_subsystem_facts_20261003/ocfs2/review.md:3,5,9` 明确“以前读过的开发接口”、两版本身份和实际读站点；其 `source_manifest.json` 保存 parent `inode.c`、`ocfs2_fs.h` 的路径/blob/SHA。该证据超过最初选样标题，因此 source_exposure_confirmed=true。\n- `3f3ae125`：`bcachefs_auto_layout_review.md:3` 明确“已经阅读过”“规则开发”，`:17` 将父版、fix和 `fs/bcachefs/bcachefs_format.h` 绑定到已执行的提取结果；`bcachefs_auto_layout_result.json:/source` 保存两版SHA及源码身份，结果含5个开发嵌入点。不是凭标题或预选池判污染。\n\n其余14项在本范围未找到匹配依据，source_exposure_confirmed=false，不能称为全局盲样本。特别是旧500短判定可能已经读过材料，当前只界定本地研究与规则开发记录；SHA缺失不证明从未读过。初次探索搜索曾返回本轮元数据，这些已知元数据在最终范围快照中明确排除。\n\n本审计没有打开C/H源码原字节或raw patch，仅阅读既存记录与来源字段；没有重新计算旧源码身份或复核旧语义。Git、联网、模型、旧检测器/来源门控、候选选择均为0；旧阶段未修改。机器记录保留每个来源摘录行号、文件指纹和JSON指针。审计JSON SHA-256 `' + sha(target) + '`。\n'
    (OUT / 'review.md').write_text(md, encoding='utf-8')
    print(json.dumps({'exposure_audit_sha256': sha(target), 'review_sha256': sha(OUT/'review.md'), 'counts': audit['counts'], 'searched_file_count': len(scope['searched_files']), 'source_exposure_commits': sorted(actual)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
