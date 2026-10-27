"""Run the registered third DT trial after independent web source inspection.

Archiving the full upstream raw file timed out before a DT process started;
keep that failure and source links. Do not retry the download or count it as a
model failure. Qualification still depends on this machine's actual DT.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

from fdt import cpus,need

HERE=Path(__file__).resolve().parent

def save(name,value):
    with (HERE/name).open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')

def main():
    save('qemu_source_archive_failure.json',{'status':'raw_upstream_file_read_timeout','timeout_seconds':45,
        'source':'https://raw.githubusercontent.com/qemu/qemu/v8.2.2/hw/arm/virt.c',
        'full_source_archive_available':False,'source_informed_DT_process_started_in_failed_script':False,
        'sources_inspected_via_web_tool':json.loads((HERE/'platform_plan_v2.json').read_bytes())['source_evidence'],
        'model_call':False,'download_retry':False})
    shutil.copyfile(HERE/'qualify_source_informed_dt.py',HERE/'qualify_source_informed_dt_before_timeout.py')
    argv=['qemu-system-aarch64','-machine','virt,gic-version=3,dumpdtb='+str(HERE/'topology_17.dtb'),
          '-cpu','cortex-a57','-accel','tcg','-smp','17','-m','512','-display','none']
    result=subprocess.run(argv,capture_output=True,timeout=30)
    (HERE/'dt_dump17.stdout.log').write_bytes(result.stdout); (HERE/'dt_dump17.stderr.log').write_bytes(result.stderr)
    save('dt_dump17_receipt.json',{'argv':argv,'returncode':result.returncode,'new_Linux_boot':False})
    need(result.returncode==0,'source_informed_DT_failed_stop')
    nodes=cpus(HERE/'topology_17.dtb'); ids=[row['hardware_id'] for row in nodes]
    need(ids==[*range(16),256],'source_informed_DT_not_expected_sparse_stop')
    need(all(row['status']=='okay' and row['enable_method']=='psci' for row in nodes),'CPU_node_qualification_missing')
    save('platform_qualification.json',{'status':'sparse_virtual_OF_platform_qualified_for_boot_trials','plan_revision':2,
        'CPU_nodes':nodes,'hardware_IDs':ids,'dt_sha256':hashlib.sha256((HERE/'topology_17.dtb').read_bytes()).hexdigest(),
        'qemu_machine':'virt,gic-version=3','qemu_cpu':'cortex-a57','qemu_smp':'17','memory_MiB':512,
        'qualification_level':'actual DT; final normal qualification requires successful CPU boot and map/register observations',
        'DT_dump_processes':3,'Linux_boots_so_far':0,'observer_mapping_slots':32,
        'upstream_reference_not_binary_source_identity':True})
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
