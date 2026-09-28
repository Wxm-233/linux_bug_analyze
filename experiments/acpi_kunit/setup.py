"""Install an explicit early-boot fixture in a dedicated kernel worktree."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from experiments.iommu_contracts.run import function

REV = 'adbf61cc47cb72b102682e690ad323e1eda652c2'
TARGET = 'arch/x86/kernel/acpi/boot.c'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--worktree',type=Path,required=True)
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--mode',choices=['before','after'],required=True)
    a=p.parse_args(); tree=a.worktree.resolve(); out=a.outdir.resolve()
    out.mkdir(parents=True,exist_ok=True)
    def git(*args): return subprocess.check_output(['git','-C',str(tree),*args],text=True)
    assert git('rev-parse','HEAD').strip()==REV
    marker=tree/'.lba-acpi-test.json'
    if marker.exists():
        for name,digest in json.loads(marker.read_text())['files'].items():
            assert hashlib.sha256((tree/name).read_bytes()).hexdigest()==digest,name
    else:
        assert not git('status','--porcelain'), 'Refusing dirty unmarked worktree'
    source=git('show',REV+':'+TARGET)
    if a.mode=='before':
        sig='static bool __init acpi_is_processor_usable('
        old=function(git('show',REV+'^:'+TARGET),sig)
        source=source.replace(function(source,sig),old)
    # Only the policy environment is injected, not the system-wide hypervisor type.
    source=source.replace('return !hypervisor_is_type(X86_HYPER_NATIVE);',
        'return !lba_native_policy();' if a.mode=='after' else 'return !hypervisor_is_type(X86_HYPER_NATIVE);')
    anchor='static int __init acpi_parse_madt('
    source=source.replace(anchor,'#include "lba-acpi-fixture.h"\n\n'+anchor,1)
    anchor='\tif (madt->address) {'
    assert source.count(anchor)==1
    source=source.replace(anchor,'\tlba_prepare_madt(madt);\n\n'+anchor,1)
    source+='\n#include "lba-acpi-tests.c"\n'
    config=git('show',REV+':arch/x86/Kconfig')
    config+='\nconfig LBA_ACPI_CONTRACT_TEST\n\tbool "Isolated QEMU ACPI boot contract fixture"\n\tdepends on X86_64 && ACPI && SMP && KUNIT=y\n\tdefault n\n'
    # Whole experiment is explicitly enabled; fail setup if built without its Kconfig.
    source=source.replace('#include "lba-acpi-fixture.h"',
        '#if !IS_ENABLED(CONFIG_LBA_ACPI_CONTRACT_TEST)\n#error This worktree requires the isolated ACPI test configuration\n#endif\n#include "lba-acpi-fixture.h"')
    files={TARGET:source,'arch/x86/Kconfig':config,
           'arch/x86/kernel/acpi/lba-acpi-fixture.h':Path(__file__).with_name('fixture.h').read_text(),
           'arch/x86/kernel/acpi/lba-acpi-tests.c':Path(__file__).with_name('tests.c').read_text()}
    patches=[]
    for name,content in files.items():
        (tree/name).write_text(content)
        base=git('show',REV+':'+name) if name in (TARGET,'arch/x86/Kconfig') else ''
        patches.append(''.join(difflib.unified_diff(base.splitlines(True),content.splitlines(True),fromfile='a/'+name if base else '/dev/null',tofile='b/'+name)))
    info={'mode':a.mode,'base':REV,'predicate_revision':git('rev-parse',REV+('^' if a.mode=='before' else '')).strip(),
          'files':{n:hashlib.sha256((tree/n).read_bytes()).hexdigest() for n in files}}
    marker.write_text(json.dumps(info,indent=2)+'\n')
    (out/(a.mode+'-source.json')).write_text(json.dumps(info,indent=2)+'\n')
    (out/(a.mode+'.patch')).write_text('\n'.join(patches))
    print(json.dumps(info,indent=2))


if __name__=='__main__': main()
