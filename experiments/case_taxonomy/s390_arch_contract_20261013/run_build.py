"""Four bounded historical configuration/build units; no kernel boot."""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = Path('/root/.cache/linux-bug-analyze/s390-contract-20261013')
REPO = '/root/repos/linux'
VERSIONS = {'old': '88b604263f3d6eedae0b1c2c3bbd602d1e2e8775',
            'fixed': 'a052096bdd6809eeab809202726634d1ac975aa1'}
ENV = dict(os.environ, LC_ALL='C', LANG='C')


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def command(argv, out, label):
    ledger = out/'commands.json'
    rows = json.loads(ledger.read_text()) if ledger.exists() else []
    number = 1 + sum(r['label'] == label for r in rows)
    stem = label if number == 1 else f'{label}.attempt{number}'
    row = {'label': label, 'attempt': number, 'argv': argv,
           'stdout': str(out/(stem+'.stdout.log')), 'stderr': str(out/(stem+'.stderr.log')),
           'state': 'running'}
    rows.append(row); save(ledger, rows)
    save(HERE/'progress.json', {'profile': out.name, **row})
    print(out.name + ': ' + label, flush=True)
    start = time.monotonic()
    with open(row['stdout'], 'wb') as stdout, open(row['stderr'], 'wb') as stderr:
        try:
            rc = subprocess.run(argv, stdout=stdout, stderr=stderr, env=ENV, timeout=300).returncode
        except subprocess.TimeoutExpired:
            rc = 124
    row.update(state='finished', returncode=rc, seconds=round(time.monotonic()-start, 2))
    save(ledger, rows); save(HERE/'progress.json', {'profile': out.name, **row})
    if rc:
        raise RuntimeError(f'{label} exit {rc}: {Path(row["stderr"]).read_text(errors="replace")[-1600:]}')
    return row


def git(*argv):
    return subprocess.check_output(['git', '-C', REPO, *argv], env=ENV)


def archive(variant):
    tree = BASE/variant/'linux'
    marker = BASE/variant/'source_revision'
    revision = VERSIONS[variant]
    if not marker.exists():
        if tree.exists() and any(tree.iterdir()):
            raise RuntimeError('Unmarked nonempty source directory; preserve it')
        tree.mkdir(parents=True, exist_ok=True)
        print('archive ' + variant, flush=True)
        proc = subprocess.Popen(['git', '-C', REPO, 'archive', revision], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=ENV)
        try:
            tar = subprocess.run(['tar', '-xf', '-', '-C', str(tree)], stdin=proc.stdout,
                                 capture_output=True, timeout=300)
            proc.stdout.close(); stderr = proc.stderr.read(); rc = proc.wait(timeout=10)
            if rc or tar.returncode:
                raise RuntimeError(f'archive/tar failed: {stderr!r} {tar.stderr!r}')
        finally:
            if proc.poll() is None:
                proc.kill(); proc.wait()
        marker.write_text(revision+'\n')
    if marker.read_text().strip() != revision:
        raise RuntimeError('Cached source at another revision')
    evidence = json.loads((HERE.parent/'cross_arch_s390_source_20261012.json').read_text())
    paths = sorted({s['path'] for s in evidence['sources']} |
                   {'Makefile', 'arch/s390/Kconfig', 'arch/x86/Kconfig', 'kernel/Kconfig.preempt'})
    identities = []
    for line in git('ls-tree', '-r', revision, '--', *paths).decode().splitlines():
        meta, path = line.split('\t'); blob = meta.split()[2]
        raw = (tree/path).read_bytes()
        actual = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if actual != blob:
            raise RuntimeError('Source changed: ' + path)
        identities.append({'path': path, 'git_blob': blob, 'actual_matches_git': True})
    save(HERE/(variant+'_sources.json'), {'revision': revision, 'files': identities})
    return tree


def configuration(path):
    values = {}
    for line in path.read_text().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            key, value = line.split('=', 1); values[key] = value
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            values[line[2:-11]] = 'n'
    return values


def body(text, name):
    """Extract a definition from a Kbuild .i, skipping prototypes/call sites."""
    for match in re.finditer(r'\b'+re.escape(name)+r'\s*\(', text):
        i = match.end(); depth = 1
        while depth and i < len(text):
            depth += (text[i] == '(') - (text[i] == ')'); i += 1
        while i < len(text):
            if text[i].isspace():
                i += 1
                continue
            directive = re.match(r'#\s+\d+\s+"[^"\n]+"[^\n]*(?:\n|$)', text[i:])
            if directive:
                i += directive.end()
                continue
            break
        if i >= len(text) or text[i] != '{':
            continue
        start = i; depth = 1; i += 1; quote = None
        while depth and i < len(text):
            c = text[i]
            if quote:
                if c == '\\': i += 1
                elif c == quote: quote = None
            elif c in ['"', "'"]: quote = c
            else: depth += (c == '{') - (c == '}')
            i += 1
        if not depth:
            return text[match.start():i]
    raise RuntimeError('Definition absent in actual preprocessing: ' + name)


