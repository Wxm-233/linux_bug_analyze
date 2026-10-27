"""Summarize the bounded trial and update the current checkpoint, not old results."""
from pathlib import Path
import hashlib
import json
import re

stage=Path(__file__).resolve().parent
inner=stage.parents[2]
outer=inner.parent
result_path=stage/'results.json'
if result_path.exists():
    raise SystemExit('Stage already summarized; preserve original summary.')
components=json.loads((stage/'parent_component_results.json').read_text(encoding='utf-8'))
receipts=[]
shape=[]
for candidate in ['A','B']:
    folder=outer/'模型调用测试/2026-10-17'/('parent_qualification_'+candidate)
    receipt=json.loads((folder/'receipt.json').read_text(encoding='utf-8'))
    receipts.append({'candidate':candidate,**{k:receipt.get(k) for k in ['status','elapsed_seconds','final_characters','actual_models','response_models','stop_reasons','exit_code','visible_reported_tokens','conservative_accounted_tokens','usage_known','usage_uncertainty']}})
    raw=(folder/'final.md').read_text(encoding='utf-8')
    match=re.fullmatch(r'\s*```(?:json)?\s*\n([\s\S]*)\n```\s*',raw)
    answer=json.loads(match[1] if match else raw)
    for claim in answer['source_claims']:
        expected='first' if claim.get('kind')=='before' else 'branch' if claim.get('kind')=='requires_branch' else None
        shape.append({'candidate':candidate,'claim_id':claim.get('id'),'kind':claim.get('kind'),'required_root_field':expected,'root_field_present':expected in claim if expected else True,'field_nested_in_target':expected in claim.get('target',{}) if expected else False,'diagnostic_only':True,'original_not_rewritten':True})
result={'date':'2026-10-17','completed_scope':'two parent-only model tasks, frozen structural component trial, post-parent qualification','registered_candidates':2,'parent_files':10,'top_level_model_tasks':2,'model_delivery':receipts,'visible_reported_tokens':sum(r['visible_reported_tokens'] for r in receipts),'conservative_reservation':sum(r['conservative_accounted_tokens'] for r in receipts),'task_ceiling':1000000,'upstream_inference_count_known':False,'configuration_oracle_supplied':False,'function_location_requests':len(components['material_trials'])+len(components['collection_failures']),'complete_functions_collected':len(components['material_trials']),'locator_failures':len(components['collection_failures']),'local_supported_functions':sum(x['source_status']=='bounded_local_flow' for x in components['material_trials']),'local_insufficient_functions':sum(x['source_status']=='insufficient' for x in components['material_trials']),'forward_supported':sum(x['forward_status']=='supported_forward_structure' for x in components['material_trials']),'forward_partial':sum(x['forward_status']=='partial_forward_structure' for x in components['material_trials']),'forward_insufficient':sum(x['forward_status']=='insufficient' for x in components['material_trials']),'model_claim_checks':len(components['unchanged_model_claim_checks']),'model_claim_insufficient':sum(x['status']=='insufficient' for x in components['unchanged_model_claim_checks']),'claim_shape_diagnostics':shape,'new_qualified_core_positive':0,'new_qualified_same_use_normal':0,'new_confirmed_defects':0,'new_builds':0,'new_kernel_runs':0,'new_method_unit_test_runs':0,'r3_resumed':False,'whole_contract':'insufficient','candidate_dispositions':{'A':'read auxiliary vendor-preparation mechanism; core positive not established','B':'read interface-responsibility migration; same-use normal not established'},'reviews':{'parent_scope':'parent_scope_review.md','oracle_blind_to_model':'oracle_qualification_review.md','method':'independent arch_check_review limited pass; raw claims preserved'},'next':'N1.4f bounded input-completeness and preparation-dependent-consumer diagnostic; development only, no paid calls or runtime expansion'}
result_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')

# Keep the current route accurate without erasing the historical failed checkpoint.
route_path=inner/'analysis_out/current_analysis_backend.json'
route=json.loads(route_path.read_text(encoding='utf-8-sig'))
primary=route['primary_analysis']
primary['prior_delivery_checkpoint_20261016']={k:primary.get(k) for k in ['connectivity_status','connectivity_note']}
primary['connectivity_status']='two_parent_source_qualifications_complete_20261017'
primary['connectivity_note']='Two new parent-only Opus tasks completed with nonempty final, exit0 and end_turn; no refusal observed. Historical refusal and failures remain preserved. This does not prove general delivery stability or semantic correctness.'
primary['latest_research_delivery']='模型调用测试/2026-10-17/README.md'
route['updated']='2026-10-17'
route_path.write_text(json.dumps(route,ensure_ascii=False,indent=2),encoding='utf-8')

sync={}
for name in ['当前代办.md','当前研究方向与进展.md']:
    sync[name]={'before_sha256':hashlib.sha256((outer/name).read_bytes()).hexdigest()}
