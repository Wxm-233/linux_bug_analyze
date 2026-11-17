source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail

cd "$REPO/experiments/case_taxonomy/boundary_enum_20261106"
sha256sum --check criteria_sha256.txt
test "$(cat "$KBUILD/completed.txt")" = success
test "$(git -C "$KSRC" rev-parse HEAD)" = "$(cat "$KBUILD/source_head.txt")"
test -z "$(git --no-optional-locks -C "$KSRC" status --porcelain=v1)"
test ! -s "$KBUILD/source_status_before.txt"
test ! -s "$KBUILD/source_status_after.txt"
test "$(clang --version)" = "$(cat "$KBUILD/clang_version.txt")"
for arch in riscv arm64 x86_64; do
    out="$KBUILD/${arch}_defconfig"
    test "$(cat "$out/status.txt")" = success
    sha256sum --check "$out/config.sha256"
    test -s "$out/vmlinux"
done

python3 -B - <<'PY'
from collections import Counter
from pathlib import Path
from clang import cindex
import json
import os
import shlex

cindex.Index.create()
print(f"libclang: {cindex.conf.lib._name}")
for name in ('clang_getCursorBinaryOperatorKind', 'clang_getCursorUnaryOperatorKind'):
    print(name, hasattr(cindex.conf.lib, name))
for arch in ('riscv', 'arm64', 'x86_64'):
    build = Path(os.environ['KBUILD']) / f'{arch}_defconfig'
    rows = json.loads((build / 'compile_commands.json').read_text())
    sources = Counter(Path(row['file']).suffix for row in rows)
    print(f'{arch}: {len(rows)} entries, {dict(sources)}')
    args = [shlex.split(row['command']) for row in rows]
    print(f"  drivers: {dict(Counter(a[0] for a in args))}; -o: {sum('-o' in a for a in args)}")
    print(f"  vmlinux.a: {(build / 'vmlinux.a').is_file()}")
    print(f"  first C command: {next(row['command'] for row in rows if row['file'].endswith('.c'))}")
PY
