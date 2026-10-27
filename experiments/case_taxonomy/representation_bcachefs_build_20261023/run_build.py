"""Actual historical translation-unit builds; run with WSL Python, once per stage."""
from pathlib import Path
import concurrent.futures
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
CACHE = Path('/root/.cache/linux-bug-analyze/bcachefs-representation-20261023')
REPO = Path('/root/repos/linux')
REVISIONS = {
    'parent': '9852d85ec9d492ebef56dc5f229416c925758edc',
    'fix': '2007d28ec0095c6db0a24fd8bb8fe280c65446cd',
}
ENV = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')
for key in ['KCFLAGS', 'KCPPFLAGS', 'CFLAGS', 'CPPFLAGS', 'KBUILD_OUTPUT',
            'KCONFIG_CONFIG', 'CROSS_COMPILE', 'ARCH', 'LLVM']:
    ENV.pop(key, None)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def command(argv, folder, label, timeout=900):
    started = time.monotonic()
    with (folder / (label + '.log')).open('wb') as out:
        try:
            done = subprocess.run(argv, stdout=out, stderr=subprocess.STDOUT,
                                  env=ENV, stdin=subprocess.DEVNULL, timeout=timeout)
            code = done.returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    result = {'argv': list(map(str, argv)), 'exit_code': code,
              'elapsed_seconds': round(time.monotonic() - started, 3)}
    write_json(folder / (label + '.json'), result)
    print(json.dumps({'phase': label, 'profile': folder.name, 'exit_code': code}), flush=True)
    return result


def build(profile):
    version, arch, cross = profile
    name = version + '_' + arch
    folder = HERE / 'runs' / name
    folder.mkdir(parents=True, exist_ok=False)
    source = CACHE / ('source-' + version)
    output = CACHE / 'build' / name
    output.mkdir(parents=True, exist_ok=False)
    base = ['make', '-C', str(source), 'O=' + str(output), 'ARCH=' + arch,
            'CROSS_COMPILE=' + cross]
    result = {'profile': name, 'revision': REVISIONS[version],
              'source': str(source), 'output': str(output), 'steps': []}
    for label, args in [
        ('defconfig', base + ['defconfig']),
        ('enable_filesystem', [str(source / 'scripts/config'), '--file', str(output / '.config'),
                               '--enable', 'BCACHEFS_FS']),
        ('olddefconfig', base + ['olddefconfig']),
    ]:
        row = command(args, folder, label)
        result['steps'].append(row)
        if row['exit_code'] != 0:
            result['status'] = 'configuration_blocked'
            write_json(folder / 'result.json', result)
            return result
    config = (output / '.config').read_text()
    shutil.copyfile(output / '.config', folder / 'used.config')
    result['config_sha256'] = hashlib.sha256((output / '.config').read_bytes()).hexdigest()
    result['filesystem_enabled'] = 'CONFIG_BCACHEFS_FS=y\n' in config
    result['block_enabled'] = 'CONFIG_BLOCK=y\n' in config
    if not result['filesystem_enabled'] or not result['block_enabled']:
        result['status'] = 'configuration_not_eligible'
        write_json(folder / 'result.json', result)
        return result
    cc = cross + 'gcc'
    defines = subprocess.run([cc, '-dM', '-E', '-'], input=b'', capture_output=True, env=ENV, check=True)
    (folder / 'compiler_defines.txt').write_bytes(defines.stdout)
    result['byte_order_definitions'] = [line for line in defines.stdout.decode().splitlines()
                                        if '__BYTE_ORDER__' in line or '__ORDER_' in line]
    row = command(base + ['-j4', 'V=1', 'fs/bcachefs/bkey.o'], folder, 'compile')
    result['steps'].append(row)
    result['compile_exit'] = row['exit_code']
    result['object_exists'] = (output / 'fs/bcachefs/bkey.o').is_file()
    if result['object_exists']:
        result['object_sha256'] = hashlib.sha256((output / 'fs/bcachefs/bkey.o').read_bytes()).hexdigest()
    row = command(base + ['-j4', 'V=1', 'fs/bcachefs/bkey.i'], folder, 'preprocess')
    result['steps'].append(row)
    preprocessed = output / 'fs/bcachefs/bkey.i'
    if row['exit_code'] == 0 and preprocessed.is_file():
        data = preprocessed.read_bytes()
        (folder / 'bkey.i.gz').write_bytes(gzip.compress(data, mtime=0))
        result['preprocessed_sha256'] = hashlib.sha256(data).hexdigest()
    for rel in ['include/generated/autoconf.h', 'include/generated/utsrelease.h',
                'fs/bcachefs/.bkey.o.cmd']:
        path = output / rel
        if path.is_file():
            shutil.copyfile(path, folder / Path(rel).name)
    result['status'] = 'build_observed'
    write_json(folder / 'result.json', result)
    return result


def main():
    marker = HERE / 'run_started.json'
    with marker.open('x', encoding='utf-8') as f:
        json.dump({'kind': 'known_case_real_translation_unit', 'revisions': REVISIONS,
                   'no_paid_model_calls': True}, f, indent=2)
    CACHE.mkdir(parents=True, exist_ok=True)
    prepare = HERE / 'prepare'
    prepare.mkdir(exist_ok=False)
    for name, rev in REVISIONS.items():
        source = CACHE / ('source-' + name)
        assert source.resolve().is_relative_to(CACHE.resolve()) and not source.exists()
        row = command(['git', '-C', str(REPO), 'worktree', 'add', '--detach', str(source), rev],
                      prepare, 'worktree_' + name)
        if row['exit_code'] != 0:
            write_json(HERE / 'build_results.json', {'status': 'source_preparation_blocked', 'step': row})
            return
        for rel in ['Makefile', 'fs/Kconfig', 'fs/bcachefs/Kconfig', 'fs/bcachefs/Makefile',
                    'fs/bcachefs/bkey.c', 'fs/bcachefs/bcachefs_format.h']:
            dest = HERE / 'sources' / name / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / rel, dest)
    profiles = [(v, a, c) for v in REVISIONS for a, c in [('x86', ''), ('s390', 's390x-linux-gnu-')]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(build, profiles))
    write_json(HERE / 'build_results.json', {'status': 'matrix_executed', 'profiles': results,
                                           'case_count': 1, 'configuration_records': len(results),
                                           'runtime_boots': 0, 'independent_samples_added': 0})
    print(json.dumps({'status': 'matrix_executed', 'profiles': len(results)}), flush=True)


if __name__ == '__main__':
    main()
