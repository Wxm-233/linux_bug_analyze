"""One filename-only direct-symbol lookup per case; bounded registered supplement."""
from pathlib import Path
import hashlib
import json
import subprocess

stage=Path(__file__).resolve().parent
protocol=json.loads((stage/'protocol_pre.json').read_text(encoding='utf-8'))
index=json.loads((stage/'parent_files.json').read_text(encoding='utf-8'))
if (stage/'symbol_locations.json').exists():
    raise SystemExit('Supplement lookup already recorded.')
queries={
 'C': {'pattern':'arch_disable_smp_support|bringup_nonboot_cpus','paths':['arch','kernel','init','include/linux']},
 'D': {'pattern':'cpu_clustergroup_mask|cpu_coregroup_mask|topology_cluster_cpumask|SCHED_CLUSTER','paths':['arch/arm64','arch/x86','drivers/base/Kconfig']}
}
locations=[]
for case in protocol['cases']:
    query=queries[case['id']]
    command=['git','-C',protocol['collection']['git'],'grep','-l','-E',query['pattern'],case['parent'],'--',*query['paths']]
    result=subprocess.run(command,capture_output=True,timeout=45)
    locations.append({'case':case['id'],'parent':case['parent'],**query,'exit_code':result.returncode,'paths_only':result.stdout.decode('utf-8').splitlines(),'error':result.stderr.decode('utf-8',errors='replace')[:1000]})
(stage/'symbol_locations.json').write_text(json.dumps({'queries':locations,'source_lines_returned':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

plan={
 'C': {'additional_paths':[], 'reason':'Existing parent files contain the weak/public hook, x86 implementation, early-parameter callers and smp_init caller. No whole-tree call-completeness or actual free-init lifetime proof is claimed.'},
 'D': {'additional_paths':['arch/arm64/include/asm/topology.h','arch/x86/kernel/smpboot.c','arch/arm64/Kconfig'], 'reason':'Direct architecture interface provider mapping, x86 mask provider/comparison, and ARM64 scheduler option conditions. Selected after initial parent source and filename-only location; exact configured build and hardware applicability remain unproved.'}
}
(stage/'supplement_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
documents=[]
for case in protocol['cases']:
    paths=plan[case['id']]['additional_paths']
    assert len(paths)<=3 and len(paths)+len(case['initial_paths'])<=8
    for path in paths:
        result=subprocess.run(['git','-C',protocol['collection']['git'],'show',case['parent']+':'+path],capture_output=True,timeout=30)
        record={'id':case['id']+':'+path,'case':case['id'],'parent':case['parent'],'path':path,'supplement_reason':plan[case['id']]['reason']}
        if result.returncode:
            record.update(status='unavailable',error=result.stderr.decode('utf-8',errors='replace')[:1000])
        else:
            target=stage/'parent_sources'/case['id']/path
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(result.stdout)
            record.update(status='collected',saved_path=str(target.relative_to(stage)),bytes=len(result.stdout),sha256=hashlib.sha256(result.stdout).hexdigest(),lines=len(result.stdout.splitlines()))
        documents.append(record)
(stage/'supplement_files.json').write_text(json.dumps({'documents':documents,'child_message_or_patch_read':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'location_path_counts':{r['case']:len(r['paths_only']) for r in locations},'supplement_documents':len(documents),'collected':sum(d['status']=='collected' for d in documents)},ensure_ascii=False))
