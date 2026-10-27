"""Independent read-only replay of saved metadata; no Git or detector execution."""
from pathlib import Path
import hashlib
import json
import re

OUT = Path(__file__).resolve().parent
STAGE = OUT.parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    manifest_path = STAGE / 'parent_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    selection = json.loads((STAGE/'selection_pre.json').read_text(encoding='utf-8'))
    card = json.loads((STAGE/'support_card.json').read_text(encoding='utf-8'))
    checks = []
    inputs = []

    def check(name, passed, detail):
        assert passed, name
        checks.append({'name': name, 'passed': bool(passed), 'detail': detail})

    receipts = {}
    streams = {}
    for name in ('commit_object', 'path_names'):
        receipt_path = STAGE / 'raw' / (name + '.receipt.json')
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        check(name + '_exit_zero', receipt['returncode'] == 0, 'Saved native command receipt; no command rerun.')
        for stream in ('stdout', 'stderr'):
            path = Path(receipt[stream])
            check(name + '_' + stream + '_sha_matches', sha(path) == receipt[stream + '_sha256'], 'Read saved raw bytes for identity only; no stderr text interpreted.')
            streams[(name, stream)] = path.read_bytes()
            inputs.append({'path': str(path), 'sha256': sha(path)})
        inputs.append({'path': str(receipt_path), 'sha256': sha(receipt_path)})
        receipts[name] = receipt

    raw = streams[('commit_object', 'stdout')]
    prefix, delimiter, _ = raw.partition(b'\n\n')
    check('commit_header_separator_present', delimiter == b'\n\n', 'Only bytes before first blank line decoded; body is preserved but not decoded, displayed or interpreted.')
    parents = [value.decode('ascii') for value in re.findall(rb'^parent ([0-9a-f]{40})$', prefix, flags=re.M)]
    check('single_parent_matches_manifest', len(parents) == 1 and parents[0] == manifest['revision'], {'parents': parents})
    tree = re.findall(rb'^tree ([0-9a-f]{40})$', prefix, flags=re.M)
    check('one_tree_header', len(tree) == 1, 'Standard commit header shape checked without using author/date/message.')
    object_id = hashlib.sha1(b'commit ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
    check('raw_commit_object_identity', object_id == manifest['selected']['commit'], 'Git object identity recomputed locally from saved payload bytes; this is not a Git reexecution.')
    check('cat_file_receipt_fix_matches', receipts['commit_object']['argv'][-3:] == ['cat-file', '-p', manifest['selected']['commit']], 'Only the one selected commit was requested.')

    raw_names = streams[('path_names', 'stdout')]
    check('nul_path_list_terminated', raw_names.endswith(b'\0'), 'Saved diff-tree -z output uses NUL delimiters.')
    paths = [p.decode('utf-8') for p in raw_names[:-1].split(b'\0')]
    check('paths_match_manifest_and_fixed_no_c_stop', paths == manifest['changed_path_names'] == ['tools/testing/kunit/qemu_configs/powerpc.py'] and not any(p.endswith('.c') for p in paths) and manifest['stop_reason'] == 'no_changed_c_file', {'paths': paths, 'stop_reason': manifest['stop_reason']})
    expected_diff_argv = ['wsl', '-d', 'Ubuntu', '--', 'git', '-C', '/root/repos/linux', 'diff-tree', '--no-commit-id', '--name-only', '-r', '-z', manifest['selected']['commit']]
    check('diff_tree_path_only_receipt', receipts['path_names']['argv'] == expected_diff_argv, 'Path-list command includes no patch option.')
    check('exactly_two_saved_git_receipts', len(list((STAGE/'raw').glob('*.receipt.json'))) == 2 and manifest['git_commands'] == 2, 'Saved execution inventory consistent; no file export batch exists.')
    check('no_source_rule_gate_patch_outputs', manifest['file_requests'] == 0 and manifest['observations'] == [] and manifest['rule_runs'] == 0 and manifest['gate_runs'] == 0 and manifest['patch_exports'] == 0 and not (STAGE/'sources').exists(), 'No C/header input, old detector output, gate output or patch export in this stage.')
    check('support_card_is_input_not_available', card['verdict'] == 'input_not_available_no_changed_c' and card['actual_support_proven'] is False and card['counts_as_false_negative'] is False and card['counts_as_true_negative'] is False and card['source_file_requests'] == 0 and card['new_confirmed_cases'] == 0 and card['independent_positive_cases'] == 0, 'Absent preregistered C input is not a semantic nonrelevance judgment or true/false negative.')
    check('selected_parent_and_card_identity', card['selected_fix'] == manifest['selected']['commit'] and card['parent_revision'] == manifest['revision'] and card['changed_path_names'] == paths, 'Single frozen queue identity preserved across artifacts.')

    locks = []
    for name in ('freeze_metadata_pre.json', 'freeze_metadata_v2_pre.json'):
        path = STAGE/name
        data = json.loads(path.read_text(encoding='utf-8'))
        checked = []
        for entry in data['files']:
            target = Path(entry['path'])
            check(name + ':' + target.name, sha(target) == entry['sha256'], {'path': str(target), 'sha256': entry['sha256']})
            checked.append({'path': str(target), 'sha256': entry['sha256']})
        locks.append({'path': str(path), 'sha256': sha(path), 'checked_files': checked})
    check('old_rules_and_gate_unchanged', all(any(Path(e['path']).name == name for e in locks[0]['checked_files']) for name in ('encoded_length_check.py', 'source_gate.py', 'interface_fact_extractor.py', 'endian_consumer_single_revision.py')), 'All old rule/gate/dependency fingerprints in original and v2 locks match current bytes; no imports or rule runs.')

    review = {'review_passed': True, 'date': '2026-10-09', 'auditor': '/root/encoded_count_exposure', 'parent_manifest_sha256': sha(manifest_path), 'support_card_sha256': sha(STAGE/'support_card.json'), 'checks': checks, 'saved_input_fingerprints': inputs, 'frozen_input_checks': locks, 'parent_revision_from_header': parents[0], 'selected_fix_from_saved_object_identity': object_id, 'changed_path_names_from_saved_nul_output': paths, 'result': 'preregistered C input not available; no detector/gate support test performed', 'counts_as_false_negative': False, 'counts_as_true_negative': False, 'new_confirmed_cases': 0, 'independent_positive_cases': 0, 'audit_git_or_network_calls': 0, 'audit_rule_or_gate_runs': 0, 'audit_project_model_calls': 0, 'audit_compiler_runs': 0, 'audit_script_repair': 'One failed audit-only invocation decoded full header as ASCII; repaired to match parent/tree on bytes. Diagnostics saved in audit_support/audit_script_repair.md; no Git/selection/source/rule execution changed.', 'limits': ['Only saved commit header and NUL path-list metadata are semantically read. Commit body is not decoded/displayed/interpreted; raw object payload was hashed for identity.', 'No source or patch was retrieved or inspected and no second candidate was searched. Missing a changed C file is a protocol input limit, not overall nonrelevance.', 'No sensitivity, specificity, new confirmed defect or independent successful detection can be inferred from this input-unavailable stop.', 'Frozen file fingerprints establish byte identity only; they do not establish contract correctness, runtime reachability, actual ABI/build binding or generalization.', 'The existing parent Git receipts are checked without rerunning Git. This audit does not independently observe external command execution beyond the saved receipts/raw-object consistency.']}
    target = OUT/'review.json'
    target.write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    md = '# 固定父版支持停止点的独立核验\n\n日期2026-10-09。review_passed=true。父版清单SHA-256 `' + sha(manifest_path) + '`。\n\n直接从已保存 `commit_object.stdout.bin` 的第一空行之前解析头部，得到唯一parent `' + parents[0] + '`；完整原payload只作Git对象SHA1重算，结果等于预选fix `' + object_id + '`。没有解读提交body、标题以外的提交语义或修复内容。两份receipt退出0，stdout/stderr保存哈希一致。\n\n对保存 `diff-tree -z --name-only` 输出按NUL解析，仅有 `tools/testing/kunit/qemu_configs/powerpc.py`，与manifest完全一致；没有预定首个变更`.c`。因此按原协议停止，源码文件请求0、规则0、门控0、patch0，不查第二样本也不把Python配置改动自动解释为不相关。该停止不能计漏检或真阴性，更不能形成独立检测成功。\n\n原冻结与修订冻结中的每项字节指纹仍一致，包括旧encoded_length检查、来源门控及两项Python依赖；审计仅重算哈希，没有导入/执行。新修订保存原锁与修订脚本身份，选样不替换。新确认0、独立阳性0。\n\n审阅限于保存证据的内部一致性，不能独立证明外部命令执行以外事实、源码契约、配置、运行可达性或泛化能力。本审计Git/联网/规则/门控/模型/编译均0。JSON记录完整检查与输入身份，SHA-256 `' + sha(target) + '`。\n'
    (OUT/'review.md').write_text(md, encoding='utf-8')
    print(json.dumps({'review_passed': True, 'review_sha256': sha(target), 'md_sha256': sha(OUT/'review.md'), 'checks': len(checks), 'parent': parents[0], 'stop': manifest['stop_reason']}, ensure_ascii=False))

if __name__ == '__main__':
    main()
