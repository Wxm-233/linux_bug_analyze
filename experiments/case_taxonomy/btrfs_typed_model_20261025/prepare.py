from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):(HERE/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
old=HERE.parent/'btrfs_typed_parts_20261025'
pins=read(old/'frozen_inputs.json')
for p,h in pins.items():assert sha(ROOT/p)==h,p
out=ROOT/'模型调用测试/2026-10-25/btrfs_typed_model';out.mkdir(exist_ok=False)
prompt=(out.parent/'btrfs_model_candidate/prompt.md').read_text(encoding='utf-8')
start=prompt.index('symbol_bindings给');end=prompt.index('\ncitations为',start)
roles=(old/'role_registry.json').read_text(encoding='utf-8')
prompt=prompt[:start]+'symbol_bindings给每个contract变量标明以下有类型词表中的一个语义角色；变量声明须与角色的type/role一致，各变量不能重复绑定同一角色。selected_profile只用于组合范围bool，具体数值使用具体角色。词表由研究者提供，不代表自动发现或事实已取得；不要依变量名称猜测未定义角色。表达式及必要变量仍由你根据源码选择。\n'+roles+prompt[end:]
(out/'prompt.md').write_text(prompt,encoding='utf-8')
shutil.copyfile(old/'role_registry.json',HERE/'role_registry.json')
shutil.copyfile(old/'sync_work_notes.py',HERE/'sync_work_notes.py')
runner=out.parent/'run_btrfs_typed_model.py';assert not runner.exists()
runner.write_text((out.parent/'run_btrfs_model_candidate.py').read_text(encoding='utf-8').replace("OUT=HERE/'btrfs_model_candidate'","OUT=HERE/'btrfs_typed_model'"),encoding='utf-8')
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
save('notes_before.json',dict(before_sha256={n:sha(ROOT/n) for n in names}))
save('protocol.json',dict(change='typed role vocabulary only; all original task/material text retained',development_only=True,manual_candidate_repair=False,no_runtime_values_or_expected_formula=True,model_calls_planned=1,format_retry=False,formal_core_approval=False,prompt_sha256=sha(out/'prompt.md')))
save('frozen_inputs.json',dict(pins,**{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [HERE/'role_registry.json',HERE/'protocol.json',HERE/'run.py',runner,out/'prompt.md',old/'results.json']}))
print('Prepared typed model candidate; old inputs verified and preserved')
