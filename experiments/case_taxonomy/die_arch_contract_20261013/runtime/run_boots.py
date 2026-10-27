"""Build unmodified historical kernels and read real sysfs under four QEMU boots."""
from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = Path('/root/.cache/linux-bug-analyze/die-contract-20261013')
VERSIONS = {'old': '555a0ce4558d87d5b97c4321f34b19e051c7b0c1',
            'fixed': '2c4dcd7fd57b20a21b65da04d89c38a7217d79cf'}
COMMON = ['64BIT', 'SMP', 'SYSFS', 'PROC_FS', 'BLK_DEV_INITRD', 'RD_GZIP',
          'BINFMT_ELF', 'PRINTK', 'TTY', 'DEVTMPFS', 'FUTEX', 'MULTIUSER',
          'POSIX_TIMERS', 'KALLSYMS']
HOST_FLAGS = ['WERROR=0', 'HOSTCFLAGS=-Wno-error=use-after-free -Wno-error=format-truncation']
ENV = dict(os.environ, LANG='C', LC_ALL='C')


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(argv: list[str], dest: Path, label: str, timeout: int | None = None) -> dict:
    record_file = dest / 'commands.json'
    records = json.loads(record_file.read_text()) if record_file.exists() else []
    attempt = 1 + sum(r['label'] == label for r in records)
    stem = label if attempt == 1 else f'{label}.attempt{attempt}'
    stdout, stderr = dest / f'{stem}.stdout.log', dest / f'{stem}.stderr.log'
    row = {'label': label, 'attempt': attempt, 'argv': argv,
           'stdout': str(stdout), 'stderr': str(stderr), 'status': 'running'}
    records.append(row)
    write(record_file, records)
    write(dest / 'progress.json', {'step': label, 'attempt': attempt, 'state': 'running'})
    start = time.monotonic()
    with stdout.open('wb') as out, stderr.open('wb') as err:
        try:
            proc = subprocess.run(argv, stdout=out, stderr=err, env=ENV, timeout=timeout)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            code = 124
    row.update(status='finished', exit_code=code, seconds=round(time.monotonic()-start, 2))
    write(record_file, records)
    write(dest / 'progress.json', {'step': label, 'attempt': attempt, 'state': 'finished', 'exit_code': code})
    if code:
        raise RuntimeError(f'{label} exit={code}: {stderr.read_text(errors="replace")[-1800:]}')
    return row