todo_path=outer/'当前代办.md'
todo=todo_path.read_text(encoding='utf-8-sig')
old=next(line for line in todo.splitlines() if line.startswith('  - [ ] **N1.4e 两项父版材料资格'))
new='  - [x] **N1.4e 两项父版材料资格与冻结组件试用（10/17有界完成）。** [本轮报告](linux_bug_analyze/experiments/case_taxonomy/parent_qualification_20261017/README.md)：补53份有限任务索引/家族元数据，登记后收集10父版文件；两Opus顶层任务均完整，119.422/109.359秒，可见287669token、预占400000，内部用量未知，不将两者相加。父版输出/组件结果先保存后才看两修复；盲于受测输出的角色裁定A为x86厂商准备辅助、B为设备/公共perf责任迁移待核，均未获核心正/同用途正常。9完整函数/1旧定位器失败，source4支持5不足、forward1支持5边界3不足；6原claim均不足，不计6假声明或准确率，5项另有字段接口不匹配但提示也不明确。未改冻结核心、补字段/桩或删宏循环；无新构建/内核/确认缺陷，正式独立0/0，两材料今后按已读资格/开发。\n  - [ ] **N1.4f 材料完整度与准备依赖消费的最小诊断（下一项，开发而非独立验证）。** 在已解封A辅助材料上，先限定核对父版cpu_init_topology、cpu_parse_topology两个消费者定义，不扩所有头文件/硬件路径。目标是明确“准备改变的状态—依赖此状态的真实消费—首次期限”，并把材料不足、采集/语法不支持和有材料仍未提出关系分开。记录模型与程序所需的最小输入、人工角色和实际未证义务；字段协议/声明定位只作配套修正，不称创新。首轮不新增付费调用、构建或运行，不回填N1.4e原结果，不再把本轮材料称未读。\n  - [ ] **N1.4g 新一轮核心样本资格（N1.4f后再预登记）。** 以共同Linux消费者、合法配置和架构差异见证为定位条件，明确厂商/设备辅助范围，分开初筛/开发/家族接触，再冻结新版本与至多两项输入。当前轮不补凑；只有资格及真值成立才增加独立正/正常分母。N2合法池选择继续作为待证方向。'
todo=todo.replace(old,new,1)
old='本轮文稿修订完成；下一研究项仍为N1.4e两项候选的父版资格与固定组件试用，正式独立正/正常0/0，R3继续暂缓。'
assert old in todo
todo=todo.replace(old,'文稿修订完成后，N1.4e两项父版试用已按有界范围完成；下一研究项N1.4f先诊断准备依赖消费的最小证据链。正式独立正/正常0/0，R3继续暂缓。',1)
todo_path.write_text(todo,encoding='utf-8')

progress_path=outer/'当前研究方向与进展.md'
progress=progress_path.read_text(encoding='utf-8-sig')
first=progress.split('\n\n')[1]
replacement='更新：2026-10-17。当前执行N1“公共接口要求与架构实际保证的条件化匹配”，N2“契约驱动的合法架构对照”作为第二方向。最小判定核心、受限源码/配置取证、条件效果及组件协议已完成有限子项；N1.4e两项父版资格和组件试用现已完成，两项均未获核心独立正/同用途正常资格。10/17两个Claude Code＋AWS-Claude-Opus-5.5新任务均完整交付；旧拒绝/空答原样保留，完整返回不等于语义正确。下一项N1.4f只在已读辅助材料上诊断准备依赖消费的最小证据链，不扩大付费或运行。完整自动提取、实际消费接卡与独立检测尚未建立，独立同机制正/正常仍0/0，N1/N2及R5/R6未完，R3继续暂缓。'
assert first.startswith('更新：')
progress=progress.replace(first,replacement,1)
anchor='## 10月17日论文修订'
addition='''## 10月17日两项父版资格与组件试用

按登记范围读取两候选10份父版完整文件，补有限任务身份审计，不给修复/初筛答案。当前原生Claude Code＋Opus两项均完整返回，分别119.422/109.359秒；客户端可见287669token、保守预占400000，内部恢复未知，不与预占相加。本轮首次取得当前入口的两项新父版完整分析，但不宣称长期稳定或语义已通过。

保持核心不变，十项函数定位取得九项、一项旧定位器不支持头注解形态；source四局部支持五不足，forward一支持五边界三不足。六原始模型claim均不足，不补字段/类型或删宏循环；五项另有根层字段不匹配，提示说明也有责任。这些是支持范围和接入限制，不是六假声明或检测率。

父版预测和组件结果先保存，之后才读两修复。独立角色未看模型输出裁定：A为x86单ISA厂商准备时机的辅助材料，缺拓扑真实消费/配置/运行；B为设备自管状态转公共perf scope的责任迁移，缺公共消费实现，不能因cleanup当正常。两项均不增加核心独立正/正常；已读身份从此保留。A提供重复求值掩盖晚准备的提交级线索，B提醒义务随版本和分工改变。未新增构建/内核/确认缺陷。

下一项N1.4f限定核对A父版两个拓扑消费者，建立准备状态到依赖消费的最小关系，先区分缺材料、程序不支持与关系漏提；不新增付费调用或运行。随后另行预登记核心样本，不在本轮替换失败。当前N1/N2/R5/R6未完、正式0/0，R3暂缓。报告见内层parent_qualification_20261017。

'''
assert anchor in progress
progress=progress.replace(anchor,addition+anchor,1)
progress=progress.replace('本轮只改文稿和工作记录，没有推进候选源码阅读、项目API或新实验；下一项仍N1.4e，独立正/正常0/0，R3暂缓。','该次文稿修订只改文稿和工作记录，当时下一项为N1.4e；其后已按上节完成两项有界试用，独立正/正常仍0/0，R3暂缓。',1)
progress_path.write_text(progress,encoding='utf-8')

