"""Fresh pinned ARM64 source plus observational logging, separate build/cache."""
from pathlib import Path
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import time

HERE=Path(__file__).resolve().parent
ROOT=Path('/root/.cache/linux-bug-analyze/cpu-identity-runtime-20261027')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')

def need(value,reason):
    if not value:
        raise ValueError(reason)

def run(name,argv):
    start=time.monotonic()
    with (HERE/(name+'.stdout.log')).open('xb') as stdout,(HERE/(name+'.stderr.log')).open('xb') as stderr:
        done=subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=900)
    receipt={'argv':argv,'returncode':done.returncode,'seconds':round(time.monotonic()-start,3)}
    save(HERE/(name+'.json'),receipt)
    need(done.returncode==0,name+'_failed')
    return receipt

def insert_once(text,anchor,replacement):
    need(text.count(anchor)==1,'probe_anchor_not_unique:'+anchor[:100])
    return text.replace(anchor,replacement,1)

ARCH_HELPER=r'''
/* Read-only experiment observer; no CPU state or mapping writes. */
static void __init lba_arch_cpu_snapshot(const char *stage)
{
	unsigned int i;

	pr_info("LBA_CPU_SNAPSHOT stage=%s nr=%u max=%u possible=%*pbl present=%*pbl online=%*pbl\n",
		stage, nr_cpu_ids, setup_max_cpus,
		cpumask_pr_args(cpu_possible_mask), cpumask_pr_args(cpu_present_mask),
		cpumask_pr_args(cpu_online_mask));
	for (i = 0; i < 32 && i < NR_CPUS; i++) {
		u64 hwid = cpu_logical_map(i);
		bool domain = i < nr_cpu_ids;

		pr_info("LBA_CPU_MAP stage=%s logical=%u hardware=0x%llx valid=%u domain=%u possible=%d present=%d online=%d\n",
			stage, i, (unsigned long long)hwid, hwid != INVALID_HWID, domain,
			domain ? cpumask_test_cpu(i, cpu_possible_mask) : -1,
			domain ? cpumask_test_cpu(i, cpu_present_mask) : -1,
			domain ? cpumask_test_cpu(i, cpu_online_mask) : -1);
	}
}

'''
COMMON_HELPER=r'''
/* Sample only; preserves all original parameter/selection operations. */
static void __init lba_scope_snapshot(const char *stage)
{
	pr_info("LBA_CPU_SNAPSHOT stage=%s nr=%u max=%u possible=%*pbl present=%*pbl online=%*pbl\n",
		stage, nr_cpu_ids, setup_max_cpus,
		cpumask_pr_args(cpu_possible_mask), cpumask_pr_args(cpu_present_mask),
		cpumask_pr_args(cpu_online_mask));
}

'''

