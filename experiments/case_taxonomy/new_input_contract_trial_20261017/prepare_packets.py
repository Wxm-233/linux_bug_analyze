"""Parent-only raw-source packets; material groups are not runtime profiles."""
from pathlib import Path
import hashlib
import json

STAGE = Path(__file__).resolve().parent
INNER = STAGE.parents[2]
OUTER = INNER.parent

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def main():
    qualification = json.loads((STAGE / 'parent_qualification.json').read_text(encoding='utf-8'))
    protocol = json.loads((STAGE / 'protocol_pre.json').read_text(encoding='utf-8'))
    baseline = STAGE / 'adapter_baseline.json'
    schema = json.loads((STAGE.parent / 'aligned_contract_candidates_20261017/packet_schema.json').read_text())['output']
    schema['architecture_paths'][0]['profile'] = 'CASE_parent (material identity, not an architecture/configuration)'
    schema['local_checks'][0]['profile'] = 'CASE_parent'
    sources, manifests = [], []
    for name in ['initial_sources.json', 'supplement_sources.json']:
        path = STAGE / name
        if not path.exists():
            continue
        raw = path.read_bytes()
        artifact = path.relative_to(INNER).as_posix()
        data = json.loads(raw.decode('utf-8-sig'))
        manifests.append({'path': artifact, 'sha256': sha(raw)})
        for i, row in enumerate(data['documents']):
            if row['status'] == 'collected':
                sources.append((row, {'artifact': artifact, 'artifact_sha256': sha(raw),
                                      'json_pointer': '/documents/' + str(i) + '/text'}))
    packets = []
    for case in qualification['cases']:
        if case['model_trial'] != 'eligible':
            packets.append({'case': case['case'], 'status': 'skipped_inadequate_parent_material',
                            'reason': case['reason']})
            continue
        folder = OUTER / '模型调用测试/2026-10-17' / ('n26_parent_' + case['case'])
        if folder.exists():
            raise RuntimeError('preserve first packet: ' + case['case'])
        documents = []
        seen = set()
        for row, binding in sources:
            if row['case'] != case['case']:
                continue
            identity = row['revision'], row['path']
            if identity in seen:
                raise RuntimeError('duplicate parent path')
            seen.add(identity)
            assert row['revision'] == case['parent'] and sha(row['text'].encode()) == row['sha256']
            documents.append({'id': f'D{len(documents)+1:02d}', 'case': case['case'],
                              'profile': case['case'] + '_parent', 'parent': case['parent'],
                              'revision': row['revision'], 'path': row['path'],
                              'kind': 'raw_source_file', 'function': None,
                              'text': row['text'], 'file_sha256': row['sha256'],
                              'text_sha256': row['sha256'], 'configuration_sha256': None,
                              'image_sha256': None, 'preprocessed_sha256': None,
                              'source_binding': binding})
        if not 1 <= len(documents) <= 8:
            raise RuntimeError('invalid file count')
        packet = {'schema': 'n25_contract_candidates_v1',
                  'case_parents': {case['case']: case['parent']},
                  'documents': documents, 'input_manifest': manifests,
                  'limits': ['Original unpreprocessed parent files, no instrumented observations supplied',
                             'Material group profile is a case/parent identifier, not a legal architecture/configuration',
                             'No generated config, compiler expansion, build, run, outcome or repair evidence',
                             'Function/file selection is researcher input; target-source and family independence remains to adjudicate']}
        instruction = '''请只依据下列精确历史父版完整文件，分析架构提供的信息/状态与公共代码实际用途之间的隐含要求。没有工具，不查外部资料，不猜后续修复。
研究问题是：架构差异从哪里来、怎样经过接口/对象进入公共消费、为何一种实现可能满足要求而另一种暴露问题。不能只按架构名字判断，也不能把多数实现或现有告警当成唯一规范。缺少关键实现就明确不足。
这是原始、未经配置选择和宏展开的源码。保留所有条件编译；有Kconfig声明也不代表某次实际选择。没有运行、真实硬件或合法配置对照。profile字段仅为本次case_parent材料身份；architecture_paths仍使用该材料组ID，在文字中区分实际架构/分支，不得将其声称为运行profile。
提出最多3项具体要求，分清公共用途推导、外部规范待补和假说。逐条追踪提供对象、目标/值域、准备资格、实际效果、消费时点、配置分支和接口依据；可属于首次使用前准备，也可属于其他机制，不能强套。是否调用、是否online或最终输出正确，都不等于对应对象及时满足要求。
给出有前提的检查候选和使用位置，区分必要/充分。不要推断真实运行结果或确认新问题，也不要因没有发现就称正常。
输出一个JSON对象，采用下方schema，中文正文；requirements最多3、architecture_paths最多6、local_checks最多6。所有evidence按完整文件文档ID和原始行号，每段最多24行，可以多段。不要引用不存在的文档或把同名变量当同一实际对象。
local_checks仅限同一完整函数中明确独立调用语句的词法位置。原文件行号用于first/second.line，function写准确名称；不包含完整唯一函数、条件编译/复杂语法未受支持时可留空。词法顺序不证明控制流、可达性、原语效果、准备完成或配置合法。不能删除分支或用占位代码求通过。所有语义要求都仍是候选，不输出补丁。
材料未提供修复、初筛标签、旧结论或预期谓词；请以原文为依据，并清楚列出未知与下一步最小验证。
'''
        parts = [instruction, '输出schema占位示例（不是事实）：\n' + json.dumps(schema, ensure_ascii=False),
                 '材料限制：' + json.dumps(packet['limits'], ensure_ascii=False)]
        for doc in documents:
            parts.append('\n### ' + json.dumps({k: doc[k] for k in ['id', 'profile', 'kind', 'path', 'revision']}, ensure_ascii=False) +
                         '\n```c\n' + '\n'.join(f'{i} | {line}' for i, line in enumerate(doc['text'].splitlines(), 1)) + '\n```')
        prompt = '\n\n'.join(parts)
        if len(prompt.encode()) > protocol['model']['maximum_input_utf8_bytes_per_task']:
            packets.append({'case': case['case'], 'status': 'skipped_input_budget', 'bytes': len(prompt.encode())})
            continue
        packet_name = 'documents_' + case['case'] + '.json'
        packet_path = STAGE / packet_name
        assert not packet_path.exists()
        packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        folder.mkdir(parents=True)
        (folder / 'prompt.md').write_text(prompt, encoding='utf-8')
        material_plans = []
        for name in ['initial_material_plan.json', 'supplement_material_plan.json']:
            plan_path = STAGE / name
            if plan_path.exists():
                material_plans.append({'path': plan_path.relative_to(INNER).as_posix(),
                                       'sha256': sha(plan_path.read_bytes())})
        manifest = {'documents_sha256': sha(packet_path.read_bytes()),
                    'protocol_sha256': sha((STAGE / 'protocol_pre.json').read_bytes()),
                    'adapter_baseline_sha256': sha(baseline.read_bytes()),
                    'prompt_sha256': sha(prompt.encode()), 'prompt_utf8_bytes': len(prompt.encode()),
                    'case': case['case'], 'parent': case['parent'], 'input_manifest': manifests,
                    'selection_sha256': sha((STAGE / 'selection.json').read_bytes()),
                    'material_plans': material_plans,
                    'model_directory': folder.relative_to(OUTER).as_posix()}
        (STAGE / ('packet_manifest_' + case['case'] + '.json')).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        packets.append({'case': case['case'], 'status': 'prepared', 'documents': len(documents),
                        'directory': manifest['model_directory'], 'prompt_utf8_bytes': len(prompt.encode())})
    out = STAGE / 'model_packets.json'
    assert not out.exists()
    out.write_text(json.dumps({'packets': packets}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(packets))

if __name__ == '__main__':
    main()
