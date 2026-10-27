"""Preserve failed V1 qualification, make one source-informed V2 DT trial."""
from pathlib import Path
import hashlib
import json
import subprocess
import urllib.request

from fdt import cpus,need

HERE=Path(__file__).resolve().parent

def save(name,value):
    with (HERE/name).open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')

def main():
    save('platform_v1_stop.json',{'status':'qualification_failed_stopped_before_build_or_boot',
        'DT_trials':2,'IDs_trial_1':[r['hardware_id'] for r in cpus(HERE/'topology.dtb')],
        'IDs_trial_2':[r['hardware_id'] for r in cpus(HERE/'topology_9.dtb')],
        'failure':'second_DT_not_sparse_stop_without_boots','new_kernel_builds':0,'new_Linux_boots':0,
        'not_relabelled_as_normal':True})
    plan=json.loads((HERE/'platform_plan_v2.json').read_bytes())
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    manifest=[]
    for row in plan['source_evidence']:
        relative=row['url'].split('/v8.2.2/',1)[1]
        with opener.open(row['url'],timeout=45) as response:
            raw=response.read()
        path=HERE/'qemu_sources'/relative; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw)
        manifest.append({**row,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'path':str(path.relative_to(HERE))})
    save('qemu_source_manifest.json',manifest)
    argv=['qemu-system-aarch64','-machine','virt,gic-version=3,dumpdtb='+str(HERE/'topology_17.dtb'),
          '-cpu','cortex-a57','-accel','tcg','-smp','17','-m','512','-display','none']
    result=subprocess.run(argv,capture_output=True,timeout=30)
    (HERE/'dt_dump17.stdout.log').write_bytes(result.stdout); (HERE/'dt_dump17.stderr.log').write_bytes(result.stderr)
    save('dt_dump17_receipt.json',{'argv':argv,'returncode':result.returncode,'new_Linux_boot':False})
    need(result.returncode==0,'source_informed_DT_failed_stop')
    nodes=cpus(HERE/'topology_17.dtb'); ids=[r['hardware_id'] for r in nodes]
    need(ids==[*range(16),256],'source_informed_DT_not_expected_sparse_stop')
    need(all(r['status']=='okay' and r['enable_method']=='psci' for r in nodes),'CPU_node_qualification_missing')
    save('platform_qualification.json',{'status':'sparse_virtual_OF_platform_qualified_for_boot_trials','plan_revision':2,
        'CPU_nodes':nodes,'hardware_IDs':ids,'dt_sha256':hashlib.sha256((HERE/'topology_17.dtb').read_bytes()).hexdigest(),
        'qemu_machine':'virt,gic-version=3','qemu_cpu':'cortex-a57','qemu_smp':'17','memory_MiB':512,
        'qualification_level':'actual DT; final normal qualification still requires successful CPU boot and map/register observations',
        'DT_dump_processes':3,'Linux_boots_so_far':0,'observer_mapping_slots':32})
    save('boot_matrix.json',{'frozen_before_kernel_build_and_boot':True,'plan_revision':2,'profiles':[
        {'name':'baseline','arguments':[],'expected_possible_count':17,'expected_online_count':17},
        {'name':'nr2','arguments':['nr_cpus=2'],'expected_possible_count':2,'expected_online_count':2},
        {'name':'max2','arguments':['maxcpus=2'],'expected_possible_count':17,'expected_online_count':2},
        {'name':'nr3_max2','arguments':['nr_cpus=3','maxcpus=2'],'expected_possible_count':3,'expected_online_count':2}],
        'expectations_are_researcher_source_hypotheses_not_observations':True,'same_kernel_config_image_and_virtual_hardware':True,
        'require_injective_map_membership_actual_registers_and_complete_guest':True})
    print(json.dumps({'status':'qualified_DT','hardware_IDs':ids,'plan_revision':2,'Linux_boots':0}))

if __name__=='__main__':
    main()