def build_unit(variant, arch, tree):
    name = variant+'_'+arch
    out = HERE/'profiles'/name; out.mkdir(parents=True, exist_ok=True)
    build = BASE/name/'build'; build.mkdir(parents=True, exist_ok=True)
    make = ['make', '-C', str(tree), f'O={build}', f'ARCH={arch}', 'WERROR=0',
            'HOSTCFLAGS=-Wno-error=use-after-free -Wno-error=deprecated-declarations']
    if arch == 's390': make += ['CROSS_COMPILE=s390x-linux-gnu-']
    result_path = out/'result.json'
    if result_path.exists() and json.loads(result_path.read_text()).get('status') == 'CONFIG_BUILD_VERIFIED':
        from verify_build import verify_binding
        verify_binding(variant, arch)
        print(name+': reuse saved successful unit', flush=True)
        return json.loads(result_path.read_text())
    command(make+['defconfig'], out, 'defconfig')
    edits = [str(tree/'scripts/config'), '--file', str(build/'.config')]
    required = ['SMP', 'SCHED_SMT', 'SCHED_CORE', 'HOTPLUG_CPU', 'SYSFS']
    if arch == 's390': required += ['SCHED_TOPOLOGY']
    for key in required: edits += ['--enable', key]
    for key in ['DEBUG_INFO', 'DEBUG_INFO_BTF', 'DEBUG_INFO_SPLIT', 'DEBUG_INFO_REDUCED', 'WERROR', 'LOCALVERSION_AUTO']:
        edits += ['--disable', key]
    edits += ['--set-val', 'NR_CPUS', '4', '--set-str', 'LOCALVERSION', '-r4-'+name]
    command(edits, out, 'config_edits'); command(make+['olddefconfig'], out, 'olddefconfig')
    actual = configuration(build/'.config')
    if any(actual.get('CONFIG_'+k) != 'y' for k in required) or actual.get('CONFIG_NR_CPUS') != '4':
        raise RuntimeError('Requested conditions did not become effective')
    (out/'kernel.config').write_bytes((build/'.config').read_bytes())
    command(make+['-j4', 'prepare'], out, 'prepare')
    generated = (build/'include/generated/autoconf.h').read_text()
    if any(f'#define CONFIG_{k} 1' not in generated for k in required):
        raise RuntimeError('Generated header disagrees with configuration')
    (out/'autoconf.h').write_text(generated)
    paths = ['kernel/sched/core', 'kernel/cpu']
    paths += ['arch/s390/kernel/smp', 'arch/s390/kernel/topology'] if arch == 's390' else ['arch/x86/kernel/smpboot']
    command(make+['-j4']+[p+s for p in paths for s in ['.i', '.o']], out, 'targets')
    prefix = 's390x-linux-gnu-' if arch == 's390' else ''
    objects = []
    for index, path in enumerate(paths):
        row = command([prefix+'readelf', '-h', str(build/(path+'.o'))], out, 'elf_'+str(index))
        elf = Path(row['stdout']).read_text()
        machine = re.search(r'Machine:\s*(.+)', elf).group(1).strip()
        expected = 'IBM S/390' if arch == 's390' else 'Advanced Micro Devices X86-64'
        if machine != expected or not re.search(r'Class:\s+ELF64', elf):
            raise RuntimeError('Wrong target object: ' + path)
        nm = command([prefix+'nm', '--defined-only', str(build/(path+'.o'))], out, 'symbols_'+str(index))
        names = {line.split()[-1] for line in Path(nm['stdout']).read_text().splitlines() if line.split()}
        objects.append({'path': path+'.o', 'machine': machine, 'bytes': (build/(path+'.o')).stat().st_size,
                        'relevant_symbols': sorted(n for n in names if any(w in n for w in ['start_secondary', 'sched_cpu_starting', 'notify_cpu_starting', 'update_cpu_masks', 'cpu_setup_mask']))})
    texts = {path: (build/(path+'.i')).read_text() for path in paths}
    core = texts['kernel/sched/core']; cpu = texts['kernel/cpu']
    extracts = {n: body(core, n) for n in ['cpu_smt_mask', 'sched_core_cpu_starting', 'sched_cpu_starting']}
    provider = 'arch/s390/kernel/smp' if arch == 's390' else 'arch/x86/kernel/smpboot'
    extracts['architecture_start'] = body(texts[provider], 'smp_start_secondary' if arch == 's390' else 'smp_callin')
    if arch == 's390':
        extracts['thread_map'] = body(texts['arch/s390/kernel/topology'], 'cpu_thread_map')
        extracts['topology_init_early'] = body(texts['arch/s390/kernel/topology'], 'topology_init_early')
    else:
        extracts['sibling_map'] = body(texts[provider], 'set_cpu_sibling_map')
    header = str(tree/f'arch/{arch}/include/asm/topology.h')
    checks = {'actual_architecture_header': bool(re.search(r'^#\s+\d+\s+"'+re.escape(header)+r'"', core, re.M)),
              'actual_mask_provider': ('thread_mask' if arch == 's390' else 'cpu_sibling_map') in extracts['cpu_smt_mask'],
              'actual_core_starting_body': all(t in extracts['sched_core_cpu_starting'] for t in ['cpu_smt_mask', 'cpumask_weight', 'core_rq']),
              'sched_starting_calls_core': 'sched_core_cpu_starting(cpu)' in extracts['sched_cpu_starting'],
              'cpuhp_callback_compiled': bool(re.search(r'\[CPUHP_AP_SCHED_STARTING\]\s*=\s*\{[^}]*startup.single\s*=\s*sched_cpu_starting', cpu)),
              'public_starting_symbol': any('sched_cpu_starting' in o['relevant_symbols'] for o in objects),
              'public_notify_symbol': any('notify_cpu_starting' in o['relevant_symbols'] for o in objects)}
    start = extracts['architecture_start']
    if arch == 's390':
        checks['architecture_order'] = (start.index('update_cpu_masks()') < start.index('notify_cpu_starting(')) == (variant == 'fixed')
        checks['eligibility_source'] = ('cpu_setup_mask' in extracts['thread_map']) if variant == 'fixed' else ('cpu_online(' in extracts['thread_map'])
        checks['prepared_membership_at_start'] = ('cpu_setup_mask' in start) == (variant == 'fixed')
    else:
        checks['architecture_order'] = start.index('set_cpu_sibling_map(') < start.index('notify_cpu_starting(')
        checks['prepared_membership_source'] = 'cpu_sibling_setup_mask' in extracts['sibling_map']
    save(out/'preprocessed_facts.json', {'header': header, 'checks': checks, 'functions': extracts})
    row = {'status': 'CONFIG_BUILD_VERIFIED' if all(checks.values()) else 'EVIDENCE_INSUFFICIENT',
           'variant': variant, 'arch': arch, 'revision': VERSIONS[variant], 'cache_build': str(build),
           'required_effective': {k: actual['CONFIG_'+k] for k in required}, 'nr_cpus': actual['CONFIG_NR_CPUS'],
           'checks': checks, 'objects': objects, 'runtime': 'NOT_EXECUTED'}
    save(result_path, row)
    if not all(checks.values()): raise RuntimeError('Actual preprocessing has incomplete chain: '+str(checks))
    from verify_build import certify_unit
    certify_unit(row)
    return row


