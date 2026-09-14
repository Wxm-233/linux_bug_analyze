from unittest import TestCase
from experiments.iommu_contracts.run import function, permission_verdict, transition_verdict


class ContractOracleTests(TestCase):
    def test_permission_rejects_expansion_and_lost_write(self):
        self.assertEqual(permission_verdict(False, 2, 3), 'permission_mismatch')
        self.assertEqual(permission_verdict(False, 3, 1), 'permission_mismatch')

    def test_unsupported_is_not_a_pass(self):
        self.assertEqual(permission_verdict(True, 2, 3), 'unsupported_requires_negotiation')
        self.assertEqual(permission_verdict(False, 2, 2), 'pass')

    def test_checks_middle_state_not_only_endpoints(self):
        row = dict(scenario=0, disable_bypass=0, rc=0, trace=[0, 1, 2])
        self.assertIn('unexpected_bypass', transition_verdict(row))
        row['trace']=[0, 2]
        self.assertEqual(transition_verdict(row), [])

    def test_direct_requires_continuity(self):
        row = dict(scenario=1, disable_bypass=1, rc=0, trace=[1, 0, 2])
        self.assertIn('direct_mapping_interrupted', transition_verdict(row))

    def test_wrong_final_or_failed_attach_not_accepted(self):
        row=dict(scenario=0, disable_bypass=1, rc=0, trace=[0])
        self.assertIn('target_not_reached', transition_verdict(row))
        row.update(scenario=2,rc=-12,trace=[0,2])
        self.assertIn('failed_attach_not_isolated', transition_verdict(row))

    def test_release_and_invalid_trace(self):
        row=dict(scenario=6, disable_bypass=1, rc=0, trace=[2,0])
        self.assertIn('release_policy_mismatch', transition_verdict(row))
        row['trace']=[99]
        self.assertEqual(transition_verdict(row), ['invalid_trace'])

    def test_extraction_ignores_comment_and_string_braces(self):
        original='static void f() { /* } */ if (1) { puts("}"); } }'
        self.assertEqual(function(original+'\nvoid g() {}','static void f('),original)
