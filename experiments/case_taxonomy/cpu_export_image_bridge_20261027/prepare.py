"""Freeze the CPU source/object/image/publication bridge experiment."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    target = HERE/'notes_before.json'
    if target.exists():
        raise ValueError('preserve original round snapshot')
    names = ['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
    before = {name:sha(OUTER/name) for name in names}
    for name in names:
        (HERE/('before_'+name)).write_bytes((OUTER/name).read_bytes())
    target.write_text(json.dumps({'before_sha256':before},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (HERE/'plan_before.md').write_bytes((OUTER/'接口验证后续规划.md').read_bytes())
    shutil.copyfile(HERE.parent/'cpu_source_policy_20261027/sync_work_notes.py',HERE/'sync_work_notes.py')
    plan = {'date':'2026-10-27','purpose':'bind reviewed compiled source use to object, linked image and archived publication without rewriting history',
        'profiles':['old_x86_64','fixed_x86_64','old_s390','fixed_s390'],
        'planned':['compile frozen previous -dD CPP with archived code-generation options into isolated outputs',
                   'compare whole rebuilt object bytes after required x86 objtool processing',
                   'verify archive membership and linked attribute/callback pointer graph',
                   'extract actual gzip payload from archived image and compare to transformed vmlinux',
                   'bind archived publication observations by image/config/profile identity',
                   'reject mismatched or incomplete bridge inputs; retain unknown historical textual origin and runtime lifecycle'],
        'kernel_builds_planned':0,'boots_planned':0,'model_calls_planned':0,
        'object_compilations_planned':4,'conditional_additional_compilations':'only if frozen CPP format requires a documented correction; preserve every attempt',
        'source_reconstruction_is_not_historical_compiler_process':True,
        'archival_publication_is_not_concurrent_or_first_consumption_proof':True,
        'independent_positive_normal':[0,0],'new_defects_expected':0,
        'previous_round':'cpu_source_policy_20261027','source_core_sha256':'42d37cc48d1c87a4c4b938d67a5acaedcc685ceb207deae3f72d7dcc88da830e'}
    (HERE/'frozen_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'frozen','notes':len(names),'planned_isolated_object_compilations':4}))

if __name__=='__main__':
    main()