def main():
    if os.name != 'posix': raise RuntimeError('Run within WSL')
    rows = []
    try:
        for variant in ['old', 'fixed']:
            tree = archive(variant)
            for arch in ['s390', 'x86']:
                rows.append(build_unit(variant, arch, tree))
                save(HERE/'results.json', {'status': 'IN_PROGRESS', 'units': rows})
        pairs = []
        for arch in ['s390', 'x86']:
            a = configuration(HERE/'profiles'/('old_'+arch)/'kernel.config')
            b = configuration(HERE/'profiles'/('fixed_'+arch)/'kernel.config')
            diff = {k: [a.get(k), b.get(k)] for k in sorted(set(a)|set(b)) if a.get(k) != b.get(k)}
            if set(diff) != {'CONFIG_LOCALVERSION'}:
                raise RuntimeError('Same-profile configurations differ: '+str(diff))
            pairs.append({'arch': arch, 'differences': diff})
        save(HERE/'results.json', {'status': 'FOUR_CONFIG_BUILD_UNITS_VERIFIED', 'units': rows,
                                  'configuration_pairs': pairs, 'kernel_boots': 0, 'new_defects': 0,
                                  'independent_detection_positives': 0})
        print('four configurations/build chains verified; no kernel boot', flush=True)
    except Exception as error:
        save(HERE/'error.json', {'status': 'INCOMPLETE', 'reason': str(error), 'completed_units': len(rows)})
        print(str(error), flush=True); raise SystemExit(1)


if __name__ == '__main__':
    main()
