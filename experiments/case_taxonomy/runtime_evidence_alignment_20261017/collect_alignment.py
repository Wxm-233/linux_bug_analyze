"""Five read-only compiler preprocesses from retained runtime build commands.

Run in WSL. Never runs make, a shell, object compilation, or a kernel.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time

ROOT = Path('/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze')
STAGE = ROOT / 'experiments/case_taxonomy/runtime_evidence_alignment_20261017'
RUNTIME = ROOT / 'experiments/case_taxonomy/s390_arch_contract_20261013/runtime'
CACHE = Path('/root/.cache/linux-bug-analyze/runtime-evidence-alignment-20261017')
sys.path.insert(0, str(ROOT))
from linux_bug_analyze.preprocessed_evidence import extract_definitions

UNITS = {
    'old_s390': ['arch/s390/kernel/topology.c', 'arch/s390/kernel/smp.c', 'kernel/sched/core.c'],
    'old_x86': ['arch/x86/kernel/smpboot.c', 'kernel/sched/core.c'],
}
SELECTORS = {
    'arch/s390/kernel/topology.c': {'cpu_thread_map': 'arch/s390/kernel/topology.c',
                                   'update_cpu_masks': 'arch/s390/kernel/topology.c'},
    'arch/s390/kernel/smp.c': {'smp_start_secondary': 'arch/s390/kernel/smp.c'},
    'arch/x86/kernel/smpboot.c': {'start_secondary': 'arch/x86/kernel/smpboot.c',
                                 'set_cpu_sibling_map': 'arch/x86/kernel/smpboot.c'},
    'kernel/sched/core.c': {'sched_core_lock': 'kernel/sched/core.c',
                           'sched_core_cpu_starting': 'kernel/sched/core.c',
                           'cpu_smt_mask': 'include/linux/topology.h'},
}
REMOVED_ENV = ['DEPENDENCIES_OUTPUT', 'SUNPRO_DEPENDENCIES', 'GCC_EXEC_PREFIX',
               'COMPILER_PATH', 'CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH',
               'OBJC_INCLUDE_PATH', 'GCC_COMPARE_DEBUG', 'LD_PRELOAD']
ENV = {k: v for k, v in os.environ.items() if k not in REMOVED_ENV}
ENV['LC_ALL'] = 'C'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    path = STAGE / name
    if path.exists():
        raise RuntimeError('refuse overwrite: ' + str(path))
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepare():
    records, protected, builds = [], set(), {}
    observed = json.loads((RUNTIME / 'old_observer_sources.json').read_text())
    for profile, units in UNITS.items():
        build = json.loads((RUNTIME / 'profiles' / profile / 'build.json').read_text())
        builds[profile] = build
        cwd, tree = Path(build['build_directory']), Path(build['source_tree'])
        if digest(cwd / '.config') != build['config_sha256'] or digest(Path(build['image'])) != build['image_sha256']:
            raise RuntimeError('historical config/image mismatch: ' + profile)
        for entry in observed['files']:
            path = tree / entry['path']
            if digest(path) != entry['observed_sha256']:
                raise RuntimeError('instrumented source mismatch: ' + entry['path'])
            protected.add(path)
        for relative in ['.config', 'include/config/auto.conf', 'include/generated/autoconf.h',
                         'include/generated/utsrelease.h', 'include/generated/uapi/linux/version.h']:
            protected.add(cwd / relative)
        protected.add(Path(build['image']))
        if digest(Path(build['initrd'])) != build['initrd_sha256']:
            raise RuntimeError('historical initramfs mismatch: ' + profile)
        protected.add(Path(build['initrd']))
        for unit in units:
            protected.update(tree / path for path in SELECTORS[unit].values())
            obj = Path(unit).with_suffix('.o')
            cmdfile = cwd / obj.parent / ('.' + obj.name + '.cmd')
            protected.update([cmdfile, cwd / obj])
            text = cmdfile.read_text()
            prefix = 'cmd_' + str(obj) + ' := '
            lines = [line[len(prefix):] for line in text.splitlines() if line.startswith(prefix)]
            if len(lines) != 1:
                raise RuntimeError('command not unique: ' + str(cmdfile))
            command = lines[0]
            if any(x in command for x in [';', '|', '&', '`', '$', '>', '<', '\n', '\r']):
                raise RuntimeError('unsupported shell syntax: ' + str(cmdfile))
            argv = shlex.split(command, posix=True)
            source = str(tree / unit)
            if argv[-4:] != ['-c', '-o', str(obj), source]:
                raise RuntimeError('unexpected compile tail: ' + str(cmdfile))
            if argv[0] not in ['gcc', 's390x-linux-gnu-gcc']:
                raise RuntimeError('unsupported compiler')
            executable = shutil.which(argv[0])
            if not executable:
                raise RuntimeError('compiler absent')
            compiler = Path(executable).resolve()
            protected.add(compiler)
            dependencies = [arg for arg in argv[:-4] if arg.startswith('-Wp,-MMD,')]
            if len(dependencies) != 1:
                raise RuntimeError('dependency flag not unique')
            core = [arg for arg in argv[:-4] if arg != dependencies[0]]
            if any(arg in ['-c', '-E', '-o', '-MF', '-MT', '-MQ', '-MD', '-MMD', '-save-temps']
                   or arg.startswith(('-Wp,-M', '-fplugin=', '-specs=')) for arg in core[1:]):
                raise RuntimeError('unsupported side effect/output option')
            output = CACHE / profile / Path(unit).with_suffix('.i')
            core[0] = str(compiler)
            new_argv = core + ['-E', '-o', str(output), source]
            records.append({'profile': profile, 'unit': unit, 'cwd': str(cwd), 'source': source,
                            'cmdfile': str(cmdfile), 'cmdfile_sha256': digest(cmdfile),
                            'original_argv': argv, 'preprocess_argv': new_argv,
                            'removed_dependency_option': dependencies[0], 'output': str(output),
                            'compiler': str(compiler), 'compiler_sha256': digest(compiler)})
    # Check all ten existing selected objects, including the untouched fixed builds.
    for profile, units in [('fixed_s390', UNITS['old_s390']), ('fixed_x86', UNITS['old_x86'])]:
        build = json.loads((RUNTIME / 'profiles' / profile / 'build.json').read_text())
        protected.update(Path(build['build_directory']) / Path(unit).with_suffix('.o') for unit in units)
    return records, protected, builds


def main():
    if CACHE.exists() or (STAGE / 'execution_plan.json').exists():
        raise RuntimeError('new cache/output required; no automatic rerun')
    records, protected, builds = prepare()
    before = {str(path): digest(path) for path in sorted(protected)}
    versions = {}
    for compiler in sorted({r['compiler'] for r in records}):
        proc = subprocess.run([compiler, '--version'], capture_output=True, text=True, timeout=10, env=ENV)
        if proc.returncode:
            raise RuntimeError('compiler version failed')
        versions[compiler] = proc.stdout.splitlines()[0]
    save('execution_plan.json', {'protocol_sha256': digest(STAGE / 'protocol_pre.json'),
                                'records': records, 'protected_before': before,
                                'compiler_versions_now': versions,
                                'environment_removed_keys': REMOVED_ENV, 'LC_ALL': 'C',
                                'historical_compiler_header_identity_fully_proved': False})
    CACHE.mkdir(parents=True, exist_ok=False)
    results, failure, attempted = [], None, 0
    try:
        for index, record in enumerate(records):
            output = Path(record['output'])
            output.parent.mkdir(parents=True, exist_ok=True)
            start = time.monotonic()
            stem = record['profile'] + '_' + record['unit'].replace('/', '_')
            attempted += 1
            try:
                proc = subprocess.run(record['preprocess_argv'], cwd=record['cwd'], shell=False,
                                      capture_output=True, timeout=90, env=ENV)
            except (subprocess.TimeoutExpired, OSError) as exc:
                (STAGE / (stem + '.stdout.log')).write_bytes(getattr(exc, 'stdout', None) or b'')
                (STAGE / (stem + '.stderr.log')).write_bytes(getattr(exc, 'stderr', None) or b'')
                results.append({'profile': record['profile'], 'unit': record['unit'],
                                'seconds': round(time.monotonic() - start, 3),
                                'failure': type(exc).__name__ + ': ' + str(exc)})
                raise
            (STAGE / (stem + '.stdout.log')).write_bytes(proc.stdout)
            (STAGE / (stem + '.stderr.log')).write_bytes(proc.stderr)
            row = {'profile': record['profile'], 'unit': record['unit'], 'exit_code': proc.returncode,
                   'seconds': round(time.monotonic() - start, 3), 'output': str(output)}
            if proc.returncode or not output.is_file():
                results.append(row)
                raise RuntimeError('preprocess failed; no retry')
            row.update({'sha256': digest(output), 'bytes': output.stat().st_size})
            try:
                definitions = extract_definitions(output.read_text(),
                    {name: str(Path(builds[record['profile']]['source_tree']) / source)
                     for name, source in SELECTORS[record['unit']].items()})
                name = stem + '.regions.json'
                save(name, {'profile': record['profile'], 'arch': builds[record['profile']]['arch'],
                            'revision': builds[record['profile']]['revision'],
                            'configuration_sha256': builds[record['profile']]['config_sha256'],
                            'image_sha256': builds[record['profile']]['image_sha256'],
                            'source_instrumented': True, 'source_path': record['source'],
                            'source_sha256': digest(Path(record['source'])),
                            'preprocessed_path': str(output), 'preprocessed_sha256': row['sha256'],
                            'cmdfile_sha256': record['cmdfile_sha256'],
                            'semantic_layer': 'configured_instrumented_lexical_regions_only',
                            'functions': definitions,
                            'control_flow_proved': False, 'preparation_effect_proved': False,
                            'historical_compiler_header_identity_fully_proved': False})
                row.update({'extraction_status': 'selected', 'regions_file': name,
                            'selected_functions': sorted(definitions)})
            except (ValueError, KeyError) as exc:
                row.update({'extraction_status': 'insufficient', 'reason': str(exc)})
            results.append(row)
    except Exception as exc:
        failure = type(exc).__name__ + ': ' + str(exc)
    finally:
        after = {str(path): digest(path) if path.is_file() else None for path in sorted(protected)}
        changed = [path for path in before if before[path] != after[path]]
        save('execution_result.json', {'status': 'PASS_BOUNDED_COLLECTION' if not failure and not changed else 'INSUFFICIENT',
                                      'preprocessor_invocations': attempted, 'results': results,
                                      'failure': failure, 'protected_after': after, 'changed_protected': changed,
                                      'protected_count': len(before), 'new_object_compilations': 0,
                                      'new_kernel_runs': 0, 'external_model_requests': 0,
                                      'independent_case': False})
        print(json.dumps({'preprocessor_invocations': attempted, 'selected_regions':
                          sum(len(r.get('selected_functions', [])) for r in results),
                          'protected_unchanged': not changed, 'failure': failure}))
    if failure or changed:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
