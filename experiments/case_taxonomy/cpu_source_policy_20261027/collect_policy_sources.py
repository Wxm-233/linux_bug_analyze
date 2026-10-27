"""Pin the normative/default-policy excerpts and whole driver/header files."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
REPO = '/root/repos/linux'
VERSIONS = {'old': '555a0ce4558d87d5b97c4321f34b19e051c7b0c1',
            'fixed': '2c4dcd7fd57b20a21b65da04d89c38a7217d79cf'}
FILES = ['Documentation/admin-guide/cputopology.rst', 'include/linux/topology.h', 'drivers/base/topology.c']

def main():
    out = HERE / 'policy_sources'
    out.mkdir(exist_ok=False)
    rows = []
    for version, revision in VERSIONS.items():
        for name in FILES:
            raw = subprocess.check_output(['git', '-C', REPO, 'show', revision + ':' + name])
            blob = subprocess.check_output(['git', '-C', REPO, 'rev-parse', revision + ':' + name], text=True).strip()
            target = out / version / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            if actual != blob:
                raise ValueError('Git blob mismatch:' + name)
            rows.append({'version': version, 'revision': revision, 'source_path': name, 'git_blob': blob,
                         'sha256': hashlib.sha256(raw).hexdigest(), 'archived_path': str(target.relative_to(HERE))})
    (out / 'manifest.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'pinned_whole_files': len(rows), 'reused_known_case': True}))

if __name__ == '__main__':
    main()
