"""Verify the expected old-fails/new-passes kernel experiment and artifact hashes."""
import argparse
import hashlib
import json
from pathlib import Path

NAMES={'first_level_read_only','first_level_read_write','first_level_wo_not_representable',
       'second_level_read_only','second_level_write_only','second_level_read_write'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir',type=Path,required=True)
    parser.add_argument('--pagetable',action='store_true',help='Verify the expanded public-API/page-table suite')
    args=parser.parse_args(); out=args.outdir
    names=set(NAMES)
    failures={'second_level_write_only'}
    if args.pagetable:
        names.update({'map_first_ro','map_first_rw','map_first_wo_characterization',
                      'map_second_ro','map_second_rw','map_second_wo',
                      'map_second_wo_cross_boundary','map_second_no_permissions'})
        failures.update({'map_second_wo','map_second_wo_cross_boundary'})
    runs={}; result={}
    for mode in ('before','after'):
        run=json.loads((out/(mode+'-run.json')).read_text());runs[mode]=run
        assert run['returncode']==(1 if mode=='before' else 0),run
        for name,digest in run['artifacts'].items():
            assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest,name
        data=json.loads((out/(mode+'-kunit.json')).read_text())
        suites=[g for g in data['sub_groups'] if g['name']=='intel-iommu-pte-contract']
        assert len(suites)==1
        cases={c['name']:c['status'] for c in suites[0]['test_cases']}
        assert set(cases)==names and len(suites[0]['test_cases'])==len(names)
        for name,status in cases.items():
            assert status==('FAIL' if mode=='before' and name in failures else 'PASS'),(mode,name,status)
        config=(out/(mode+'-config')).read_text()
        for flag in ('X86_64','INTEL_IOMMU','KUNIT','INTEL_IOMMU_PTE_CONTRACT_TEST'):
            assert 'CONFIG_'+flag+'=y\n' in config
        boot=(out/(mode+'-boot.log')).read_text()
        assert 'Linux version ' in boot and 'intel-iommu-pte-contract' in boot
        if args.pagetable:
            assert boot.count('EXPECTATION FAILED')==(4 if mode=='before' else 0)
            for unexpected in ('WARNING:', 'BUG:', 'Kernel panic', 'Oops:'):
                assert unexpected not in boot,(mode,unexpected)
        result[mode]={'cases':cases,'passed':sum(v=='PASS' for v in cases.values()),
                      'failed':sum(v=='FAIL' for v in cases.values()),'elapsed_seconds':run['elapsed_seconds']}
    for path in ('drivers/iommu/intel/Kconfig','drivers/iommu/intel/pte-contract-test.c'):
        assert runs['before']['source']['managed_files'][path]==runs['after']['source']['managed_files'][path]
    assert runs['before']['artifacts']['before-config']==runs['after']['artifacts']['after-config']
    assert runs['before']['artifacts']['before-bzImage']!=runs['after']['artifacts']['after-bzImage']
    result['scope']='real x86 kernel / real Intel IOMMU encoding helper; no page-table installation or DMA access test'
    if args.pagetable:
        result['scope']='real x86 kernel / public iommu_map and iommu_unmap / production Intel ops / allocated page tables and leaf readback; detached domain, no device DMA or hardware IOTLB validation'
        assert hashlib.sha256((out/'pte-contract-test.c').read_bytes()).hexdigest()==runs['after']['source']['managed_files']['drivers/iommu/intel/pte-contract-test.c']
    result['unsupported_case']='first_level_wo_not_representable is characterization, not WO support'
    (out/'verified-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
