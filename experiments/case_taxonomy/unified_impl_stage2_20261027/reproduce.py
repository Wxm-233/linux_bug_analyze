"""(attempt2: FINAL map count includes MAP_FAIL, via multi-kind count_kind.)
Reproduce stored dedicated-checker conclusions with contract v2 (built by the shared builder).

Sections: SMMU qtest ordering (event_seq + reviewed qualification), virtio split publication/recycle
(event_seq), SPARC compiled objects (compiled_object tier), arithmetic (virtio layout floor_to,
Btrfs min). Adapters only turn stored raw inputs into facts; relations are evaluated by the core.
Dedicated checkers are imported read-only to regenerate their in-memory controls where needed.
"""
from pathlib import Path
from collections import Counter
import copy
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
CASES = HERE.parent
INNER = HERE.parents[2]
sys.path.insert(0, str(INNER))
from linux_bug_analyze.contract_envelope import build_envelope, document, symbol_type, symbols_used, whole  # noqa: E402
from linux_bug_analyze.contract_protocol import CLAIM_ROLES  # noqa: E402
from linux_bug_analyze.contract_protocol_v2 import evaluate_contract  # noqa: E402

OUT = HERE / 'reproduction'
POLICY = HERE / 'relations_policy.md'


def sym(n): return {'symbol': n}
def lit(v): return {'literal': v}
def op(name, *args): return {'op': name, 'args': list(args)}


def item(context, revision, basis, scope, relation, values, config, evidence, qualification=None):
    docs = {'evidence': document(evidence, INNER, revision, source_revision=revision),
            'policy': document(POLICY, INNER, revision, source_revision=revision)}
    names = symbols_used(scope, relation, *([qualification] if qualification else []))
    symbols = {n: {'type': symbol_type(values[n]), 'role': 'configuration' if n in config else 'observation'} for n in sorted(names)}
    roles = {r: {'statement': 'Registered relation for dedicated-checker reproduction; evidence tier as declared.',
                 'references': whole(docs, 'policy' if r in ('authority', 'consumer_requirement') else 'evidence')}
             for r in CLAIM_ROLES}
    spec = {'schema': 'architecture_contract_v2', 'contract_id': 'stage2.' + context, 'revision': revision, 'basis': basis,
            'context_id': context, 'object_id': context + '.object', 'sample_event': context + '.sample',
            'deadline_event': context + '.unobserved_consumer', 'authority_kind': 'consumer_inferred',
            'symbols': symbols, 'scope': scope, 'relation': relation, 'documents': docs, 'role_claims': roles,
            'observation_claim': {'statement': 'Stored raw input projected by the registered adapter.', 'references': whole(docs, 'evidence')},
            'facts': {n: {'value': values[n], 'statement': 'Adapter projection of the stored input.', 'references': whole(docs, 'evidence')} for n in symbols}}
    if qualification is not None:
        spec['observation_qualification'] = qualification
    return build_envelope(spec)


def judge(it):
    return evaluate_contract(it['contract'], it['ledger'], it['record'])['relation_at_observation']


def save_evidence(name, payload):
    path = OUT / (name + '.json')
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return path


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(mod)
    sys.path.pop(0)
    return mod


# ---------------- SMMU qtest ----------------
SMMU_KINDS = ['payload_write', 'payload_readback', 'base_config', 'enable', 'enable_ack', 'prod_write', 'status_read']


