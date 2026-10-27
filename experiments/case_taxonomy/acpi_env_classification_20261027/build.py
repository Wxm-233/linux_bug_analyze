"""Archive the fixed revision, build an x86_64 defconfig bzImage, a static PID1 and a newc initramfs (run in WSL)."""
from pathlib import Path
import gzip
import hashlib
import json
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
REV = 'adbf61cc47cb72b102682e690ad323e1eda652c2'
REPO = Path('/root/repos/linux')
CACHE = Path('/root/.cache/linux-bug-analyze/acpi-env-20261027')
SRC, BUILD = CACHE / 'linux', CACHE / 'build'
OUT = HERE / 'build_attempt1'
KEYS = ['CONFIG_SMP', 'CONFIG_HOTPLUG_CPU', 'CONFIG_ACPI_HOTPLUG_CPU', 'CONFIG_HYPERVISOR_GUEST', 'CONFIG_PARAVIRT',
        'CONFIG_KVM_GUEST', 'CONFIG_BLK_DEV_INITRD', 'CONFIG_DEVTMPFS', 'CONFIG_NR_CPUS', 'CONFIG_X86_X2APIC',
        'CONFIG_SERIAL_8250_CONSOLE', 'CONFIG_LOCALVERSION']
ENSURE = ['KVM_GUEST', 'ACPI_HOTPLUG_CPU', 'DEVTMPFS']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(name, argv, **kw):
    t0 = time.time()
    done = subprocess.run(argv, capture_output=True, **kw)
    (OUT / f'{name}.stdout.log').write_bytes(done.stdout)
    (OUT / f'{name}.stderr.log').write_bytes(done.stderr)
    return {'step': name, 'argv': [str(a) for a in argv], 'returncode': done.returncode, 'seconds': round(time.time() - t0, 3)}


def config_values():
    text = (BUILD / '.config').read_text()
    vals = {}
    for k in KEYS:
        m = re.search(rf'^{k}=(.*)$', text, re.M)
        vals[k] = m.group(1) if m else ('not set' if f'# {k} is not set' in text else 'absent')
    return vals


def newc(entries):
    """entries: (name, mode, data_bytes, rdev_major, rdev_minor)."""
    out = bytearray()
    for ino, (name, mode, data, maj, mnr) in enumerate(entries + [('TRAILER!!!', 0, b'', 0, 0)], 1):
        nb = name.encode() + b'\0'
        hdr = '070701' + ''.join(f'{v:08x}' for v in [ino, mode, 0, 0, 1, 0, len(data), 0, 0, maj, mnr, len(nb), 0])
        out += hdr.encode() + nb
        out += b'\0' * ((4 - len(out) % 4) % 4)
        out += data
        out += b'\0' * ((4 - len(out) % 4) % 4)
    return bytes(out)


def main():
    if OUT.exists():
        raise SystemExit('preserve build_attempt1')
    OUT.mkdir()
    steps = []
    if not SRC.exists():
        SRC.mkdir(parents=True)
        archive = subprocess.run(['git', '-C', str(REPO), 'archive', REV], capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', str(SRC)], input=archive, check=True)
        steps.append({'step': 'archive', 'tar_sha256': hashlib.sha256(archive).hexdigest(), 'bytes': len(archive)})
    make = ['make', '-C', str(SRC), f'O={BUILD}', 'ARCH=x86_64', '-j20']
    steps.append(run('defconfig', make + ['x86_64_defconfig']))
    before = config_values()
    cfg = [str(SRC / 'scripts/config'), '--file', str(BUILD / '.config'), '--set-str', 'LOCALVERSION', '-lba-acpi-env']
    enabled = []
    for k in ENSURE:
        if before['CONFIG_' + k] != 'y':
            cfg += ['--enable', k]
            enabled.append(k)
    steps.append(run('config_edit', cfg))
    steps.append(run('olddefconfig', make + ['olddefconfig']))
    after = config_values()
    steps.append(run('bzImage', make + ['bzImage']))
    image = BUILD / 'arch/x86/boot/bzImage'
    if image.exists():
        shutil.copyfile(image, OUT / 'bzImage')
        shutil.copyfile(BUILD / '.config', OUT / 'kernel.config')
        shutil.copyfile(BUILD / 'vmlinux', CACHE / 'vmlinux')
    steps.append(run('pid1', ['gcc', '-static', '-O2', '-Wall', '-o', str(OUT / 'init'), str(HERE / 'guest_init.c')]))
    if (OUT / 'init').exists():
        entries = [('dev', 0o40755, b'', 0, 0), ('proc', 0o40755, b'', 0, 0), ('sys', 0o40755, b'', 0, 0),
                   ('dev/console', 0o20600, b'', 5, 1), ('init', 0o100755, (OUT / 'init').read_bytes(), 0, 0)]
        (OUT / 'initramfs.cpio.gz').write_bytes(gzip.compress(newc(entries), mtime=0))
    receipt = {'revision': REV, 'steps': steps, 'config_after_defconfig': before, 'config_final': after,
               'enabled_because_absent': enabled,
               'artifacts': {p.name: sha(p) for p in OUT.iterdir() if p.suffix not in {'.log'} and p.is_file()},
               'kernel_release': (BUILD / 'include/config/kernel.release').read_text().strip()
               if (BUILD / 'include/config/kernel.release').exists() else None}
    (OUT / 'build_receipt.json').write_text(json.dumps(receipt, indent=1) + '\n')
    print(json.dumps({'steps': [(s['step'], s.get('returncode'), s.get('seconds')) for s in steps],
                      'enabled': enabled, 'final': after, 'release': receipt['kernel_release']}))


if __name__ == '__main__':
    main()