def config_values(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            k, v = line.split('=', 1); values[k] = v
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            values[line[2:-11]] = 'n'
    return values


def build_one(label: str, arch: str) -> dict:
    name = f'{label}_{arch}'
    dest = HERE / 'profiles' / name
    dest.mkdir(parents=True, exist_ok=True)
    result = dest / 'build.json'
    init_source = HERE / 'init_probe.c'
    cached = json.loads(result.read_text()) if result.exists() else {}
    tree = BASE / label / 'linux'
    if (BASE / label / 'source_revision').read_text().strip() != VERSIONS[label]:
        raise RuntimeError('Wrong historical archive revision')
    build = BASE / 'runtime' / name
    prefix = 's390x-linux-gnu-' if arch == 's390' else ''
    srcarch = 's390' if arch == 's390' else 'x86'
    make = ['make', '-C', str(tree), f'O={build}', f'ARCH={arch}'] + HOST_FLAGS
    if prefix: make += [f'CROSS_COMPILE={prefix}']
    source_identity = []
    for item in json.loads((HERE.parent / f'{label}_source_map.json').read_text()):
        data = (tree / item['path']).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != item['git_blob']: raise RuntimeError(f'Historical source changed: {item["path"]}')
        source_identity.append({'path': item['path'], 'git_blob': blob, 'matches': True})
    if cached.get('image'):
        if (cached.get('revision') != VERSIONS[label] or cached.get('arch') != arch
                or cached.get('profile') != name or cached.get('build_directory') != str(build)
                or cached.get('image') != str(build / f'arch/{srcarch}/boot/bzImage')):
            raise RuntimeError(f'Cached kernel has another source/profile identity: {name}')
        if digest(Path(cached['image'])) != cached['image_sha256']:
            raise RuntimeError(f'Cached kernel changed: {name}')
        if ((build / '.config').read_bytes() != (dest / 'kernel.config').read_bytes()
                or (build / 'include/config/kernel.release').read_text().strip() != cached['release']):
            raise RuntimeError(f'Cached kernel configuration/release changed: {name}')
        receipts = json.loads((dest / 'commands.json').read_text())
        if any([r for r in receipts if r['label'] == step][-1].get('exit_code') != 0
               for step in ['kernel_build', 'kernel_elf']):
            raise RuntimeError(f'Cached kernel lacks successful build/ELF receipts: {name}')
        if cached.get('status') == 'READY' and cached['init_source_sha256'] == digest(init_source):
            for artifact in ['init_binary', 'initrd']:
                if digest(Path(cached[artifact])) != cached[artifact+'_sha256']:
                    raise RuntimeError(f'Cached {artifact} changed: {name}')
            cached['source_identity'] = source_identity
            print(f'{name}: reuse kernel and initramfs; no repeated compilation', flush=True)
            return cached
        if not (dest / 'build_attempt1.json').exists():
            (dest / 'build_attempt1.json').write_bytes(result.read_bytes())
    row = {'profile': name, 'revision': VERSIONS[label], 'arch': arch,
           'source_tree': str(tree), 'build_directory': str(build),
           'init_source_sha256': digest(init_source), 'source_c_modified': False}
    row['source_identity'] = source_identity
    try:
        features = COMMON + (['SERIAL_8250', 'SERIAL_8250_CONSOLE', 'ACPI', 'PCI',
                              'X86_MPPARSE', 'X86_LOCAL_APIC', 'X86_IO_APIC']
                             if arch == 'x86_64' else ['SCLP_TTY', 'SCLP_CONSOLE',
                              'SCLP_VT220_TTY', 'SCLP_VT220_CONSOLE'])
        if not cached.get('image'):
            print(f'{name}: configure minimal historical kernel', flush=True)
            command(make + ['allnoconfig'], dest, 'allnoconfig')
            edits = [str(tree / 'scripts/config'), '--file', str(build / '.config')]
            for symbol in features: edits += ['--enable', symbol]
            for symbol in ['WERROR', 'MODULES', 'DEBUG_INFO', 'GCC_PLUGINS', 'LOCALVERSION_AUTO']:
                edits += ['--disable', symbol]
            edits += ['--set-val', 'NR_CPUS', '4', '--set-str', 'LOCALVERSION', f'-die-r2-{label}']
            command(edits, dest, 'config_edits')
            command(make + ['olddefconfig'], dest, 'olddefconfig')
        config = config_values(build / '.config')
        required = COMMON + ['MMU', 'X86_64' if arch == 'x86_64' else 'S390']
        required += ['SERIAL_8250_CONSOLE', 'X86_LOCAL_APIC', 'X86_MPPARSE'] if arch == 'x86_64' else ['SCLP_VT220_CONSOLE']
        missing = [k for k in required if config.get('CONFIG_'+k) != 'y']
        if missing or int(config.get('CONFIG_NR_CPUS', '0')) < 2:
            raise RuntimeError(f'Boot configuration unreachable: {missing}')
        row['effective_configuration'] = {k: v for k, v in config.items() if k in
                 {'CONFIG_'+s for s in features+['MMU','X86_64','S390','NR_CPUS','WERROR','LOCALVERSION','LOCALVERSION_AUTO']}}
        (dest / 'kernel.config').write_bytes((build / '.config').read_bytes())
        if cached.get('image'):
            print(f'{name}: resume init packaging; reuse completed kernel', flush=True)
            row['kernel_reused_after_init_failure'] = True
        else:
            print(f'{name}: build bzImage with 6 workers', flush=True)
            command(make + ['-j6', 'bzImage'], dest, 'kernel_build')
        image = build / f'arch/{srcarch}/boot/bzImage'
        row.update(image=str(image), image_sha256=digest(image),
                   release=(build / 'include/config/kernel.release').read_text().strip())
        if not cached.get('image'):
            command([prefix+'readelf', '-h', str(build/'vmlinux')], dest, 'kernel_elf')
        elf = (dest/'kernel_elf.stdout.log').read_text()
        machine = 'IBM S/390' if arch == 's390' else 'Advanced Micro Devices X86-64'
        if not re.search(r'Class:\s+ELF64', elf) or not re.search(r'Machine:\s+'+re.escape(machine), elf):
            raise RuntimeError('Wrong kernel ELF identity')
        binary = build / 'pid1.elf'
        command([prefix+'gcc','-static','-Os','-std=c11','-Wall','-Wextra',
                 '-fno-pie','-no-pie',str(init_source),'-o',str(binary)],dest,'init_build')
        command([prefix+'readelf','-h','-l',str(binary)],dest,'init_elf')
        elf = (dest/'init_elf.stdout.log').read_text()
        if 'INTERP' in elf or not re.search(r'Class:\s+ELF64', elf) or not re.search(r'Machine:\s+'+re.escape(machine), elf):
            raise RuntimeError('Init is dynamically linked or has wrong machine')
        listing = build / 'initramfs.list'
        listing.write_text('dir /dev 755 0 0\ndir /proc 755 0 0\ndir /sys 755 0 0\n'
                           'nod /dev/console 600 0 0 c 5 1\n'
                           f'file /init {binary} 755 0 0\n')
        cpio = subprocess.check_output([str(build/'usr/gen_init_cpio'), str(listing)])
        initrd = build / 'initramfs.cpio.gz'
        initrd.write_bytes(gzip.compress(cpio, mtime=0))
        row.update(init_binary=str(binary), init_binary_sha256=digest(binary),
                   initrd=str(initrd), initrd_sha256=digest(initrd),
                   config_sha256=digest(build / '.config'), status='READY')
        (dest/'autoconf.h').write_bytes((build/'include/generated/autoconf.h').read_bytes())
    except Exception as exc:
        row.update(status='ERROR', error=str(exc))
    write(result, row)
    print(f'{name}: {row["status"]}', flush=True)
    return row


def cpulist(text: str) -> set[int]:
    values = set()
    for part in text.strip().split(','):
        if not re.fullmatch(r'\d+(?:-\d+)?', part): raise ValueError('Malformed CPU list')
        bounds = [int(n) for n in part.split('-')]
        lo, hi = bounds[0], bounds[-1]
        if hi < lo or hi > 4096: raise ValueError('Invalid CPU range')
        values.update(range(lo, hi+1))
    return values


def integer(text: str) -> int:
    if not re.fullmatch(r'-?\d+', text.strip()): raise ValueError('Malformed integer')
    return int(text.strip())


def cpumask(text: str) -> set[int]:
    if not re.fullmatch(r'[0-9a-fA-F]{1,8}(?:,[0-9a-fA-F]{8})*', text.strip()):
        raise ValueError('Malformed CPU bitmap')
    bits = int(text.strip().replace(',', ''), 16)
    if bits.bit_length() > 4096: raise ValueError('CPU bitmap exceeds probe scope')
    return {i for i in range(bits.bit_length()) if bits & (1 << i)}


def analyse_log(build: dict, log: Path) -> dict:
    events, parse_errors = [], []
    for line in log.read_text(errors='replace').splitlines():
        start = line.find('{"event":')
        if start < 0: continue
        try: events.append(json.loads(line[start:]))
        except json.JSONDecodeError: parse_errors.append(line)
    expected_arch = 's390x' if build['arch']=='s390' else 'x86_64'
    setup = {e['operation']: e for e in events if e['event']=='setup'}
    uname = [e for e in events if e['event']=='uname']
    begin = [e for e in events if e['event']=='probe_begin']
    end = [e for e in events if e['event']=='probe_end']
    reads = {}
    for e in events:
        if e['event']=='file_read': reads.setdefault(e['path'], []).append(e)
    def read(path: str) -> dict:
        return reads.get(path, [{}])[-1]
    def okay(e: dict) -> bool:
        return e.get('status')=='ok' and e.get('errno')==0 and not e.get('truncated')
    online = reads.get('/sys/devices/system/cpu/online', [])
    selection = [e for e in events if e['event']=='online_selection']
    raw_cpu_sets={}
    for name in ['online','present','possible']:
        item=read('/sys/devices/system/cpu/'+name)
        try: raw_cpu_sets[name]=sorted(cpulist(item['raw'])) if okay(item) else None
        except (KeyError,ValueError): raw_cpu_sets[name]=None
    foundation = {'json_complete':not parse_errors and len(begin)==1 and len(end)==1 and end[0].get('reached_end') and not end[0].get('setup_skipped'),
        'pid1_schema':len(begin)==1 and begin[0].get('pid')==1 and begin[0].get('schema')=='die_sysfs_runtime_v1',
        'uname_matches_image':len(uname)==1 and uname[0].get('release')==build['release'] and uname[0].get('machine')==expected_arch,
        'mount_proc':setup.get('mount_proc',{}).get('return_code')==0,
        'mount_sysfs':setup.get('mount_sysfs',{}).get('return_code')==0,
        'console_open':setup.get('open_console',{}).get('return_code')==0,
        'two_online_cpus':len(selection)==1 and selection[0].get('parse_ok') and not selection[0].get('truncated') and selection[0].get('selected_cpu_ids')==[0,1] and selection[0].get('online_cpu_count')==2,
        'independent_raw_online_set':raw_cpu_sets['online']==[0,1],
        'end_cpu_count':len(end)==1 and end[0].get('observed_cpus')==2 and end[0].get('online_parse_ok') is True and end[0].get('truncated') is False,
        'online_stable':len(online)==2 and all(okay(e) for e in online) and online[0].get('raw')==online[1].get('raw'),
        'present_possible_readable':all(okay(read('/sys/devices/system/cpu/'+n)) for n in ['present','possible']),
        'cpu_set_relationship':all(raw_cpu_sets[n] is not None for n in ['online','present','possible']) and set(raw_cpu_sets['online']).issubset(raw_cpu_sets['present']) and set(raw_cpu_sets['present']).issubset(raw_cpu_sets['possible']),
        'cmdline_case':okay(read('/proc/cmdline')) and [s for s in read('/proc/cmdline').get('raw','').split() if s.startswith('die_case=')]==[f'die_case={build["profile"]}']}
    cpu_results = []
    dirs={e['path']:e for e in events if e['event']=='directory_stat'}
    for cpu in [0,1]:
        base=f'/sys/devices/system/cpu/cpu{cpu}/topology'
        controls={n:read(base+'/'+n) for n in ['physical_package_id','core_id','thread_siblings_list']}
        control_match = dirs.get(base,{}).get('is_directory') is True and all(okay(v) for v in controls.values())
        if control_match:
            try:
                integer(controls['physical_package_id']['raw'])
                integer(controls['core_id']['raw'])
                control_match = cpu in cpulist(controls['thread_siblings_list']['raw'])
            except (ValueError,KeyError): control_match = False
        foundation[f'cpu{cpu}_topology_controls'] = control_match
        die={n:read(base+'/'+n) for n in ['die_id','die_cpus','die_cpus_list']}
        if build['arch']=='s390' and build['profile'].startswith('fixed_'):
            match=all(v.get('status')=='open_error' and v.get('errno')==2 for v in die.values())
        else:
            match=all(okay(v) for v in die.values())
            if match:
                try:
                    die_id=integer(die['die_id']['raw'])
                    bitmap=cpumask(die['die_cpus']['raw'])
                    listing=cpulist(die['die_cpus_list']['raw'])
                    match=bitmap==listing and cpu in listing
                    if build['arch']=='s390': match=match and die_id==-1 and listing=={cpu}
                    else: match=match and die_id>=0
                except (ValueError,KeyError): match=False
        cpu_results.append({'cpu':cpu,'controls':controls,'die':die,'matches_contract':match})
    return {'events':events,'parse_errors':parse_errors,'raw_cpu_sets':raw_cpu_sets,'foundation':foundation,
            'cpus':cpu_results,'status':'PASS' if all(foundation.values()) and all(r['matches_contract'] for r in cpu_results) else 'MISMATCH',
            'scope':'real historical kernel under QEMU, not physical hardware truth'}


def qemu_argv(build: dict) -> list[str]:
    qemu='qemu-system-s390x' if build['arch']=='s390' else 'qemu-system-x86_64'
    topology=['-machine','s390-ccw-virtio-8.2','-cpu','max','-smp','2'] if build['arch']=='s390' else ['-machine','pc-i440fx-8.2','-cpu','qemu64','-smp','2,sockets=1,cores=2,threads=1']
    console='ttysclp0' if build['arch']=='s390' else 'ttyS0'
    return [qemu,'-accel','tcg']+topology+['-m','512','-nographic','-monitor','none','-no-reboot','-nic','none',
             '-kernel',build['image'],'-initrd',build['initrd'],'-append',f'console={console} rdinit=/init panic=1 quiet loglevel=3 die_case={build["profile"]}']


def boot_one(build: dict) -> dict:
    dest=HERE/'profiles'/build['profile']
    cached=dest/'boot.json'
    row={k:build.get(k) for k in ['profile','revision','arch','release','image_sha256',
                                  'init_source_sha256','init_binary_sha256','initrd_sha256']}
    if build['status']!='READY':
        row.update(status='NOT_RUN',reason='kernel build incomplete'); write(cached,row); return row
    argv=qemu_argv(build)
    row['qemu_argv']=argv
    row['analysis_runner_sha256']=digest(Path(__file__))
    if cached.exists():
        prior=json.loads(cached.read_text())
        binding=list(row)
        binding.remove('analysis_runner_sha256')
        if prior.get('status')=='PASS' and all(prior.get(k)==row[k] for k in binding):
            observations=analyse_log(build,Path(prior['qemu_receipt']['stdout']))
            row.update(status=observations['status'],observations=observations,
                       qemu_receipt=prior['qemu_receipt'],reanalysed_without_new_boot=True)
            write(cached,row)
            print(f'{build["profile"]}: reanalyse bound original boot log; no repeated boot',flush=True)
            return row
    print(f'{build["profile"]}: boot real kernel',flush=True)
    try:
        receipt=command(argv,dest,'qemu_boot',timeout=90)
        observations=analyse_log(build,Path(receipt['stdout']))
        row.update(status=observations['status'],observations=observations,qemu_receipt=receipt)
    except Exception as exc:
        row.update(status='ERROR',error=str(exc))
    write(cached,row)
    print(f'{build["profile"]}: boot {row["status"]}',flush=True)
    return row


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument('--build-only',action='store_true'); args=parser.parse_args()
    if os.name!='posix': raise RuntimeError('Run inside WSL')
    versions={tool:subprocess.check_output([tool,'--version']).decode().splitlines()[0] for tool in ['gcc','s390x-linux-gnu-gcc','qemu-system-x86_64','qemu-system-s390x']}
    write(HERE/'environment.json',versions)
    builds=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(build_one,label,arch) for label in VERSIONS for arch in ['x86_64','s390']]
        for future in concurrent.futures.as_completed(futures):
            builds.append(future.result()); write(HERE/'build_results.json',builds)
    builds.sort(key=lambda b:b['profile'])
    write(HERE/'build_results.json',builds)
    if not all(b['status']=='READY' for b in builds): raise SystemExit(1)
    config_pairs=[]
    for arch in ['x86_64','s390']:
        old=config_values(HERE/'profiles'/f'old_{arch}'/'kernel.config')
        fixed=config_values(HERE/'profiles'/f'fixed_{arch}'/'kernel.config')
        changes={k:{'old':old.get(k),'fixed':fixed.get(k)} for k in old.keys()|fixed.keys() if old.get(k)!=fixed.get(k)}
        old_lines=(HERE/'profiles'/f'old_{arch}'/'kernel.config').read_bytes().splitlines()
        fixed_lines=(HERE/'profiles'/f'fixed_{arch}'/'kernel.config').read_bytes().splitlines()
        exact_except_label=[l for l in old_lines if not l.startswith(b'CONFIG_LOCALVERSION=')]==[l for l in fixed_lines if not l.startswith(b'CONFIG_LOCALVERSION=')]
        config_pairs.append({'arch':arch,'differences':changes,'status':'PASS' if set(changes)=={'CONFIG_LOCALVERSION'} and exact_except_label else 'MISMATCH'})
    write(HERE/'configuration_pairs.json',config_pairs)
    if not all(p['status']=='PASS' for p in config_pairs): raise RuntimeError('Configuration drift between historical versions')
    if args.build_only: return
    boots=[]
    for b in builds:
        boots.append(boot_one(b)); write(HERE/'boot_results.json',boots)
    by_name={b['profile']:b for b in boots}
    old, fixed=by_name['old_x86_64'],by_name['fixed_x86_64']
    pair={'kind':'same virtual x86 topology preserves raw native die values', 'status':'NOT_EVALUATED'}
    if old['status']=='PASS' and fixed['status']=='PASS':
        before=[{k:v['raw'] for k,v in cpu['die'].items()} for cpu in old['observations']['cpus']]
        after=[{k:v['raw'] for k,v in cpu['die'].items()} for cpu in fixed['observations']['cpus']]
        pair.update(status='PASS' if before==after else 'MISMATCH', old_raw=before, fixed_raw=after)
    write(HERE/'x86_preservation.json',pair)
    if not all(b['status']=='PASS' for b in boots) or pair['status']!='PASS': raise SystemExit(1)


if __name__=='__main__': main()
