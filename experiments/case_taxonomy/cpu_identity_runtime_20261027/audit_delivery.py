"""Final provenance/count/reference audit; no guest, model or core rerun."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
INNER=HERE.parents[2]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(path.read_bytes())
def need(value,reason):
    if not value: raise ValueError(reason)

def main():
    target=HERE/'delivery_manifest.json'; need(not target.exists(),'preserve_delivery_manifest')
    build=load(HERE/'build_complete.json'); guest=load(HERE/'guest_build.json'); boots=load(HERE/'boot_execution.json')
    need(sha(HERE/'kernel_inputs/Image')==build['image_sha256'],'image_identity_changed')
    need(sha(HERE/'kernel_inputs/vmlinux')==build['vmlinux_sha256'],'ELF_identity_changed')
    need(sha(HERE/'kernel_inputs/initramfs.cpio.gz')==guest['initrd_sha256'],'initrd_identity_changed')
    need(sha(HERE/'kernel_inputs/init')==guest['binary_sha256'],'PID1_identity_changed')
    need(sha(HERE/'kernel.config')==build['config_sha256'],'config_identity_changed')
    need(len(boots['runs'])==4 and all(row['returncode']==0 and row['observer_reached_end'] and row['power_down_observed'] for row in boots['runs']),'guest_completion_missing')
    for row in boots['runs']:
        need(sha(HERE/'runs'/row['profile']/'console.log')==row['console_sha256'],'guest_console_changed')
    final=load(HERE/'final_source_identity.json')
    need(set(final['configuration_changes_from_existing_baseline'])=={'CONFIG_LOCALVERSION'},'unreviewed_config_change')
    source=load(HERE/'source_manifest.json')
    for row in source:
        raw=(HERE/'sources'/row['path']).read_bytes()
        need(hashlib.sha256(raw).hexdigest()==row['sha256'],'source_archive_digest_changed')
        need(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['git_blob'],'source_archive_blob_changed')
    inputs=load(HERE/'analysis/arm64_contract_inputs.json')+load(HERE/'analysis/sparc_replay_inputs.json')
    for item in inputs:
        for document in item['ledger']['documents'].values():
            need(sha(INNER/document['path'])==document['sha256'],'contract_reference_changed')
    arm=load(HERE/'analysis/arm64_results.json'); old=load(HERE/'analysis/sparc_replay_results.json'); controls=load(HERE/'controls.json')
    need(arm['contract_decision_counts']=={'satisfied':20},'ARM64_check_results_unexpected')
    need(old['mapping_counts']=={'parent':{'satisfied':2,'violated':4},'fixed':{'satisfied':6}},'SPARC_replay_mapping_unexpected')
    need(old['selection_counts']=={'satisfied':12},'SPARC_quantity_replay_unexpected')
    need(controls['count']==12 and all(row['actual']==row['expected'] for row in controls['rows']),'control_result_mismatch')
    for item in inputs:
        need(item['ledger']['actual_first_content_consumption_proved'] is False,'deadline_promoted')
    summary=load(HERE/'analysis/summary.json')
    core=INNER/'linux_bug_analyze/contract_protocol.py'
    need(sha(core)==summary['core_sha256']=='42d37cc48d1c87a4c4b938d67a5acaedcc685ceb207deae3f72d7dcc88da830e','core_changed')
    artifacts={}
    for path in sorted(HERE.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.name.startswith('before_') or path.name=='plan_before.md': continue
        artifacts[str(path.relative_to(HERE))]={'sha256':sha(path),'bytes':path.stat().st_size}
    result={'date':'2026-10-27','status':'actual_ARM64_mapping_and_boot_limit_normal_control_stage_complete_CPU_identity_still_in_progress',
        'revision':build['revision'],'cache_root':'/root/.cache/linux-bug-analyze/cpu-identity-runtime-20261027',
        'source_files':14,'new_kernel_Image_builds':1,'new_PID1_builds':1,'new_qualified_Linux_guest_boots':4,
        'DT_only_QEMU_processes':3,'total_QEMU_processes':7,'new_project_model_calls':0,
        'actual_hardware_records_across_boots':sum(row['actual_online_hardware_records'] for row in arm['rows']),
        'new_ARM64_core_checks':20,'final_control_core_calls':6,'old_SPARC_core_replays':24,
        'initial_control_protocol_rejection_core_calls':1,'all_core_calls':51,'constructed_controls':12,
        'normal_scope':'one already-exposed ARM64 virtual platform/configuration and four positive limit conditions',
        'old_SPARC_level':'source/API-substitute projection only; no new execution or legality upgrade',
        'new_defects':0,'formal_independent_positive_normal':[0,0],
        'manual':['policy and requirement authority','namespace/mapping meanings','object and stage roles','legal normal qualification','finite observer support domain'],
        'open':['SPARC full historical provider/consumer and legal configuration chain','actual SPARC boot/tool availability','physical bare-metal and lifecycle','automatic requirement inference','independent evaluation'],
        'failures_preserved':['platform_v1_stop.json','qemu_source_archive_failure.json','controls_attempt1/'],
        'core_sha256':sha(core),'artifact_index_scope':'research artifacts before working-note updates','artifacts':artifacts}
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in result.items() if key!='artifacts'},ensure_ascii=False))

if __name__=='__main__': main()
