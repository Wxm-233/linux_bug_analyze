"""Close the bounded evidence diagnostic and keep the current checkpoint consistent."""
from pathlib import Path
import hashlib
import json
import sys

stage=Path(__file__).resolve().parent
inner=stage.parents[2]
outer=inner.parent
if '--sync-wsl' in sys.argv:
    records=json.loads((stage/'notes_sync.json').read_text(encoding='utf-8'))
    for name,item in records.items():
        target=Path('/root')/name
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() not in {item['before_sha256'],item['after_sha256']}:
            raise RuntimeError('WSL note changed independently: '+name)
    for name,item in records.items():
        target=Path('/root')/name
        target.write_bytes((outer/name).read_bytes())
        assert hashlib.sha256(target.read_bytes()).hexdigest()==item['after_sha256']
    print(json.dumps({'status':'synchronized_byte_equal','files':list(records)},ensure_ascii=False))
    raise SystemExit(0)

result_path=stage/'results.json'
if result_path.exists():
    raise SystemExit('Stage already completed; preserve its original result.')
material=json.loads((stage/'consumer_functions.json').read_text(encoding='utf-8'))
diagnostic=json.loads((stage/'structural_diagnostic.json').read_text(encoding='utf-8'))
assert len(material['documents'])==2
assert (stage/'review.md').is_file()
for document in material['documents']:
    assert hashlib.sha256(document['text'].encode()).hexdigest()==document['function_sha256']
frozen=json.loads((stage.parent/'component_transfer_20261017/component_versions.json').read_text(encoding='utf-8'))
checked=[]
for record in frozen['files']:
    if record['path'] in ['linux_bug_analyze/source_conditions.py','linux_bug_analyze/forward_guards.py']:
        assert hashlib.sha256((inner/record['path']).read_bytes()).hexdigest()==record['sha256']
        checked.append(record['path'])
assert len(checked)==2
result={'date':'2026-10-17','task':'N1.4f','completed_scope':'two complete parent consumer definitions and bounded preparation-dependency diagnostic','case_status':'already-read vendor auxiliary; not independent validation','source_file':'arch/x86/kernel/cpu/topology_common.c','parent':material['parent'],'complete_definitions':[{k:d[k] for k in ['function','start_line','end_line','location_method']} for d in material['documents']],'unchanged_old_locator_successes':1,'old_locator_failures_preserved':1,'collection_only_exact_location_fallbacks':1,'machine_facts':{'cpu_init_topology_call_inventory':[200,203,213],'complete_supported_local_flows':0,'precise_cpuid_dependency_consumer_proved':False},'remaining_obligations':['parse_topology/topo_set_ids effects','actual dependency read and applicability','hardware preparation effect and cached metadata','actual target/configuration and first-use state','recomputation and intervening writers'],'candidate_origin':'researcher synthesis, not newly model-inferred or auto-generated','frozen_method_files_checked':checked,'core_changed':False,'prior_parent_results_rewritten':False,'new_project_model_requests':0,'new_builds':0,'new_kernel_runs':0,'new_unit_test_runs':0,'new_confirmed_defects':0,'new_independent_positive':0,'new_independent_normal':0,'r3_resumed':False,'whole_contract':'insufficient','next':'N1.4g new core common-consumer candidate qualification under separate registration; stop auxiliary helper expansion'}
result_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')

