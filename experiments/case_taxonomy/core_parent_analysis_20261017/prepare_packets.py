"""Prepare full exact-parent material, keeping repair/screening answers out of input."""
from pathlib import Path
import hashlib
import json

stage=Path(__file__).resolve().parent
inner=stage.parents[2]
outer=inner.parent
protocol=json.loads((stage/'protocol_pre.json').read_text(encoding='utf-8'))
documents=[]
for name in ['parent_files.json','supplement_files.json']:
    documents.extend(json.loads((stage/name).read_text(encoding='utf-8'))['documents'])

instruction='''你在审查某个历史Linux版本的完整父版源码。请只依据下面材料分析，不猜测后续修复，也没有已确认正例/正常标签。
研究目标是识别架构实现提供的信息/状态/分组，与公共Linux代码实际要求之间的条件化契约。重点解释：架构差异来自哪里、怎样进入公共消费、什么条件下A满足而B可能暴露。只出现架构名字或共享函数名不够；通用错误、同架构设备/配置变化要单列。
请用中文完成一次充分但有重点的源码分析：
1. 先描述材料确实覆盖的公共用途、架构提供者、实际消费者及相关调用/数据链；逐处引文件路径和行号。
2. 最多提出三项具体接口要求。每项分清：提供的保证、消费的要求、同一个对象/范围、配置/分支、实际内容读取时点、是否有中途修改/重算，以及接口依据。区分源码事实、推导、有待外部文档/构建/运行证明的部分。
3. 评估是否属于“首次使用前完成语义准备”。范围/包含关系等其他机制可以有用，但不要硬归入这个机制。无具体违约不代表同用途正常。
4. 对可能的跨架构暴露给出严格的条件式解释；不允许把两条不同用途或不适用路径的结果当架构正常对照。给出最小检查谓词及应该检查的位置；无法证明时明确缺什么，别补造结构字段/调用/运行事实。
5. 最后给出材料资格结论和下一步最小验证。完整回答即可，不需遵守脆弱JSON格式，不要输出补丁。
模型分析是候选，不是最终事实；材料未经实际Kconfig/预处理/运行验证。你没有工具，只能引用提供文件。行号是各文件完整原始父版的行号。
'''

records=[]
for case in protocol['cases']:
    folder=outer/'模型调用测试/2026-10-17'/('core_parent_'+case['id'])
    if (folder/'prompt.md').exists():
        raise SystemExit('Prompt already exists; preserve first material.')
    selected=[d for d in documents if d['case']==case['id'] and d['status']=='collected']
    assert len(selected)<=8
    parts=[instruction, '\n精确父版：'+case['parent']+'\n研究者选择完整文件；未自动证明这些文件足以覆盖全部相关实现。\n']
    for d in selected:
        raw=(stage/d['saved_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['sha256']
        lines=raw.decode('utf-8').splitlines()
        parts.append('\n### '+d['path']+'\n```c\n'+'\n'.join(str(i)+' | '+line for i,line in enumerate(lines,1))+'\n```\n')
    prompt='\n'.join(parts)
    assert len(prompt.encode('utf-8'))<=protocol['model']['max_input_utf8_bytes_per_case']
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'prompt.md').write_text(prompt,encoding='utf-8')
    records.append({'case':case['id'],'parent':case['parent'],'directory':str(folder.relative_to(outer)),'document_ids':[d['id'] for d in selected],'prompt_bytes':len(prompt.encode('utf-8')),'prompt_sha256':hashlib.sha256(prompt.encode('utf-8')).hexdigest(),'screening_or_child_material_included':False})
(stage/'model_packets.json').write_text(json.dumps({'packets':records,'manual_input':'research purpose and complete file selection; no prefilled roles, predicate or truth'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(records,ensure_ascii=False))
