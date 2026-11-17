"""Read-only inputs, new-round outputs only. No kernel build or scan here."""
from pathlib import Path
import gzip
import hashlib
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OLD = BASE / 'boundary_enum_20261106'
AUDIT = BASE / 'boundary_audit_20261107'
KSRC = Path('/root/repos/linux')
ARCHES = ('riscv', 'arm64', 'x86_64')

def read(path):
    op = gzip.open if str(path).endswith('.gz') else open
    with op(path, 'rt', encoding='utf-8') as f:
        return json.load(f)

def lines(path):
    op = gzip.open if str(path).endswith('.gz') else open
    with op(path, 'rt', encoding='utf-8') as f:
        for line in f:
            yield json.loads(line)

def write(name, obj):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def sha(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def git(*args, optional=False):
    p = subprocess.run(['git', '--no-optional-locks', '-C', str(KSRC), *args],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if p.returncode and not optional:
        raise RuntimeError((args, p.returncode, p.stderr[-1600:]))
    return None if p.returncode else p.stdout

def revised():
    d = read(AUDIT / 'revised_stats.json')['architectures']
    result = {}
    for arch in ARCHES:
        p = Path(d[arch]['output'])
        assert (p / 'complete.txt').is_file(), p
        result[arch] = p
    return result

def check_criteria():
    expected = (HERE / 'criteria_sha256.txt').read_text().split()[0]
    assert sha(HERE / 'criteria.md') == expected
    return expected

def key(s):
    d = s['definition']
    return (s['kind'], s['usr'], d['file'], d['line'], d['column'])

def side(path):
    return 'arch' if path.removeprefix('@build/').startswith('arch/') else 'public'

def inputs_manifest(paths):
    return {str(p): {'size': p.stat().st_size, 'sha256': sha(p)} for p in paths}

