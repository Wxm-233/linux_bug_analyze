import copy
import unittest
from linux_bug_analyze.candidate_parts import inspect_parts
from tests.test_interface_intent import fixture


def inputs():
    _,candidate=fixture()
    roles={k:dict(v) for k,v in candidate['contract']['symbols'].items()}
    facts={k:dict(value=v,origin='program_projection',context_id='run',evidence=[{'archive':'synthetic fixture'}])
           for k,v in [('enabled',True),('cached',4)]}
    return candidate,roles,facts


class PartsTests(unittest.TestCase):
    def test_missing_reference_not_filled(self):
        c,r,f=inputs();f['adjacent']=dict(f['cached'])
        out=inspect_parts(c,r,f,context_id='run')
        self.assertEqual(out['summary']['relation']['insufficient'],1)

    def test_observed_values_do_not_approve_deadline(self):
        c,r,f=inputs();f['reference']=dict(f['cached']);out=inspect_parts(c,r,f,context_id='run')
        self.assertEqual(out['summary']['relation']['satisfied'],1)
        self.assertEqual(out['relation_at_deadline'],'insufficient')

    def test_nested_and_all_preserved(self):
        c,r,f=inputs();eq=copy.deepcopy(c['contract']['relation'])
        c['contract']['relation']={'op':'and','args':[eq,{'op':'and','args':[eq,eq]}]}
        before=copy.deepcopy(c);out=inspect_parts(c,r,f,context_id='run')
        self.assertEqual(out['summary']['relation']['insufficient'],3)
        self.assertEqual(c,before)
        self.assertEqual(out['original_relation'],before['contract']['relation'])

    def test_or_not_split(self):
        c,r,f=inputs();eq=copy.deepcopy(c['contract']['relation'])
        c['contract']['relation']={'op':'or','args':[eq,{'literal':True}]}
        out=inspect_parts(c,r,f,context_id='run')
        self.assertEqual(len([x for x in out['parts'] if x['field']=='relation']),1)
        self.assertEqual(out['summary']['relation']['insufficient'],1)

    def test_duplicate_roles_not_repaired(self):
        c,r,f=inputs();c['symbol_bindings']['reference']='cached'
        out=inspect_parts(c,r,f,context_id='run')
        self.assertEqual(out['binding_status'],'insufficient')
        self.assertEqual(out['summary']['relation']['insufficient'],1)

    def test_type_mismatch(self):
        c,r,f=inputs();r['cached']['type']='string'
        self.assertEqual(inspect_parts(c,r,f,context_id='run')['binding_status'],'insufficient')

    def test_fact_type_bool_is_not_int(self):
        c,r,f=inputs();f['cached']['value']=True
        out=inspect_parts(c,r,f,context_id='run')
        self.assertIn('fact type mismatch',[x['reason'] for row in out['parts'] for x in row['missing']])

    def test_other_context(self):
        c,r,f=inputs();f['cached']['context_id']='other'
        out=inspect_parts(c,r,f,context_id='run')
        self.assertIn('untrusted or different-context fact',[x['reason'] for row in out['parts'] for x in row['missing']])

    def test_model_fact_not_admitted(self):
        c,r,f=inputs();f['cached']['origin']='model_proposal'
        out=inspect_parts(c,r,f,context_id='run')
        self.assertEqual(out['summary']['relation']['insufficient'],1)

    def test_invalid_scope_does_not_drop_relation(self):
        c,r,f=inputs();c['symbol_bindings']['enabled']='missing';f['reference']=dict(f['cached'])
        out=inspect_parts(c,r,f,context_id='run')
        self.assertEqual(out['binding_status'],'insufficient')
        self.assertEqual(out['summary']['relation']['satisfied'],1)
        self.assertEqual(out['whole_path'],'insufficient')


if __name__=='__main__':unittest.main()
