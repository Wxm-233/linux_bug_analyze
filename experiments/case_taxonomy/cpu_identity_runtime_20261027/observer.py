"""Finite CPU identity/boot-stage trace adapter for this actual ARM64 image."""
from pathlib import Path
import hashlib
import json
import re

HERE=Path(__file__).resolve().parent
STAGES=['arch_after_enumeration','common_before_rebound','common_after_rebound',
        'arch_before_prepare','arch_after_prepare','common_before_bringup','common_after_bringup']
MAP_STAGES=['arch_after_enumeration','arch_before_prepare','arch_after_prepare']
INVALID=(1<<64)-1

def need(value,reason):
    if not value:
        raise ValueError(reason)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_bytes())

def cpulist(text):
    text=text.strip()
    if not text:
        return []
    need(re.fullmatch(r'\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*',text) is not None,'unsupported_CPU_list')
    out=set()
    for part in text.split(','):
        values=[int(x) for x in part.split('-')]; low,high=values[0],values[-1]
        need(0<=low<=high<512,'CPU_list_outside_compile_capacity')
        for cpu in range(low,high+1):
            need(cpu not in out,'CPU_list_has_duplicate_or_overlap'); out.add(cpu)
    return sorted(out)

def parse(console):
    snapshots={}; maps={stage:{} for stage in MAP_STAGES}; hardware={}; user=[]
    snapshot_re=re.compile(r'LBA_CPU_SNAPSHOT stage=(\w+) nr=(\d+) max=(\d+) possible=([0-9,-]*) present=([0-9,-]*) online=([0-9,-]*)$')
    map_re=re.compile(r'LBA_CPU_MAP stage=(\w+) logical=(\d+) hardware=0x([0-9a-f]+) valid=([01]) domain=([01]) possible=(-?\d+) present=(-?\d+) online=(-?\d+)$')
    hw_re=re.compile(r'LBA_CPU_HW logical=(\d+) mapped=0x([0-9a-f]+) actual=0x([0-9a-f]+) boot=([01])$')
    for index,line in enumerate(console.splitlines(),1):
        if 'LBA_CPU_SNAPSHOT ' in line:
            match=snapshot_re.search(line); need(match is not None,'malformed_snapshot')
            stage=match[1]; need(stage not in snapshots,'duplicate_snapshot:'+stage)
            snapshots[stage]={'stage':stage,'nr':int(match[2]),'max':int(match[3]),
                'possible':cpulist(match[4]),'present':cpulist(match[5]),'online':cpulist(match[6]),'line':index}
        elif 'LBA_CPU_MAP ' in line:
            match=map_re.search(line); need(match is not None,'malformed_mapping')
            stage=match[1]; cpu=int(match[2]); need(stage in maps and cpu not in maps[stage],'unknown_or_duplicate_mapping')
            maps[stage][cpu]={'logical':cpu,'hardware':int(match[3],16),'valid':bool(int(match[4])),
                'domain':bool(int(match[5])),'possible':int(match[6]),'present':int(match[7]),'online':int(match[8]),'line':index}
        elif 'LBA_CPU_HW ' in line:
            match=hw_re.search(line); need(match is not None,'malformed_hardware_record')
            cpu=int(match[1]); need(cpu not in hardware,'duplicate_actual_hardware_record')
            hardware[cpu]={'logical':cpu,'mapped':int(match[2],16),'actual':int(match[3],16),'boot':bool(int(match[4])),'line':index}
        elif 'LBA_USER ' in line:
            start=line.index('LBA_USER ')+len('LBA_USER ')
            user.append(json.loads(line[start:]))
    return {'snapshots':snapshots,'maps':maps,'hardware':hardware,'user':user}

