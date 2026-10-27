"""Bounded parent-only source collection; no patch, model, build, or boot."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
REPO = '/root/repos/linux'
COMMON = ['kernel/cpu.c', 'drivers/base/cpu.c', 'include/linux/cpu.h', 'init/main.c']
ISSUE = ['Documentation/arch/arm64/cpu-hotplug.rst', 'arch/arm64/kernel/acpi.c',
         'arch/arm64/kernel/smp.c', 'arch/arm64/Kconfig', *COMMON]
NORMAL_BASE = ['arch/x86/Kconfig', 'arch/x86/kernel/smpboot.c', 'arch/x86/configs/x86_64_defconfig', *COMMON]
NORMAL_REGISTRATION_ALTERNATIVES = ['arch/x86/kernel/topology.c', 'arch/x86/kernel/setup.c']


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(name, value):
    with (HERE/name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def invoke(argv):
    done = subprocess.run(argv, capture_output=True, timeout=30,
                          env=dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0'))
    if done.returncode:
        raise RuntimeError({'argv':argv,'returncode':done.returncode,'stderr':done.stderr.decode('utf-8',errors='replace')})
    return done.stdout, done.stderr.decode('utf-8',errors='replace')


def plan():
    selected = json.loads((HERE/'selection_pre.json').read_text(encoding='utf-8'))
    parent = selected['prospective_issue']['parents'][0]
    candidates = sorted(set(ISSUE+NORMAL_BASE+NORMAL_REGISTRATION_ALTERNATIVES))
    argv = ['git','-C',REPO,'ls-tree','-r','--name-only',parent,'--',*candidates]
    raw, stderr = invoke(argv)
    available = raw.decode('utf-8').splitlines()
    registration = next((p for p in NORMAL_REGISTRATION_ALTERNATIVES if p in available), None)
    normal = NORMAL_BASE + ([registration] if registration else [])
    missing = sorted((set(ISSUE)|set(normal))-set(available))
    result = {'task':'N2.24','revision':parent,'selection_sha256':digest((HERE/'selection_pre.json').read_bytes()),
              'availability_argv':argv,'availability_stderr':stderr,'available_named_paths':available,
              'issue_paths':ISSUE,'normal_paths':normal,'missing_paths':missing,
              'registration_choice_rule':'first available fixed metadata path; no source body consulted',
              'status':'ready_for_review' if not missing and registration else 'insufficient_paths',
              'file_limit_per_role':8,'unique_sources':len(set(ISSUE+normal)),'new_source_body_reads':0}
    assert len(ISSUE)==8 and len(normal)<=8
    save('source_plan.json',result)
    print(json.dumps({'status':result['status'],'issue_files':len(ISSUE),'normal_files':len(normal),
                      'unique_sources':result['unique_sources'],'registration_path':registration,'missing':missing}))


def collect():
    assert not (HERE/'source_manifest.json').exists(), 'preserve first collection'
    gate = (HERE/'pre_collection_review.md').read_text(encoding='utf-8')
    assert 'PARENT_COLLECTION_GATE: PASS' in gate
    plan = json.loads((HERE/'source_plan.json').read_text(encoding='utf-8'))
    assert plan['status']=='ready_for_review'
    assert digest((HERE/'selection_pre.json').read_bytes()) == plan['selection_sha256']
    destination = HERE/'parent_sources'
    destination.mkdir(exist_ok=False)
    rows = []
    result = {'task':'N2.24','revision':plan['revision'],'status':'collecting','files':rows,
              'source_plan_sha256':digest((HERE/'source_plan.json').read_bytes()),
              'collector_sha256':digest(Path(__file__).read_bytes()),'repair_body_reads':0,
              'new_builds':0,'new_boots':0,'paid_model_requests':0}
    try:
        for name in sorted(set(plan['issue_paths']+plan['normal_paths'])):
            argv = ['git','-C',REPO,'show',plan['revision']+':'+name]
            raw, stderr = invoke(argv)
            output = destination/name
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_bytes(raw)
            rows.append({'path':name,'revision':plan['revision'],'sha256':digest(raw),
                         'artifact':str(output.relative_to(HERE)).replace('\\','/'),'bytes':len(raw),
                         'roles':[role for role in ('issue','normal') if name in plan[role+'_paths']],
                         'argv':argv,'stderr':stderr})
        result['status']='collected'
    except Exception as error:
        result['status']='stopped'
        result['error']=repr(error)
        save('source_manifest.json',result)
        raise
    save('source_manifest.json',result)
    print(json.dumps({'status':result['status'],'complete_parent_files':len(rows),'repair_body_reads':0}))


if __name__ == '__main__':
    assert os.name=='posix', 'use the existing WSL repository'
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=['plan','collect'])
    args = parser.parse_args()
    {'plan':plan,'collect':collect}[args.action]()
