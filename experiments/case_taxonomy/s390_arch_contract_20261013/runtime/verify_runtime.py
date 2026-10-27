"""Verify this bounded run and reject misleading logs; no build or boot."""
from pathlib import Path
import json
import re
import tempfile

from run_runtime import HERE, BASE, VERSIONS, COMMON, analyse, configuration, sha, save


def main():
    rows=[]
    for name in ['old_s390','fixed_s390','old_x86','fixed_x86']:
        dest=HERE/'profiles'/name
        build=json.loads((dest/'build.json').read_text())
        boot=json.loads((dest/'boot.json').read_text())
        variant,arch=name.split('_')
        assert build['profile']==name and build['revision']==VERSIONS[variant]
        assert build['arch']==arch and build['variant']==variant
        for item in ['image','initrd']:
            assert sha(Path(build[item]))==build[item+'_sha256']
        assert sha(dest/'kernel.config')==build['config_sha256']
        actual=configuration(dest/'kernel.config')
        required=COMMON+(['S390','SCHED_TOPOLOGY'] if arch=='s390' else ['X86_64'])
        auto=(dest/'autoconf.h').read_text()
        assert all(actual.get('CONFIG_'+k)=='y' and re.search(r'^#define CONFIG_'+k+r' 1$',auto,re.M) for k in required)
        assert actual['CONFIG_NR_CPUS']=='4' and re.search(r'^#define CONFIG_NR_CPUS 4$',auto,re.M)
        commands=json.loads((dest/'commands.json').read_text())
        boots=[r for r in commands if r['name']=='qemu_boot']
        assert len(boots)==1 and boots[0]['attempt']==1 and boots[0]['exit_code']==0
        assert (dest/'qemu_boot.stderr.log').read_bytes()==b''
        observed=analyse(build,dest/'qemu_boot.stdout.log')
        assert observed==boot['observations'] and observed['status']=='EXPECTED_CONTRAST'
        warnings=re.findall(r'^.*WARNING:.*$',(dest/'qemu_boot.stdout.log').read_text(),re.M)
        assert len(warnings)==(1 if name=='old_s390' else 0)
        assert not warnings or 'sched_core_cpu_starting' in warnings[0]
        lock=next(e for e in observed['events'] if e['cpu']==1 and e['phase']=='lock_snapshot')
        before=next(e for e in observed['events'] if e['cpu']==1 and e['phase']=='arch_before_notify')
        rows.append({'profile':name,'revision':build['revision'],'first_mask':lock['mask'],
            'self':lock['self'],'locks':lock['locks'],'online_at_first_use':lock['online'],
            'prepared_known':before['prepared_known'],'prepared':before['prepared'],
            'core_starting_warning':bool(warnings),'mode':observed['mode'],
            'boot_seconds':boots[0]['seconds'],'log_sha256':sha(dest/'qemu_boot.stdout.log')})
    pairs={}
    for arch in ['s390','x86']:
        old=configuration(HERE/'profiles'/('old_'+arch)/'kernel.config')
        fixed=configuration(HERE/'profiles'/('fixed_'+arch)/'kernel.config')
        differences={k:[old.get(k),fixed.get(k)] for k in set(old)|set(fixed) if old.get(k)!=fixed.get(k)}
        assert set(differences)=={'CONFIG_LOCALVERSION'}
        pairs[arch]=differences
    assert rows[0]['mode']==rows[1]['mode']==[['1','0','0']]
    original=[]
    manifests={}
    for variant in ['old','fixed']:
        manifests[variant]={item['path']:item for item in json.loads((HERE/(variant+'_observer_sources.json')).read_text())['files']}
        for item in manifests[variant].values():
            if item['original_sha256']:
                assert sha(BASE/variant/'linux'/item['path'])==item['original_sha256']
                original.append(variant+':'+item['path'])
    common=['kernel/cpu.c','kernel/sched/core.c','arch/x86/kernel/smpboot.c']
    assert all(manifests['old'][p]['original_sha256']==manifests['fixed'][p]['original_sha256'] for p in common)
    profile=HERE/'profiles'/'old_s390'
    build=json.loads((profile/'build.json').read_text())
    raw=(profile/'qemu_boot.stdout.log').read_text()
    variants={
        'missing_first_consumer':re.sub(r'^.*R4 phase=lock_snapshot cpu=1.*\n','',raw,flags=re.M),
        'pid10_is_not_pid1':raw.replace('machine=s390x pid=1','machine=s390x pid=10'),
        'wrong_online_set':raw.replace('field=online value=0-1','field=online value=0-12'),
        'wrong_cpuhp_state':re.sub(r'(phase=cpuhp_before cpu=1[^\n]* state=)90',r'\g<1>91',raw),
        'inconsistent_self':re.sub(r'(phase=lock_snapshot cpu=1[^\n]* self=)0',r'\g<1>1',raw),
        'duplicate_end':raw+'\nR4_USER end=1\n',
    }
    rejected=[]
    with tempfile.TemporaryDirectory(prefix='r4-log-verification-') as tmp:
        p=Path(tmp)/'log.txt'
        for name,text in variants.items():
            assert text!=raw,name
            p.write_text(text)
            assert analyse(build,p)['status']=='INSUFFICIENT_OR_MISMATCH',name
            rejected.append(name)
    result={'status':'PASS','profiles':rows,'config_differences':pairs,
        'original_observed_files_unchanged':original,'common_and_x86_sources_same':common,
        'misleading_logs_rejected':rejected,
        'kernel_boots':4,'new_cases':0,'external_model_calls':0,
        'scope':'Instrumented ordinary two-CPU initial self-preparation only; no SMT/hotplug/generalization.'}
    save(HERE/'verification.json',result)
    print(json.dumps({'status':result['status'],'boots':4,'misleading_logs_rejected':len(rejected)}))


if __name__=='__main__':main()