def smmu_facts(raw):
    words = raw.get('words') or []
    pairs = words + [[0x46, 0]]
    reserved = commands = 0
    for a, b in words:
        if a & 255 == 0x12:
            commands += 1
            tg, ttl, num, scale = (b >> 10) & 3, (b >> 8) & 3, (a >> 12) & 31, (a >> 20) & 31
            reserved += int(tg != 0 and ttl == num == scale == 0)
    lo, hi = 0x40010000, 0x40010000 + len(pairs) * 16
    events, anomalies, values = [], 0, {}
    written = {}
    requests = raw.get('requests', [])
    responses = raw.get('stdout', '').splitlines()
    anomalies += abs(len(requests) - len(responses))
    for req, resp in zip(requests, responses):
        p = req.split()
        opn, addr = p[0], int(p[1], 0)
        f = resp.split()
        if opn.startswith('write'):
            anomalies += int(f != ['OK'])
        else:
            anomalies += int(len(f) != 2 or f[0] != 'OK')
        if opn == 'writeq' and lo <= addr < hi:
            kind = 'payload_write'; written[addr] = int(p[2], 0)
        elif opn == 'readq' and lo <= addr < hi:
            kind = 'payload_readback'
            if len(f) == 2 and int(f[1], 0) != written.get(addr):
                anomalies += 1
        elif opn == 'writeq' and addr == 0x9050090: kind = 'base_config'
        elif opn == 'writel' and addr == 0x9050020: kind = 'enable'
        elif opn == 'readl' and addr == 0x9050024:
            kind = 'enable_ack'; anomalies += int(len(f) != 2 or int(f[1], 0) != 8)
        elif opn == 'writel' and addr == 0x9050098:
            kind = 'prod_write'; anomalies += int(int(p[2], 0) != len(pairs))
        elif opn == 'readl' and addr in (0x9050098, 0x905009c, 0x9050060, 0x9050064):
            kind = 'status_read'
            if len(f) == 2:
                values[addr] = int(f[1], 0)
        else:
            kind = 'unregistered'
        events.append([kind, 'cmdq', 0])
    cons, ge, gn = values.get(0x905009c), values.get(0x9050060), values.get(0x9050064)
    unsupported = cons is None or bool(cons & ~((127 << 24) | 127)) or (cons & 127) > len(pairs)
    return {'authority_verified': True, 'commands_present': commands > 0, 'expected_payload_words': 2 * len(pairs),
            'events': events, 'reply_anomalies': anomalies, 'unsupported_consumer_state': unsupported,
            'reserved_commands': reserved}


def smmu_contract(name, raw):
    v = smmu_facts(raw)
    ev = sym('events')
    qual = op('and', op('ordered_within', ev, *[lit(k) for k in SMMU_KINDS]),
              op('eq', op('count_kind', ev, lit('unregistered')), lit(0)),
              op('eq', op('count_kind', ev, lit('payload_write')), sym('expected_payload_words')),
              op('eq', op('count_kind', ev, lit('payload_readback')), sym('expected_payload_words')),
              op('eq', op('count_kind', ev, lit('prod_write')), lit(1)),
              op('eq', op('count_kind', ev, lit('status_read')), lit(4)),
              op('eq', sym('reply_anomalies'), lit(0)), op('not', sym('unsupported_consumer_state')))
    scope = op('and', sym('authority_verified'), sym('commands_present'))
    relation = op('eq', sym('reserved_commands'), lit(0))
    ev_path = save_evidence('smmu_' + name, {'raw': raw, 'facts': v})
    return item('smmu.' + name, 'smmu_queue_20261026', 'archived_runtime', scope, relation, v,
                {'authority_verified', 'commands_present', 'expected_payload_words'}, ev_path, qual)


def section_smmu():
    checker = load_module(CASES / 'smmu_review_20261026/checker.py', 'smmu_checker')
    mapping = {'violation': 'violated', 'pass_this_rule_only': 'satisfied', 'not_applicable': 'not_applicable', 'insufficient': 'insufficient'}
    rows = []
    q = CASES / 'smmu_queue_20261026'
    inputs = [(r['name'], json.loads((q / (r['name'] + '.json')).read_text(encoding='utf-8')))
              for r in json.loads((q / 'results.json').read_text(encoding='utf-8'))['cases']]
    inputs += [('control_' + c['name'], c['raw']) for c in json.loads((CASES / 'smmu_review_20261026/control_inputs.json').read_text(encoding='utf-8'))]
    for name, raw in inputs:
        dedicated = mapping[checker.assess(raw, True)['observed_encoding']]
        got = judge(smmu_contract(name, raw))
        rows.append({'case': name, 'dedicated_observed_encoding': dedicated, 'v2': got, 'match': dedicated == got})
    return rows


# ---------------- virtio split publication/recycle ----------------
VKINDS = {'MAP_OK': 'map', 'BYPASS': 'bypass', 'MAP_FAIL': 'map_fail', 'BEFORE_PUBLISH': 'barrier', 'PUBLISHED': 'publish',
          'SIM_USED': 'used', 'UNMAP': 'unmap', 'TOKEN': 'token', 'CPU_READ': 'cpu_read'}
IGNORED = {'LOCK', 'UNLOCK', 'RMB', 'EVENT_STORE', 'NO_TOKEN', 'KICK', 'MANUAL_RECOVERY', 'AFTER_FILL', 'AFTER_RECV', 'BROKEN_IN_CALLBACK'}


