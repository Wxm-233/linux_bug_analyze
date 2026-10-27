"""Second and final topology qualification attempt; freeze actual boot matrix."""
from pathlib import Path
import hashlib
import json
import subprocess

from fdt import cpus,need

HERE=Path(__file__).resolve().parent

def save(name,value):
    with (HERE/name).open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')

def main():
    first=cpus(HERE/'topology.dtb')
    save('dt_attempt1_review.json',{'CPU_nodes':first,'process_succeeded':True,
        'sparse_hardware_IDs':{r['hardware_id'] for r in first}!=set(range(len(first))),
        'not_a_Linux_boot':True,'finding':'requested clusters=2 did not make the actual CPU reg IDs sparse'})
    argv=['qemu-system-aarch64','-machine','virt,gic-version=3,dumpdtb='+str(HERE/'topology_9.dtb'),
          '-cpu','cortex-a57','-accel','tcg','-smp','9','-m','512','-display','none']
    result=subprocess.run(argv,capture_output=True,timeout=30)
    (HERE/'dt_dump9.stdout.log').write_bytes(result.stdout); (HERE/'dt_dump9.stderr.log').write_bytes(result.stderr)
    save('dt_dump9_receipt.json',{'argv':argv,'returncode':result.returncode,'new_Linux_boot':False})
    need(result.returncode==0,'second_DT_dump_failed')
    nodes=cpus(HERE/'topology_9.dtb'); ids=[r['hardware_id'] for r in nodes]
    need(len(nodes)==9 and set(ids)!=set(range(len(nodes))),'second_DT_not_sparse_stop_without_boots')
    need(0 in ids and all(r['status']=='okay' and r['enable_method']=='psci' for r in nodes),'CPU_nodes_not_normal_candidate')
    save('platform_qualification.json',{'status':'sparse_virtual_OF_platform_qualified_for_boot_trials','CPU_nodes':nodes,
        'hardware_IDs':ids,'dt_sha256':hashlib.sha256((HERE/'topology_9.dtb').read_bytes()).hexdigest(),
        'qemu_machine':'virt,gic-version=3','qemu_cpu':'cortex-a57','qemu_smp':'9','memory_MiB':512,
        'qualification_level':'actual DT, successful CPU online/acceptance still requires Linux boot observations',
        'DT_dump_processes':2,'Linux_boots_so_far':0,'observer_mapping_slots':16})
    save('boot_matrix.json',{'frozen_before_kernel_build_and_boot':True,'profiles':[
        {'name':'baseline','arguments':[],'expected_possible_count':9,'expected_online_count':9},
        {'name':'nr2','arguments':['nr_cpus=2'],'expected_possible_count':2,'expected_online_count':2},
        {'name':'max2','arguments':['maxcpus=2'],'expected_possible_count':9,'expected_online_count':2},
        {'name':'nr3_max2','arguments':['nr_cpus=3','maxcpus=2'],'expected_possible_count':3,'expected_online_count':2}],
        'expected_counts_are_researcher_source_hypotheses_not_oracle_observations':True,
        'same_kernel_configuration_image_and_QEMU_hardware':True,
        'require_actual_mapping_injectivity_and_register_checks':True})
    print(json.dumps({'status':'qualified_DT','hardware_IDs':ids,'qualified_boot_trials_planned':4}))

if __name__=='__main__':
    main()