sync={name:{'before_sha256':hashlib.sha256((outer/name).read_bytes()).hexdigest()} for name in ['当前代办.md','当前研究方向与进展.md']}
todo_path=outer/'当前代办.md'
todo=todo_path.read_text(encoding='utf-8-sig')
old=next(line for line in todo.splitlines() if line.startswith('**下一操作：'))
new='**下一操作：N1.4g，另轮预登记核心公共消费者候选资格。** N1.4e两项父版试用和N1.4f两消费定义补证均已按有界范围完成；A只作x86厂商辅助、B为设备/公共perf迁移待核，正式独立正/正常仍0/0。停止辅助helper/include扩展；新轮从固定500的任务/变更路径元数据定位共同Linux消费用途与架构差异线索，先接触/家族审计，再确定至多两项父版范围。不要求同时改公共与arch目录，不以标题或模型标签当真值；当前不补凑，不新增付费/构建/运行，N1/N2/R5/R6未完，R3暂缓。'
todo=todo.replace(old,new,1)
old=next(line for line in todo.splitlines() if line.startswith('  - [ ] **N1.4f '))
new='  - [x] **N1.4f 材料完整度与准备依赖消费的最小诊断（10/17限定完成）。** [补证报告](linux_bug_analyze/experiments/case_taxonomy/preparation_dependency_20261017/README.md)：取得父版cpu_parse_topology 166–193与cpu_init_topology 195–220。接出局部scan→共享dom_shifts→派生dom_size及后续APIC/shift日志比较；实际CPUID依赖仍在未展开parse_topology中，比较不是阻断门槛。一个定义旧定位器成功，另一个保留__init失败后仅按已定位原文完整采集；source保留初始化函数200/203/213三调用，循环/宏/头注解继续不足。研究者卡分开硬件可见域、缓存level、scratch和派生对象，不当模型自动输出；不要求所有CPUID读取先解锁。独立有限复核完成，冻结核心与旧六claim不改，无新API/构建/运行/独立样本；至此停止厂商辅助补源，转N1.4g。'
todo=todo.replace(old,new,1)
old=next(line for line in todo.splitlines() if line.startswith('  - [ ] **N1.4g '))
new='  - [ ] **N1.4g 新一轮核心样本资格（当前下一项）。** 先预登记固定500中的元数据定位条件、最多两候选和接触/家族核查范围：能说明架构差异如何进入共同Linux消费者及为何A满足/B暴露，正常对照要有同用途合法满足依据。变更路径只作定位，不强制同时修改公共与arch，不用标题/旧模型标签当真值；厂商和设备例单列辅助。首段只做元数据资格和精确父版材料计划，不新增付费或运行；后续分析按独立协议执行。不给e轮补选或回填，只有资格/真值成立才增正式独立分母；N2合法配置池选择仍待实现。'
todo=todo.replace(old,new,1)
old=next(line for line in todo.splitlines() if line.startswith('**当前继续入口：**'))
new='**当前继续入口：**顶部N1.4g。e轮父版模型/组件试用与f轮两个消费定义有限补证已完成，A/B均已读；A厂商辅助不再递归补源，B设备迁移不预定正常。新轮先预登记核心共同消费者定位与接触/家族审计，再定最多两项精确父版材料。正式正/正常仍0/0，完整N1/N2/R5/R6未完，R3暂缓。'
todo=todo.replace(old,new,1)
old='文稿修订完成后，N1.4e两项父版试用已按有界范围完成；下一研究项N1.4f先诊断准备依赖消费的最小证据链。'
assert old in todo
todo=todo.replace(old,'文稿修订、N1.4e父版试用及N1.4f两个消费定义补证均已按范围完成；下一研究项N1.4g回到核心公共消费者资格，不继续辅助源码扩展。',1)
todo+='\n\n**本次操作核对（2026-10-17，N1.4f有限补证）：**两函数定义补齐，区分状态来源、派生对象及外层消费；真正CPUID依赖仍未闭合，研究者卡不是自动契约。保留旧定位/语法失败和原6claim，冻结核心不改；0API/构建/内核/新独立样本。停止厂商辅助补源，转N1.4g新轮核心候选资格，R3暂缓。\n'
todo_path.write_text(todo,encoding='utf-8')

progress_path=outer/'当前研究方向与进展.md'
progress=progress_path.read_text(encoding='utf-8-sig')
opening=progress.split('\n\n')[1]
replacement=opening.replace('下一项N1.4f只在已读辅助材料上诊断准备依赖消费的最小证据链，不扩大付费或运行。','N1.4f已补齐两个拓扑外层定义并形成有边界的研究者候选卡，实际CPUID依赖仍未闭合；厂商辅助补源到此停止。下一项N1.4g回到核心共同Linux消费者的新轮资格，先元数据/材料计划，不增加付费或运行。')
assert replacement!=opening
progress=progress.replace(opening,replacement,1)
anchor='## 10月17日两项父版资格与组件试用'
addition='''## 10月17日准备依赖与拓扑派生状态的有限补证

补齐已读A父版的cpu_parse_topology和cpu_init_topology两定义，接出了局部scan、共享dom_shifts、派生dom_size以及后续APIC/shift日志比较。这说明检查应追踪准备结果会进入哪些派生数据，不能只检查能力缓存重采或函数先后。实际CPUID读取及parse_topology/topo_set_ids效果仍未展开，日志比较不等于阻断条件或完整判定器。

研究侧提出有条件的候选：若派生确实依赖准备结果，应先满足相应状态，或另证首次使用前已重算受影响结果。硬件可见范围、缓存level、能力位、两个局部scan与共享派生字段分开；不要求所有CPUID读取先解锁，也不把函数入口当精确期限。候选来自已读材料综合，非新模型自动提取。

源分析程序仅保留初始化函数200/203/213三调用；两个完整局部流程仍不足，旧__init定位失败与宏/循环/注解限制分别保存。没有删代码、补桩、改冻结核心或回填原六claim，无新API/构建/运行/独立样本。限定复核完成，厂商辅助补源到此停止；下一项N1.4g回到核心共同Linux消费者的新轮资格，0/0和R3暂缓保持。

'''
assert anchor in progress
progress=progress.replace(anchor,addition+anchor,1)
progress_path.write_text(progress,encoding='utf-8')

