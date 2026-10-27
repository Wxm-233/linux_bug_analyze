"""Real historical Kbuild configuration/preprocessing/object pairs; no kernel boot."""
from __future__ import annotations

import json
import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path('/root/repos/linux')
WORK = Path('/root/.cache/linux-bug-analyze/die-contract-20261013')
VERSIONS = {
    'old': '555a0ce4558d87d5b97c4321f34b19e051c7b0c1',
    'fixed': '2c4dcd7fd57b20a21b65da04d89c38a7217d79cf',
}
PROFILES = (
    ('x86_smp', 'x86_64', 'x86', '', True),
    ('s390_smp', 's390', 's390', 's390x-linux-gnu-', True),
    ('x86_up', 'x86_64', 'x86', '', False),
)
ATTRS = ('dev_attr_die_id', 'bin_attr_die_cpus', 'bin_attr_die_cpus_list')
COMMANDS: list[dict] = []
ENV = dict(os.environ, LANG='C', LC_ALL='C')
HOST_COMPAT_FLAGS = ('WERROR=0',
                     'HOSTCFLAGS=-Wno-error=use-after-free -Wno-error=format-truncation')


def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def run(argv: list[str], label: str, dest: Path) -> str:
    dest.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(argv, env=ENV, capture_output=True)
    stdout = dest / f'{label}.stdout.log'
    stderr = dest / f'{label}.stderr.log'
    stdout.write_bytes(proc.stdout)
    stderr.write_bytes(proc.stderr)
    COMMANDS.append({'argv': argv, 'exit_code': proc.returncode,
                     'stdout': str(stdout), 'stderr': str(stderr)})
    save_json(HERE / 'commands.json', COMMANDS)
    if proc.returncode:
        raise RuntimeError(f'{label} exit={proc.returncode}: '
                           + proc.stderr.decode(errors='replace')[-1500:])
    return proc.stdout.decode(errors='replace')


