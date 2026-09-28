"""Prepare a fixed, dedicated worktree for in-kernel VT-d encoding tests."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

REV='6f5dc7658094610debe2fad1b09a2034e14857b1'
TARGET='drivers/iommu/intel/iommu.c'
KCONFIG='drivers/iommu/intel/Kconfig'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worktree', type=Path, required=True)
    parser.add_argument('--mode', choices=['before','after'], required=True)
    parser.add_argument('--outdir', type=Path, required=True)
    args=parser.parse_args()
    tree=args.worktree.resolve(); out=args.outdir.resolve(); out.mkdir(parents=True,exist_ok=True)
    def git(*parts):
        return subprocess.check_output(['git','-C',str(tree),*parts],text=True)
    if git('rev-parse','HEAD').strip()!=REV:
        raise RuntimeError('Dedicated worktree must be at the fixed repair commit')
    marker=tree/'.lba-vtd-kunit.json'
    dirty=git('status','--porcelain','--untracked-files=normal')
    if dirty and not marker.exists():
        raise RuntimeError('Refusing to overwrite a dirty unmarked worktree')
    if marker.exists():
        prior=json.loads(marker.read_text())
        for path,digest in prior['managed_files'].items():
            if hashlib.sha256((tree/path).read_bytes()).hexdigest()!=digest:
                raise RuntimeError('Managed file changed outside setup: '+path)
    source=git('show',REV+('^' if args.mode=='before' else '')+':'+TARGET)
    begin=source.index('\tattr = prot &')
    end=source.index('\tdomain->has_mappings',begin)
    block=source[begin:end]
    assert block.count('domain->use_first_level')==1
    helper=('static u64 intel_iommu_encode_pte_attr(bool first_level, int prot)\n{\n\tu64 attr;\n\n'
            +block.replace('domain->use_first_level','first_level')+'\treturn attr;\n}\n\n')
    source=source[:begin]+'\tattr = intel_iommu_encode_pte_attr(domain->use_first_level, prot);\n\n'+source[end:]
    # Place directly before __domain_mapping, using its declaration start.
    location=source.index('__domain_mapping(')
    line=source.rfind('\n',0,location)+1
    # The return type is on the preceding line in this fixed revision.
    if not source[line:location].strip():
        line=source.rfind('\n',0,line-1)+1
    source=source[:line]+helper+source[line:]
    source+='\n#if IS_ENABLED(CONFIG_INTEL_IOMMU_PTE_CONTRACT_TEST)\n#include "pte-contract-test.c"\n#endif\n'
    (tree/TARGET).write_text(source)
    config=git('show',REV+':'+KCONFIG)
    config+='\nconfig INTEL_IOMMU_PTE_CONTRACT_TEST\n\tbool "Intel IOMMU PTE encoding contract tests"\n\tdepends on INTEL_IOMMU && KUNIT=y\n\tdefault n\n\thelp\n\t  Test the production PTE attribute helper without requiring hardware.\n'
    (tree/KCONFIG).write_text(config)
    test_path='drivers/iommu/intel/pte-contract-test.c'
    shutil.copyfile(Path(__file__).with_name('pte-contract-test.c'),tree/test_path)
    files={p:hashlib.sha256((tree/p).read_bytes()).hexdigest() for p in [TARGET,KCONFIG,test_path]}
    metadata={'mode':args.mode,'base_revision':REV,'encoding_revision':git('rev-parse',REV+('^' if args.mode=='before' else '')).strip(),
              'managed_files':files,'helper_transform':'original attr block; domain->use_first_level replaced with bool parameter; caller invokes same helper'}
    marker.write_text(json.dumps(metadata,indent=2)+'\n')
    (out/(args.mode+'-source.json')).write_text(json.dumps(metadata,indent=2)+'\n')
    addition=('diff --git a/'+test_path+' b/'+test_path+'\nnew file mode 100644\n'
              +''.join(difflib.unified_diff([], (tree/test_path).read_text().splitlines(True),
                                          fromfile='/dev/null', tofile='b/'+test_path)))
    (out/(args.mode+'.patch')).write_text(git('diff','--',TARGET,KCONFIG)+addition)
    shutil.copyfile(tree/test_path,out/'pte-contract-test.c')
    print(json.dumps(metadata,indent=2))


if __name__=='__main__': main()
