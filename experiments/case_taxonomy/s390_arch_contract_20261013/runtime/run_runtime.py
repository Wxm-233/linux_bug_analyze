"""Bounded observational historical startup runs; no API calls."""
from __future__ import annotations
import argparse
import difflib
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
BASE = Path('/root/.cache/linux-bug-analyze/s390-contract-20261013')
RUNTIME = BASE/'runtime'
sys.path.insert(0,str(STAGE))
from run_build import VERSIONS, configuration

HEADER = '''#ifndef _LINUX_R4_OBSERVE_H
#define _LINUX_R4_OBSERVE_H
#include <linux/printk.h>
#include <linux/smp.h>
#include <linux/cpuhotplug.h>
#include <linux/sched/topology.h>
unsigned int r4_next_seq(unsigned int cpu);
static inline void r4_note(const char *phase, unsigned int cpu,
                          int known, int prepared, int state, int target, int ret)
{
    const struct cpumask *mask = cpu_smt_mask(cpu);
    pr_info("R4 phase=%s cpu=%u current=%u seq=%u online=%u mask=%lx self=%u weight=%u prepared_known=%d prepared=%d state=%d target=%d ret=%d sched_state=%d\\n",
        phase, cpu, raw_smp_processor_id(), r4_next_seq(cpu), cpu_online(cpu),
        cpumask_bits(mask)[0], cpumask_test_cpu(cpu, mask), cpumask_weight(mask),
        known, prepared, state, target, ret, CPUHP_AP_SCHED_STARTING);
}
#endif
'''


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(argv, dest, name, timeout=900):
    ledger=dest/'commands.json'
    rows=json.loads(ledger.read_text()) if ledger.exists() else []
    attempt=1+sum(r['name']==name for r in rows)
    stem=name if attempt==1 else name+f'.attempt{attempt}'
    row={'name':name,'attempt':attempt,'argv':argv,'stdout':str(dest/(stem+'.stdout.log')),'stderr':str(dest/(stem+'.stderr.log')),'state':'running'}
    rows.append(row);save(ledger,rows);save(HERE/'progress.json',{'profile':dest.name,**row})
    print(dest.name+': '+name,flush=True)
    start=time.monotonic()
    with open(row['stdout'],'wb') as out,open(row['stderr'],'wb') as err:
        try:code=subprocess.run(argv,stdout=out,stderr=err,timeout=timeout,env=dict(os.environ,LC_ALL='C',LANG='C')).returncode
        except subprocess.TimeoutExpired:code=124
    row.update(state='finished',exit_code=code,seconds=round(time.monotonic()-start,2));save(ledger,rows);save(HERE/'progress.json',{'profile':dest.name,**row})
    if code:raise RuntimeError(f'{name} exit {code}: '+Path(row['stderr']).read_text(errors='replace')[-1800:])
    return row


def replace_once(s,old,new):
    if s.count(old)!=1:raise RuntimeError('Observer anchor not unique: '+old[:90])
    return s.replace(old,new,1)


