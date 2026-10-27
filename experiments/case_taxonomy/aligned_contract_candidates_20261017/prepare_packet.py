"""Create a numbered source-only packet; no call, outcome, or repair lookup."""
from pathlib import Path
import hashlib
import json

STAGE = Path(__file__).resolve().parent
INNER = STAGE.parents[2]
OUTER = INNER.parent
BASE = STAGE.parent
ALIGNED = BASE / 'runtime_evidence_alignment_20261017'
PROTOCOL = json.loads((STAGE / 'protocol_pre.json').read_text(encoding='utf-8'))
FOLDER = OUTER / '模型调用测试/2026-10-17/n25_aligned_contract'

def sha(payload):
    return hashlib.sha256(payload).hexdigest()

def rel(path):
    return path.relative_to(INNER).as_posix()

def main():
    if (STAGE / 'documents.json').exists() or FOLDER.exists():
        raise RuntimeError('preserve original packet; no overwrite')
    documents, manifest = [], []
    for name in PROTOCOL['inputs']['regions']:
        path = ALIGNED / name
        raw = path.read_bytes()
        data = json.loads(raw.decode('utf-8-sig'))
        manifest.append({'path': rel(path), 'sha256': sha(raw)})
        for function, region in sorted(data['functions'].items()):
            text = region['text']
            if sha(text.encode('utf-8')) != region['sha256']:
                raise RuntimeError('region text hash mismatch')
            documents.append({'id': f'D{len(documents)+1:02d}', 'profile': data['profile'],
                              'kind': 'configured_function', 'function': function,
                              'path': region['name_location']['path'], 'text': text,
                              'text_sha256': region['sha256'], 'revision': data['revision'],
                              'configuration_sha256': data['configuration_sha256'],
                              'image_sha256': data['image_sha256'],
                              'preprocessed_sha256': data['preprocessed_sha256'],
                              'source_binding': {'artifact': rel(path), 'artifact_sha256': sha(raw),
                                                 'json_pointer': '/functions/' + function + '/text'},
                              'source_identity_note': 'instrumented current preprocessing; local packet lines are not original C lines',
                              'supplementary_region': 'supplementary' in name})
    if len(documents) != 12:
        raise RuntimeError('unexpected region count')
    keys = PROTOCOL['inputs']['configuration_keys']
    for relative in PROTOCOL['inputs']['configuration_files']:
        path = BASE / relative
        raw = path.read_bytes()
        manifest.append({'path': rel(path), 'sha256': sha(raw)})
        profile = path.parent.name
        bindings = {d['configuration_sha256'] for d in documents if d['profile'] == profile}
        if bindings != {sha(raw)}:
            raise RuntimeError('configuration digest mismatch')
        selected = [(i, line) for i, line in enumerate(raw.decode('utf-8').splitlines(), 1)
                    if any(line.startswith(k + '=') or line == '# ' + k + ' is not set' for k in keys)]
        text = '\n'.join(line for _, line in selected)
        documents.append({'id': f'D{len(documents)+1:02d}', 'profile': profile,
                          'kind': 'selected_config_facts', 'function': None,
                          'path': rel(path), 'text': text, 'text_sha256': sha(text.encode()),
                          'configuration_sha256': sha(raw),
                          'source_binding': {'artifact': rel(path), 'artifact_sha256': sha(raw),
                                             'projection': 'selected_lines', 'source_lines': [i for i, _ in selected]},
                          'source_identity_note': 'only selected explicit config records; missing keys are unknown'})
    packet = {'schema': 'n25_contract_candidates_v1', 'documents': documents,
              'input_manifest': manifest,
              'limits': ['Known-case development; not independent or blinded',
                         'Instrumented source is preserved; probe reads are not original content-use events',
                         'Current preprocessing is not an exact historical compiler/header replay',
                         'No old runtime results, repair, manual provider feature values, or source oracle included',
                         'No complete external notify-to-public-callback chain is supplied; missing evidence remains unknown']}
    instruction = '''请基于下列材料，研究Linux中架构提供的状态与公共代码使用要求之间的隐含契约。只依据提供源码，不猜测后续修复，不把多数架构的写法当规范。
材料是同一历史版本的两种架构、各自实际构建配置下的函数区域，不是完整内核；包含为旧实验添加的观测代码。保留了观测源码，观测读/打印/命名不能当作真实准备完成或故障真值，也不能替代原公共消费者的内容读取。没有工具，不查其他文件。
目标是提出可审查的检查候选，而不是只描述代码错误：架构差异从哪里产生，经过什么对象/接口进入公共消费，在什么条件下一条架构路径满足要求而另一条可能不满足。不要要求不同架构的原始输出或掩码逐字相同。
先依据公共操作用途提出最多3项具体要求，并区分消费前提推导、外部规范待补与假说；不要将现有代码或当前告警等同于完备规范。逐架构追踪提供对象、准备资格、准备效果与使用期限；调用出现在前，不等于callee已经准备好对应对象。条件、循环覆盖、原语效果、对象身份、外部调用链或写后稳定性缺失时，明确保留不足，不为给出肯定结果补前提。
区分取指针、探针读取、原内容遍历/操作及事后状态。给出最小检查谓词及适用位置，说明必要条件与充分条件的界限。可描述限定路径的条件式失配，但不能报告新确认缺陷或真实运行结果。
输出一个合法JSON对象，遵守下方schema，正文用中文。requirements最多3项，architecture_paths最多6项，local_checks最多6项。local_checks只提出你确实能在同一文档看到的lexical_call_order；这只是源码词法位置关系，不能证明CFG、可达性或准备效果。没有合适项可留空。
所有evidence使用给定文档ID和文档内局部行号start_line/end_line，单段最多24行，可以用多段；不能使用原C行号代替局部行号。local_checks的first/second.line也是局部行号，可选column指该原样文本行的1-based列。其他规范、对象和guard关系用evidence支撑并明确未证明部分。无需抄长原文或输出补丁。
你看到的只有已读案例的开发材料，本轮不估计准确率或泛化。
'''
    schema = json.loads((STAGE / 'packet_schema.json').read_text(encoding='utf-8'))
    parts = [instruction, '输出schema示例（占位内容不是事实）：\n' + json.dumps(schema['output'], ensure_ascii=False),
             '本轮证据限制：' + json.dumps(packet['limits'], ensure_ascii=False)]
    for document in documents:
        metadata = {k: document[k] for k in ['id', 'profile', 'kind', 'function', 'path',
                                            'revision', 'configuration_sha256', 'source_identity_note'] if k in document}
        parts.append('\n### ' + json.dumps(metadata, ensure_ascii=False) + '\n```text\n' +
                     '\n'.join(f'{i:04d} | {line}' for i, line in enumerate(document['text'].splitlines(), 1)) + '\n```')
    prompt = '\n\n'.join(parts)
    if len(prompt.encode('utf-8')) > PROTOCOL['model']['maximum_input_utf8_bytes']:
        raise RuntimeError('input budget exceeded')
    FOLDER.mkdir(parents=True)
    (FOLDER / 'prompt.md').write_text(prompt, encoding='utf-8')
    (STAGE / 'documents.json').write_text(json.dumps(packet, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest = {'protocol_sha256': sha((STAGE / 'protocol_pre.json').read_bytes()),
                'schema_sha256': sha((STAGE / 'packet_schema.json').read_bytes()),
                'documents_sha256': sha((STAGE / 'documents.json').read_bytes()),
                'inputs': manifest, 'function_regions': 12, 'config_excerpts': 2,
                'prompt_sha256': sha(prompt.encode('utf-8')),
                'prompt_utf8_bytes': len(prompt.encode('utf-8')),
                'model_directory': FOLDER.relative_to(OUTER).as_posix(),
                'predetermined_requirements_or_outcomes': False,
                'source_selection': 'previous known-case regions, including disclosed supplemental region'}
    (STAGE / 'packet_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: manifest[k] for k in ['function_regions', 'config_excerpts', 'prompt_utf8_bytes', 'model_directory']}))

if __name__ == '__main__':
    main()