def virtio_facts(row):
    gens, current, events = {}, None, []
    final, unknown, parse_ok = None, 0, row.get('code') == 0
    for line in row['stdout'].splitlines():
        p = line.split()
        if not p:
            parse_ok = False
            continue
        tag = p[0]
        try:
            if tag == 'ATTEMPT':
                obj = int(p[2]); gens[obj] = gens.get(obj, 0) + 1; current = obj
                events.append(['attempt', 'buf%d' % obj, gens[obj]])
            elif tag in ('MAP_OK', 'MAP_FAIL', 'BEFORE_PUBLISH', 'PUBLISHED'):
                obj = int(p[2]) if tag != 'BYPASS' else int(p[1])
                events.append([VKINDS[tag], 'buf%d' % obj, gens.get(obj, 0)])
            elif tag == 'BYPASS':
                obj = int(p[1]); events.append(['bypass', 'buf%d' % obj, gens.get(obj, 0)])
            elif tag == 'ADD_RETURN':
                obj, ret = int(p[2]), int(p[3])
                events.append(['add_ok' if ret == 0 else 'add_fail', 'buf%d' % obj, gens.get(obj, 0)])
            elif tag in ('SIM_USED', 'UNMAP', 'TOKEN', 'CPU_READ'):
                obj = int(p[1]); events.append([VKINDS[tag], 'buf%d' % obj, gens.get(obj, 0)])
            elif tag == 'FINAL':
                final = list(map(int, p[1:]))
            elif tag not in IGNORED:
                unknown += 1
        except (IndexError, ValueError):
            parse_ok = False
    route = row.get('route')
    v = {'route': route, 'events': events, 'final_present': final is not None and len(final) == 8,
         'parse_ok': parse_ok and unknown == 0}
    keys = ['final_attempts', 'final_maps', 'final_unmaps', 'final_reads', 'final_kicks', 'final_barriers', 'final_g0', 'final_g1']
    for k, val in zip(keys, final or [-1] * 8):
        v[k] = val
    return v


def virtio_contracts(name, row):
    v = virtio_facts(row)
    ev = sym('events')
    cnt = lambda k: op('count_kind', ev, lit(k))
    qual = op('and', sym('parse_ok'), sym('final_present'),
              op('eq', cnt('attempt'), sym('final_attempts')),
              op('eq', op('count_kind', ev, lit('map'), lit('map_fail')), sym('final_maps')),  # attempt2: FINAL counts failed maps too
              op('eq', cnt('unmap'), sym('final_unmaps')), op('eq', cnt('cpu_read'), sym('final_reads')),
              op('eq', cnt('barrier'), sym('final_barriers')))
    order = op('and',
               op('ordered_within', ev, *[lit(k) for k in ['attempt', 'map', 'bypass', 'barrier', 'publish', 'add_ok', 'used', 'unmap', 'token', 'cpu_read']]),
               op('ordered_within', ev, lit('attempt'), lit('map_fail'), lit('add_fail')),
               op('at_most_once_within', ev, *[lit(k) for k in ['attempt', 'map', 'bypass', 'map_fail', 'barrier', 'publish', 'add_ok', 'add_fail', 'used', 'unmap', 'token']]),
               op('exclusive_within', ev, lit('publish'), lit('add_fail')),
               op('exclusive_within', ev, lit('add_ok'), lit('add_fail')),
               op('generations_disjoint', ev))
    complete = op('and',
                  op('complete_within', ev, lit('cpu_read'), lit('attempt'), lit('barrier'), lit('publish'), lit('add_ok'), lit('used'), lit('token')),
                  op('complete_within', ev, lit('publish'), lit('attempt'), lit('barrier')),
                  op('complete_within', ev, lit('add_ok'), lit('publish')),
                  op('complete_within', ev, lit('used'), lit('publish')),
                  op('or', op('and', op('eq', sym('route'), lit(0)), op('complete_within', ev, lit('token'), lit('bypass')),
                              op('eq', cnt('map'), lit(0)), op('eq', cnt('unmap'), lit(0))),
                        op('and', op('ne', sym('route'), lit(0)), op('complete_within', ev, lit('token'), lit('map'), lit('unmap')),
                           op('eq', cnt('bypass'), lit(0)))))
    scope = op('ge', sym('route'), lit(0))
    ev_path = save_evidence('virtio_' + name, {'row': row, 'facts': v})
    return [item('virtio.%s.%s' % (name, part), 'virtio_add_recycle_20261027', 'archived_runtime', scope, rel, v, {'route'}, ev_path, qual)
            for part, rel in (('order', order), ('completeness', complete))]


