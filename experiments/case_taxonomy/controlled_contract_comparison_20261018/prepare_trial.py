"""Identical source-only prompts; old artifacts and answers remain untouched."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
OUTER = INNER.parent
SOURCE = 'experiments/case_taxonomy/aligned_contract_candidates_20261017/documents.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, text):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)


def main():
    manifest_path = HERE / 'packet_manifest.json'
    if manifest_path.exists():
        raise RuntimeError('preserve first prompt preparation')
    raw = (INNER / SOURCE).read_bytes()
    packet = json.loads(raw)
    assert len(packet['documents']) == 14
    assert {d['profile'] for d in packet['documents']} == {'old_s390', 'old_x86'}
    for row in packet['input_manifest']:
        assert sha((INNER/row['path']).read_bytes()) == row['sha256']
    schema = json.loads((HERE.parent/'aligned_contract_candidates_20261017/packet_schema.json').read_text())['output']
    schema['requirements'][0]['basis'] = 'hypothesis'
    schema['architecture_paths'][0]['profile'] = 'old_s390'
    schema['architecture_paths'][0]['assessment'] = 'insufficient'
    schema['local_checks'][0]['profile'] = 'old_s390'
    schema['local_checks'][0]['expected'] = 'before'
    schema['recommended_checks'][0]['status'] = 'insufficient'
    for group in ['requirements', 'architecture_paths', 'local_checks', 'recommended_checks']:
        for item in schema[group]:
            item['evidence'] = [{'document': 'D01', 'start_line': 1, 'end_line': 1}]
    description = {
        'schema': 'n25_contract_candidates_v1',
        'allowed_profiles': ['old_s390', 'old_x86'],
        'allowed_document_ids': [d['id'] for d in packet['documents']],
        'evidence_exact_keys': ['document', 'start_line', 'end_line'],
        'evidence_rules': 'Each evidence object uses integer, non-bool, inclusive local document coordinates: 1 <= start_line <= end_line <= document lines, end_line-start_line+1 <= 24. No lines string; no original C line numbers.',
        'profile_rules': 'Use exactly the actual document profile old_s390 or old_x86. A path/local check must cite that same profile. These are configured material identities, not proof of a successful run.',
        'bounds': {'requirements': 3, 'architecture_paths': 6, 'local_checks': 6, 'recommended_checks': 3},
        'basis_values': ['consumer_precondition_inference', 'external_norm_needed', 'hypothesis'],
        'assessment_values': ['conditional_mismatch', 'conditional_satisfaction', 'insufficient', 'not_applicable'],
        'local_check_rules': 'Same complete configured_function document only. Exact function name. first/second each need callee and local integer line; optional column. expected is before or after. Only independent call-shaped statements supported; no if-condition, assignment RHS or declaration. Unsupported/unknown or no useful local facts: leave local_checks empty. No control-flow/effect proof follows.',
        'output_field_shape_only': schema,
        'example_warning': 'This is field syntax, not a claim or reference. Replace every example statement, callee, function and evidence with your own source-grounded candidate; do not copy the D01:1 example blindly. No supplied oracle or desired predicate.'
    }
    description_text = json.dumps(description, ensure_ascii=False, indent=2)
    write_new(HERE/'output_description.json', description_text+'\n')
    blocks = []
    for doc in packet['documents']:
        header = {k:doc.get(k) for k in ['id','profile','kind','function','path','configuration_sha256','source_identity_note']}
        numbered = '\n'.join(f'{n} | {line}' for n,line in enumerate(doc['text'].splitlines(),1))
        blocks.append('### '+json.dumps(header,ensure_ascii=False)+'\n```c\n'+numbered+'\n```')
    source_text = '\n\n'.join(blocks)
    write_new(HERE/'source_block.md', source_text+'\n')
    instruction = '''请只依据下列同版本两架构的配置源码区域，推导公共消费者对架构所提供对象/信息的要求，并分析不同实现可能如何满足或错过这些要求。不使用工具，不补画未给出的调用体，不猜修复或运行结果。
请提出最多3项具体、可定位的条件要求，区分公共用途依据、待外部规范确认与假说；追踪提供对象、资格/条件、准备效果、共同消费与期限。按实际材料profile解释架构差异如何进入公共用途。要求是否必要、是否充分、适用与未知分开；不消费的路径与满足要求分开。不能把任何单个字段、日志文字或函数存在当作完整正确性的证明。
材料为已读开发案例的带观测预处理区域和配置摘录，保留了o->self等观测线索。这些线索不是实际观测值；没有提供真实事件记录、修复、旧模型回答、初筛标签或研究侧oracle。14份材料没有保证所有外链、对象身份、写入效果或运行期稳定性已经齐全。局部事实可以成立，同时完整机制仍不足；无证据勿补造。
输出一个JSON对象，顶层字段和引用格式严格按下面说明。中文正文，无字段长度压缩；可充分解释前提与未知。引用按本包编号文档的局部行号，每段最多24行，可多段。local_checks仅填写源码中受支持的独立调用位置；它可以描述有依据的用途期望，也可以描述观察到的词法顺序，但须在相关要求或limits说明期望与已发生事实的区别。不输出补丁。
'''
    prompt = instruction+'\n输出协议（示例只是字段形状）：\n'+description_text+'\n\n材料限制：'+json.dumps(packet['limits'],ensure_ascii=False)+'\n\n'+source_text+'\n'
    prompt_bytes = prompt.encode('utf-8')
    folders = []
    for name in ['X','Y']:
        folder = OUTER/'模型调用测试/2026-10-18'/('n28_repeat_'+name)
        if folder.exists():
            raise RuntimeError('preserve existing repeat folder '+name)
        folder.mkdir(parents=True)
        write_new(folder/'prompt.md', prompt)
        assert (folder/'prompt.md').read_bytes() == prompt_bytes
        folders.append({'repeat':name,'directory':folder.relative_to(OUTER).as_posix()})
    manifest = {'documents_path':SOURCE,'documents_sha256':sha(raw),
                'input_manifest':packet['input_manifest'],'prompt_sha256':sha(prompt_bytes),
                'prompt_utf8_bytes':len(prompt_bytes),'source_block_sha256':sha(source_text.encode('utf-8')),
                'output_description_sha256':sha((HERE/'output_description.json').read_bytes()),
                'source_document_count':len(packet['documents']), 'repeats':folders,
                'limits':'Identical prompt and original document bytes. No old final/oracle/runtime results supplied. Development instrumentation clues retained.'}
    write_new(manifest_path,json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    before = {n:sha((OUTER/n).read_bytes()) for n in ['当前代办.md','当前研究方向与进展.md']}
    write_new(HERE/'notes_before.json',json.dumps(before,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'prepared','repeats':2,'identical_prompt_sha256':sha(prompt_bytes),'bytes':len(prompt_bytes),'documents':14}))


if __name__ == '__main__':
    main()