def archive_tree(label: str, revision: str) -> Path:
    dest = WORK / label
    marker = dest / 'source_revision'
    tree = dest / 'linux'
    if marker.exists():
        if marker.read_text().strip() != revision:
            raise RuntimeError('Refusing a cache with another source revision')
        return tree
    if tree.exists() and any(tree.iterdir()):
        raise RuntimeError('Incomplete archive cache; preserve it for diagnosis')
    tree.mkdir(parents=True, exist_ok=True)
    archive = subprocess.Popen(['git', '-C', str(REPO), 'archive', revision],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    extracted = subprocess.run(['tar', '-xf', '-', '-C', str(tree)],
                               stdin=archive.stdout, capture_output=True)
    assert archive.stdout is not None and archive.stderr is not None
    archive.stdout.close()
    error = archive.stderr.read()
    code = archive.wait()
    if code or extracted.returncode:
        raise RuntimeError(f'archive={code}, tar={extracted.returncode}: {error!r}')
    marker.write_text(revision + '\n')
    return tree


def config_values(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            key, value = line.split('=', 1)
            values[key] = value
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            values[line[2:-11]] = 'n'
    return values


def extract_pp(path: Path) -> dict:
    text = path.read_text()
    current, logical_line = '', 0
    macros: dict[str, list[dict]] = {}
    includes = []
    for number, line in enumerate(text.splitlines(), 1):
        marker = re.match(r'^# (\d+) "([^"]+)"(?: (.*))?$', line)
        if marker:
            logical_line, current = int(marker[1]), marker[2]
            if current.endswith(('/asm/topology.h', '/linux/topology.h')):
                if current not in includes:
                    includes.append(current)
            continue
        define = re.match(r'^#define (topology_die_id|topology_die_cpumask|TOPOLOGY_DIE_SYSFS)(\b|\()', line)
        if define:
            macros.setdefault(define[1], []).append({
                'file': current, 'source_line': logical_line,
                'preprocessed_line': number, 'definition': line})
        logical_line += 1
    arrays = {}
    for name, kind in [('default_attrs', 'attribute'), ('bin_attrs', 'bin_attribute')]:
        matches = list(re.finditer(
            rf'static\s+struct\s+{kind}\s*\*\s*{name}\s*\[\s*\]\s*=\s*\{{(.*?)\}};',
            text, flags=re.S))
        if len(matches) != 1:
            raise RuntimeError(f'Expected exactly one complete {name} array')
        arrays[name] = {'text': matches[0][0],
                        'die_references': [n for n in ATTRS if re.search(rf'\b{n}\b', matches[0][1])]}
    declarations = {}
    for name in ATTRS:
        # Actual variable definition, not an arbitrary string or final macro.
        pattern = rf'struct\s+(?:device_attribute|bin_attribute)\s+{name}\s*='
        declarations[name] = bool(re.search(pattern, text))
    functions = {name: bool(re.search(rf'\b{name}\s*\(', text)) for name in
                 ['die_id_show', 'die_cpus_read', 'die_cpus_list_read',
                  'topology_add_dev', 'topology_sysfs_init', 'sysfs_create_group',
                  'cpuhp_setup_state']}
    return {'include_sources': includes, 'macro_definitions': macros,
            'arrays': arrays, 'declarations': declarations,
            'functions_or_calls': functions,
            'attribute_reference_count': sum(len(v['die_references']) for v in arrays.values())}


def source_map(tree: Path, revision: str) -> list[dict]:
    records = []
    paths = ['Makefile', 'arch/x86/Kconfig', 'arch/s390/Kconfig',
             'fs/sysfs/Kconfig', 'include/linux/topology.h',
             'arch/x86/include/asm/topology.h', 'arch/s390/include/asm/topology.h',
             'drivers/base/topology.c', 'drivers/base/Makefile']
    for relative in paths:
        identity = subprocess.check_output(['git', '-C', str(REPO), 'rev-parse',
                                            f'{revision}:{relative}']).decode().strip()
        raw = subprocess.check_output(['git', '-C', str(REPO), 'show', f'{revision}:{relative}'])
        if (tree / relative).read_bytes() != raw:
            raise RuntimeError(f'Archive source mismatch: {relative}')
        records.append({'path': relative, 'git_blob': identity, 'archive_bytes_match': True})
    return records


def verify_identity(row: dict) -> bool:
    config_key = 'CONFIG_X86_64' if row['source_arch'] == 'x86' else 'CONFIG_S390'
    header = row.get('object', {}).get('elf_header', '')
    fields = dict(re.findall(r'^\s*(Class|Data|Machine):\s*(.*?)\s*$', header, re.M))
    expected_machine = 'Advanced Micro Devices X86-64' if row['source_arch'] == 'x86' else 'IBM S/390'
    expected_endian = 'little endian' if row['source_arch'] == 'x86' else 'big endian'
    row['target_identity'] = {'configuration_key': config_key,
                              'configuration_value': row['configuration'].get(config_key),
                              'elf_fields': fields, 'expected_machine': expected_machine}
    match = (row['configuration'].get(config_key) == 'y' and
             fields.get('Class') == 'ELF64' and fields.get('Machine') == expected_machine
             and expected_endian in fields.get('Data', ''))
    row['target_identity']['matches_expectation'] = match
    return match


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume-errors', action='store_true',
                        help='Preserve initial failures, retry only incomplete profiles with host warning options')
    args = parser.parse_args()
    if os.name != 'posix':
        raise RuntimeError('Run inside WSL, not with the Windows host compiler')
    HERE.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    environment = {'uname': subprocess.check_output(['uname', '-m']).decode().strip(),
                   'tool_versions': {}, 'kernel_boots': 0, 'external_model_calls': 0}
    for tool in ['gcc', 's390x-linux-gnu-gcc', 'make']:
        environment['tool_versions'][tool] = subprocess.check_output([tool, '--version']).decode().splitlines()[0]
    environment['qemu_system_x86_64'] = shutil.which('qemu-system-x86_64')
    environment['qemu_system_s390x'] = shutil.which('qemu-system-s390x')
    save_json(HERE / 'environment.json', environment)
    existing = {}
    if args.resume_errors:
        original = HERE / 'results.json'
        if not original.exists():
            raise RuntimeError('No initial run to resume')
        previous = json.loads(original.read_text())
        existing = {row['profile']: row for row in previous}
        if not (HERE / 'results_attempt1.json').exists():
            shutil.copyfile(original, HERE / 'results_attempt1.json')
            shutil.copyfile(HERE / 'commands.json', HERE / 'commands_attempt1.json')
        COMMANDS.extend(json.loads((HERE / 'commands.json').read_text()))
        for row in previous:
            if row['status'] != 'PASS':
                dest = HERE / 'profiles' / row['profile']
                for stream in ['stdout', 'stderr']:
                    log = dest / f'prepare.{stream}.log'
                    if log.exists() and not log.with_name(f'prepare.attempt1.{stream}.log').exists():
                        shutil.copyfile(log, log.with_name(f'prepare.attempt1.{stream}.log'))
    results = []
    for label, revision in VERSIONS.items():
        print(f'Archive {label} {revision}', flush=True)
        tree = archive_tree(label, revision)
        save_json(HERE / f'{label}_source_map.json', source_map(tree, revision))
        for profile, arch, srcarch, prefix, smp in PROFILES:
            name = f'{label}_{profile}'
            dest = HERE / 'profiles' / name
            dest.mkdir(parents=True, exist_ok=True)
            if name in existing and existing[name]['status'] == 'PASS':
                row = existing[name]
                if not verify_identity(row):
                    raise RuntimeError(f'Existing successful profile has wrong target identity: {name}')
                save_json(dest / 'result.json', row)
                results.append(row)
                save_json(HERE / 'results.json', results)
                print(f'{name}: retained PASS, target identity checked; no repeated build', flush=True)
                continue
            build = WORK / label / profile
            base = ['make', '-C', str(tree), f'O={build}', f'ARCH={arch}']
            if prefix:
                base += [f'CROSS_COMPILE={prefix}']
            if args.resume_errors and srcarch == 'x86':
                base += list(HOST_COMPAT_FLAGS)
            row = {'profile': name, 'revision': revision, 'arch': arch,
                   'source_arch': srcarch, 'requested_smp': smp,
                   'build_directory': str(build), 'kernel_boot': False}
            row['host_compatibility_options'] = list(HOST_COMPAT_FLAGS) if args.resume_errors and srcarch == 'x86' else []
            print(f'Prepare {name}', flush=True)
            try:
                run(base + ['defconfig'], 'defconfig', dest)
                edits = [str(tree / 'scripts/config'), '--file', str(build / '.config'),
                         '--enable', 'SYSFS', '--enable' if smp else '--disable', 'SMP']
                run(edits, 'edits', dest)
                run(base + ['olddefconfig'], 'olddefconfig', dest)
                config = config_values(build / '.config')
                keys = ['CONFIG_SMP', 'CONFIG_SYSFS', 'CONFIG_X86_64', 'CONFIG_S390',
                        'CONFIG_NUMA', 'CONFIG_SCHED_BOOK', 'CONFIG_HOTPLUG_CPU',
                        'CONFIG_NR_CPUS', 'CONFIG_STACK_VALIDATION', 'CONFIG_UNWINDER_ORC']
                row['configuration'] = {k: config.get(k, 'not emitted') for k in keys}
                if config.get('CONFIG_SMP', 'n') != ('y' if smp else 'n') or config.get('CONFIG_SYSFS') != 'y':
                    raise RuntimeError('Requested SMP/SYSFS profile not reachable')
                if config.get('CONFIG_X86_64' if srcarch == 'x86' else 'CONFIG_S390') != 'y':
                    raise RuntimeError('Actual Kconfig does not select requested architecture')
                shutil.copyfile(build / '.config', dest / 'kernel.config')
                run(base + ['-j4', 'prepare'], 'prepare', dest)
                shutil.copyfile(build / 'include/generated/autoconf.h', dest / 'autoconf.h')
                run(base + ['V=1', 'KCFLAGS=-dD -H', 'drivers/base/topology.i'], 'preprocess', dest)
                pp = extract_pp(build / 'drivers/base/topology.i')
                row['preprocessing'] = pp
                save_json(dest / 'preprocessed_evidence.json', pp)
                expected = 3 if label == 'old' or profile == 'x86_smp' else 0
                native_id = profile.startswith('x86')
                native_mask = profile == 'x86_smp'
                expected_sources = {'topology_die_id': native_id, 'topology_die_cpumask': native_mask}
                provenance_pass = True
                for macro, native in expected_sources.items():
                    definitions = pp['macro_definitions'].get(macro, [])
                    suffix = f'/arch/{srcarch}/include/asm/topology.h' if native else '/include/linux/topology.h'
                    provenance_pass &= len(definitions) == 1 and definitions[0]['file'].endswith(suffix)
                guard = bool(pp['macro_definitions'].get('TOPOLOGY_DIE_SYSFS'))
                guard_expected = label == 'fixed' and profile == 'x86_smp'
                row['expected_attributes'] = expected
                row['expected_native_sources'] = expected_sources
                row['preprocess_matches_expectation'] = (
                    pp['attribute_reference_count'] == expected and provenance_pass
                    and all(v == (expected == 3) for v in pp['declarations'].values())
                    and guard == guard_expected)
                # Preserve preprocessing results if object compilation encounters a host-tool issue.
                save_json(dest / 'result.json', row)
                run(base + ['-j4', 'V=1', 'drivers/base/topology.o'], 'object', dest)
                obj = build / 'drivers/base/topology.o'
                elf = run([prefix + 'readelf', '-h', str(obj)], 'elf', dest)
                nm = run([prefix + 'nm', '-a', str(obj)], 'symbols', dest)
                row['object'] = {'path': str(obj), 'elf_header': elf,
                                 'die_symbols': [n for n in ATTRS if re.search(rf'\b{n}$', nm, re.M)]}
                row['object_matches_expectation'] = len(row['object']['die_symbols']) == expected
                identity_pass = verify_identity(row)
                row['status'] = 'PASS' if row['preprocess_matches_expectation'] and row['object_matches_expectation'] and identity_pass else 'MISMATCH'
            except Exception as exc:
                row['status'] = 'ERROR'
                row['error'] = str(exc)
            save_json(dest / 'result.json', row)
            results.append(row)
            save_json(HERE / 'results.json', results)
            print(f'{name}: {row["status"]}', flush=True)
    if not all(row['status'] == 'PASS' for row in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
