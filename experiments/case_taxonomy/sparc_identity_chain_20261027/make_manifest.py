"""Write delivery_manifest.json: SHA256 of every delivered file plus round statistics."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent


def main():
    files = {}
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and path.name != 'delivery_manifest.json' and '__pycache__' not in path.parts:
            files[path.relative_to(HERE).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    results = json.loads((HERE / 'analysis/results.json').read_text(encoding='utf-8'))
    controls = json.loads((HERE / 'controls/summary.json').read_text(encoding='utf-8'))
    manifest = {
        'date': '2026-10-27', 'files': files,
        'statistics': {'host_projection_builds': 4, 'projection_records': 24,
                       'core_evaluations': results['core_evaluations'], 'controls': controls['controls'],
                       'controls_as_expected': controls['as_expected'], 'decision_counts': results['decision_counts'],
                       'new_kernel_builds': 0, 'new_boots': 0, 'model_calls': 0, 'packages_installed': 0,
                       'confirmed_linux_defects': 0, 'independent_positive_normal': [0, 0]},
        'candidate': 'fixed/mainline sparc64 NR_CPUS>4*BITS_PER_LONG branch with nr_cpus below a sparse cpuid: '
                     'possible may exceed nr_cpus and IRQ stacks are not allocated for possible CPUs >= early nr_cpu_ids; '
                     'source projection only, unconfirmed',
    }
    (HERE / 'delivery_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(files))


if __name__ == '__main__':
    main()
