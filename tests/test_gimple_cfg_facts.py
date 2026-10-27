"""N2.13 current-format component tests, not real-source reference scores."""
from pathlib import Path
import copy
import hashlib
import unittest

from linux_bug_analyze.gimple_cfg_facts import analyze_cfg
from linux_bug_analyze.gimple_local_flow import analyze_gimple


def record(bodies=None, successors=None, loops=None, order=None):
    bodies = bodies or {2: '[a.c:1:1] if (a == b)\n goto <bb 3>; [INV]\n else\n goto <bb 4>; [INV]',
                        3: '[a.c:2:1] p->value = a;', 4: '[a.c:3:1] return;'}
    successors = successors or {2: [3, 4], 3: [4], 4: [1]}
    nodes = [0, 1] + sorted(bodies)
    all_loops = [{"id": 0, "header": 0, "latches": [1], "nodes": nodes, "depth": 0, "outer": -1}] + (loops or [])
    lines = [';; Function example (example, funcdef_no=1)', '', ';; ' + str(len(all_loops)) + ' loops found']
    for loop in all_loops:
        latch = 'latch ' + str(loop['latches'][0]) if len(loop['latches']) == 1 else 'multiple latches: ' + ' '.join(map(str, loop['latches']))
        lines += [';;', ';; Loop ' + str(loop['id']), ';;  header ' + str(loop['header']) + ', ' + latch,
                  ';;  depth ' + str(loop['depth']) + ', outer ' + str(loop['outer']), ';;  nodes: ' + ' '.join(map(str, loop['nodes']))]
    lines += [';; ' + str(block) + ' succs { ' + ' '.join(map(str, targets)) + ' }' for block, targets in successors.items()]
    lines += ['void example (int a, int b)', '{', ' int value;']
    for block in order or sorted(bodies): lines += [' <bb ' + str(block) + '> :', bodies[block]]
    return '\n'.join(lines + ['}', ''])


def analyze(text=None, local=None, identity='component'):
    return analyze_cfg({'id': identity, 'path': 'component.cfg', 'revision': 'dev', 'text': text or record()}, local_analysis=local)


def old_local(body, identity='component'):
    return analyze_gimple({'id': identity, 'path': 'component.gimple', 'revision': 'dev', 'text': 'void example ()\n{\n' + body + '\n}\n'})


