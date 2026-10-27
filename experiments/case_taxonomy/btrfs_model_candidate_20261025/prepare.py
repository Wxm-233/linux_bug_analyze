from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):(HERE/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
out=ROOT/'模型调用测试/2026-10-25/btrfs_model_candidate';out.mkdir(exist_ok=False)
inventory=BASE/'btrfs_stability_inventory_20261024';inv=read(inventory/'inventory.json')['versions'][0]
revision=inv['revision'];docs={};sections=[]
for ident,name,spans in [
 ('disk','fs/btrfs/disk-io.c',[(2973,2983),(3264,3380)]),
 ('super','fs/btrfs/super.c',[(564,606),(775,801)]),
 ('ctree','fs/btrfs/ctree.h',[(224,275),(1623,1634),(2390,2410)]),
 ('inode','fs/btrfs/inode.c',[(335,370)])]:
 item=inv['files'][name];p=inventory/item['artifact'];assert sha(p)==item['sha256']
 docs[ident]=dict(path=str(p),sha256=sha(p),revision=revision,provided_spans=spans)
raw=ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024'
entry=read(raw/'manifest.json')[0];assert entry['mode']=='parent'
for ident,filename,spans,expected in [('config','kernel.config',[(535,545),(1207,1217)],entry['artifacts']['kernel.config']),
 ('observer','super.observed.c',[(780,802)],entry['source_after_sha256'])]:
 p=raw/'parent'/filename;assert sha(p)==expected
 docs[ident]=dict(path=str(p),sha256=sha(p),revision=revision,provided_spans=spans)
for ident,d in docs.items():
 lines=Path(d['path']).read_text(encoding='utf-8').splitlines();sections.append('\n## DOCUMENT '+ident)
 for lo,hi in d['provided_spans']:
  assert 1<=lo<=hi<=len(lines)
  sections.append('\n'.join(f'{n}: {lines[n-1]}' for n in range(lo,hi+1)))
task='''请为Btrfs几何提供者→max_inline公共消费接口提出一个可由程序检查的准备条件候选。这是已读开发案例的结构化接口试验，不是盲测。研究者已选择接口和材料，但没有提供目标关系表达式、原接口卡、修复版、运行观测值、以前模型结论或判定答案。请自行从给出的源码提出候选；材料不足在uncertainties中说明，不自行批准证据。
范围：指定父版，已登记ARM64/64K、64K磁盘、单设备、flags=0、max_inline=2048/8192成功新挂载。selected_profile是研究者选择的这个范围，不代表准备条件已满足。observer为取证变换，不能据插桩推原代码全部机器语义。保持输出纯JSON对象，无代码围栏、前后说明或隐藏思维过程。
输出顶层键必须且仅为schema,interface_id,revision,deadline_event,contract,symbol_bindings,citations,uncertainties。
schema=model_interface_candidate_v1；interface_id=btrfs.geometry_before_max_inline；revision=REVISION。
deadline_event只能从cache_capture/min_consumption/disk_sample中选一个；分别对应observer中缓存局部量取得、min求值、磁盘getter样本，不预设哪一个应当作为要求期限。
contract格式：schema=architecture_contract_v1；id=btrfs.layered.C；revision同上；authority_kind选documented或consumer_inferred；sufficient_for_correctness=false。
contract.symbols是你选用的变量声明字典，值为{type:bool或int或string或int_set,role:configuration或observation}。scope和relation为表达式，节点为{symbol:变量名}、{literal:值}或{op:操作,args:[节点...]}。支持eq/ne/lt/le/gt/ge/contains/nonempty/and/or/not。scope须只用configuration变量，relation须用observation，不能有未用变量。请选择适合源码用途的表达式，不局限于相等。
contract.required_claims必须具有authority/interface/consumer_requirement/provider_binding/object_binding/deadline_binding/applicability七个键，每个值等于其键名。
contract.field_origins必须含scope/relation/symbols/required_claims/authority_kind五键，值全部为model_proposal；禁止输出任何supported账本。
symbol_bindings给每个contract变量标明语义角色，从以下命名词汇选择：selected_profile（上述选中范围）、cache（消费缓存操作数）、disk_at_deadline（候选消费时刻适用磁盘几何）、adjacent_disk（后采样磁盘值）、request（用户请求）、result（裁剪结果）。命名词汇是人为提供的适配器接口，不是自动发现，也不保证其中值已取得。
citations为4到12条引用，键仅supports/document/start_line/end_line/quote。supports取scope/relation/symbol_bindings/deadline_event，四类都至少一条。document必须为附件DOCUMENT id，引用范围必须在实际提供的连续片段内，quote为对应行中逐字连续子串（可含换行，不得加省略号）。引用可定位不等于语义已审，引用scope只支撑所选输入的部分相关性即可，其他研究者范围假设写入uncertainties。
uncertainties为字符串数组，明确未取得的参考值、对象/时刻绑定及规范依据。只输出一个候选，不提供运行数值或伪造事实；不要填入未提供的答案。
'''.replace('REVISION',revision)
prompt=task+'\n'.join(sections);(out/'prompt.md').write_text(prompt,encoding='utf-8',newline='\n')
save('documents.json',docs)
save('protocol.json',dict(input_scope='known parent-only development case; manual interface/material/role vocabulary selection',
 no_expected_formula_supplied=True,no_runtime_values_supplied=True,no_fix_supplied=True,
 manual_candidate_repair_allowed=False,format_retry_allowed=False,
 parser='strict JSON with duplicate key, provenance, reference span/hash/quote checks',
 on_failure='record insufficiency without repair',
 on_match='invoke original core with unmodified evidence ledger; model provenance is not review approval',
 abstract_event_bindings={'cache_capture':'context_id+:cache','min_consumption':'record.deadline_event','disk_sample':'record.sample_event'},
 prompt_sha256=sha(out/'prompt.md'),output=str(out)))
template=(ROOT/'模型调用测试/2026-10-25/run_kimi_btrfs_helper_expanded.py').read_text(encoding='utf-8')
template=template.replace("OUT=HERE/'btrfs_kimi_helper_expanded'","OUT=HERE/'btrfs_model_candidate'")
runner=ROOT/'模型调用测试/2026-10-25/run_btrfs_model_candidate.py';assert not runner.exists();runner.write_text(template,encoding='utf-8')
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
save('notes_before.json',dict(before_sha256={n:sha(ROOT/n) for n in names}))
shutil.copyfile(BASE/'new_input_contract_trial_20261017/sync_work_notes.py',HERE/'sync_work_notes.py')
files=[ROOT/'linux_bug_analyze/linux_bug_analyze'/n for n in ('model_candidate.py','interface_intent.py','contract_protocol.py','contract_archive.py')]
files += [HERE/'documents.json',HERE/'protocol.json',runner]
save('frozen_inputs.json',{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in files})
print(json.dumps(dict(documents=len(docs),prompt_bytes=len(prompt.encode()),prompt_sha256=sha(out/'prompt.md'))))
