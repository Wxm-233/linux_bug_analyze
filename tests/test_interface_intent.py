"""Synthetic boundary controls; not independent interface/defect evaluation."""
import copy
import unittest

from linux_bug_analyze.contract_protocol import CLAIM_ROLES, SCHEMA
from linux_bug_analyze.interface_intent import check_intent, evaluate_with_intent


def fixture():
    contract = dict(schema=SCHEMA, id='example', revision='v1', authority_kind='consumer_inferred',
        sufficient_for_correctness=False, required_claims={r:r for r in CLAIM_ROLES},
        field_origins={k:'researcher_authored' for k in ('scope','relation','symbols','required_claims','authority_kind')},
        symbols={'enabled':{'type':'bool','role':'configuration'},
                 'cached':{'type':'int','role':'observation'},'reference':{'type':'int','role':'observation'}},
        scope={'symbol':'enabled'}, relation={'op':'eq','args':[{'symbol':'cached'},{'symbol':'reference'}]})
    intent=dict(schema='interface_intent_v1',interface_id='geometry.readiness',deadline_event='first-use',contract=contract)
    candidate=dict(interface_id=intent['interface_id'],deadline_event=intent['deadline_event'],
        contract=copy.deepcopy(contract),symbol_bindings={s:s for s in contract['symbols']})
    return intent,candidate


class IntentTests(unittest.TestCase):
    def test_matching_is_not_evidence(self):
        i,c=fixture();out=evaluate_with_intent(i,c,{},dict(deadline_event='first-use'))
        self.assertTrue(out['core_executed'])
        self.assertEqual(out['evaluation']['relation_at_deadline'],'insufficient')
        self.assertFalse(out['intent']['semantic_authority_established'])

    def test_alpha_rename_and_symmetric_equality(self):
        i,c=fixture();p=c['contract']
        p['symbols']['rhs']=p['symbols'].pop('reference')
        p['relation']['args']=[{'symbol':'rhs'},{'symbol':'cached'}]
        c['symbol_bindings']['rhs']=c['symbol_bindings'].pop('reference')
        self.assertEqual(check_intent(i,c)['intent_status'],'matches_registered_intent')

    def test_shifted_deadline_even_if_record_agrees(self):
        i,c=fixture();c['deadline_event']='later-sample'
        out=evaluate_with_intent(i,c,{},dict(deadline_event='later-sample'))
        self.assertFalse(out['core_executed'])

    def test_record_cannot_change_target(self):
        i,c=fixture();out=evaluate_with_intent(i,c,{},dict(deadline_event='later-sample'))
        self.assertFalse(out['core_executed'])

    def test_self_reference(self):
        i,c=fixture();p=c['contract'];del p['symbols']['reference']
        del c['symbol_bindings']['reference'];p['relation']['args']=[{'symbol':'cached'}]*2
        self.assertEqual(check_intent(i,c)['intent_status'],'insufficient')

    def test_role_aliasing(self):
        i,c=fixture();c['symbol_bindings']['reference']='cached'
        self.assertEqual(check_intent(i,c)['intent_status'],'insufficient')

    def test_narrowed_scope(self):
        i,c=fixture();c['contract']['scope']={'op':'not','args':[{'symbol':'enabled'}]}
        self.assertEqual(check_intent(i,c)['intent_status'],'insufficient')

    def test_changed_relation(self):
        i,c=fixture();c['contract']['relation']['op']='ne'
        self.assertEqual(check_intent(i,c)['intent_status'],'insufficient')

    def test_revision_binding(self):
        i,c=fixture();c['contract']['revision']='v2'
        self.assertEqual(check_intent(i,c)['intent_status'],'insufficient')

    def test_malformed_binding(self):
        i,c=fixture();c['symbol_bindings']['reference']=[]
        self.assertEqual(check_intent(i,c)['intent_status'],'insufficient')

    def test_type_mismatch(self):
        i,c=fixture()
        for s in ('cached','reference'):c['contract']['symbols'][s]['type']='string'
        self.assertEqual(check_intent(i,c)['intent_status'],'insufficient')

    def test_untrusted_origin_does_not_approve_core(self):
        i,c=fixture();c['contract']['field_origins']={k:'model_proposal' for k in c['contract']['field_origins']}
        out=evaluate_with_intent(i,c,{},dict(deadline_event='first-use'))
        self.assertTrue(out['core_executed'])
        self.assertEqual(out['evaluation']['relation_at_observation'],'insufficient')


if __name__=='__main__':unittest.main()