def section_virtio():
    checker = load_module(CASES / 'virtio_add_recycle_20261027/checker.py', 'virtio_checker')
    rows = []
    stored = json.loads((CASES / 'virtio_add_recycle_20261027/results.json').read_text(encoding='utf-8'))
    inputs = [('m%d_r%d_i%d' % (r['mode'], r['route'], r['indirect']), r) for r in stored]
    inputs += [('control_' + c['name'], c['input']) for c in json.loads((CASES / 'virtio_add_recycle_20261027/controls.json').read_text(encoding='utf-8'))]
    for name, row in inputs:
        dedicated = 'accepted' if checker.assess(row)['status'] != 'rejected' else 'rejected'
        decisions = [judge(it) for it in virtio_contracts(name, row)]
        v2 = 'accepted' if all(d == 'satisfied' for d in decisions) else 'rejected'
        rows.append({'case': name, 'dedicated': dedicated, 'v2_parts': decisions, 'v2': v2, 'match': v2 == dedicated})
    return rows


# ---------------- SPARC compiled objects ----------------
def section_objects():
    root = CASES / 'sparc_identity_objects_20261027'
    co = load_module(root / 'check_objects.py', 'check_objects_ro')
    facts = json.loads((root / 'analysis/object_facts.json').read_text(encoding='utf-8'))
    stored = json.loads((root / 'object_results.json').read_text(encoding='utf-8'))['decisions']
    revisions = {'parent': '95706e717c4f55ca62025c151451ccc28863d085', 'fixed': '98937707fea8375e8acea0aaa0b68a956dd52719'}

    def contract(name, variant, f, setup, weight, basis='compiled_object', schema=None):
        version, _ = variant.split('-')
        nr = int(f['config_NR_CPUS'])
        o1 = co.o1(setup, nr)[0] if setup is not None else 'insufficient'
        o2 = co.o2(weight, nr, version)[0]
        o3 = co.o3(f, nr)[0]
        v = {'nr_cpus': nr, 'irq_loop_bound': o1, 'weight_width': o2, 'i_expansion': o3}
        rel = op('and', op('eq', sym('i_expansion'), lit('matches')),
                 op('or', op('and', op('gt', sym('nr_cpus'), lit(64)), op('eq', sym('irq_loop_bound'), lit('runtime_nr_cpu_ids')),
                             op('eq', sym('weight_width'), lit('runtime_nr_cpu_ids'))),
                    op('and', op('le', sym('nr_cpus'), lit(64)), op('eq', sym('irq_loop_bound'), lit('constant_64')),
                       op('eq', sym('weight_width'), lit('constant_64')))))
        ev_path = save_evidence('objects_' + name, {'variant': variant, 'facts': v})
        it = item('objects.' + name, revisions[version], basis, op('gt', sym('nr_cpus'), lit(0)), rel, v, {'nr_cpus'}, ev_path)
        if schema:
            it['contract']['schema'] = schema
        return it

    rows = []
    for variant in co.VARIANTS:
        wf = 'record_one_cpu' if variant.startswith('fixed') else 'smp_fill_in_cpu_possible_map'
        dedicated_ok = all(x[0] in ('runtime_nr_cpu_ids', 'constant_64', 'matches', 'matches_version') for x in stored[variant].values())
        got = judge(contract(variant, variant, facts[variant], co.lines(variant, 'setup_arch'), co.lines(variant, wf)))
        rows.append({'case': variant, 'dedicated_consistent': dedicated_ok, 'v2': got, 'match': (got == 'satisfied') == dedicated_ok})
    fd = facts['fixed-default']
    setup, rec = co.lines('fixed-default', 'setup_arch'), co.lines('fixed-default', 'record_one_cpu')
    import re
    controls = [
        ('nr_cpu_ids_reloc_removed', 'fixed-default', fd, [l for l in setup if not re.search(r'R_SPARC_LO10\s+nr_cpu_ids$', l)], rec),
        ('irq_stack_stores_removed', 'fixed-default', fd, [l for l in setup if 'irq_stack' not in l], rec),
        ('weight_helper_swapped', 'fixed-default', fd, setup, [l.replace('__bitmap_weight', '__arch_hweight64') for l in rec]),
        ('default_labelled_nr64', 'fixed-default', dict(fd, config_NR_CPUS='64'), setup, rec),
        ('nr64_claimed_4096', 'fixed-nr64', dict(facts['fixed-nr64'], config_NR_CPUS='4096'), co.lines('fixed-nr64', 'setup_arch'), co.lines('fixed-nr64', 'record_one_cpu')),
        ('preprocessed_bound_constant', 'fixed-default', dict(fd, **{'setup_64.i:alloc_irqstack_bootmem': fd['setup_64.i:alloc_irqstack_bootmem'].replace('(nr_cpu_ids)', '(((unsigned int)4096))')}), setup, rec),
    ]
    for name, variant, f, s, w in controls:
        got = judge(contract('control_' + name, variant, f, s, w))
        rows.append({'case': 'control_' + name, 'dedicated_consistent': False, 'v2': got, 'match': got != 'satisfied'})
    tier = judge(contract('tier_check_v1_schema', 'fixed-default', fd, setup, rec, schema='architecture_contract_v1'))
    rows.append({'case': 'v1_schema_cannot_carry_compiled_object', 'v2': tier, 'match': tier == 'insufficient'})
    return rows