def instrument(variant):
    original=BASE/variant/'linux'
    assert (BASE/variant/'source_revision').read_text().strip()==VERSIONS[variant]
    modified={}
    def source(rel):return (original/rel).read_text()
    def include(s):return re.sub(r'(?m)^#include ', '#include <linux/r4_observe.h>\n#include ',s,count=1)
    rel='kernel/cpu.c';s=include(source(rel))
    s=replace_once(s,'static int cpuhp_invoke_callback(', 'static DEFINE_PER_CPU(unsigned int, r4_sequence);\nunsigned int r4_next_seq(unsigned int cpu)\n{\n\treturn ++per_cpu(r4_sequence, cpu);\n}\n\nstatic int cpuhp_invoke_callback(')
    s=replace_once(s,'\t\tret = cb(cpu);\n\t\ttrace_cpuhp_exit', '\t\tif (bringup && state == CPUHP_AP_SCHED_STARTING)\n\t\t\tr4_note("cpuhp_before", cpu, 0, -1, state, st->target, 0);\n\t\tret = cb(cpu);\n\t\tif (bringup && state == CPUHP_AP_SCHED_STARTING)\n\t\t\tr4_note("cpuhp_after", cpu, 0, -1, state, st->target, ret);\n\t\ttrace_cpuhp_exit')
    pos=s.index('void notify_cpu_starting(unsigned int cpu)\n{')
    end=s.index('\n}\n',pos)+3
    function=s[pos:end]
    function=replace_once(function,'\trcu_cpu_starting(cpu);\t/* Enables RCU usage on this CPU. */', '\tr4_note("notify_enter", cpu, 0, -1, st->state, target, 0);\n\trcu_cpu_starting(cpu);\t/* Enables RCU usage on this CPU. */')
    function=replace_once(function,'\tret = cpuhp_invoke_callback_range(true, cpu, st, target);','\tret = cpuhp_invoke_callback_range(true, cpu, st, target);\n\tr4_note("notify_exit", cpu, 0, -1, st->state, target, ret);')
    s=s[:pos]+function+s[end:]
    modified[rel]=s
    rel='kernel/sched/core.c';s=include(source(rel))
    anchor='static struct cpumask sched_core_mask;'
    additions='''
struct r4_lock_observation {
    bool active;
    unsigned int seq, self, weight, count, rq_self, online;
    unsigned long mask;
};
static DEFINE_PER_CPU(struct r4_lock_observation, r4_lock_observation);
'''
    s=replace_once(s,anchor,anchor+'\n'+additions)
    s=replace_once(s,'\tint t, i = 0;\n\n\tlocal_irq_save(*flags);','''\tint t, i = 0;
\tstruct r4_lock_observation *o = &per_cpu(r4_lock_observation, cpu);

\tif (o->active) {
\t\to->seq = r4_next_seq(cpu);
\t\to->mask = cpumask_bits(smt_mask)[0];
\t\to->self = cpumask_test_cpu(cpu, smt_mask);
\t\to->weight = cpumask_weight(smt_mask);
\t\to->rq_self = cpu_rq(cpu)->core == cpu_rq(cpu);
\t\to->online = cpu_online(cpu);
\t\to->count = 0;
\t}
\tlocal_irq_save(*flags);''')
    s=replace_once(s,'\tfor_each_cpu(t, smt_mask)\n\t\traw_spin_lock_nested(&cpu_rq(t)->__lock, i++);', '\tfor_each_cpu(t, smt_mask) {\n\t\traw_spin_lock_nested(&cpu_rq(t)->__lock, i++);\n\t\tif (o->active)\n\t\t\to->count++;\n\t}')
    head='static void sched_core_cpu_starting(unsigned int cpu)\n{'
    pos=s.index(head);end=s.index('\n}\n',pos)+3
    function=s[pos:end]
    function=replace_once(function,'\tsched_core_lock(cpu, &flags);','\tper_cpu(r4_lock_observation, cpu).active = true;\n\tr4_note("core_enter", cpu, 0, -1, -1, -1, 0);\n\tsched_core_lock(cpu, &flags);')
    function=replace_once(function,'\tsched_core_unlock(cpu, &flags);','''\tsched_core_unlock(cpu, &flags);
\t{
\t\tstruct r4_lock_observation *o = &per_cpu(r4_lock_observation, cpu);
\t\to->active = false;
\t\tpr_info("R4 phase=lock_snapshot cpu=%u current=%u seq=%u mask=%lx self=%u weight=%u locks=%u rq_self=%u online=%u printed_after_unlock=1\\n",
\t\t\tcpu, raw_smp_processor_id(), o->seq, o->mask, o->self, o->weight, o->count, o->rq_self, o->online);
\t}
\tr4_note("core_exit", cpu, 0, -1, -1, -1, 0);''')
    s=s[:pos]+function+s[end:];modified[rel]=s
    rel='arch/s390/kernel/smp.c';s=include(source(rel))
    known,prep=('1','cpumask_test_cpu(cpu, &cpu_setup_mask)') if variant=='fixed' else ('0','-1')
    before=f'\tr4_note("arch_before_notify", cpu, {known}, {prep}, -1, -1, 0);\n'
    after=f'\tr4_note("arch_after_notify", cpu, {known}, {prep}, -1, -1, 0);'
    s=replace_once(s,'\tnotify_cpu_starting(cpu);',before+'\tnotify_cpu_starting(cpu);\n'+after)
    s=replace_once(s,'\tinc_irq_stat(CPU_RST);',f'\tr4_note("arch_online_ready", cpu, {known}, {prep}, -1, -1, 0);\n\tinc_irq_stat(CPU_RST);')
    modified[rel]=s
    rel='arch/s390/kernel/topology.c';s=source(rel)
    pos=s.index('void __init topology_init_early(void)');end=s.index('\n}\n',pos)+3
    f=s[pos:end];tail='\t__arch_update_dedicated_flag(NULL);'
    f=replace_once(f,tail,tail+'\n\tpr_info("R4_MODE mode=%d facility=%d mtid=%u\\n", topology_mode, !!MACHINE_HAS_TOPOLOGY, smp_cpu_mtid);')
    modified[rel]=s[:pos]+f+s[end:]
    rel='arch/x86/kernel/smpboot.c';s=include(source(rel))
    prep='cpumask_test_cpu(cpuid, cpu_sibling_setup_mask)'
    s=replace_once(s,'\tnotify_cpu_starting(cpuid);',f'\tr4_note("arch_before_notify", cpuid, 1, {prep}, -1, -1, 0);\n\tnotify_cpu_starting(cpuid);\n\tr4_note("arch_after_notify", cpuid, 1, {prep}, -1, -1, 0);')
    modified[rel]=s
    modified['include/linux/r4_observe.h']=HEADER
    return modified