nav_path=inner/'experiments/README.md'
nav=nav_path.read_text(encoding='utf-8-sig').replace('更新：2026-10-13。','更新：2026-10-17。',1)
nav=nav.replace('四类Pattern是分析框架，自动化目前主要集中在表示与部分长度边界；尚未建立稳定的未知缺陷检测能力。','Pattern保留为可重叠的分析索引；当前自动化主线为N1条件化要求推导与受限组件，N2合法对照选择尚为方案，尚未建立稳定的未知缺陷检测能力。',1)
anchor='| [案例复核与五维口径]'
pos=nav.index(anchor)
nav=nav[:pos]+'| [两项父版资格与组件试用](case_taxonomy/parent_qualification_20261017/README.md) | 两项Opus完整交付；9函数/6原claim有界试用，核心独立正/正常0/0，人工辅助与不足单列。 |\n| [冻结组件迁移协议](case_taxonomy/component_transfer_20261017/README.md) | 五核心及103项既有方法测试基线，非完整检测器；同材料比较、父版先行和人工输入边界。 |\n'+nav[pos:]
nav_path.write_text(nav,encoding='utf-8')

log=outer/'日志/2026-10-17.md'
with log.open('a',encoding='utf-8') as f:
    f.write('''\n\n## N1.4e：两项父版资格与冻结组件试用

继续当前待办，登记protocol_pre后仅推进0c2和a8，不补替换、不碰R3。独立接触角色核53份任务索引和路径存在性，补旧500/run身份及家族未知；读取两固定父版10文件，A原文114966/B85605字节，编号后API输入140906/103480字节。不提供修复、旧assessment或预期谓词，人工路径选择单列。

两个Windows原生Claude Code2.1.301＋AWS-Claude-Opus-5.5父版任务均完整，A119.422秒/9415字符/168353可见token，B109.359秒/8180字符/119316。均exit0、返回型号匹配、仅end_turn且无refusal；合计287669客户端可见token，40万保守预占低于本任务1M约定，内部恢复/实际账单未知，两数不相加。原始增量/assistant/final分别保留，旧拒绝任务未续写。两次新成功不证明所有长请求稳定，当前路由追加本轮交付并保留旧checkpoint。

冻结13指定文件及协议/环境核对一致，未重跑103测试。按父版选8函数，加模型另指2函数，去重10定位/9完整/1旧定位器不支持void __init；不是源码缺失。source4支持5不足，forward1支持5边界3不足。6原claim均insufficient：5先在定位/完整flow处受阻，1因return嵌套调用；另5条first/branch放target内且提示无明确根层示例，属接口歧义，不全归因模型。不补字段/桩、不删#if或循环、不改冻结核心。局部结构不是运行或效果，完整契约仍不足。

父版模型及组件结果落盘后，再收两child说明和有限diff；独立oracle角色不看受测输出裁定：A是Intel厂商条件下解锁晚于x86共同评估的辅助线索，缺拓扑消费者/实际配置/运行，不进核心CPU跨架构正例；B自管cpumask/CPUHP改system-wide scope，缺公共perf消费，cleanup不证明正常。A原回答未提出修复所指主准备关系，但消费者材料缺失，不能算正式漏报率；B模型候选的注册前IRQ要求不是本修订证实的根因。提交报告的冗余求值掩盖/新单次求值暴露，以及责任移入公共层，是后续机制分析线索，不当本项目实测。

源范围、oracle资格与方法计数三次限定独立复核完成。N1.4e有界项勾选，完整N1/N2/R5/R6未完；正式独立正/正常仍0/0，新增确认缺陷/构建/内核运行0。本轮为2顶层模型任务，不声称仅2底层推理。材料今后按已读资格/开发，原结果不回填，Word和GitHub未改。

下一项N1.4f仅补A父版cpu_init_topology/cpu_parse_topology两消费定义，明确准备改变的状态—依赖消费—期限，分开材料不足/方法不支持/关系漏提；首轮不新增付费/构建/运行。之后新轮再按共同公共消费者和合法配置预登记样本，本轮不凑正/正常。当前代办与研究进展更新并同步Windows/WSL，今日日志仍此一份。\n''')
for name in sync:
    sync[name]['after_sha256']=hashlib.sha256((outer/name).read_bytes()).hexdigest()
(stage/'notes_sync.json').write_text(json.dumps(sync,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ['top_level_model_tasks','visible_reported_tokens','conservative_reservation','complete_functions_collected','new_qualified_core_positive','new_qualified_same_use_normal','whole_contract','next']},ensure_ascii=False))
