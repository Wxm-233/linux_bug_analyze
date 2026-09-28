"""Execute unchanged historical ACPI parser functions with logical test doubles."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from experiments.iommu_contracts.run import function

VERSIONS = {
    'before': 'aa06e20f1be628186f0c2dcec09ea0009eb69778^',
    'lapic_only': 'aa06e20f1be628186f0c2dcec09ea0009eb69778',
    'both_madt': 'e2869bd7af608c343988429ceb1c2fe99644a01f',
    'both_fadt': 'a74fabfbd1b7013045afc8cc541e6cab3360ccb5',
    'legacy_all': 'fed8d8773b8ea68ad99d9eee8c8343bef9da2c2c',
    'guest_scoped': 'adbf61cc47cb72b102682e690ad323e1eda652c2',
}
# Explicit contract fixtures, not an implementation of the historical predicate.
# Accepted flags for bare metal / guest; Enabled=1 with reserved bit=1 is omitted.
PLATFORMS = [
    ('legacy_62', 6, 2, 4, False, (1,), (0, 1)),
    ('legacy_62b', 6, 2, 45, False, (1,), (0, 1)),
    ('modern_63', 6, 3, 5, True, (1, 2), (1, 2)),
    ('modern_64', 6, 4, 5, True, (1, 2), (1, 2)),
    ('future_major', 7, 0, 5, True, (1, 2), (1, 2)),
]


def support_slice(source):
    body = function(source, 'static int __init acpi_parse_madt(')
    for prefix in ('\tif (madt->header.revision >= 5)',
                   '\tif (acpi_gbl_FADT.header.revision > 6'):
        if prefix in body:
            start = body.index(prefix)
            end = body.index('acpi_support_online_capable = true;', start)
            return body[start:end + len('acpi_support_online_capable = true;')]
    if 'acpi_support_online_capable' in body:
        raise ValueError('Unrecognized capability detection')
    return ''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--linux-dir', type=Path, required=True)
    ap.add_argument('--outdir', type=Path, required=True)
    args = ap.parse_args()
    out = args.outdir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    manifest = {'scope': 'source-slice C execution; not kernel boot, binary table parsing or CPU hotplug',
                'compiler': subprocess.check_output(['gcc', '--version'], text=True).splitlines()[0],
                'versions': {}}
    summaries = {}
    for name, ref in VERSIONS.items():
        folder = out / name
        folder.mkdir()
        def read(path):
            data = subprocess.check_output(['git', '-C', str(args.linux_dir), 'show', ref + ':' + path])
            (folder / path.replace('/', '_')).write_bytes(data)
            return data.decode()
        source = read('arch/x86/kernel/acpi/boot.c')
        header = read('include/acpi/actbl2.h')
        constants = '\n'.join(re.findall(r'^#define\s+ACPI_MADT_(?:ENABLED|ONLINE_CAPABLE)\s+.*$', header, re.M))
        assert len(constants.splitlines()) == 2
        sections = {'capability': support_slice(source)}
        for key, sig in [('lapic', 'static int __init\nacpi_parse_lapic('),
                         ('x2apic', 'static int __init\nacpi_parse_x2apic(')]:
            sections[key] = function(source, sig)
        if 'static bool __init acpi_is_processor_usable(' in source:
            sections['predicate'] = function(source, 'static bool __init acpi_is_processor_usable(')
        if 'static int acpi_register_lapic(' in source:
            sections['register'] = function(source, 'static int acpi_register_lapic(')
        (folder / 'slices.json').write_text(json.dumps(sections, indent=2) + '\n')
        here = Path(__file__).parent
        combined = (here / 'harness.h').read_text() + '\n' + constants + '\n'
        combined += 'static void determine_support(struct acpi_table_madt *madt) {\n(void)madt;\n' + sections['capability'] + '\n}\n'
        combined += '\n'.join(sections[k] for k in ('register', 'predicate', 'lapic', 'x2apic') if k in sections)
        combined += '\n' + (here / 'main.c').read_text()
        cfile = folder / 'experiment.c'
        cfile.write_text(combined)
        # Some shared doubles are unused in individual historical versions.
        command = ['gcc', '-std=gnu11', '-O0', '-Wall', '-Wextra', '-Werror',
                   '-Wno-unused-function', '-Wno-unused-variable', str(cfile), '-o', str(folder/'experiment')]
        build = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (folder/'build.log').write_text(build.stdout)
        build.check_returncode()
        rows = []
        for label, major, minor, madt, support, bare, guests in PLATFORMS:
            for guest, kind, flags in itertools.product((0, 1), (0, 1), (0, 1, 2) if support else (0, 1)):
                observed = json.loads(subprocess.check_output([str(folder/'experiment'), *map(str, (major, minor, madt, guest, kind, flags))], text=True))
                accepted = int(flags in (guests if guest else bare))
                expected = {'rc': 0, 'support': int(support), 'accepted': accepted,
                            'enabled_registered': int(accepted and flags == 1),
                            'disabled_registered': int(accepted and flags != 1)}
                errors = [key for key in expected if observed[key] != expected[key]]
                rows.append(dict(platform=label, guest=bool(guest), entry='x2apic' if kind else 'lapic', flags=flags,
                                 observed=observed, expected=expected, errors=errors))
        (folder/'results.json').write_text(json.dumps(rows, indent=2)+'\n')
        summaries[name] = {'cases': len(rows), 'acceptance_mismatches': sum('accepted' in r['errors'] for r in rows),
                           'capability_mismatches': sum('support' in r['errors'] for r in rows),
                           'fully_matching': sum(not r['errors'] for r in rows)}
        manifest['versions'][name] = {'ref': ref, 'resolved': subprocess.check_output(['git','-C',str(args.linux_dir),'rev-parse',ref],text=True).strip(),
                                      'compile_command': command}
    # The regression gate checks named counterexamples, not just aggregate counts.
    def row(version, platform, guest, entry, flags):
        return next(r for r in json.loads((out/version/'results.json').read_text())
                    if (r['platform'],r['guest'],r['entry'],r['flags'])==(platform,guest,entry,flags))
    assert row('lapic_only','modern_63',False,'lapic',0)['observed']['accepted']==0
    assert row('lapic_only','modern_63',False,'x2apic',0)['observed']['accepted']==1
    assert row('both_madt','legacy_62b',True,'lapic',0)['observed']['support']==1
    assert row('both_fadt','legacy_62b',True,'lapic',0)['observed']['support']==0
    assert row('both_fadt','legacy_62',True,'x2apic',0)['observed']['accepted']==0
    assert row('legacy_all','legacy_62',False,'lapic',0)['observed']['accepted']==1
    assert summaries['guest_scoped']['fully_matching']==52
    for name in VERSIONS:
        # An enabled CPU is accepted even before capability detection existed.
        # Its acceptance control must not demand later-version feature detection.
        assert all(r['observed']['accepted']==1 and r['observed']['enabled_registered']==1
                   for r in json.loads((out/name/'results.json').read_text()) if r['flags']==1)
    manifest['artifacts'] = {str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
    print(json.dumps(summaries,indent=2))


if __name__ == '__main__':
    main()