def prepare():
    HERE.mkdir(exist_ok=True)
    env={'tools':{x:shutil.which(x) for x in ['qemu-system-s390x','qemu-system-x86_64','s390x-linux-gnu-gcc','gcc','flex','bison']},'free_gb':round(shutil.disk_usage(BASE).free/2**30,1)}
    save(HERE/'feasibility.json',env)
    if not all(env['tools'].values()):raise RuntimeError('Required existing tool missing')
    for variant in ['old','fixed']:
        modified=instrument(variant)
        patch=''
        manifest=[]
        for rel,new in modified.items():
            p=BASE/variant/'linux'/rel
            old=p.read_text() if p.exists() else ''
            patch+=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
            dest=HERE/'observer_sources'/variant/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(new)
            manifest.append({'path':rel,'original_sha256':sha(p) if p.exists() else None,'observed_sha256':sha(dest)})
        (HERE/(variant+'_observer.patch')).write_text(patch)
        save(HERE/(variant+'_observer_sources.json'),{'revision':VERSIONS[variant],'files':manifest})
    print('Observer diffs prepared; no kernel build or boot.',flush=True)


COMMON=['64BIT','SMP','SCHED_SMT','SCHED_CORE','HOTPLUG_CPU','SYSFS','PROC_FS','BLK_DEV_INITRD','RD_GZIP','BINFMT_ELF','PRINTK','BUG','TTY','DEVTMPFS','FUTEX','MULTIUSER','POSIX_TIMERS','KALLSYMS']


