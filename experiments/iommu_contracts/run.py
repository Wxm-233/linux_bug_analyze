"""Compile source slices from fixed commits. No network, API or kernel execution."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

VTD = '6f5dc7658094610debe2fad1b09a2034e14857b1'
SMMU = '8c73c32c83ce7f3c31864cb044abd3daefacd996'


def function(source, signature):
    start = source.index(signature)
    # Preserve offsets while hiding comments and strings before counting braces.
    masked = re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',
                    lambda m: ' ' * len(m[0]), source, flags=re.S)
    begin = masked.index('{', start)
    depth = 0
    for end in range(begin, len(masked)):
        if masked[end] == '{': depth += 1
        elif masked[end] == '}':
            depth -= 1
            if depth == 0: return source[start:end+1]
    raise ValueError('unclosed function')


def permission_verdict(first, requested, encoded):
    # Contract chosen for the experiment: exact R/W preservation on supported modes.
    if first and requested == 2:
        return 'unsupported_requires_negotiation'
    return 'pass' if encoded == requested else 'permission_mismatch'


def transition_verdict(row):
    s, trace = row['scenario'], row['trace']
    if not trace or any(x not in (0, 1, 2) for x in trace):
        return ['invalid_trace']
    errors = []
    if s in (0, 2, 3, 4) and 1 in trace:
        errors.append('unexpected_bypass')
    if s == 1 and 0 in trace:
        errors.append('direct_mapping_interrupted')
    expected_rc = -12 if s in (2, 3) else (-16 if s == 4 else 0)
    if row['rc'] != expected_rc: errors.append('unexpected_return_code')
    if s in (0, 1) and trace[-1] != 2: errors.append('target_not_reached')
    if s in (2, 3, 4) and trace[-1] != 0: errors.append('failed_attach_not_isolated')
    if s in (5, 6):
        expected = 0 if row['disable_bypass'] and s == 5 else 1
        if trace[-1] != expected: errors.append('release_policy_mismatch')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--linux-dir', type=Path, required=True)
    parser.add_argument('--outdir', type=Path, required=True)
    args = parser.parse_args()
    out = args.outdir.resolve(); out.mkdir(parents=True, exist_ok=True)
    evidence = out/'source'; evidence.mkdir(exist_ok=True)
    manifest = {'method':'source-slice C execution with test doubles; not kernel/hardware reproduction',
                'sources':[], 'compiler':subprocess.check_output(['gcc','--version'],text=True).splitlines()[0]}
    def read(ref, path):
        data = subprocess.check_output(['git','-C',str(args.linux_dir),'show',ref+':'+path])
        name = ref.replace('^','-parent')+'-'+path.replace('/','_')
        (evidence/name).write_bytes(data)
        resolved = subprocess.check_output(['git','-C',str(args.linux_dir),'rev-parse',ref],text=True).strip()
        manifest['sources'].append({'ref':ref,'resolved_commit':resolved,'path':path,'sha256':hashlib.sha256(data).hexdigest(),'snapshot':name})
        return data.decode()
    def compile_run(name, source):
        f = out/(name+'.c'); f.write_text(source)
        exe = out/name
        subprocess.run(['gcc','-std=gnu11','-O0','-Wall','-Wextra','-Werror',str(f),'-o',str(exe)],check=True)
        return [json.loads(line) for line in subprocess.check_output([str(exe)],text=True).splitlines()]
    results = {'vtd':{},'smmu':{}}
    for label, suffix in [('before','^'),('after','')]:
        ref = VTD+suffix
        source = read(ref,'drivers/iommu/intel/iommu.c')
        header = read(ref,'drivers/iommu/intel/iommu.h')
        public = read(ref,'include/linux/iommu.h')
        macros = []
        for name in ('DMA_PTE_READ','DMA_PTE_WRITE','DMA_PTE_SNP','DMA_FL_PTE_PRESENT',
                     'DMA_FL_PTE_US','DMA_FL_PTE_ACCESS','DMA_FL_PTE_DIRTY','IOMMU_READ','IOMMU_WRITE'):
            macros.append(re.search(r'^#define\s+'+name+r'\s+[^\n]+',header+'\n'+public,re.M)[0])
        attr_start = source.index('\tattr = prot &')
        attr = source[attr_start:source.index('\tdomain->has_mappings',attr_start)]
        map_fn = function(source, 'static int intel_iommu_map(')
        convert = map_fn[map_fn.index('\tif (iommu_prot & IOMMU_READ)'):map_fn.index('\tmax_addr =')]
        code = '#include <stdint.h>\n#include <stdbool.h>\n#include <stdio.h>\n#define BIT_ULL(n) (1ULL << (n))\n'
        code += '\n'.join(macros)+'\nstruct dmar_domain { bool use_first_level, set_pte_snp; };\n'
        code += 'static uint64_t encode(int first, int iommu_prot) {\nstruct dmar_domain storage={first,false};\nstruct dmar_domain *domain=&storage,*dmar_domain=&storage;\nint prot=0; uint64_t attr;\n'
        code += convert+attr+'return attr;\n}\n'
        code += Path(__file__).with_name('vtd_main.c').read_text()
        rows = compile_run('vtd-'+label,code)
        for row in rows: row['verdict']=permission_verdict(row['first'],row['requested'],row['encoded'])
        results['vtd'][label]=rows
        source = read(SMMU+suffix,'drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.c')
        functions = '\n\n'.join(function(source,signature) for signature in (
            'static void arm_smmu_detach_dev(', 'static int arm_smmu_attach_dev(',
            'static void arm_smmu_release_device('))
        template = Path(__file__).with_name('smmu_harness.c').read_text()
        rows = compile_run('smmu-'+label,template.replace('/* EXTRACTED_FUNCTIONS */',functions))
        for row in rows: row['violations']=transition_verdict(row)
        results['smmu'][label]=rows
    # These checks verify the discriminating experiment, not that old code is safe.
    assert sum(r['verdict']=='permission_mismatch' for r in results['vtd']['before']) == 1
    assert sum(r['verdict']=='permission_mismatch' for r in results['vtd']['after']) == 0
    assert any(r['violations'] for r in results['smmu']['before'])
    assert all(not r['violations'] for r in results['smmu']['after'])
    results['summary'] = {
        'vtd':{k:{'supported':sum(r['verdict']!='unsupported_requires_negotiation' for r in rows),
                  'mismatch':sum(r['verdict']=='permission_mismatch' for r in rows)} for k,rows in results['vtd'].items()},
        'smmu':{k:{'scenarios':len(rows),'violations':sum(bool(r['violations']) for r in rows)} for k,rows in results['smmu'].items()}}
    manifest['harness_sha256']=hashlib.sha256(Path(__file__).with_name('smmu_harness.c').read_bytes()).hexdigest()
    manifest['runner_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    manifest['vtd_main_sha256']=hashlib.sha256(Path(__file__).with_name('vtd_main.c').read_bytes()).hexdigest()
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results['summary'],indent=2))


if __name__ == '__main__':
    main()
