"""Build the four projection variants and run the frozen 24-record matrix (WSL)."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
OUT = HERE / 'attempt1'
BUILD = Path('/tmp/lba_sparc_identity_20261027')
VARIANTS = [('parent', 64), ('parent', 4096), ('fixed', 64), ('fixed', 4096)]
INPUTS = {'dense_01': '0,1', 'reported_02': '0,2', 'boundary_024': '0,2,4'}
LIMITS = ['none', '2']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    if OUT.exists():
        raise SystemExit('preserve existing attempt1')
    OUT.mkdir()
    BUILD.mkdir(parents=True, exist_ok=True)
    gcc = subprocess.run(['gcc', '--version'], capture_output=True, text=True).stdout.splitlines()[0]
    builds, records = [], []
    for version, nr in VARIANTS:
        exe = BUILD / f'proj_{version}_{nr}'
        cmd = ['gcc', '-std=gnu11', '-O0', '-Wall', '-Wno-unused-function', f'-DNR_CPUS={nr}',
               '-I', str(HERE), '-o', str(exe), str(HERE / 'projection.c')]
        if version == 'fixed':
            cmd.insert(-3, '-DVERSION_FIXED')
        done = subprocess.run(cmd, capture_output=True)
        builds.append({'version': version, 'NR_CPUS': nr, 'argv': cmd, 'returncode': done.returncode,
                       'stderr': done.stderr.decode('utf-8', 'replace'),
                       'binary_sha256': sha(exe.read_bytes()) if exe.exists() else None})
        if done.returncode != 0:
            continue
        for name, ids in INPUTS.items():
            for limit in LIMITS:
                run = subprocess.run([str(exe), ids, limit], capture_output=True, timeout=30)
                raw = run.stdout
                (OUT / f'{version}_{nr}_{name}_L{limit}.stdout').write_bytes(raw)
                try:
                    parsed = json.loads(raw)
                except ValueError:
                    parsed = None
                records.append({'version': version, 'NR_CPUS': nr, 'input': name, 'ids': ids, 'L': limit,
                                'returncode': run.returncode, 'stdout_sha256': sha(raw),
                                'stderr': run.stderr.decode('utf-8', 'replace'), 'observation': parsed})
    receipt = {'gcc': gcc, 'projection_c_sha256': sha((HERE / 'projection.c').read_bytes()),
               'fragment_manifest_sha256': sha((HERE / 'source_manifest.tsv').read_bytes()),
               'builds': builds, 'records': records}
    (OUT / 'execution.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'builds_ok': sum(b['returncode'] == 0 for b in builds), 'records': len(records),
                      'records_rc0': sum(r['returncode'] == 0 for r in records)}))


if __name__ == '__main__':
    main()
