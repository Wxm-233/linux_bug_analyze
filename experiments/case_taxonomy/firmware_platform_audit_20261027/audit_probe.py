"""Read-only audit of existing firmware/platform materials plus accelerator feasibility probes (run in WSL).

No kernel build or Linux boot. QEMU is started paused with no guest code (-S) and told to quit.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
OUT = INNER / 'analysis_out'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def acpi_contract_integrity():
    root = OUT / 'acpi-contract-20260914-v2'
    manifest = json.loads((root / 'manifest.json').read_text())
    entries = manifest.get('artifacts', manifest)
    bad, n = [], 0
    for rel, digest in entries.items():
        if isinstance(digest, dict):
            digest = digest.get('sha256')
        if not isinstance(digest, str) or len(digest) != 64:
            continue
        n += 1
        p = root / rel
        if not p.is_file() or sha(p) != digest:
            bad.append(rel)
    summary = json.loads((root / 'summary.json').read_text())
    return {'checked': n, 'mismatched_or_missing': bad, 'summary_keys': sorted(summary)[:12]}


def acpi_kunit_integrity():
    """Same assertions as experiments/acpi_kunit/verify.py, without writing verified-summary.json."""
    root = OUT / 'acpi-kunit-20260914'
    result = {}
    for mode in ('before', 'after'):
        run = json.loads((root / f'{mode}-run.json').read_text())
        bad = [n for n, d in run['artifacts'].items() if sha(root / n) != d]
        rows = []
        for row in run['runs']:
            boot = (root / row['log']).read_text(errors='replace')
            found = re.findall(r'^\s*(not ok|ok) \d+ (fixture_installed|actual_cpu_masks|actual_apic_membership)\b', boot, re.M)
            failed = sorted({n for status, n in found if status == 'not ok'})
            headers = re.findall(r'ACPI: (FACP|APIC) 0x[0-9A-F]+ [0-9A-F]+ \((v\d+) BOCHS', boot)
            rows.append({'scenario': row['scenario'], 'returncode': row['returncode'], 'failed': failed,
                         'hypervisor_line': bool(re.search(r'Hypervisor detected', boot)),
                         'firmware_headers': sorted(set(headers)),
                         'qemu_accel': next((a for a in row['command'] if a.startswith('-accel') or 'accel=' in a), None)})
        result[mode] = {'artifacts_checked': len(run['artifacts']), 'artifact_mismatch': bad, 'runs': rows}
    return result


def probe(name, argv):
    try:
        done = subprocess.run(argv, input='quit\n', capture_output=True, text=True, timeout=30)
        return {'name': name, 'argv': argv, 'returncode': done.returncode,
                'stderr': done.stderr[-600:], 'stdout_tail': done.stdout[-300:]}
    except subprocess.TimeoutExpired:
        return {'name': name, 'argv': argv, 'returncode': None, 'timeout': True}


def main():
    target = HERE / 'audit_probe_results.json'
    if target.exists():
        raise SystemExit('preserve audit_probe_results.json')
    base = ['qemu-system-x86_64', '-machine', 'q35', '-display', 'none', '-nodefaults', '-monitor', 'stdio', '-S']
    probes = [
        probe('tcg', base + ['-accel', 'tcg']),
        probe('kvm', base + ['-accel', 'kvm']),
        probe('kvm_xen_hvm_emulation', base + ['-accel', 'kvm,xen-version=0x4000a,kernel-irqchip=split']),
        probe('kvm_hotplug_slots', base + ['-accel', 'kvm', '-smp', '1,maxcpus=4', '-cpu', 'qemu64']),
    ]
    env = {
        'kvm_device': subprocess.run(['ls', '-l', '/dev/kvm'], capture_output=True, text=True).stdout.strip(),
        'qemu': subprocess.run(['qemu-system-x86_64', '--version'], capture_output=True, text=True).stdout.splitlines()[0],
        'xen_tools': subprocess.run(['bash', '-c', 'command -v xl xenstore-read || true'], capture_output=True, text=True).stdout.strip(),
        'nproc': subprocess.run(['nproc'], capture_output=True, text=True).stdout.strip(),
    }
    result = {'acpi_contract_v2': acpi_contract_integrity(), 'acpi_kunit': acpi_kunit_integrity(),
              'environment': env, 'probes': probes, 'kernel_builds': 0, 'linux_boots': 0, 'model_calls': 0}
    target.write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'acpi_contract_mismatch': len(result['acpi_contract_v2']['mismatched_or_missing']),
                      'acpi_contract_checked': result['acpi_contract_v2']['checked'],
                      'kunit': {m: (v['artifacts_checked'], len(v['artifact_mismatch']),
                                    [(r['scenario'], r['failed'], r['hypervisor_line']) for r in v['runs']])
                                for m, v in result['acpi_kunit'].items()},
                      'headers': result['acpi_kunit']['after']['runs'][0]['firmware_headers'],
                      'accel_in_kunit': result['acpi_kunit']['after']['runs'][0]['qemu_accel'],
                      'env': env, 'probes': [(p['name'], p['returncode'], p.get('stderr', '')[:160]) for p in probes]},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
