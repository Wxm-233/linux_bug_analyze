"""Generate and independently check reduced C from known revision evidence.

Revision IDs select development inputs only; the generator does not use them.
No kernel/driver is run. Failed attempts are preserved in separate directories.
"""
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
RULES = HERE.parent
sys.path.insert(0, str(RULES))
import structured_hci_single_revision as extractor
import contract_assertion_generator as generator
from gcc_projection_bindings import verify_bindings

INPUTS = [('parent', 'cef456cd354ef485f12d57000c455e83e416a2b6'),
          ('fix', '727ea61a5028f8ac96f75ab34cb1b56e63fd9227')]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')

def verify_runtime(rows, program, host_endian):
    layouts = [row for row in rows if row.get('kind') == 'layout']
    checks = [row for row in rows if row.get('kind') == 'field_check']
    if len(layouts) != 1 or layouts[0]['host_endian'] != host_endian:
        raise ValueError('actual runtime byte order/layout missing')
    fields = {field['name']:field for field in program['fields']}
    variants = [item['name'] if isinstance(item, dict) else item for item in program['variants']]
    expected_keys = {(variant, active, index, target) for variant in variants
                     for active in fields for index in range(3) for target in fields}
    seen, counts, failed_vectors = set(), Counter(), set()
    layout_by_field = {}
    for row in checks:
        key = row['variant'], row['case_field'], row['case_index'], row['field']
        if key in seen or key not in expected_keys:
            raise ValueError('unexpected/duplicate runtime field check')
        seen.add(key)
        if row['host_endian'] != host_endian:
            raise ValueError('runtime host endianness changed')
        if row['program'] != program['id']:
            raise ValueError('runtime program identity differs from plan')
        field = fields[row['field']]
        bits, width = field['bits'], field['bits']//8
        domain = {'le':'little', 'be':'big'}[field['endian']]
        value = row['expected_value']
        active_bits = fields[row['case_field']]['bits']
        if row['value'] != program['test_values'][str(active_bits)][row['case_index']]:
            raise ValueError('runtime input differs from planned asymmetric/zero controls')
        if not isinstance(value, int) or not 0 <= value < 2**bits:
            raise ValueError('runtime expected value outside host field width')
        # Per-case source initialization must not silently change another field.
        if row['field'] == row['case_field']:
            if value != row['value']:
                raise ValueError('active-field source differs from test input')
        elif value != 0:
            raise ValueError('inactive field not initialized to zero')
        if row['case_index'] == 2 and row['value'] != 0:
            raise ValueError('zero control not executed')
        if row['case_index'] < 2:
            active_width = fields[row['case_field']]['bits']//8
            bytes_ = int(row['value']).to_bytes(active_width, 'little')
            if not row['value'] or bytes_ == bytes_[::-1]:
                raise ValueError('nonzero asymmetric control missing')
        expected = value.to_bytes(width, domain).hex()
        if row['expected_bytes'] != expected or row['width'] != width:
            raise ValueError('C schema oracle differs from independent Python oracle')
        raw = bytes.fromhex(row['actual_bytes'])
        if len(raw) != width or row['decoded'] != int.from_bytes(raw, domain):
            raise ValueError('C decoder differs from independent byte decoder')
        producer_domain = domain
        if row['variant'] == 'actual':
            producer_domain = host_endian if field['producer_status'] == 'candidate' else domain
        elif row['variant'].startswith('partial_'):
            if row['variant'] == 'partial_'+row['field']:
                producer_domain = host_endian
        elif row['variant'] != 'reference':
            raise ValueError('unsupported generated variant')
        if row['actual_bytes'] != value.to_bytes(width, producer_domain).hex():
            raise ValueError('generated producer no longer preserves planned assignment relation')
        result = raw.hex() == expected and row['decoded'] == value
        if row['pass'] is not result:
            raise ValueError('C verdict disagrees with independent oracle')
        offset = row['offset']
        if not isinstance(offset, int) or offset < 0 or offset+width > layouts[0]['size']:
            raise ValueError('compiled field layout out of bounds')
        existing = layout_by_field.setdefault(row['field'], (offset, width))
        if existing != (offset, width):
            raise ValueError('compiled layout changes across variants')
        counts[(row['variant'], 'nonzero_checks' if value else 'zero_checks')] += 1
        if not result:
            counts[(row['variant'], 'failed_nonzero_checks' if value else 'failed_zero_checks')] += 1
            failed_vectors.add(key[:3])
    if seen != expected_keys:
        raise ValueError('incomplete runtime matrix')
    spans = sorted(layout_by_field.values())
    if any(start+width > next_start for (start,width),(next_start,_) in zip(spans,spans[1:])):
        raise ValueError('unexpected overlapping scalar fields')
    summaries = []
    for variant in variants:
        summaries.append(dict(variant=variant,
            nonzero_field_checks=counts[(variant,'nonzero_checks')],
            failed_nonzero_field_checks=counts[(variant,'failed_nonzero_checks')],
            zero_field_checks=counts[(variant,'zero_checks')],
            failed_zero_field_checks=counts[(variant,'failed_zero_checks')],
            failed_input_vectors=sum(vector[0]==variant for vector in failed_vectors)))
    return dict(host_endian=host_endian, compiled_layout=layouts[0],
                field_layout=layout_by_field, field_check_rows=len(checks),
                independent_oracle='All bytes, decoding, source relation, pass flags and matrix coverage verified',
                variants=summaries)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--linux-dir', type=Path, default=Path('/root/repos/linux'))
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if out.exists():
        raise RuntimeError('use a new output directory; attempts are preserved')
    out.mkdir(parents=True)
    commands, programs = [], []
    code_paths = [Path(generator.__file__), Path(extractor.__file__), Path(__file__),
                  HERE/'gcc_projection_bindings.py']
    started_code_hashes = {str(path):sha(path) for path in code_paths}
    def run(argv):
        process = subprocess.run(argv, capture_output=True, text=True)
        commands.append(dict(argv=argv, returncode=process.returncode,
                             stdout=process.stdout, stderr=process.stderr))
        if process.returncode:
            raise RuntimeError('command failed: '+str(argv)+': '+process.stderr)
        return process.stdout
    try:
        versions = {tool:run([tool,'--version']).splitlines()[0]
                    for tool in ('gcc','s390x-linux-gnu-gcc','qemu-s390x')}
        with tempfile.TemporaryDirectory(prefix='contract-assertions-') as temp:
            temp = Path(temp)
            for name, revision in INPUTS:
                report = extractor.analyze_revision(args.linux_dir, revision, 'net/bluetooth/hci_core.c')
                files = {row['path']:extractor.git_file(args.linux_dir, revision, row['path'])
                         for row in report['files_read']}
                save(out/(name+'_source_report.json'), report)
                plan = generator.build_plan(report, files)
                save(out/(name+'_plan.json'), plan)
                if plan['status'] != 'generated' or not plan['programs']:
                    raise ValueError('known complete payload was refused; see saved plan')
                if len(plan['programs']) > 8:
                    raise ValueError('bounded program cap exceeded')
                for index, program in enumerate(plan['programs']):
                    prefix = name+'_program_'+str(index)
                    source_path = out/(prefix+'.c')
                    source_path.write_text(generator.emit_c(program), encoding='utf-8')
                    targets = []
                    for target, compiler, launcher, byteorder in (
                        ('x86_64','gcc',[],'little'),
                        ('s390x','s390x-linux-gnu-gcc',['qemu-s390x'],'big')):
                        binary = temp/(prefix+'_'+target)
                        dump = out/(prefix+'_'+target+'_tree.txt')
                        run([compiler,'-std=gnu11','-static','-O0','-Wall','-Wextra','-Werror',
                             '-fdump-tree-original-raw='+str(dump),str(source_path),'-o',str(binary)])
                        bindings = verify_bindings(dump, program)
                        text = run(launcher+[str(binary)])
                        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
                        save(out/(prefix+'_'+target+'_rows.json'), rows)
                        check = verify_runtime(rows, program, byteorder)
                        check.update(target=target, gcc_bindings=bindings,
                                     executable_sha256=sha(binary), dump_sha256=sha(dump))
                        targets.append(check)
                    programs.append(dict(input=name, revision=revision, program_id=program['id'],
                        generated_source=source_path.name, generated_source_sha256=sha(source_path),
                        fields=program['fields'], targets=targets))
        for path in code_paths:
            if sha(path) != started_code_hashes[str(path)]:
                raise ValueError('code changed during run; this attempt is not version evidence')
        save(out/'results.json', dict(saved_at_utc=datetime.now(timezone.utc).isoformat(),
            status='verified', versions=versions, commands=commands, programs=programs,
            generator_sha256=sha(Path(generator.__file__)), extractor_sha256=sha(Path(extractor.__file__)),
            started_code_hashes=started_code_hashes,
            runner_sha256=sha(Path(__file__)), binding_checker_sha256=sha(HERE/'gcc_projection_bindings.py'),
            scope='Automatically generated known-case reduced TU, conditional on schema/source numeric assumptions. No independent bug, kernel or controller execution.'))
        print('automatic projections verified:', len(programs), 'programs on two targets')
    except Exception as exc:
        save(out/'failure.json', dict(saved_at_utc=datetime.now(timezone.utc).isoformat(),
            error=type(exc).__name__+': '+str(exc), commands=commands, completed_programs=programs,
            started_code_hashes=started_code_hashes))
        raise

if __name__ == '__main__':
    main()