# ---------------- arithmetic ----------------
def section_arithmetic():
    rows = []
    for r in json.loads((CASES / 'virtio_platform_qualification_20261027/runtime_results.json').read_text(encoding='utf-8')):
        L, base, lay = r['maintenance_stride'], r['base'], r['layout']
        v = {'granule': L, 'evt': base + lay['evts'], 'end': base + lay['end'], 'lock': base + lay['lock']}
        rel = op('and', op('eq', op('floor_to', sym('evt'), sym('granule')), sym('evt')),
                 op('le', sym('end'), op('floor_to', sym('lock'), sym('granule'))))
        ev_path = save_evidence('layout_' + r['name'], {'runtime_result': {k: r[k] for k in ('name', 'layout', 'base', 'maintenance_stride')}, 'facts': v})
        got = judge(item('layout.' + r['name'], 'virtio_platform_qualification_20261027', 'archived_runtime',
                         op('gt', sym('granule'), lit(0)), rel, v, {'granule'}, ev_path))
        dedicated = 'satisfied' if r['group_geometry'] == 'isolated' else 'violated'
        rows.append({'case': 'layout_' + r['name'], 'dedicated_group_geometry': r['group_geometry'], 'v2': got, 'match': got == dedicated})
    diags = json.loads((CASES / 'btrfs_method_20261026/results.json').read_text(encoding='utf-8'))['diagnostics']
    for i, d in enumerate(diags):
        v = {'request': d['request'], 'effective': d['effective'], 'geometry': d['disk_sector_size']}
        rel = op('eq', sym('effective'), op('min', sym('request'), sym('geometry')))
        ev_path = save_evidence('btrfs_%d' % i, {'diagnostic': d, 'facts': v})
        got = judge(item('btrfs.%d' % i, 'btrfs_method_20261026', 'archived_runtime', op('ge', sym('request'), lit(0)), rel, v, {'request'}, ev_path))
        dedicated = 'satisfied' if d['matches_archived_geometry_arithmetic'] else 'violated'
        rows.append({'case': 'btrfs_%s_%d_%d_%d' % (d['mode'], d['page_size'], d['disk_sector_size'], d['request']), 'dedicated': dedicated, 'v2': got, 'match': got == dedicated})
    v = {'granule': 0, 'evt': 256, 'end': 768, 'lock': 768}
    ev_path = save_evidence('layout_zero_granule_control', {'facts': v})
    got = judge(item('layout.zero_granule', 'virtio_platform_qualification_20261027', 'archived_runtime', op('ge', sym('granule'), lit(0)),
                     op('eq', op('floor_to', sym('evt'), sym('granule')), sym('evt')), v, {'granule'}, ev_path))
    rows.append({'case': 'control_zero_granule', 'v2': got, 'match': got == 'insufficient'})
    return rows


def main():
    if OUT.exists():
        raise SystemExit('preserve reproduction/')
    OUT.mkdir()
    sections = {'smmu_qtest': section_smmu(), 'virtio_split_trace': section_virtio(),
                'sparc_compiled_objects': section_objects(), 'arithmetic': section_arithmetic()}
    summary = {k: {'cases': len(v), 'match': sum(r['match'] for r in v), 'v2': dict(Counter(r['v2'] for r in v))} for k, v in sections.items()}
    (HERE / 'reproduction_results.json').write_text(json.dumps({'summary': summary, 'sections': sections}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))
    for k, v in sections.items():
        for r in v:
            if not r['match']:
                print('MISMATCH', k, r)


if __name__ == '__main__':
    main()
