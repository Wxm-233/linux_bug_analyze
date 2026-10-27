"""Development tests guarding false credit in the source comparison adapter."""
import unittest
from compare_source_checks import dependency_state, evaluate, label, selected


class AdapterAttributionTests(unittest.TestCase):
    def test_label_and_source_path_identity_are_not_lost_in_adaptation(self):
        self.assertEqual([label(x) for x in ['D.2', '<D.2>', '<D.2>:']], ['D.2'] * 3)
        packet = {'status': 'partial_local_facts', 'events': [
            {'id': 'a', 'kind': 'load', 'source_locations': [{'path': 'a.c', 'line': 4}]},
            {'id': 'b', 'kind': 'load', 'source_locations': [{'path': 'b.c', 'line': 4}]}]}
        self.assertEqual(len(selected(packet, {'source_path': 'a.c', 'source_line': 4})), 1)
        result = evaluate({'id': 'ambiguous', 'profile': 'component', 'op': 'event_count',
                           'selector': {'kind': 'load', 'source_line': 4}, 'expected': {'count': 2}}, packet)
        self.assertEqual(result['status'], 'insufficient')

    def test_dependency_walk_cannot_cross_unknown_call_argument_result_boundary(self):
        origin = {'id': 'input_def', 'kind': 'load', 'region': 0, 'defines': ['a']}
        call = {'id': 'call', 'kind': 'call', 'region': 0, 'defines': ['b']}
        use = {'id': 'use', 'kind': 'branch', 'region': 1}
        analysis = {'events': [origin, call, use], 'dependencies': [
            {'use_event': 'call', 'definition_event': 'input_def', 'variable': 'a', 'region': 0},
            {'use_event': 'use', 'definition_event': 'call', 'variable': 'b', 'region': 1}],
            'unresolved_uses': []}
        self.assertEqual(dependency_state(analysis, call, use, 'b')[0], 'supported')
        self.assertEqual(dependency_state(analysis, origin, use)[0], 'not_established')

    def test_missing_definition_anchor_cannot_pass_a_negative_relation_check(self):
        result = evaluate({'id': 'negative', 'profile': 'component', 'op': 'dependency',
                           'def_selector': {'kind': 'load'}, 'use_selector': {'kind': 'branch'},
                           'expected': {'relation': 'unresolved'}},
                          {'status': 'partial_local_facts', 'events': [], 'dependencies': [], 'unresolved_uses': []})
        self.assertEqual(result['status'], 'insufficient')

    def test_unrelated_live_in_is_not_evidence_for_an_unresolved_selected_value(self):
        definition = {'id': 'a', 'defines': ['x'], 'region': 1}
        use = {'id': 'b', 'region': 1}
        state, _ = dependency_state({'dependencies': [], 'unresolved_uses': [
            {'use_event': 'b', 'variable': 'unrelated_pointer', 'region': 1, 'reason': 'live_in_or_barrier_cleared'}]},
                                    definition, use)
        self.assertEqual(state, 'not_established')

    def test_zero_events_with_unparsed_spans_is_insufficient(self):
        result = evaluate({'id': 'zero', 'profile': 'component', 'op': 'event_count',
                           'selector': {'kind': 'return'}, 'expected': {'count': 0}},
                          {'status': 'partial_local_facts', 'events': [{'id': 'unknown', 'kind': 'opaque'}]})
        self.assertEqual(result['status'], 'insufficient')

    def test_explicit_two_targets_must_bind_to_actual_label_events(self):
        check = {'id': 'edges', 'profile': 'component', 'op': 'explicit_edge',
                 'from_selector': {'kind': 'branch'}, 'expected': {'target_labels': ['<D.2>', 'D.1']}}
        analysis = {'status': 'partial_local_facts', 'events': [
            {'id': 'b', 'kind': 'branch'}, {'id': 'l1', 'kind': 'label'}, {'id': 'l2', 'kind': 'label'}],
            'control_edges': [{'source_event': 'b', 'target_label': 'D.1', 'target_event': 'l1'},
                              {'source_event': 'b', 'target_label': '<D.2>', 'target_event': 'l2'}]}
        self.assertEqual(evaluate(check, analysis)['status'], 'match')
        analysis['control_edges'][1]['target_event'] = 'missing'
        self.assertEqual(evaluate(check, analysis)['status'], 'insufficient')


if __name__ == '__main__':
    unittest.main()
