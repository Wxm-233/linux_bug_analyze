import unittest
from linux_bug_analyze.observation_planning import assess_observability,plan_clamp_probes

class PlanningTests(unittest.TestCase):
 def test_no_sample_substitution(self):
  a={'sample':dict(status='available',origin='reviewed_adapter',references=['r'])}
  self.assertEqual(assess_observability(['deadline'],a)['missing'],['deadline'])
 def test_reviewed_coverage_not_authority(self):
  a={'cache':dict(status='available',origin='reviewed_adapter',references=['r'])}
  r=assess_observability(['cache'],a);self.assertEqual(r['missing'],[]);self.assertFalse(r['semantic_authority_established'])
 def test_no_model_approval(self):
  a={'cache':dict(status='available',origin='model_proposal',references=['r'])}
  self.assertEqual(assess_observability(['cache'],a)['status'],'insufficient')
 def test_no_reference(self):
  self.assertEqual(assess_observability(['cache'],{'cache':dict(status='available',origin='reviewed_adapter',references=[])})['missing'],['cache'])
 def test_duplicate_requirements(self):self.assertEqual(assess_observability(['a','a'],{})['status'],'invalid_input')
 def test_discrimination_and_control(self):
  r=plan_clamp_probes([8192,2048],[4096,65536]);self.assertEqual([x['role'] for x in r['rows']],['behavior_control','discriminating_probe'])
 def test_equal_boundary_control(self):self.assertEqual(plan_clamp_probes([4096],[4096,65536])['rows'][0]['role'],'behavior_control')
 def test_reversed_hypotheses_same_roles(self):
  self.assertEqual(plan_clamp_probes([2048,8192],[65536,4096])['rows'][1]['role'],'discriminating_probe')
 def test_no_duplicates_or_single_hypothesis(self):
  for xs in [[1],[1,1]]:self.assertEqual(plan_clamp_probes([2],xs)['status'],'invalid_input')
 def test_no_bool_negative_or_overflow(self):
  for x in [True,-1,2**64]:self.assertEqual(plan_clamp_probes([x],[1,2])['status'],'invalid_input')
