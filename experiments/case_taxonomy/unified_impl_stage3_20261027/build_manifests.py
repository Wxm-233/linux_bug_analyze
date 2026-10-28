"""Generate unified-entry case manifests from stored development materials (relations copied from the
original rounds; expected decisions taken from their stored results). Read-only over archives."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
CASES = HERE.parent
INNER = HERE.parents[2]
MAN = HERE / 'manifests'
REL = lambda p: Path(p).resolve().relative_to(INNER).as_posix()


def sym(n): return {'symbol': n}
def lit(v): return {'literal': v}
def op(name, *args): return {'op': name, 'args': list(args)}


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def save(name, m):
    m['schema'] = 'unified_case_v1'
    (MAN / (name + '.json')).write_text(json.dumps(m, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def acpi():
    root = CASES / 'acpi_env_classification_20261027'
    rows = {r['env']: r['decisions'] for r in load(root / 'analysis/results.json')['rows']}
    return {'case': 'acpi_env', 'family': 'firmware_platform', 'mechanism': 'scoped policy provider',
            'revision': 'adbf61cc47cb72b102682e690ad323e1eda652c2', 'basis': 'archived_runtime', 'authority_kind': 'documented',
            'policy': REL(root / 'checking_policy.md'), 'adapter': 'acpi_env_console',
            'config_symbols': ['supported_context', 'qemu_guest_with_legacy_slots', 'required_possible_count'],
            'inputs': [{'id': e, 'dir': REL(root / 'runs_attempt1' / e), 'params': {'required_possible_count': 4}} for e in rows],
            'relations': [{'name': 'P1_policy_reach', 'sample': 'after_boot_pid1_sysfs',
                           'scope': op('and', sym('supported_context'), sym('qemu_guest_with_legacy_slots')),
                           'relation': op('ge', sym('boot_possible_count'), sym('required_possible_count'))},
                          {'name': 'P3_hotplug_consumption', 'sample': 'after_hotplug_online_attempt', 'scope': sym('supported_context'),
                           'relation': op('eq', sym('online_outside_boot_possible'), lit([]))}],
            'expected': rows}


def sparc():
    root = CASES / 'sparc_identity_chain_20261027'
    execution = load(root / 'attempt1/execution.json')
    results = {r['context']: r['decisions'] for r in load(root / 'analysis/results.json')['rows']}
    revs = {'parent': '95706e717c4f55ca62025c151451ccc28863d085', 'fixed': '98937707fea8375e8acea0aaa0b68a956dd52719'}
    inputs, expected = [], {}
    for i, rec in enumerate(execution['records']):
        ctx = f"{rec['version']}.NR{rec['NR_CPUS']}.{rec['input']}.L{rec['L']}"
        inputs.append({'id': ctx, 'json': REL(root / 'attempt1/execution.json'), 'select': ['records', i], 'revision': revs[rec['version']]})
        expected[ctx] = results[ctx]
    sc = sym('supported_context')
    return {'case': 'sparc_identity_chain', 'family': 'cpu_identity_range', 'mechanism': 'identity/count/preparation',
            'revision': revs['fixed'], 'basis': 'source_projection', 'authority_kind': 'consumer_inferred',
            'policy': REL(root / 'checking_policy.md'), 'adapter': 'sparc_projection',
            'config_symbols': ['supported_context', 'limit_given', 'no_truncation_needed', 'limit'], 'inputs': inputs,
            'relations': [
                {'name': 'R1_identity', 'sample': 'after_setup_nr_cpu_ids', 'scope': sc, 'relation': op('eq', sym('invented_possible'), lit([]))},
                {'name': 'R2_count_limit', 'sample': 'after_setup_nr_cpu_ids', 'scope': op('and', sc, sym('limit_given')),
                 'relation': op('le', sym('possible_count'), sym('limit'))},
                {'name': 'R3_preserve', 'sample': 'after_setup_nr_cpu_ids', 'scope': op('and', sc, sym('no_truncation_needed')),
                 'relation': op('eq', sym('possible_set'), sym('provided_set'))},
                {'name': 'R4_irqstack', 'sample': 'after_bringup', 'scope': sc, 'relation': op('eq', sym('online_without_irqstack'), lit([]))},
                {'name': 'R5_percpu', 'sample': 'after_bringup', 'scope': sc, 'relation': op('eq', sym('online_without_percpu'), lit([]))}],
            'expected': expected}


def stage2_rows(section):
    return load(CASES / 'unified_impl_stage2_20261027/reproduction_results.json')['sections'][section]


def smmu():
    q, review = CASES / 'smmu_queue_20261026', CASES / 'smmu_review_20261026'
    names = [c['name'] for c in load(q / 'results.json')['cases']]
    controls = load(review / 'control_inputs.json')
    inputs = [{'id': n, 'json': REL(q / (n + '.json'))} for n in names]
    inputs += [{'id': 'control_' + c['name'], 'json': REL(review / 'control_inputs.json'), 'select': [i, 'raw']} for i, c in enumerate(controls)]
    expected = {r['case']: {'observed_encoding': r['dedicated_observed_encoding']} for r in stage2_rows('smmu_qtest')}
    ev = sym('events')
    kinds = ['payload_write', 'payload_readback', 'base_config', 'enable', 'enable_ack', 'prod_write', 'status_read']
    qual = op('and', op('ordered_within', ev, *[lit(k) for k in kinds]),
              op('eq', op('count_kind', ev, lit('unregistered')), lit(0)),
              op('eq', op('count_kind', ev, lit('payload_write')), sym('expected_payload_words')),
              op('eq', op('count_kind', ev, lit('payload_readback')), sym('expected_payload_words')),
              op('eq', op('count_kind', ev, lit('prod_write')), lit(1)),
              op('eq', op('count_kind', ev, lit('status_read')), lit(4)),
              op('eq', sym('reply_anomalies'), lit(0)), op('not', sym('unsupported_consumer_state')))
    return {'case': 'smmu_qtest', 'family': 'iommu', 'mechanism': 'ordered command submission', 'revision': 'smmu_queue_20261026',
            'basis': 'archived_runtime', 'authority_kind': 'consumer_inferred',
            'policy': REL(CASES / 'unified_impl_stage2_20261027/relations_policy.md'), 'adapter': 'smmu_qtest',
            'config_symbols': ['authority_verified', 'commands_present', 'expected_payload_words'], 'inputs': inputs,
            'relations': [{'name': 'observed_encoding', 'scope': op('and', sym('authority_verified'), sym('commands_present')),
                           'relation': op('eq', sym('reserved_commands'), lit(0)), 'qualification': qual}],
            'expected': expected}


def virtio():
    root = CASES / 'virtio_add_recycle_20261027'
    stored = load(root / 'results.json')
    controls = load(root / 'controls.json')
    inputs = [{'id': 'm%d_r%d_i%d' % (r['mode'], r['route'], r['indirect']), 'json': REL(root / 'results.json'), 'select': [i]} for i, r in enumerate(stored)]
    inputs += [{'id': 'control_' + c['name'], 'json': REL(root / 'controls.json'), 'select': [i, 'input']} for i, c in enumerate(controls)]
    expected = {r['case']: {'order': r['v2_parts'][0], 'completeness': r['v2_parts'][1]} for r in stage2_rows('virtio_split_trace')}
    ev = sym('events')
    cnt = lambda *k: op('count_kind', ev, *[lit(x) for x in k])
    qual = op('and', sym('parse_ok'), sym('final_present'), op('eq', cnt('attempt'), sym('final_attempts')),
              op('eq', cnt('map', 'map_fail'), sym('final_maps')), op('eq', cnt('unmap'), sym('final_unmaps')),
              op('eq', cnt('cpu_read'), sym('final_reads')), op('eq', cnt('barrier'), sym('final_barriers')))
    order = op('and',
               op('ordered_within', ev, *[lit(k) for k in ['attempt', 'map', 'bypass', 'barrier', 'publish', 'add_ok', 'used', 'unmap', 'token', 'cpu_read']]),
               op('ordered_within', ev, lit('attempt'), lit('map_fail'), lit('add_fail')),
               op('at_most_once_within', ev, *[lit(k) for k in ['attempt', 'map', 'bypass', 'map_fail', 'barrier', 'publish', 'add_ok', 'add_fail', 'used', 'unmap', 'token']]),
               op('exclusive_within', ev, lit('publish'), lit('add_fail')), op('exclusive_within', ev, lit('add_ok'), lit('add_fail')),
               op('generations_disjoint', ev))
    complete = op('and',
                  op('complete_within', ev, lit('cpu_read'), lit('attempt'), lit('barrier'), lit('publish'), lit('add_ok'), lit('used'), lit('token')),
                  op('complete_within', ev, lit('publish'), lit('attempt'), lit('barrier')),
                  op('complete_within', ev, lit('add_ok'), lit('publish')), op('complete_within', ev, lit('used'), lit('publish')),
                  op('or', op('and', op('eq', sym('route'), lit(0)), op('complete_within', ev, lit('token'), lit('bypass')),
                              op('eq', cnt('map'), lit(0)), op('eq', cnt('unmap'), lit(0))),
                        op('and', op('ne', sym('route'), lit(0)), op('complete_within', ev, lit('token'), lit('map'), lit('unmap')),
                           op('eq', cnt('bypass'), lit(0)))))
    return {'case': 'virtio_split_trace', 'family': 'dma', 'mechanism': 'per-object publication/recycle order',
            'revision': 'virtio_add_recycle_20261027', 'basis': 'archived_runtime', 'authority_kind': 'consumer_inferred',
            'policy': REL(CASES / 'unified_impl_stage2_20261027/relations_policy.md'), 'adapter': 'virtio_split_trace',
            'config_symbols': ['route'], 'inputs': inputs,
            'relations': [{'name': 'order', 'scope': op('ge', sym('route'), lit(0)), 'relation': order, 'qualification': qual},
                          {'name': 'completeness', 'scope': op('ge', sym('route'), lit(0)), 'relation': complete, 'qualification': qual}],
            'expected': expected}


def layout():
    path = CASES / 'virtio_platform_qualification_20261027/runtime_results.json'
    rows = load(path)
    return {'case': 'virtio_layout', 'family': 'dma', 'mechanism': 'maintenance-granule isolation (floor_to)',
            'revision': 'virtio_platform_qualification_20261027', 'basis': 'archived_runtime', 'authority_kind': 'consumer_inferred',
            'policy': REL(CASES / 'unified_impl_stage2_20261027/relations_policy.md'), 'adapter': 'virtio_layout',
            'config_symbols': ['granule'],
            'inputs': [{'id': r['name'], 'json': REL(path), 'select': [i]} for i, r in enumerate(rows)],
            'relations': [{'name': 'group_isolated', 'scope': op('gt', sym('granule'), lit(0)),
                           'relation': op('and', op('eq', op('floor_to', sym('evt'), sym('granule')), sym('evt')),
                                          op('le', sym('end'), op('floor_to', sym('lock'), sym('granule'))))}],
            'expected': {r['name']: {'group_isolated': 'satisfied' if r['group_geometry'] == 'isolated' else 'violated'} for r in rows}}


def btrfs():
    path = CASES / 'btrfs_method_20261026/results.json'
    diags = load(path)['diagnostics']
    ident = lambda d: '%s_%d_%d_%d' % (d['mode'], d['page_size'], d['disk_sector_size'], d['request'])
    return {'case': 'btrfs_min', 'family': 'memory_geometry', 'mechanism': 'clipping arithmetic (min)',
            'revision': 'btrfs_method_20261026', 'basis': 'archived_runtime', 'authority_kind': 'consumer_inferred',
            'policy': REL(CASES / 'unified_impl_stage2_20261027/relations_policy.md'), 'adapter': 'btrfs_min',
            'config_symbols': ['request'],
            'inputs': [{'id': ident(d), 'json': REL(path), 'select': ['diagnostics', i]} for i, d in enumerate(diags)],
            'relations': [{'name': 'min_clipping', 'scope': op('ge', sym('request'), lit(0)),
                           'relation': op('eq', sym('effective'), op('min', sym('request'), sym('geometry')))}],
            'expected': {ident(d): {'min_clipping': 'satisfied' if d['matches_archived_geometry_arithmetic'] else 'violated'} for d in diags}}


def unsupported():
    root = CASES / 'sparc_identity_objects_20261027'
    return {'case': 'sparc_compiled_objects', 'family': 'cpu_identity_range', 'mechanism': 'compiled width branch',
            'revision': '98937707fea8375e8acea0aaa0b68a956dd52719', 'basis': 'compiled_object', 'authority_kind': 'consumer_inferred',
            'policy': REL(CASES / 'unified_impl_stage2_20261027/relations_policy.md'), 'adapter': 'sparc_objects',
            'config_symbols': ['nr_cpus'],
            'inputs': [{'id': 'fixed-default', 'json': REL(root / 'analysis/object_facts.json'), 'select': ['fixed-default']}],
            'relations': [{'name': 'width_branch', 'scope': op('gt', sym('nr_cpus'), lit(0)), 'relation': op('eq', sym('irq_loop_bound'), lit('runtime_nr_cpu_ids'))}]}


def main():
    MAN.mkdir(exist_ok=False)
    for name, fn in [('acpi_env', acpi), ('sparc_identity_chain', sparc), ('smmu_qtest', smmu), ('virtio_split_trace', virtio),
                     ('virtio_layout', layout), ('btrfs_min', btrfs), ('sparc_compiled_objects_unsupported', unsupported)]:
        save(name, fn())
    print(sorted(p.name for p in MAN.iterdir()))


if __name__ == '__main__':
    main()