nav_path=inner/'experiments/README.md'
nav=nav_path.read_text(encoding='utf-8-sig')
anchor='| [两项父版资格与组件试用]'
pos=nav.index(anchor)
nav=nav[:pos]+'| [准备依赖与派生状态补证](case_taxonomy/preparation_dependency_20261017/README.md) | 两完整外层定义，区分准备/缓存/局部scan/共享派生对象；helper依赖未知，已读辅助到此收束，不计自动提取或独立样本。 |\n'+nav[pos:]
nav_path.write_text(nav,encoding='utf-8')

with (outer/'日志/2026-10-17.md').open('a',encoding='utf-8') as f:
    f.write('''\n\n## N1.4f：准备依赖与拓扑派生状态的有限补证

用户强调按大方向推进。先按待办在已读A辅助材料上登记两个消费定义范围，精确父版2a38e4，单次Git符号定位后只读topology_common.c内cpu_parse_topology 166–193与cpu_init_topology 195–220；其他helper体未展开，不触B或新候选。两函数中一个由旧定位器取得，另一个保留void __init头形态失败后仅据原始定位与平衡括号完整采集，原文不改，不当冻结定位器两项成功。

源码接出形参c→两个不同局部tscan.c→parse_topology不透明边界→局部/共享dom_shifts与派生dom_size；后续CPU比较APIC/shift只记日志，不是资格阻断。实际CPUID依赖、helper副作用、具体首次内容读取、配置/硬件效果/最终对象与稳定性继续未知，不能由wrapper入口或memcpy名字证明。能力重采也不等于已证明拓扑重算或必不重算。

冻结source在init保留parse_topology200、memcpy203、topo_set_ids213三调用坐标，for导致完整flow不足；parse受FW_BUG字符串宏阻断，forward对init另有__init声明限制。不删宏/循环、不补桩或修改核心，两源模块当前指纹与既有冻结表相符；这是支持范围诊断，不是2例新检测或6原claim重算。

形成明确标研究者综合的dependency_candidate：只对真实依赖准备效果的派生/消费要求有效状态，或另证首次使用前重算；不要求所有CPUID读取先解锁，厂商/型号识别可在前。卡分开硬件可见域、缓存level、能力、scratch及共享派生对象，whole_contract保持insufficient。独立角色只看新两定义及限定材料复核，未新增项目API或运行。

N1.4f有界项完成，厂商辅助到此停止补源，比继续修本例解析更贴合跨架构主线。下一项N1.4g另轮预登记核心共同Linux消费者、架构差异及合法可比条件的元数据/家族资格，不给e轮补选或把已读当未读；不强制一个提交同时改公共与arch目录。0新增API/构建/内核/单元测试重跑/确认缺陷/独立样本，正式正/正常仍0/0，N1/N2/R5/R6未完，R3暂缓，Word/GitHub未改。同步修正当前代办顶部及中部两个仍指e的旧“继续入口”，与最新下一项一致；Windows/WSL两工作记录同步。\n''')
for name,item in sync.items():
    item['after_sha256']=hashlib.sha256((outer/name).read_bytes()).hexdigest()
(stage/'notes_sync.json').write_text(json.dumps(sync,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'completed':'N1.4f','definitions':2,'new_project_model_requests':0,'whole_contract':'insufficient','next':'N1.4g','independent_positive_normal':[0,0],'old_current_entry_points_corrected':2},ensure_ascii=False))