def build(variant,arch):
    name=variant+'_'+arch;dest=HERE/'profiles'/name;dest.mkdir(parents=True,exist_ok=True)
    tree=RUNTIME/variant/'linux';out=RUNTIME/name/'build'
    if not tree.exists():
        shutil.copytree(BASE/variant/'linux',tree)
        for item in json.loads((HERE/(variant+'_observer_sources.json')).read_text())['files']:
            p=tree/item['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((HERE/'observer_sources'/variant/item['path']).read_bytes())
    for item in json.loads((HERE/(variant+'_observer_sources.json')).read_text())['files']:
        if sha(tree/item['path'])!=item['observed_sha256']:raise RuntimeError('Observer source changed')
        original=BASE/variant/'linux'/item['path']
        if item['original_sha256'] and sha(original)!=item['original_sha256']:raise RuntimeError('Original source changed')
    out.mkdir(parents=True,exist_ok=True)
    prefix='s390x-linux-gnu-' if arch=='s390' else ''
    make=['make','-C',str(tree),f'O={out}',f'ARCH={arch}','WERROR=0','HOSTCFLAGS=-Wno-error=use-after-free -Wno-error=deprecated-declarations -Wno-error=format-truncation']
    if prefix:make.append('CROSS_COMPILE='+prefix)
    ready=dest/'build.json'
    if ready.exists():
        row=json.loads(ready.read_text())
        if row.get('status')=='READY':
            if any(row.get(k)!=v for k,v in {'profile':name,'variant':variant,'arch':arch,'revision':VERSIONS[variant]}.items()):raise RuntimeError('Saved profile identity mismatch')
            if row['release']!=(out/'include/config/kernel.release').read_text().strip():raise RuntimeError('Saved release changed')
            for key in ['image','initrd']:
                if sha(Path(row[key]))!=row[key+'_sha256']:raise RuntimeError('Saved runtime artifact changed')
            if sha(out/'.config')!=row['config_sha256']:raise RuntimeError('Saved configuration changed')
            print(name+': reuse completed image',flush=True);return row
    if not (out/'.config').exists():
        command(make+['allnoconfig'],dest,'allnoconfig')
        features=COMMON+(['SCHED_TOPOLOGY','SCLP_TTY','SCLP_CONSOLE','SCLP_VT220_TTY','SCLP_VT220_CONSOLE'] if arch=='s390' else ['SERIAL_8250','SERIAL_8250_CONSOLE','ACPI','PCI','X86_MPPARSE','X86_LOCAL_APIC','X86_IO_APIC'])
        edits=[str(tree/'scripts/config'),'--file',str(out/'.config')]
        for symbol in features:edits+=['--enable',symbol]
        for symbol in ['MODULES','DEBUG_INFO','GCC_PLUGINS','LOCALVERSION_AUTO','WERROR']:edits+=['--disable',symbol]
        edits+=['--set-val','NR_CPUS','4','--set-val','LOG_BUF_SHIFT','18','--set-str','LOCALVERSION','-r4-observe-'+name]
        command(edits,dest,'config_edits');command(make+['olddefconfig'],dest,'olddefconfig')
    values=configuration(out/'.config')
    required=COMMON+(['S390','SCHED_TOPOLOGY','SCLP_VT220_CONSOLE'] if arch=='s390' else ['X86_64','SERIAL_8250_CONSOLE','X86_LOCAL_APIC','X86_MPPARSE'])
    missing=[k for k in required if values.get('CONFIG_'+k)!='y']
    if missing or values.get('CONFIG_NR_CPUS')!='4':raise RuntimeError('Effective configuration missing: '+str(missing))
    sibling=HERE/'profiles'/(('fixed' if variant=='old' else 'old')+'_'+arch)/'kernel.config'
    if sibling.exists():
        other=configuration(sibling)
        differences={k:[values.get(k),other.get(k)] for k in set(values)|set(other) if values.get(k)!=other.get(k) and k!='CONFIG_LOCALVERSION'}
        if differences:raise RuntimeError('Old/fixed effective config mismatch: '+str(differences))
    (dest/'kernel.config').write_bytes((out/'.config').read_bytes())
    command(make+['-j4','bzImage'],dest,'kernel_build')
    machine='IBM S/390' if arch=='s390' else 'Advanced Micro Devices X86-64'
    command([prefix+'readelf','-h',str(out/'vmlinux')],dest,'kernel_elf')
    if machine not in (dest/'kernel_elf.stdout.log').read_text():raise RuntimeError('Wrong ELF machine')
    image=out/f'arch/{arch}/boot/bzImage'
    pid1=out/'pid1.elf'
    command([prefix+'gcc','-static','-Os','-std=c11','-Wall','-Wextra','-fno-pie','-no-pie',str(HERE/'init_probe.c'),'-o',str(pid1)],dest,'init_build')
    command([prefix+'readelf','-h','-l',str(pid1)],dest,'init_elf')
    init_elf=(dest/'init_elf.stdout.log').read_text()
    if 'INTERP' in init_elf or machine not in init_elf:raise RuntimeError('Invalid init ELF')
    listing=out/'initramfs.list';listing.write_text('dir /dev 755 0 0\ndir /proc 755 0 0\ndir /sys 755 0 0\nnod /dev/console 600 0 0 c 5 1\n'+f'file /init {pid1} 755 0 0\n')
    cpio=subprocess.check_output([str(out/'usr/gen_init_cpio'),str(listing)])
    initrd=out/'initramfs.cpio.gz';initrd.write_bytes(gzip.compress(cpio,mtime=0))
    (dest/'autoconf.h').write_bytes((out/'include/generated/autoconf.h').read_bytes())
    auto=(dest/'autoconf.h').read_text()
    auto_missing=[k for k in required if not re.search(r'^#define CONFIG_'+re.escape(k)+r' 1$',auto,re.M)]
    if auto_missing or not re.search(r'^#define CONFIG_NR_CPUS 4$',auto,re.M):raise RuntimeError('Generated autoconf missing: '+str(auto_missing))
    row={'status':'READY','profile':name,'variant':variant,'arch':arch,'revision':VERSIONS[variant],'source_instrumented':True,'source_tree':str(tree),'build_directory':str(out),'image':str(image),'image_sha256':sha(image),'initrd':str(initrd),'initrd_sha256':sha(initrd),'config_sha256':sha(out/'.config'),'release':(out/'include/config/kernel.release').read_text().strip(),'effective_required':{k:values['CONFIG_'+k] for k in required}}
    save(ready,row);return row


def analyse(row,log):
    raw=log.read_text(errors='replace');events=[]
    for index,line in enumerate(raw.splitlines()):
        m=re.search(r'\bR4 phase=(\w+) (.*)',line)
        if not m:continue
        fields=dict(re.findall(r'(\w+)=([^\s]+)',m[2]));e={'phase':m[1],'line':index+1}
        for k,v in fields.items():e[k]=int(v,16 if k=='mask' else 10)
        events.append(e)
    target=[e for e in events if e.get('cpu')==1]
    phases=['arch_before_notify','notify_enter','cpuhp_before','core_enter','lock_snapshot','core_exit','cpuhp_after','notify_exit','arch_after_notify']
    found={p:[e for e in target if e['phase']==p] for p in phases}
    machine='s390x' if row['arch']=='s390' else 'x86_64'
    identities=re.findall(r'R4_USER release=(\S+) machine=(\S+) pid=(\d+)\s*$',raw,re.M)
    users={}
    for name,value in re.findall(r'R4_USER field=(\w+) value=([^\r\n]*)',raw):users.setdefault(name,[]).append(value.strip())
    modes=[list(m) for m in re.findall(r'R4_MODE mode=(\d+) facility=(\d+) mtid=(\d+)\s*$',raw,re.M)]
    foundation={'all_events_exactly_once':all(len(v)==1 for v in found.values()),
        'pid1_and_release':identities==[(row['release'],machine,'1')],
        'two_online':users.get('online')==['0-1'],
        'thread_membership':users.get('cpu1_threads')==['1'],
        'user_end':len(re.findall(r'R4_USER end=1\s*$',raw,re.M))==1,
        'mounts':len(re.findall(r'R4_USER mount_proc=0 mount_sysfs=0\s*$',raw,re.M))==1,
        'user_read_errors_absent':not re.search(r'R4_USER field=\w+ error=',raw),
        'case_cmdline':len(users.get('cmdline',[]))==1 and f'r4_case={row["profile"]}' in users['cmdline'][0].split(),
        'mode_initialized_no_smt':row['arch']!='s390' or (len(modes)==1 and int(modes[0][0]) in [0,1,2] and int(modes[0][2])==0)}
    if foundation['all_events_exactly_once']:
        ordered=[found[p][0] for p in phases]
        foundation['sequence_order']=all(a['seq']<b['seq'] for a,b in zip(ordered,ordered[1:]))
        foundation['current_cpu_matches']=all(e['current']==1 for e in ordered)
        foundation['real_cpuhp_state']=found['cpuhp_before'][0]['state']==found['cpuhp_after'][0]['state']==found['cpuhp_before'][0]['sched_state']
        foundation['callback_return_zero']=found['cpuhp_after'][0]['ret']==0 and found['notify_exit'][0]['ret']==0
        foundation['mask_fields_consistent']=all(e['weight']==e['mask'].bit_count() and e['self']==((e['mask']>>1)&1) and e['mask']<16 for e in ordered)
        foundation['mask_stable_before_consumer']=len({found[p][0]['mask'] for p in ['arch_before_notify','notify_enter','cpuhp_before','core_enter','lock_snapshot']})==1
        if row['arch']=='s390':
            ready=[e for e in target if e['phase']=='arch_online_ready']
            foundation['final_arch_ready']=len(ready)==1 and ready[0]['seq']>ordered[-1]['seq'] and ready[0]['current']==1 and ready[0]['online']==1 and ready[0]['self']==1
        old=row['arch']=='s390' and row['variant']=='old'
        core=found['lock_snapshot'][0];before=found['arch_before_notify'][0]
        contract={'pre_notify_offline':before['online']==0,'first_consumption_offline':core['online']==0,'actual_lock_count_matches_weight':core['locks']==core['weight'],'self_matches_expected':core['self']==(0 if old else 1),'lock_count_matches_expected':core['locks']==0 if old else core['locks']>=1,'arch_first_self_matches':before['self']==(0 if old else 1),'setup_source_matches':(before['prepared_known']==0 and before['prepared']==-1) if old else (before['prepared_known']==1 and before['prepared']==1),'captured_before_locks_printed_after_unlock':core['printed_after_unlock']==1}
    else:contract={}
    return {'status':'EXPECTED_CONTRAST' if all(foundation.values()) and contract and all(contract.values()) else 'INSUFFICIENT_OR_MISMATCH','foundation':foundation,'contract':contract,'events':events,'mode':modes,'user_fields':users,'warning_mentions_core_starting':'WARNING:' in raw and 'sched_core_cpu_starting' in raw}


def boot(row):
    dest=HERE/'profiles'/row['profile'];result=dest/'boot.json'
    if result.exists():raise RuntimeError('Boot already recorded; inspect saved log instead of restarting')
    ledger=dest/'commands.json'
    if ledger.exists() and any(r['name']=='qemu_boot' for r in json.loads(ledger.read_text())):
        raise RuntimeError('Boot was already attempted; preserve the failure and inspect saved logs')
    arch=row['arch'];console='ttysclp0' if arch=='s390' else 'ttyS0'
    topology=['-machine','s390-ccw-virtio-8.2','-cpu','max','-smp','2'] if arch=='s390' else ['-machine','pc-i440fx-8.2','-cpu','qemu64','-smp','2,sockets=1,cores=2,threads=1']
    argv=['qemu-system-s390x' if arch=='s390' else 'qemu-system-x86_64','-accel','tcg']+topology+['-m','512','-nographic','-monitor','none','-no-reboot','-nic','none','-kernel',row['image'],'-initrd',row['initrd'],'-append',f'console={console} rdinit=/init panic=1 loglevel=7 r4_case={row["profile"]}']
    receipt=command(argv,dest,'qemu_boot',timeout=90)
    result_row={'profile':row['profile'],'receipt':receipt,'observations':analyse(row,Path(receipt['stdout']))}
    save(result,result_row)
    print(row['profile']+': '+result_row['observations']['status'],flush=True)
    return result_row


def main():
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--profile',choices=['old_s390','fixed_s390','old_x86','fixed_x86']);p.add_argument('--build-only',action='store_true');args=p.parse_args()
    if args.prepare:prepare();return
    if not args.profile:p.error('Specify one bounded profile')
    if not (HERE/'observer_review.md').exists():raise RuntimeError('Independent observer source review missing')
    variant,arch=args.profile.split('_')
    try:
        row=build(variant,arch)
        if not args.build_only:boot(row)
    except Exception as exc:
        save(HERE/('error_'+args.profile+'.json'),{'profile':args.profile,'error':str(exc),'status':'INCOMPLETE'});raise


if __name__=='__main__':main()
