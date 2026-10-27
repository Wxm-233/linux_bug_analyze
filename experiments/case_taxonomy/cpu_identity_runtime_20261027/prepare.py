"""Pre-register the bounded ARM64 normal mapping/boot-limit experiment."""
from pathlib import Path
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent
OUTER=HERE.parents[3]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    out=HERE/'frozen_plan.json'
    if out.exists():
        raise ValueError('preserve frozen plan')
    names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
    before={name:sha(OUTER/name) for name in names}
    for name in names:
        (HERE/('before_'+name)).write_bytes((OUTER/name).read_bytes())
    (HERE/'notes_before.json').write_text(json.dumps({'before_sha256':before},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (HERE/'plan_before.md').write_bytes((OUTER/'接口验证后续规划.md').read_bytes())
    shutil.copyfile(HERE.parent/'cpu_export_image_bridge_20261027/sync_work_notes.py',HERE/'sync_work_notes.py')
    plan={'date':'2026-10-27','purpose':'actual ARM64 normal control for legal hardware-to-logical CPU renumbering and separate boot count/bound stages',
        'development_scope':True,'new_independent_samples':0,
        'revision':'db191ba0c8564ff84877e5b1c9553e991feca239',
        'existing_configuration':'virtio_platform_qualification_20261027/kernel.config; SMP=Y, NR_CPUS=512, OF/SYSFS/PROC enabled, no hotplug',
        'sparc_status':'historical projections preserved; qemu-system-sparc64 and sparc64-linux-gnu-gcc currently absent; no new SPARC reproduction claimed',
        'normal_qualification':['actual legal OF CPU nodes with sparse hardware affinity identifiers',
             'kernel admits a dense logical mapping without inventing or duplicating hardware targets',
             'actual SMP boot and per-CPU software map/register observations',
             'nr_cpus limits selected possible domain; maxcpus limits activation and preserves possible/present capacity, subject to pinned source verification'],
        'platform_qualification':'at most two DT dump attempts before freezing four boot command lines; prefer 4 CPUs/2 clusters; if unsupported use an actual QEMU topology whose DT has sparse hardware IDs',
        'source_files':['arch/arm64/kernel/smp.c','arch/arm64/kernel/setup.c','arch/arm64/kernel/cpu_ops.c',
            'arch/arm64/include/asm/smp_plat.h','arch/arm64/include/asm/smp.h','arch/arm64/include/asm/cputype.h',
            'kernel/smp.c','init/main.c','include/linux/cpumask.h','include/linux/smp.h',
            'kernel/cpu.c','drivers/base/cpu.c','drivers/of/base.c','Documentation/admin-guide/kernel-parameters.txt'],
        'observations':'read-only printk of actual mapping, masks, bounds and stage; raw DT plus PID1 sysfs/proc observations; no changes to selection or mapping',
        'planned_boot_conditions':['no runtime count limit','nr_cpus=2','maxcpus=2','nr_cpus=3 maxcpus=2'],
        'planned_builds':{'fresh_observational_kernel':1,'PID1':1},'planned_qualified_boots':4,
        'limits':['no new source-level claim that raw hardware IDs must equal logical IDs','no SPARC before/after real-boot claim',
            'no new Xen/LoongArch independent admission','no physical bare-metal or concurrent CPU hotplug claim',
            'previous metadata/exposure and rejected normal qualifications preserved','representation/R3 remain deferred'],
        'new_model_calls_planned':0,'core_expected_unchanged':'42d37cc48d1c87a4c4b938d67a5acaedcc685ceb207deae3f72d7dcc88da830e'}
    out.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'frozen','planned_qualified_boots':4,'new_model_calls':0}))

if __name__=='__main__':
    main()
