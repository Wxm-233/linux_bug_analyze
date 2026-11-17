"""Compile check of criteria.md section 3 for the RISC-V test patches that apply: for each patched commit and its T^,
extract the tree (git archive), configure defconfig plus KVM, KEXEC_FILE (the options the pairs touch), and build
the objects of the changed .c files, or the directory of a changed Makefile; report whether the patched build adds
errors. Builds run one at a time with -j20. WSL; no model calls. Output: compile_test.json, logs in /root/work/replay_build.
"""
from pathlib import Path
import json
import subprocess

HERE = Path(__file__).resolve().parent
REPO = '/root/repos/linux'
W = Path('/root/work/replay_build')
ENV = 'ARCH=riscv CROSS_COMPILE=riscv64-linux-gnu-'


def sh(cmd):
    r = subprocess.run(['bash', '-c', cmd], capture_output=True)
    return r.returncode, (r.stdout + r.stderr).decode('utf-8', 'replace')


def build(sha, targets):
    src, log = W / f'src-{sha[:12]}', W / f'{sha[:12]}.log'
    if not src.exists():
        src.mkdir(parents=True)
        sh(f'git -C {REPO} archive {sha} | tar -x -C {src}')
        sh(f'cd {src} && make {ENV} defconfig >/dev/null && scripts/config -e KVM -e KEXEC_FILE '
           f'&& make {ENV} olddefconfig >/dev/null && make {ENV} -j20 prepare >/dev/null 2>&1')
    code, out = sh(f'cd {src} && make {ENV} -j20 {" ".join(targets)}')
    log.write_text(out, encoding='utf-8')
    errors = [l for l in out.splitlines() if ' error:' in l or 'Error ' in l]
    return code, errors


def targets_of(files):
    out = []
    for f in files:
        if f.endswith('.c'):
            out.append(f[:-2] + '.o')
        elif f.endswith('Makefile'):
            out.append(f.rsplit('/', 1)[0] + '/')
    return out


def main():
    if (HERE / 'compile_test.json').exists():
        raise SystemExit('preserve')
    W.mkdir(parents=True, exist_ok=True)
    rows = {r['dir']: r for r in json.loads((HERE / 'eval_test.json').read_text(encoding='utf-8'))}
    commits = json.loads((HERE / 'commits_test.json').read_text(encoding='utf-8'))
    result = {}
    for d, c in commits.items():
        r = rows[d]
        if r['target_arch'] != 'riscv' or not c['sha']:
            continue
        targets = targets_of(r['gen_files'])
        base_code, base_err = build(c['base'], targets)
        code, err = build(c['sha'], targets)
        result[d] = {'targets': targets, 'base_ok': base_code == 0, 'patched_ok': code == 0,
                     'new_errors': [e for e in err if e not in base_err][:10]}
        print(d, targets, base_code, code, len(result[d]['new_errors']), flush=True)
    (HERE / 'compile_test.json').write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
