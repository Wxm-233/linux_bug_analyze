"""Verify real-kernel CPU-mask and APIC-set checks for all isolated boots."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--outdir',type=Path,required=True)
    out=p.parse_args().outdir
    runs={}; summary={}
    names={'fixture_installed','actual_cpu_masks','actual_apic_membership'}
    for mode in ('before','after'):
        run=json.loads((out/(mode+'-run.json')).read_text()); runs[mode]=run
        assert {r['scenario'] for r in run['runs']}==set(range(8))
        assert len(run['runs'])==8
        for name,digest in run['artifacts'].items():
            assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest,name
        summary[mode]=[]
        for row in run['runs']:
            s=row['scenario']; boot=(out/row['log']).read_text()
            assert row['returncode']==0
            assert 'Linux version ' in boot and 'acpi-boot-contract' in boot
            assert f'LBA fixture scenario={s//2} x2={s%2}' in boot
            found=re.findall(r'^\s*(not ok|ok) \d+ (fixture_installed|actual_cpu_masks|actual_apic_membership)\b',boot,re.M)
            assert len(found)==3 and {n for _,n in found}==names,(mode,s,found)
            failed={n for status,n in found if status=='not ok'}
            expected={'actual_cpu_masks','actual_apic_membership'} if mode=='before' and s in (2,3) else set()
            assert failed==expected,(mode,s,failed)
            assert boot.count('EXPECTATION FAILED')==len(expected),(mode,s)
            for unexpected in ('WARNING:', 'BUG:', 'Kernel panic', 'Oops:'):
                assert unexpected not in boot,(mode,s,unexpected)
            summary[mode].append({'scenario':s,'passed':3-len(failed),'failed':sorted(failed)})
    for name in ('arch/x86/Kconfig','arch/x86/kernel/acpi/lba-acpi-fixture.h','arch/x86/kernel/acpi/lba-acpi-tests.c'):
        assert runs['before']['source']['files'][name]==runs['after']['source']['files'][name]
    assert runs['before']['artifacts']['before-config']==runs['after']['artifacts']['after-config']
    assert runs['before']['artifacts']['before-bzImage']!=runs['after']['artifacts']['after-bzImage']
    (out/'verified-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
