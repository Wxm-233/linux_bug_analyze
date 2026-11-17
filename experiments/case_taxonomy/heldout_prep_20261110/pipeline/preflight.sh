source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
python3 - <<'PY'
import json, os
from pathlib import Path
paths = ['/root/work/casemodel/facts/CUR.json.gz', '/root/work/static2/facts/CUR.json.gz', '/root/work/static2/values/CUR.json', '/root/work/pgdev/patches_x86_arm64.json.gz', '/root/work/heldout/build/cur_loongarch/vmlinux']
for p in paths:
    f=Path(p); print(p, 'exists', f.exists(), 'bytes', f.stat().st_size if f.exists() else None)
for a in ('riscv','arm64','x86_64'):
    b=Path('/root/work/boundary_build') / (a+'_defconfig')
    print(a, 'mmap_cmd', (b/'mm/.mmap.o.cmd').exists(), 'cc', (b/'compile_commands.json').exists())
    if a=='riscv':
        cc=json.loads((b/'compile_commands.json').read_text())
        entries=[e for e in cc if e['file'].endswith('kernel/futex/syscalls.c')]
        print('futex_commands', json.dumps(entries))
import clang.cindex as ci
print('libclang', ci.__file__, ci.Index.create() is not None)
PY
