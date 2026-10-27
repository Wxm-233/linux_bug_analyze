import copy,hashlib,tempfile,unittest
from pathlib import Path
from linux_bug_analyze.event_citation import check_event_citations

class EventCitationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  p=Path(self.tmp.name)/'source.c';p.write_text('consume();\nwrite();\nsample();\n',encoding='utf-8')
  self.docs={'source':dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),revision='r')}
  self.c=dict(interface_id='i',contract=dict(revision='r'),deadline_event='consume')
  self.reg=dict(origin='researcher_registered',interface_id='i',revision='r',events={
   s:dict(document='source',start_line=n,end_line=n,quote=s+'();') for n,s in enumerate(['consume','write','sample'],1)})
 def check(self,refs):return check_event_citations(self.c,refs,self.reg,self.docs)
 def ref(self,n,support='deadline_event'):
  return dict(supports=support,document='source',start_line=n,end_line=n,quote=['consume();','write();','sample();'][n-1])
 def test_match_does_not_approve_semantics(self):
  r=self.check([self.ref(1)]);self.assertEqual(r['status'],'registered_event_location_matches');self.assertFalse(r['deadline_evidence_established'])
 def test_wrong_write_event(self):
  r=self.check([self.ref(2)]);self.assertEqual(r['status'],'insufficient');self.assertEqual(r['matches'][0]['registered_events'],['write'])
 def test_no_borrow_from_relation(self):
  self.assertEqual(self.check([self.ref(1,'relation'),self.ref(2)])['status'],'insufficient')
 def test_broad_ambiguous_quote(self):
  r=self.ref(1);r.update(end_line=2,quote='consume();\nwrite();')
  self.assertEqual(self.check([r])['status'],'insufficient')
 def test_wrong_revision(self):
  self.reg['revision']='other';self.assertEqual(self.check([self.ref(1)])['status'],'insufficient')
 def test_changed_source(self):
  Path(self.docs['source']['path']).write_text('changed');self.assertEqual(self.check([self.ref(1)])['status'],'insufficient')
 def test_no_model_registry(self):
  self.reg['origin']='model_proposal';self.assertEqual(self.check([self.ref(1)])['status'],'insufficient')
 def test_unknown_event(self):
  self.c['deadline_event']='unknown';self.assertEqual(self.check([self.ref(1)])['status'],'insufficient')
 def test_unquoted_anchor_not_matched(self):
  r=self.ref(2);r.update(start_line=1)
  self.assertEqual(self.check([r])['status'],'insufficient')
 def test_conflicting_refs_not_ignored(self):
  self.assertEqual(self.check([self.ref(1),self.ref(3)])['status'],'insufficient')

if __name__=='__main__':unittest.main()
