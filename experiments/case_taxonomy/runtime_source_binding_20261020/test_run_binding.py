"""Per-CPU evidence must not borrow candidates or other CPUs' success."""
import unittest
import run_binding as runner


class RuntimeBoundaryTests(unittest.TestCase):
    def test_self_consistent_single_cpu_cannot_replace_archived_pair(self):
        runner.validate_cpu_scope({'cpus': [{'cpu': 0}, {'cpu': 1}]})
        for rows in [[{'cpu': 0}], [{'cpu': False}, {'cpu': True}], [{'cpu': 0}, {'cpu': 0}], [{'cpu': 0}, {'cpu': 1}, {'cpu': 2}]]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                runner.validate_cpu_scope({'cpus': rows})

    def test_complete_presence_or_absence_does_not_prove_native_origin(self):
        for status, count, listed in [('all_success', 3, True), ('all_enoent', 0, False)]:
            with self.subTest(status=status):
                projected = runner.cpu_projection({'status': 'supported'}, {'cpu': 0, 'status': status, 'count': count, 'listed_any': listed,
                                                                                 'id_native': True, 'mask_native': True})
                self.assertEqual(projected['status'], 'supported')
                self.assertIsNone(projected['id_native']); self.assertIsNone(projected['mask_native'])
                self.assertFalse(projected['provider_body_reviewed'])

    def test_partial_or_mixed_group_and_failed_foundation_remain_insufficient(self):
        examples = [({'status': 'supported'}, {'cpu': 0, 'status': 'all_success', 'count': 1, 'listed_any': True}),
                    ({'status': 'supported'}, {'cpu': 0, 'status': 'all_enoent', 'count': 0, 'listed_any': True}),
                    ({'status': 'insufficient'}, {'cpu': 0, 'status': 'all_success', 'count': 3, 'listed_any': True}),
                    ({'status': 'supported'}, {'cpu': True, 'status': 'all_success', 'count': 3, 'listed_any': True}),
                    ({'status': 'supported'}, {'cpu': 0, 'status': 'all_enoent', 'count': False, 'listed_any': False})]
        for runtime, cpu in examples:
            with self.subTest(cpu=cpu, runtime=runtime):
                p = runner.cpu_projection(runtime, cpu)
                self.assertEqual(p['status'], 'insufficient'); self.assertIsNone(p['listed_any'])

    def test_source_candidate_cannot_close_actual_or_deadline_relation(self):
        projected = runner.cpu_projection({'status': 'supported'}, {'cpu': 0, 'status': 'all_success', 'count': 3, 'listed_any': True})
        row = runner.legacy.envelope('synthetic_boundary', runner.legacy.OLD, 'archived_runtime', 'method_boundary.cpu0', projected,
                                     True, runner.HERE / 'protocol_pre.json')
        self.assertNotIn('native_id', row['record']['facts'])
        result = runner.legacy.evaluate_contract(row['contract'], row['ledger'], row['record'])
        for key in ['relation_at_observation', 'relation_at_deadline', 'whole_path']:
            self.assertEqual(result[key], 'insufficient')
        self.assertEqual(row['policy_application'], 'counterfactual_policy_from_fixed')


if __name__ == '__main__': unittest.main()