def main():
    qualify=json.loads((HERE/'platform_qualification.json').read_bytes())
    need(qualify['hardware_IDs']==[*range(16),256],'sparse_platform_not_qualified')
    plan=json.loads((HERE/'frozen_plan.json').read_bytes()); revision=plan['revision']
    ROOT.mkdir(exist_ok=False); source=ROOT/'source'; build=ROOT/'build'
    source.mkdir(); build.mkdir()
    start=time.monotonic()
    archive=subprocess.Popen(['git','-C','/root/repos/linux','archive',revision],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    extraction=subprocess.run(['tar','-x','-C',str(source)],stdin=archive.stdout,capture_output=True)
    archive.stdout.close(); stderr=archive.stderr.read(); code=archive.wait()
    (HERE/'source_archive.stderr.log').write_bytes(stderr+extraction.stderr)
    need(code==extraction.returncode==0,'source_archive_failed')
    save(HERE/'source_archive.json',{'revision':revision,'source':str(source),'build':str(build),'seconds':round(time.monotonic()-start,3)})
    paths=['arch/arm64/kernel/smp.c','kernel/smp.c']; changes=[]
    for name in paths:
        path=source/name; before=path.read_text(); expected=(HERE/'sources'/name).read_text()
        need(before==expected,'pinned_probe_source_mismatch:'+name)
        text=before
        if name=='arch/arm64/kernel/smp.c':
            text=insert_once(text,'void __init smp_init_cpus(void)\n',ARCH_HELPER+'void __init smp_init_cpus(void)\n')
            text=insert_once(text,'void __init smp_prepare_cpus(unsigned int max_cpus)\n',
                'void __init smp_prepare_cpus(unsigned int max_cpus)\n')
            anchor='\t}\n}\n\nvoid __init smp_prepare_cpus(unsigned int max_cpus)'
            text=insert_once(text,anchor,'\t}\n\tlba_arch_cpu_snapshot("arch_after_enumeration");\n}\n\nvoid __init smp_prepare_cpus(unsigned int max_cpus)')
            text=insert_once(text,'\tinit_cpu_topology();\n','\tlba_arch_cpu_snapshot("arch_before_prepare");\n\tinit_cpu_topology();\n')
            anchor='\t\tnuma_store_cpu_info(cpu);\n\t}\n}\n\nstatic const char *ipi_types'
            text=insert_once(text,anchor,'\t\tnuma_store_cpu_info(cpu);\n\t}\n\tlba_arch_cpu_snapshot("arch_after_prepare");\n}\n\nstatic const char *ipi_types')
            anchor='\tkasan_init_sw_tags();\n}\n\n/*\n * Duplicate MPIDRs'
            text=insert_once(text,anchor,'\tkasan_init_sw_tags();\n\tpr_info("LBA_CPU_HW logical=%u mapped=0x%llx actual=0x%llx boot=1\\n",\n\t\tsmp_processor_id(), (unsigned long long)cpu_logical_map(smp_processor_id()),\n\t\t(unsigned long long)(read_cpuid_mpidr() & MPIDR_HWID_BITMASK));\n}\n\n/*\n * Duplicate MPIDRs')
            anchor='\tpr_info("CPU%u: Booted secondary processor 0x%010lx [0x%08x]\\n",'
            text=insert_once(text,anchor,'\tpr_info("LBA_CPU_HW logical=%u mapped=0x%llx actual=0x%llx boot=0\\n",\n\t\tcpu, (unsigned long long)cpu_logical_map(cpu), (unsigned long long)mpidr);\n'+anchor)
        else:
            text=insert_once(text,'/* this is hard limit */\n',COMMON_HELPER+'/* this is hard limit */\n')
            anchor='\t\tset_nr_cpu_ids(nr_cpus);\n\n\treturn 0;'
            text=insert_once(text,anchor,'\t\tset_nr_cpu_ids(nr_cpus);\n\n\tlba_scope_snapshot("early_nr_cpus");\n\treturn 0;')
            anchor='\tif (setup_max_cpus == 0)\n\t\tarch_disable_smp_support();\n\n\treturn 0;'
            text=insert_once(text,anchor,'\tif (setup_max_cpus == 0)\n\t\tarch_disable_smp_support();\n\n\tlba_scope_snapshot("early_maxcpus");\n\treturn 0;')
            anchor='\tset_nr_cpu_ids(find_last_bit(cpumask_bits(cpu_possible_mask), NR_CPUS) + 1);'
            text=insert_once(text,anchor,'\tlba_scope_snapshot("common_before_rebound");\n'+anchor+'\n\tlba_scope_snapshot("common_after_rebound");')
            anchor='\tbringup_nonboot_cpus(setup_max_cpus);'
            text=insert_once(text,anchor,'\tlba_scope_snapshot("common_before_bringup");\n'+anchor+'\n\tlba_scope_snapshot("common_after_bringup");')
        path.write_text(text)
        diff=''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
        changes.append({'path':name,'before_sha256':hashlib.sha256(before.encode()).hexdigest(),'after_sha256':sha(path),'diff':diff})
    (HERE/'instrumentation.patch').write_text(''.join(row['diff'] for row in changes),encoding='utf-8')
    save(HERE/'instrumentation.json',{'files':changes,'mapping_writes_added':False,'observer_limit':32,
          'outside_nr_cpu_ids_mask_queries':'not performed; printed as -1 unknown','printk_can_perturb_timing':True})
    shutil.copyfile(HERE/'baseline.config',build/'.config')
    run('set_localversion',[str(source/'scripts/config'),'--file',str(build/'.config'),'--set-str','LOCALVERSION','-lba-cpu-identity'])
    common=['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-']
    run('olddefconfig',common+['olddefconfig'])
    shutil.copyfile(build/'.config',HERE/'kernel.config')
    run('kernel_build',common+['-j12','Image'])
    result={'status':'built','revision':revision,'source_root':str(source),'build_directory':str(build),
            'image':str(build/'arch/arm64/boot/Image'),'image_sha256':sha(build/'arch/arm64/boot/Image'),
            'vmlinux':str(build/'vmlinux'),'vmlinux_sha256':sha(build/'vmlinux'),'config_sha256':sha(build/'.config'),
            'release':(build/'include/config/kernel.release').read_text().strip(),'instrumentation_sha256':sha(HERE/'instrumentation.patch')}
    save(HERE/'build_complete.json',result)
    print(json.dumps(result),flush=True)

if __name__=='__main__':
    main()
