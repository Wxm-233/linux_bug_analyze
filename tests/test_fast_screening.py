import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
from unittest import TestCase

from linux_bug_analyze.fast_screening import FastScreener, SharedBudget
from linux_bug_analyze.models import CommitInfo
from linux_bug_analyze.screening import StopRun
from tests.test_screening import response

class FastTests(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)
        self.c=CommitInfo('aaaa','aaaa','plain edit','a','d','',('a.c',),'plain diff')

    def runner(self,create,**kw):
        return FastScreener(NS(chat=NS(completions=NS(create=create))),self.path,model='test',**kw)

    def test_atomic_reservation_and_resume_unknown_usage(self):
        budget=SharedBudget(self.path,2,200)
        def reserve(_):
            try:return budget.reserve(100,'aaaa','compact')
            except StopRun:return None
        with ThreadPoolExecutor(max_workers=8) as p:
            results=list(p.map(reserve,range(8)))
        self.assertEqual(sum(r is not None for r in results),2)
        resumed=SharedBudget(self.path,3,200)
        with self.assertRaises(StopRun):resumed.reserve(1,'bbbb','compact')
        self.assertEqual(resumed.data['charged_tokens'],200)

    def test_parallel_execution_dedup_and_cached_resume(self):
        barrier=threading.Barrier(2);calls=[]
        def create(**kw):
            calls.append(kw);barrier.wait(timeout=3);return response()
        r=self.runner(create,workers=2)
        r.run([self.c,replace(self.c,hash='bbbb'),self.c])
        self.assertEqual(len(calls),2)
        resumed=self.runner(lambda **kw:self.fail('cache should avoid API'),workers=2)
        resumed.run([self.c,replace(self.c,hash='bbbb'),self.c])
        self.assertEqual(resumed.budget.data['requests'],2)
        self.assertEqual(json.loads((self.path/'summary.json').read_text())['duplicates_removed'],1)

    def test_truncated_negative_expands_and_retains(self):
        calls=[]
        def create(**kw):calls.append(kw);return response()
        r=self.runner(create,compact_chars=200,full_chars=400)
        result=r.screen(replace(self.c,diff='line\n'*150))
        self.assertEqual(len(calls),2)
        self.assertEqual(result['decision']['relevance'],'uncertain')
        self.assertTrue(result['truncated'])

    def test_related_short_stage_does_not_expand(self):
        calls=[]
        def create(**kw):calls.append(kw);return response('related')
        r=self.runner(create,compact_chars=200,full_chars=1000)
        r.screen(replace(self.c,diff='line\n'*150))
        self.assertEqual(len(calls),1)

    def test_fence_is_free_but_bad_ids_not_repaired(self):
        good=response();good.choices[0].message.content='```json\n'+good.choices[0].message.content+'\n```'
        r=self.runner(lambda **kw:good)
        self.assertEqual(r.screen(self.c)['status'],'success')
        bad=response(ids=[99999])
        r.client.chat.completions.create=lambda **kw:bad
        self.assertEqual(r.screen(replace(self.c,hash='bbbb'))['status'],'validation_failed')
        self.assertEqual(r.budget.data['requests'],2)

    def test_expansion_budget_stop_preserves_pending(self):
        r=self.runner(lambda **kw:response(),max_requests=1,compact_chars=200,full_chars=1000)
        r.run([replace(self.c,diff='line\n'*150)])
        checkpoint=json.loads((self.path/'checkpoint.json').read_text())
        self.assertEqual(checkpoint['pending'],['aaaa'])
        self.assertTrue((self.path/'stages/compact/aaaa.json').exists())

    def test_changed_model_cannot_reuse_directory(self):
        self.runner(lambda **kw:response())
        with self.assertRaises(ValueError):FastScreener(None,self.path,model='other')

    def test_extended_evidence_preserved_and_33_rejected(self):
        c=replace(self.c,diff='\n'.join('source '+str(i) for i in range(50)))
        r=self.runner(lambda **kw:response(ids=list(range(1,33))))
        result=r.screen(c)
        self.assertEqual(len(result['decision']['evidence']),32)
        r.client.chat.completions.create=lambda **kw:response(ids=list(range(1,34)))
        self.assertEqual(r.screen(replace(c,hash='bbbb'))['status'],'validation_failed')

    def test_auth_error_stops_dispatch_and_never_logs_secret(self):
        calls=[]
        def create(**kw):
            calls.append(kw)
            e=RuntimeError('test-secret-not-for-logs');e.status_code=402;raise e
        r=self.runner(create,workers=1)
        r.run([self.c,replace(self.c,hash='bbbb')])
        self.assertEqual(len(calls),1)
        self.assertEqual(len(json.loads((self.path/'checkpoint.json').read_text())['pending']),2)
        self.assertNotIn('test-secret',(self.path/'usage.json').read_text())

    def test_equal_tier_limits_never_repeat_same_material(self):
        calls=[]
        def create(**kw):calls.append(kw);return response('uncertain')
        r=self.runner(create,compact_chars=200,full_chars=200)
        r.screen(replace(self.c,diff='line\n'*150))
        self.assertEqual(len(calls),1)

    def test_hash_loader_does_not_eagerly_read_whole_input(self):
        loaded=[]
        def load(h):
            loaded.append(h)
            return replace(self.c,hash=h)
        r=self.runner(lambda **kw:response('related'),workers=1,max_requests=1)
        hashes=[f'{i:04x}' for i in range(100)]
        r.run_hashes(hashes,load)
        self.assertLessEqual(len(loaded),2)
        self.assertEqual(json.loads((self.path/'input.json').read_text()),hashes)
        self.assertEqual(len(json.loads((self.path/'checkpoint.json').read_text())['pending']),99)

    def test_hash_loader_rejects_wrong_commit(self):
        r=self.runner(lambda **kw:self.fail('wrong commit must not reach API'),workers=1)
        with self.assertRaises(ValueError):
            r.run_hashes(['bbbb'],lambda h:self.c)