class GimpleCfgFactsTests(unittest.TestCase):
    def test_exact_artificial_location_keeps_span_without_source_anchor(self):
        text = record({2: 'if (a == b) goto <bb 3>; [INV] else goto <bb 4>; [INV]',
                       3: '[0:0] goto <bb 4>; [INV]', 4: 'return;'}, {2: [3, 4], 3: [4], 4: [1]})
        result = analyze(text)
        self.assertEqual(result['status'], 'compiler_normal_graph_facts', result['unknowns'])
        span = next(item for item in result['lexical_spans'] if item['kind'] == 'compiler_artificial_location')
        self.assertEqual(span['raw'], '[0:0]')
        self.assertEqual(text[span['start_offset']:span['end_offset']], '[0:0]')
        goto = next(event for block in result['blocks'] for event in block['events'] if event['kind'] == 'goto')
        self.assertEqual(goto['source_locations'], [])
        self.assertEqual({(edge['source'], edge['target']) for edge in result['edges']}, {(2, 3), (2, 4), (3, 4), (4, 1)})
        self.assertFalse(result['runtime_reachability_proved'])

    def test_other_short_locations_and_mixed_malformed_control_fail_closed(self):
        for locus in ('[0:1]', '[1:0]', '[00:0]', '[0:0x]', '[0:0] [bad:location]'):
            with self.subTest(locus=locus):
                text = record({2: locus + ' goto <bb 3>; [INV]', 3: 'return;'}, {2: [3], 3: [1]})
                result = analyze(text)
                self.assertEqual(result['status'], 'insufficient_cfg_input')
                self.assertIn('unsupported_control_statement', str(result['unknowns']))
                self.assertFalse(result['edges'])

    def test_exact_always_inline_declaration_annotation_keeps_original_locus(self):
        text = record().replace('void example (int a, int b)', '__attribute__((always_inline))\nvoid example (int a, int b)')
        for source in (text, text.replace('\n', '\r\n')):
            with self.subTest(crlf='\r\n' in source):
                result = analyze(source)
                self.assertEqual(result['status'], 'compiler_normal_graph_facts', result['unknowns'])
                attribute = result['declaration_attributes'][0]
                self.assertEqual(attribute['name'], 'always_inline')
                self.assertEqual(source[attribute['start_offset']:attribute['end_offset']], attribute['raw'])
                self.assertEqual(source.splitlines()[attribute['dump_line_start'] - 1], '__attribute__((always_inline))')
                self.assertEqual(attribute['dump_line_start'], attribute['dump_line_end'])
                self.assertFalse(result['runtime_reachability_proved'])
                self.assertFalse(result['asm_or_call_must_return_proved'])
                self.assertEqual(result['source_sha256'], hashlib.sha256(source.encode('utf-8')).hexdigest())

    def test_unknown_multiple_or_parameterized_attributes_fail_closed(self):
        for name in ('naked', 'noreturn', 'always_inline, noreturn', 'always_inline(1)', '__always_inline__'):
            with self.subTest(name=name):
                text = record().replace('void example (int a, int b)', f'__attribute__(({name}))\nvoid example (int a, int b)')
                result = analyze(text)
                self.assertEqual(result['status'], 'insufficient_cfg_input')
                self.assertFalse(result['declaration_attributes'])
                self.assertFalse(result['edges'])

    def test_attribute_only_allowed_immediately_before_function_signature(self):
        annotation = '__attribute__((always_inline))\n'
        misplaced = [record().replace(';; 1 loops found', annotation + ';; 1 loops found'),
                     record().replace(' int value;', annotation + ' int value;'),
                     record().replace('[a.c:2:1] p->value = a;', annotation + '[a.c:2:1] p->value = a;'),
                     record().replace('void example (int a, int b)', annotation + '\nvoid example (int a, int b)'),
                     record().replace('void example (int a, int b)', annotation + annotation + 'void example (int a, int b)'),
                     record().replace('void example (int a, int b)', '__attribute__((always_inline)) void example (int a, int b)')]
        for text in misplaced:
            with self.subTest(text=text):
                result = analyze(text)
                self.assertEqual(result['status'], 'insufficient_cfg_input')
                self.assertFalse(result['declaration_attributes'])

    def test_metadata_edges_and_conditional_store_before_join(self):
        result = analyze()
        self.assertEqual(result['status'], 'compiler_normal_graph_facts', result['unknowns'])
        self.assertEqual({(e['source'], e['target']) for e in result['edges']}, {(2, 3), (2, 4), (3, 4), (4, 1)})
        relation = next(r for r in result['relations'] if r['kind'] == 'branch_to_store')
        self.assertEqual((relation['branch_block'], relation['arm'], relation['store_block'], relation['linear_join']), (2, 'true', 3, 4))
        self.assertFalse(result['runtime_reachability_proved'])
        self.assertFalse(result['alias_or_contract_proved'])

    def test_physical_order_does_not_create_edges(self):
        result = analyze(record(order=[2, 4, 3]))
        self.assertEqual(result['status'], 'compiler_normal_graph_facts', result['unknowns'])
        self.assertNotIn((4, 3), {(e['source'], e['target']) for e in result['edges']})
        self.assertIn((3, 4), {(e['source'], e['target']) for e in result['edges']})

    def test_inv_and_discriminator_are_annotations_not_polarity(self):
        text = record().replace('[a.c:1:1]', '[a.c:1:1 discrim 7]')
        result = analyze(text)
        self.assertEqual(result['status'], 'compiler_normal_graph_facts', result['unknowns'])
        branch = result['blocks'][0]['terminator']
        self.assertEqual(branch['targets'], [{'branch': 'true', 'block': 3}, {'branch': 'false', 'block': 4}])
        self.assertEqual(branch['source_locations'][0]['discriminator'], 7)
        self.assertFalse(any(e['kind'] == 'opaque' for b in result['blocks'] for e in b['events']))

    def test_explicit_polarity_must_agree_with_successors(self):
        text = record().replace(';; 2 succs { 3 4 }', ';; 2 succs { 3 }')
        result = analyze(text)
        self.assertEqual(result['status'], 'insufficient_cfg_input')
        self.assertIn('explicit_successors_disagree', str(result['unknowns']))
        self.assertFalse(result['edges'])
        self.assertFalse(result['relations'])

    def test_body_metadata_targets_and_unknown_format_fail_closed(self):
        changes = [(';; 3 succs { 4 }', ''), (';; 3 succs { 4 }', ';; 3 succs { 99 }'),
                   (';; 3 succs { 4 }', ';; 3 succs { 4 }\n;; 3 succs { 4 }'),
                   (';; 1 loops found', ';; 2 loops found'), (';; 1 loops found', ';; mystery graph extension')]
        for old, new in changes:
            with self.subTest(new=new):
                result = analyze(record().replace(old, new))
                self.assertEqual(result['status'], 'insufficient_cfg_input')
                self.assertFalse(result['relations'])

    def test_reported_loop_exit_and_multiple_latches(self):
        bodies = {2: 'goto <bb 4>; [INV]', 3: '[a.c:8:1] if (a == b) goto <bb 5>; [INV] else goto <bb 4>; [INV]',
                  4: 'if (a < b) goto <bb 3>; [INV] else goto <bb 6>; [INV]',
                  5: '[a.c:9:1] value = a;\ngoto <bb 6>; [INV]', 6: 'return;'}
        successors = {2: [4], 3: [5, 4], 4: [3, 6], 5: [6], 6: [1]}
        loop = {'id': 1, 'header': 4, 'latches': [3], 'nodes': [4, 3], 'depth': 1, 'outer': 0}
        result = analyze(record(bodies, successors, [loop]))
        self.assertEqual(result['status'], 'compiler_normal_graph_facts', result['unknowns'])
        exit_relation = next(r for r in result['relations'] if r['kind'] == 'branch_arm_exits_loop' and r['branch_block'] == 3)
        self.assertEqual((exit_relation['arm'], exit_relation['target_block'], exit_relation['target_successors']), ('true', 5, [6]))
        self.assertTrue(exit_relation['target_assignments'])
        bodies = {2: 'if (a == b) goto <bb 3>; [INV] else goto <bb 4>; [INV]', 3: 'goto <bb 2>; [INV]', 4: 'goto <bb 2>; [INV]'}
        successors = {2: [3, 4], 3: [2], 4: [2]}
        loop = {'id': 1, 'header': 2, 'latches': [3, 4], 'nodes': [2, 3, 4], 'depth': 1, 'outer': 0}
        result = analyze(record(bodies, successors, [loop]))
        self.assertEqual(result['status'], 'compiler_normal_graph_facts', result['unknowns'])
        self.assertEqual(result['loops'][1]['latches'], [3, 4])
        self.assertFalse(result['loops'][1]['exit_edges'])
        bad = analyze(record(bodies, successors, [dict(loop, header=3)]))
        self.assertEqual(bad['status'], 'insufficient_cfg_input')
        self.assertIn('loop_latch_edge_missing', str(bad['unknowns']))

    def test_false_arm_future_iteration_does_not_control_current_store(self):
        bodies = {2: 'if (a == b) goto <bb 3>; [INV] else goto <bb 4>; [INV]',
                  3: 'p->value = a;', 4: 'goto <bb 2>; [INV]'}
        successors = {2: [3, 4], 3: [4], 4: [2]}
        loop = {'id': 1, 'header': 2, 'latches': [4], 'nodes': [2, 3, 4], 'depth': 1, 'outer': 0}
        result = analyze(record(bodies, successors, [loop]))
        self.assertEqual(result['status'], 'compiler_normal_graph_facts', result['unknowns'])
        stores = [r for r in result['relations'] if r['kind'] == 'branch_to_store']
        self.assertEqual(len(stores), 1)
        self.assertEqual(stores[0]['arm'], 'true')
        self.assertEqual(result['branch_arms'][0]['prefixes']['false'], [])

    def test_exact_locus_shape_binding_and_ambiguity(self):
        local = old_local('[a.c:1:1] if (a == b) goto <D.4>; else goto <D.5>;\n<D.4>:\n[a.c:2:1] p->value = a;\n<D.5>:\n[a.c:3:1] return;')
        result = analyze(local=local)
        bound = [b for b in result['event_bindings'] if b['status'] == 'unique']
        self.assertEqual({b['kind'] for b in bound}, {'branch', 'store', 'return'})
        self.assertEqual(next(b['block'] for b in bound if b['kind'] == 'store'), 3)
        ambiguous = record().replace('[a.c:3:1] return;', '[a.c:2:1] p->value = a;\n[a.c:3:1] return;')
        result = analyze(ambiguous, local)
        store = next(b for b in result['event_bindings'] if b['kind'] == 'store')
        self.assertEqual((store['status'], store['reason']), ('insufficient', 'ambiguous_shape_locus_match'))
        result = analyze(local=local, identity='different_profile')
        self.assertTrue(all(b['status'] == 'insufficient' for b in result['event_bindings']))

    def test_locus_path_and_temp_names_are_not_silently_renamed(self):
        local = old_local('[other.c:2:1] p->value = a;')
        result = analyze(local=local)
        self.assertFalse(any(b['status'] == 'unique' for b in result['event_bindings']))
        local = old_local('[a.c:2:1] p->value = a.123_1;')
        result = analyze(local=local)
        self.assertFalse(any(b['status'] == 'unique' for b in result['event_bindings']))

    def test_discriminator_missing_in_old_is_not_an_exact_binding(self):
        local = old_local('[a.c:2:1] p->value = a;')
        result = analyze(record().replace('[a.c:2:1]', '[a.c:2:1 discrim 4]'), local)
        bound = next(b for b in result['event_bindings'] if b['kind'] == 'store')
        self.assertEqual((bound['status'], bound['reason']), ('insufficient', 'insufficient_discriminator_not_comparable'))

    def test_two_old_statements_cannot_both_bind_one_cfg_statement(self):
        local = old_local('[a.c:2:1] p->value = a;')
        store = copy.deepcopy(next(e for e in local['events'] if e['kind'] == 'store'))
        store['id'] = 'second_old_store'
        local['events'].append(store)
        result = analyze(local=local)
        stores = [b for b in result['event_bindings'] if b['kind'] == 'store']
        self.assertEqual(len(stores), 2)
        self.assertTrue(all(b['status'] == 'insufficient' and b['reason'] == 'ambiguous_old_shape_locus_match' for b in stores))

    def test_real_asm_is_whole_and_only_normal_successors(self):
        path = Path(__file__).resolve().parents[1] / 'experiments/case_taxonomy/compiler_consumer_frontend_20261018/old_s390.consumer.gimple.txt'
        text = path.read_bytes().decode('utf-8')
        start = text.index('__asm__ __volatile__ __inline__')
        terminal = '" :  : "i" 5762, "i" 2307, "i" 12);'
        stop = text.index(terminal, start) + len(terminal)
        result = analyze(record().replace('[a.c:2:1] p->value = a;', '[a.c:2:1 discrim 1] ' + text[start:stop]))
        self.assertEqual(result['status'], 'compiler_normal_graph_facts', result['unknowns'])
        asms = [e for b in result['blocks'] for e in b['events'] if e['kind'] == 'asm']
        self.assertEqual(len(asms), 1)
        continuation = next(r for r in result['relations'] if r['kind'] == 'branch_arm_asm_rejoins')
        self.assertEqual(continuation['linear_join'], 4)
        self.assertIs(continuation['asm_returns_proved'], False)
        self.assertFalse(any(e['kind'] == 'label' for b in result['blocks'] for e in b['events']))

    def test_unsupported_control_and_unclosed_asm_remain_insufficient(self):
        for body in ['switch (a) { }', 'asm("unterminated\np->fake = x;']:
            with self.subTest(body=body):
                result = analyze(record().replace('[a.c:2:1] p->value = a;', body))
                self.assertEqual(result['status'], 'insufficient_cfg_input')
                self.assertFalse(result['relations'])

    def test_missing_source_coordinates_do_not_get_previous_annotation(self):
        text = record().replace('[a.c:2:1] p->value = a;', '[a.c:99:1] // comment only\np->value = a;')
        result = analyze(text, old_local('[a.c:99:1] p->value = a;'))
        self.assertEqual(result['status'], 'compiler_normal_graph_facts', result['unknowns'])
        store = next(e for b in result['blocks'] for e in b['events'] if e['kind'] == 'store')
        self.assertFalse(store['source_locations'])
        self.assertFalse(any(b['status'] == 'unique' for b in result['event_bindings']))


if __name__ == '__main__': unittest.main()