def validate_trace(trace,profile,build,receipt,qualification):
    snaps,maps,hardware,user=(trace[k] for k in ['snapshots','maps','hardware','user'])
    need(set(STAGES)<=set(snaps),'required_stage_missing')
    positions=[snaps[stage]['line'] for stage in STAGES]
    need(positions==sorted(positions) and len(set(positions))==len(positions),'consumer_stage_order_not_bound')
    args=profile['arguments']; expected_early=[]
    if any(x.startswith('nr_cpus=') for x in args): expected_early.append('early_nr_cpus')
    if any(x.startswith('maxcpus=') for x in args): expected_early.append('early_maxcpus')
    need(set(snaps)==set(STAGES+expected_early),'unexpected_early_parameter_stage')
    need(all(snaps[stage]['line']<positions[0] for stage in expected_early),'early_limit_observed_after_enumeration')
    for stage,row in snaps.items():
        need(1<=row['nr']<=512 and 1<=row['max']<=512,'outside_positive_limit_configuration')
    for stage in MAP_STAGES:
        rows=maps[stage]; need(set(rows)==set(range(32)),'mapping_observer_interval_incomplete:'+stage)
        snapshot=snaps[stage]
        need(set(snapshot['possible'])<=set(rows),'selected_CPU_outside_mapping_observer')
        for cpu,row in rows.items():
            need(row['line']>snapshot['line'],'mapping_before_its_snapshot')
            need(row['valid']==(row['hardware']!=INVALID),'mapping_validity_flag_inconsistent')
            need(row['domain']==(cpu<snapshot['nr']),'mapping_domain_bound_inconsistent')
            for flag in ['possible','present','online']:
                expected=int(cpu in snapshot[flag]) if row['domain'] else -1
                need(row[flag]==expected,'mapping_flag_not_same_stage_or_outside_domain_queried')
    final=snaps['common_after_bringup']
    need(set(hardware)==set(final['online']),'actual_register_observations_do_not_cover_online_CPUs')
    need(hardware.get(0,{}).get('boot') is True and all(not r['boot'] for c,r in hardware.items() if c!=0),'boot_CPU_role_not_bound')
    need(all(row['line']<final['line'] for row in hardware.values()),'hardware_observed_after_final_sample')
    need(user and user[0].get('event')=='begin' and user[-1].get('event')=='end','PID1_observation_window_incomplete')
    need(user[0].get('schema')=='cpu_identity_runtime_v1' and user[0].get('pid')==1 and user[-1].get('reached_end') is True,'PID1_identity_not_established')
    def one(kind):
        rows=[row for row in user if row.get('event')==kind]; need(len(rows)==1,'user_event_not_unique:'+kind); return rows[0]
    mount=one('mount'); need(mount.get('proc_rc')==mount.get('sysfs_rc')==0,'proc_or_sysfs_mount_failed')
    uname=one('uname'); need(uname.get('release')==build['release'] and uname.get('machine')=='aarch64','guest_kernel_identity_mismatch')
    files={}
    for row in user:
        if row.get('event')!='file': continue
        path=row.get('path'); need(path not in files,'duplicate_user_file')
        need(row.get('errno')==0 and row.get('truncated') is False,'user_file_read_incomplete')
        files[path]=row['raw']
    need(files.get('/proc/cmdline','').rstrip('\n')==receipt['cmdline'],'actual_runtime_arguments_mismatch')
    for name in ['possible','present','online']:
        need(cpulist(files.get('/sys/devices/system/cpu/'+name,''))==final[name],'sysfs_mask_not_final_snapshot:'+name)
    offline=cpulist(files['/sys/devices/system/cpu/offline'])
    need(set(offline)==set(final['possible'])-set(final['online']),'offline_set_not_corresponding_to_possible_domain')
    need(files['/sys/devices/system/cpu/kernel_max']=='511\n','compile_capacity_identity_mismatch')
    nodes=[r for r in user if r.get('event')=='dt_cpu']
    expected={r['path']:r['reg_hex'] for r in qualification['CPU_nodes']}
    observed={}
    for node in nodes:
        path=node.get('path',''); match=re.fullmatch(r'/sys/firmware/devicetree/base(/cpus/cpu@[^/]+)/reg',path)
        need(match is not None and match[1] not in observed,'DT_CPU_path_invalid_or_duplicate')
        encoded=node.get('reg_hex',''); need(re.fullmatch(r'[0-9a-f]{8}|[0-9a-f]{16}',encoded) is not None,'DT_reg_invalid')
        need(node.get('bytes')==len(encoded)//2,'DT_reg_length_mismatch'); observed[match[1]]=encoded
    need(observed==expected,'guest_CPU_DT_different_from_qualified_platform')
    trace['files']=files; trace['provided_hardware']=sorted(int(x,16) for x in observed.values())
    trace['profile']=profile['name']; trace['runtime_arguments']=args
    return trace

def collect(name):
    build=load(HERE/'build_complete.json'); guest=load(HERE/'guest_build.json'); qualification=load(HERE/'platform_qualification.json')
    profiles={p['name']:p for p in load(HERE/'boot_matrix.json')['profiles']}; need(name in profiles,'unsupported_profile')
    folder=HERE/'runs'/name; receipt=load(folder/'receipt.json')
    need(receipt['profile']==name and receipt['returncode']==0 and receipt['timed_out'] is False and receipt['qualification']=='collection_complete','guest_collection_not_complete')
    need(receipt['image_sha256']==build['image_sha256']==sha(HERE/'kernel_inputs/Image'),'boot_image_binding_failed')
    need(receipt['config_sha256']==build['config_sha256']==sha(HERE/'kernel.config'),'config_binding_failed')
    need(receipt['initrd_sha256']==guest['initrd_sha256']==sha(HERE/'kernel_inputs/initramfs.cpio.gz'),'PID1_initrd_binding_failed')
    need(receipt['console_sha256']==sha(folder/'console.log') and receipt['stderr_sha256']==sha(folder/'qemu.stderr.log'),'raw_observation_digest_changed')
    need(receipt['runtime_arguments']==profiles[name]['arguments'],'profile_limit_binding_failed')
    argv=receipt['argv']; need(argv[argv.index('-smp')+1]=='17' and argv[argv.index('-cpu')+1]=='cortex-a57','virtual_CPU_identity_mismatch')
    need(argv[argv.index('-machine')+1]=='virt,gic-version=3' and argv[argv.index('-append')+1]==receipt['cmdline'],'machine_or_cmdline_binding_failed')
    console=(folder/'console.log').read_text(encoding='utf-8')
    need('reboot: Power down' in console and 'Kernel panic' not in console,'guest_not_normal_poweroff')
    trace=validate_trace(parse(console),profiles[name],build,receipt,qualification)
    trace['console_sha256']=receipt['console_sha256']; trace['image_sha256']=build['image_sha256']; trace['config_sha256']=build['config_sha256']
    return trace

def projections(trace):
    snaps=trace['snapshots']; final=snaps['common_after_bringup']; selected=snaps['arch_after_prepare']['possible']
    mapping=trace['maps']['arch_after_prepare']; valid={c:r['hardware'] for c,r in mapping.items() if r['valid']}
    targets=[valid[c] for c in selected if c in valid]; provided=set(trace['provided_hardware'])
    bad_hw=[c for c,row in trace['hardware'].items() if row['mapped']!=row['actual']]
    args=trace['runtime_arguments']; selection_limit=next((int(a.split('=')[1]) for a in args if a.startswith('nr_cpus=')),512)
    rebound=snaps['common_after_rebound']
    return {
        'mapping':{'unprovided_hardware':sorted(set(targets)-provided),'missing_selected_map':sorted(set(selected)-set(valid)),
                   'selected_count':len(selected),'unique_target_count':len(set(targets))},
        'hardware':{'mismatched_online_hardware':sorted(bad_hw)},
        'bound':{'runtime_bound':rebound['nr'],'required_logical_upper':max(rebound['possible'])+1},
        'activation':{'online_outside_present':sorted(set(final['online'])-set(final['present'])),
                      'present_outside_possible':sorted(set(final['present'])-set(final['possible'])),
                      'online_count':len(final['online']),'activation_limit':final['max']},
        'selection':{'selected_count':len(final['possible']),'selection_limit':selection_limit}}
