from pathlib import Path
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
OUTER = INNER.parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    module = HERE.parent / 'candidate_packet_protocol_20261017/schema_instruction.py'
    spec = importlib.util.spec_from_file_location('n220_unchanged_schema', module)
    schema = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(schema)
    adapter_path = HERE.parent / 'new_input_contract_trial_20261017/run_raw_candidate_checks.py'
    spec = importlib.util.spec_from_file_location('n220_raw_binding', adapter_path)
    raw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(raw)
    raw.verify_baseline()
    artifacts = {}
    sources = []
    for filename in ['initial_sources.json', 'supplement_sources.json']:
        path = HERE / filename
        relative = str(path.relative_to(INNER)).replace('\\', '/')
        artifacts[relative] = path.read_bytes()
        data = json.loads(artifacts[relative])
        assert all(row['status'] == 'collected' for row in data['documents'])
        for index, row in enumerate(data['documents']):
            sources.append((relative, index, row))
    packets = []
    for case in ['P01', 'P02']:
        selected = [(path, index, row) for path, index, row in sources if row['case'] == case]
        assert len(selected) == 8
        parent = selected[0][2]['revision']
        documents = []
        for number, (path, index, row) in enumerate(selected, 1):
            assert row['revision'] == parent
            documents.append({'id': f'D{number:02d}', 'case': case, 'parent': parent,
                              'revision': parent, 'profile': case + '_parent', 'kind': 'raw_source_file',
                              'function': None, 'path': row['path'], 'text': row['text'],
                              'file_sha256': row['sha256'], 'text_sha256': row['sha256'],
                              'configuration_sha256': None, 'image_sha256': None, 'preprocessed_sha256': None,
                              'source_binding': {'artifact': path, 'artifact_sha256': hashlib.sha256(artifacts[path]).hexdigest(),
                                                 'json_pointer': f'/documents/{index}/text'}})
        packet = {'schema': schema.SCHEMA, 'case_parents': {case: parent}, 'documents': documents,
                  'input_manifest': [{'path': path, 'sha256': hashlib.sha256(data).hexdigest()}
                                     for path, data in artifacts.items()],
                  'limits': ['Original parent files, not effective config/runtime or normal/defect ground truth',
                             'Manual material choice; no repair/title/screening verdict/expected predicate supplied',
                             'Shared background exposure and actual target-position/family eligibility separate']}
        bindings = raw.bind_documents(packet, artifacts)
        assert sum(row['status'] == 'source_bound' for row in bindings.values()) == 8
        path = HERE / ('documents_' + case + '.json')
        with path.open('x', encoding='utf-8') as f:
            json.dump(packet, f, ensure_ascii=False, indent=2)
            f.write('\n')
        instructions = '''请只根据这份父版材料，研究CPU身份/集合接口能否满足公共使用。
研究关注已经固定：区分硬件与逻辑编号命名空间、显式映射、选择范围/数量限制，以及准备和实际使用阶段。不同架构可以合法映射到不同逻辑编号，不能仅用原始值相等、集合大小相同、所有present均possible或“调用过准备函数”作为统一真值。
这是方法迁移假说，不是对本材料已存在错误、某一映射或某条谓词成立的暗示。材料没有正常/缺陷标签；不要推断后续提交、补丁或研究者期待。版本、配置、用途、政策和实际路径缺证时保留insufficient。
提出至多三项有依据的条件要求，连接提供者/映射/选择、公共消费者及阶段，明确已有文档或消费者推导与假说。不为了凑满三项提出臆测新缺陷。只报告材料能支持的事实和需要补证的地方。
原文包含未预处理分支；材料组名不是实际架构/配置证明。引文坐标使用每份完整源文件的原始1起始行号，单段不超过24行。局部顺序只是词法线索，不能替代效果、对象、实际路径或运行正确性。
请严格按随后格式要求输出一个完整JSON对象，无额外散文。没有依据的组可以为空，字段不要用CASE_parent占位。\n'''
        text = instructions + schema.render_schema_instructions(packet) + '\n\n父版原始材料如下。行号前缀不属于源码。\n'
        for document in documents:
            text += '\nSOURCE ' + json.dumps({k: document[k] for k in ['id', 'profile', 'path', 'revision', 'text_sha256']}, ensure_ascii=False) + '\n'
            text += '\n'.join(f'{number}: {line}' for number, line in enumerate(document['text'].splitlines(), 1)) + '\n'
        assert len(text.encode('utf-8')) <= 600000
        folder = OUTER / '模型调用测试/2026-10-22' / ('n220_parent_' + case)
        folder.mkdir(parents=True, exist_ok=False)
        (folder / 'prompt.md').write_bytes(text.encode('utf-8'))
        packets.append({'case': case, 'parent': parent, 'documents_sha256': sha(path),
                        'prompt_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                        'prompt_utf8_bytes': len(text.encode('utf-8')), 'documents_bound': 8,
                        'protocol_sha256': sha(HERE / 'protocol_pre.json'),
                        'method_versions_sha256': sha(HERE / 'method_versions.json'),
                        'model_directory': str(folder.relative_to(OUTER)).replace('\\', '/')})
    manifest = {'packets': packets, 'artifacts': {path: hashlib.sha256(data).hexdigest()
                                                for path, data in artifacts.items()},
                'source_schema_unchanged_sha256': sha(module)}
    with (HERE / 'packet_manifest.json').open('x', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'status': 'two_parent_inputs_bound', 'packets':
                      [{k: row[k] for k in ['case', 'documents_bound', 'prompt_utf8_bytes']} for row in packets]}))


if __name__ == '__main__':
    main()
