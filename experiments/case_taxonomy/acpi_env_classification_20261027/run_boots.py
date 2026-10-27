"""Boot the same image in the four frozen environments; hot-add one CPU over QMP after LBA_READY (run in WSL)."""
from pathlib import Path
import hashlib
import json
import os
import select
import socket
import subprocess
import time

HERE = Path(__file__).resolve().parent
BUILD = HERE / 'build_attempt1'
OUT = HERE / 'runs_attempt1'
PLAN = json.loads((HERE / 'frozen_plan.json').read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


class QMP:
    def __init__(self, path):
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        for _ in range(50):
            try:
                self.s.connect(path)
                break
            except OSError:
                time.sleep(0.1)
        self.buf = b''
        self.log = []
        self.log.append({'greeting': self._read()})

    def _read(self):
        while b'\n' not in self.buf:
            chunk = self.s.recv(65536)
            if not chunk:
                raise EOFError
            self.buf += chunk
        line, self.buf = self.buf.split(b'\n', 1)
        return json.loads(line)

    def cmd(self, name, **args):
        msg = {'execute': name}
        if args:
            msg['arguments'] = args
        self.s.sendall(json.dumps(msg).encode() + b'\n')
        while True:
            reply = self._read()
            if 'event' in reply:
                self.log.append({'event': reply})
                continue
            self.log.append({'command': msg, 'reply': reply})
            return reply


def boot(env):
    name = env['name']
    sock = f'/tmp/lba-acpi-env-{name}.qmp'
    if os.path.exists(sock):
        os.unlink(sock)
    append = 'console=ttyS0 rdinit=/init panic=-1 loglevel=7 lba_case=' + name + (' ' + env['append'] if env['append'] else '')
    argv = ['qemu-system-x86_64', '-machine', 'q35', '-accel', env['accel'], '-cpu', env['cpu'], '-m', '512',
            '-smp', '1,maxcpus=4', '-nodefaults', '-display', 'none', '-serial', 'stdio', '-no-reboot',
            '-qmp', f'unix:{sock},server=on,wait=off', '-kernel', str(BUILD / 'bzImage'),
            '-initrd', str(BUILD / 'initramfs.cpio.gz'), '-append', append]
    t0 = time.time()
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    console, qmp, hotplug, deadline = b'', None, None, t0 + 240
    while proc.poll() is None and time.time() < deadline:
        r, _, _ = select.select([proc.stdout], [], [], 0.5)
        if r:
            chunk = os.read(proc.stdout.fileno(), 65536)
            console += chunk
        if hotplug is None and b'LBA_READY' in console:
            qmp = QMP(sock)
            qmp.cmd('qmp_capabilities')
            slots = qmp.cmd('query-hotpluggable-cpus').get('return', [])
            free = [s for s in slots if 'qom-path' not in s]
            if free:
                slot = sorted(free, key=lambda s: json.dumps(s['props'], sort_keys=True))[0]
                args = {'driver': slot['type'], 'id': 'lbacpu1', **slot['props']}
                hotplug = {'slot': slot, 'device_add': qmp.cmd('device_add', **args)}
            else:
                hotplug = {'slot': None, 'device_add': None}
    timed_out = proc.poll() is None
    if timed_out:
        proc.kill()
    rest, err = proc.communicate()
    console += rest
    d = OUT / name
    d.mkdir()
    (d / 'console.log').write_bytes(console)
    (d / 'qemu.stderr.log').write_bytes(err)
    receipt = {'environment': env, 'argv': argv, 'returncode': proc.returncode, 'timed_out': timed_out,
               'seconds': round(time.time() - t0, 3), 'hotplug': hotplug, 'qmp_log': qmp.log if qmp else None,
               'console_sha256': sha(console), 'stderr_sha256': sha(err),
               'image_sha256': sha((BUILD / 'bzImage').read_bytes()),
               'initrd_sha256': sha((BUILD / 'initramfs.cpio.gz').read_bytes()),
               'config_sha256': sha((BUILD / 'kernel.config').read_bytes()),
               'ready_seen': b'LBA_READY' in console, 'done_seen': b'LBA_DONE' in console}
    (d / 'receipt.json').write_text(json.dumps(receipt, indent=1) + '\n')
    return receipt


def main():
    if OUT.exists():
        raise SystemExit('preserve runs_attempt1')
    OUT.mkdir()
    rows = [boot(env) for env in PLAN['environments']]
    (OUT / 'boot_execution.json').write_text(json.dumps(rows, indent=1) + '\n')
    print(json.dumps([{k: r[k] for k in ['returncode', 'timed_out', 'seconds', 'ready_seen', 'done_seen']}
                      | {'env': r['environment']['name'],
                         'device_add': (r['hotplug'] or {}).get('device_add')} for r in rows]))


if __name__ == '__main__':
    main()
