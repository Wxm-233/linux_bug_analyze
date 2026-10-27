import copy
import hashlib
import json
import unittest

from linux_bug_analyze.model_candidate import CandidateInputError, parse_model_candidate
from tests.test_interface_intent import fixture as intent_fixture


def fixture():
    _,candidate=intent_fixture()
    candidate['contract']['field_origins']={k:'model_proposal' for k in candidate['contract']['field_origins']}
    value=dict(schema='model_interface_candidate_v1',revision='v1',**candidate,
        citations=[dict(supports=k,document='source',start_line=1,end_line=1,quote='read cached;')
                   for k in ('scope','relation','symbol_bindings','deadline_event')],uncertainties=['No semantic approval.'])
    raw=b'read cached;\ncompare reference;\nnot supplied;\n'
    docs={'source':dict(path='source.c',sha256=hashlib.sha256(raw).hexdigest(),revision='v1',provided_spans=[[1,2]])}
    return value,docs,raw


class CandidateTests(unittest.TestCase):
    def parse(self,value,docs,raw):
        return parse_model_candidate(json.dumps(value),docs,read_bytes=lambda _:raw)

    def test_identity_not_semantics(self):
        value,docs,raw=fixture();out=self.parse(value,docs,raw)
        self.assertTrue(out['citation_identity_verified'])
        self.assertFalse(out['citation_semantics_verified'])
        self.assertEqual(out['candidate']['contract'],value['contract'])

    def test_duplicate_json_keys(self):
        value,docs,raw=fixture();text=json.dumps(value)
        text='{"schema":"other",'+text[1:]
        with self.assertRaises(CandidateInputError):parse_model_candidate(text,docs,read_bytes=lambda _:raw)

    def test_surrounding_prose_rejected(self):
        value,docs,raw=fixture()
        with self.assertRaises(CandidateInputError):parse_model_candidate('Here is the answer: '+json.dumps(value),docs,read_bytes=lambda _:raw)

    def test_single_fence_only(self):
        value,docs,raw=fixture();text='```json\n'+json.dumps(value)+'\n```'
        out=parse_model_candidate(text,docs,read_bytes=lambda _:raw)
        self.assertEqual(out['normalization'],'outer_json_fence_removed')

    def test_self_approval_rejected(self):
        value,docs,raw=fixture();value['contract']['field_origins']['relation']='researcher_authored'
        with self.assertRaises(CandidateInputError):self.parse(value,docs,raw)

    def test_unregistered_document(self):
        value,docs,raw=fixture();value['citations'][0]['document']='other'
        with self.assertRaises(CandidateInputError):self.parse(value,docs,raw)

    def test_source_tampering(self):
        value,docs,raw=fixture()
        with self.assertRaises(CandidateInputError):self.parse(value,docs,raw+b'changed')

    def test_omitted_source_span(self):
        value,docs,raw=fixture();ref=value['citations'][0]
        ref.update(start_line=3,end_line=3,quote='not supplied;')
        with self.assertRaises(CandidateInputError):self.parse(value,docs,raw)

    def test_wrong_quote(self):
        value,docs,raw=fixture();value['citations'][0]['quote']='write cached;'
        with self.assertRaises(CandidateInputError):self.parse(value,docs,raw)

    def test_missing_support_category(self):
        value,docs,raw=fixture();value['citations'][0]['supports']='relation'
        with self.assertRaises(CandidateInputError):self.parse(value,docs,raw)

    def test_wrong_revision(self):
        value,docs,raw=fixture();docs['source']['revision']='v2'
        with self.assertRaises(CandidateInputError):self.parse(value,docs,raw)

    def test_boolean_line_number(self):
        value,docs,raw=fixture();value['citations'][0]['start_line']=True
        with self.assertRaises(CandidateInputError):self.parse(value,docs,raw)

    def test_unknown_top_field(self):
        value,docs,raw=fixture();value['ledger']={'status':'supported'}
        with self.assertRaises(CandidateInputError):self.parse(value,docs,raw)


if __name__=='__main__':unittest.main()
