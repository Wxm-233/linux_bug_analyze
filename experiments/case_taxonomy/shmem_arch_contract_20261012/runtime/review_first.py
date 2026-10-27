"""Review only the fixed first old ARM64/64K run; never infer from syscall success.

This is an evidence check for an already-read case, not a defect detector.
The original console log remains the source of all observations.
"""
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent
OUT = HERE / 'old_arm64_64k'
NAMES = ['partial_in', 'partial_out', 'split_in', 'split',
         'xarray_in', 'xarray_out', 'punch']
CHAIN = ['SC_ALLOC', 'SC_INSERT', 'partial_in', 'split_in',
         'xarray_in', 'xarray_out', 'split', 'partial_out', 'punch']
POINTERS = {'page', 'folio', 'mapping', 'fmap', 'entry', 'xas', 'node', 'flags', 'flags1'}


def review(rows, receipt):
    checks = {}

    def check(name, condition):
        checks[name] = bool(condition)

    def one(event):
        found = [r for r in rows if r.get('event') == event]
        if len(found) != 1:
            raise ValueError(f'Expected one {event}, got {len(found)}')
        return found[0]

    def raw(path):
        found = [r for r in rows if r.get('event') == 'file' and r.get('path') == path]
        if len(found) != 1 or found[0]['errno'] or found[0]['truncated']:
            raise ValueError(f'Incomplete capture: {path}')
        value = found[0]['raw']
        if len(value.encode()) != found[0]['bytes']:
            raise ValueError(f'Capture length differs: {path}')
        return value

    try:
        build = receipt['build']
        g = one('geometry')
        check('fixed_revision', build['revision'] == '3390916aca7af1893ed2ebcdfee1d6fdb65bb058')
        check('qemu_completed_once', receipt['qemu']['exit_code'] == 0 and receipt['qemu']['attempt'] == 1)
        check('pid1_schema', one('begin') == {'event': 'begin', 'schema': 'shmem_chain_v1', 'pid': 1})
        check('kernel_identity', one('uname')['release'] == build['release'] and one('uname')['machine'] == 'aarch64')
        check('instrumentation_declared', build['source_instrumentation'])
        check('target_geometry', (g['runtime_page_size'], g['page_shift'], g['pmd_shift'], g['pmd_order'], g['chunk_shift']) == (65536, 16, 29, 13, 6))
        check('target_layout_bound', g['head_mask'] == build['geometry']['FOLIO_HEAD_MASK'] and g['xa_nomem'] == build['geometry']['XA_NOMEM_ENCODING'])
        end = one('end')
        check('init_completed', end['failures'] == 0 and end['reached_end'])
        ops = [r for r in rows if r['event'] == 'operation']
        check('operations_succeeded', all(r['return'] >= 0 and r['errno'] == 0 for r in ops))
        check('tmpfs_policy', bool(re.search(r'^tmpfs /work tmpfs .*size=1048576k,huge=always ', raw('/proc/mounts'), re.M)))
        check('single_cpu', raw('/sys/devices/system/cpu/online').strip() == '0')
        inp = one('input')
        check('fixed_input', inp == {'event': 'input', 'file_size': 1 << 29, 'offset': 2 * 65536 + 17, 'write_hex': '5aa5', 'hole_length': 1, 'mode': 3})
        definitions = [r['raw'] for r in rows if r['event'] == 'probe_definition']
        registrations = [r for r in ops if r['path'] == '/trace/kprobe_events']
        check('registrations_complete', len(definitions) == len(registrations) == 7 and all(r['return'] == len(d.encode()) for r, d in zip(registrations, definitions)))
        events = raw('/trace/kprobe_events')
        check('registered_names', sorted(re.findall(r'shmem_contract/(\w+)', events)) == sorted(NAMES))
        profile = {m.group(1): (int(m.group(2)), int(m.group(3))) for m in re.finditer(r'^\s*(\w+)\s+(\d+)\s+(\d+)\s*$', raw('/trace/kprobe_profile'), re.M)}
        check('one_hit_no_miss', profile == {n: (1, 0) for n in NAMES})
        stats = {m.group(1): int(m.group(2)) for m in re.finditer(r'^([\w ]+):\s*(\d+)\s*$', raw('/trace/per_cpu/cpu0/stats'), re.M)}
        check('no_trace_loss', all(stats.get(n) == 0 for n in ['overrun', 'commit overrun', 'dropped events']))
        trace = raw('/trace/trace')
        found = []
        for line in trace.splitlines():
            if not line.strip() or line.startswith('#'):
                continue
            m = re.match(r'\s*init-1\s+\[000\]\s+\S+\s+(\d+\.\d+):\s+(\w[^:]*):\s+(.*)', line)
            if not m:
                raise ValueError('Trace contains an unassociated task/CPU/event')
            payload = m.group(3)
            name = payload.split()[0] if payload.startswith('SC_') else m.group(2)
            values = {}
            for key, value in re.findall(r'(\w+)=(-?(?:0x)?[\da-f]+)\b', payload):
                values[key] = int(value, 16 if key in POINTERS else 10)
            found.append({'name': name, 'time': float(m.group(1)), 'fields': values})
        check('complete_ordered_trace', [r['name'] for r in found] == CHAIN and all(a['time'] <= b['time'] for a, b in zip(found, found[1:])))
        check('trace_count', stats.get('entries') == 9 and len(found) == 9 and 'entries-in-buffer/entries-written: 9/9' in trace)
        if not all(checks.values()):
            return {'status': 'OBSERVATION_INSUFFICIENT', 'checks': checks}

        facts = {r['name']: r['fields'] for r in found}
        a, i, p = facts['SC_ALLOC'], facts['SC_INSERT'], facts['partial_in']
        if not (a['page'] and a['order'] == a['requested'] == 13 and i['order'] == 13):
            return {'status': 'TARGET_PATH_NOT_OBTAINED', 'checks': checks, 'trace': found}
        ptr = a['page']
        check('same_folio_all_steps', i['folio'] == p['folio'] == facts['split_in']['page'] == facts['split']['page'] == facts['xarray_in']['entry'] == facts['xarray_out']['entry'] == facts['partial_out']['folio'] == ptr)
        check('successful_same_mapping_index', i['rc'] == 0 and i['mapping'] != 0 and i['mapping'] == i['fmap'] == p['fmap'] and i['index'] == i['findex'] == p['findex'] == 0)
        check('actual_large_order_at_use', bool(p['flags'] & g['head_mask']) and (p['flags1'] & 255) == 13)
        check('partial_range', p['start'] == p['end'] == inp['offset'])
        check('base_page_split', facts['split_in']['new_order'] == facts['split']['new_order'] == 0)
        xi, xo = facts['xarray_in'], facts['xarray_out']
        check('same_xarray_context', xi['xas'] != 0 and xi['xas'] == xo['xas'] and xi['order'] == xo['order'] == 13 and xi['shift'] == xo['shift'] == 0)
        check('actual_consumer_limit_exceeded', xi['order'] > xi['shift'] + 2 * g['chunk_shift'])
        check('internal_nomem', xo['node'] == g['xa_nomem'] and facts['split']['rc'] == -12 and facts['partial_out']['rc'] == 0)
        punch = facts['punch']
        check('punch_parameters', punch == {'mode': 3, 'offset': inp['offset'], 'length': 1, 'rc': 0})
        check('syscall_and_readback', any(r['name'] == 'punch_hole' and r['return'] == 0 for r in ops) and any(r['name'] == 'pread' and r['return'] == 2 for r in ops) and one('readback')['hex'] == '00a5')
        dmesg = one('dmesg')
        check('dmesg_captured', dmesg['errno'] == 0)
        warnings = [line for line in dmesg['raw'].splitlines() if 'WARNING:' in line]
        check('same_task_consumer_warning', len(warnings) == 1 and 'CPU: 0 PID: 1' in warnings[0] and 'lib/xarray.c:' in warnings[0] and 'xas_split_alloc+' in warnings[0])
        return {'status': 'OBSERVED_OLD_CONTRACT_MISMATCH' if all(checks.values()) else 'CHAIN_OR_OUTCOME_INSUFFICIENT',
                'checks': checks, 'trace': found, 'warning': warnings,
                'observed_policy': {'defrag': raw('/sys/kernel/mm/transparent_hugepage/defrag').strip(),
                                    'shmem_enabled': raw('/sys/kernel/mm/transparent_hugepage/shmem_enabled').strip()},
                'scope': 'One instrumented historical kernel in QEMU TCG; known case; paired fixed/4K runs pending'}
    except (ValueError, KeyError, TypeError) as error:
        return {'status': 'OBSERVATION_INSUFFICIENT', 'checks': checks, 'reason': str(error)}


def main():
    console = (OUT / 'qemu_boot.stdout.log').read_text()
    rows = [json.loads(line) for line in console.splitlines() if line.startswith('{')]
    result = review(rows, json.loads((OUT / 'boot_receipt.json').read_text()))
    (OUT / 'review.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'checks': len(result['checks']),
                      'failed': [k for k, v in result['checks'].items() if not v]}))


if __name__ == '__main__':
    main()
