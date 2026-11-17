source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
python3 - <<'PY'
import hashlib
import json
import pathlib
import re
import subprocess

base = pathlib.Path('/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/heldout_commit_20261117')
out = base / 'codex_blind'
patchdir = out / 'full_patches'
patchdir.mkdir(exist_ok=True)
entries = re.findall(r'^\[(\d+)\] ([0-9a-f]{12}) +(.*)$', (base / 'show_heldout.txt').read_text(encoding='utf-8'), re.M)
assert len(entries) == 60
manifest = []
for number, commit, title in entries:
    patch = subprocess.check_output(['git', '-C', '/root/repos/linux', '--no-pager', 'show', '--no-ext-diff', '--format=fuller', commit])
    target = patchdir / f'{int(number):02d}_{commit}.patch'
    target.write_bytes(patch)
    item = dict(k=int(number), commit=commit, title=title, file=target.name, bytes=len(patch), lines=patch.count(b'\n'), sha256=hashlib.sha256(patch).hexdigest())
    manifest.append(item)
    print(f'{int(number):02d} {commit} {item["lines"]:5} lines {item["bytes"]:7} bytes {title}')
(out / 'patch_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('criteria_sha256=' + hashlib.sha256((base / 'criteria.md').read_bytes()).hexdigest())
PY
