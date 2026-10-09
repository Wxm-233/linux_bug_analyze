from dataclasses import replace
import json
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
from unittest import TestCase

from linux_bug_analyze.config import FileSettings
from linux_bug_analyze.models import CommitInfo
from linux_bug_analyze.review_config import ReviewSettings, parse_review_settings
from linux_bug_analyze.review_reading import ReadingSummarizer
from linux_bug_analyze.review_workflow import ReviewWorkflow
from linux_bug_analyze.review_prefetch import ReadingPrefetch
from linux_bug_analyze.review_web import ReviewApplication
from linux_bug_analyze.fast_screening import digest
from linux_bug_analyze.screening import StopRun


def response(text=None, finish='stop', total=100):
    return NS(choices=[NS(finish_reason=finish,message=NS(content=text or json.dumps({
        'summary':'提交修改了内存访问方式；具体触发条件需要结合调用者核对。',
        'evidence_ids':[1], 'limitations':'仅依据所提供提交材料。'},ensure_ascii=False)))],
        usage=NS(total_tokens=total))


class ReadingTests(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)
        self.commit=CommitInfo('abcd','abcd','fix arm access','a','d','body',('kernel/test.c',),'+ new code')

    def summarizer(self, **kwargs):
        values=dict(model='test',endpoint='https://example.test',max_requests=10,token_budget=100000)
        values.update(kwargs)
        return ReadingSummarizer(self.path,**values)

    def test_cache_resume_no_duplicate_requests_and_uses_original_material(self):
        calls=[]
        def create(**kw):calls.append(kw);return response()
        result=self.summarizer().generate(self.commit,lambda:NS(chat=NS(completions=NS(create=create))))
        cached=self.summarizer().generate(self.commit,lambda:self.fail('cached result should not construct client'))
        self.assertEqual(result,cached)
        self.assertEqual(len(calls),1)
        self.assertIn('+ new code',calls[0]['messages'][1]['content'])
        self.assertNotIn('model_decision',calls[0]['messages'][1]['content'])
        self.assertEqual(result['evidence'][0]['text'],'hash: abcd')
        self.assertEqual(json.loads((self.path/'usage.json').read_text(encoding='utf-8'))['requests'],1)

    def test_cache_identity_changes_with_model_patch_and_limits(self):
        r=self.summarizer()
        r.generate(self.commit,lambda:NS(chat=NS(completions=NS(create=lambda **kw:response()))))
        self.assertIsNone(self.summarizer(model='other').cached(self.commit))
        self.assertIsNone(r.cached(replace(self.commit,diff='changed')))
        self.assertIsNone(self.summarizer(max_tokens=2000).cached(self.commit))

    def test_invalid_or_truncated_response_is_not_cached(self):
        for text,finish in [('not JSON','stop'),('anything','length'),
            (json.dumps({'summary':'ok','evidence_ids':[9999],'limitations':''}),'stop')]:
            with self.subTest(text=text),self.assertRaises(ValueError):
                self.summarizer().generate(self.commit,lambda:NS(chat=NS(completions=NS(create=lambda **kw:response(text,finish)))))
            self.assertIsNone(self.summarizer().cached(self.commit))

    def test_budget_survives_restart_unknown_usage_is_reserved(self):
        factory=lambda:NS(chat=NS(completions=NS(create=lambda **kw:response(total=None))))
        self.summarizer(max_requests=1).generate(self.commit,factory)
        with self.assertRaises(StopRun):
            self.summarizer(max_requests=1).generate(replace(self.commit,hash='bbbb'),factory)
        usage=json.loads((self.path/'usage.json').read_text(encoding='utf-8'))
        self.assertGreater(usage['charged_tokens'],1000)

    def test_truncation_is_explicit(self):
        result=self.summarizer(diff_chars=200).generate(replace(self.commit,diff='source line\n'*500),
            lambda:NS(chat=NS(completions=NS(create=lambda **kw:response()))))
        self.assertTrue(result['material_truncated'])

    def test_summary_configuration_validation(self):
        for data in ({'summary_max_requests':0},{'summary_token_budget':True},{'summary_diff_chars':-1}):
            with self.assertRaises(ValueError):parse_review_settings(data,self.path)


class AutoReadingTests(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        settings=FileSettings(linux_dir=self.root,model='test',review=ReviewSettings(
            output_dir=self.root/'work',training_target=2))
        self.w=ReviewWorkflow(settings)
        self.commits={str(i)*4:CommitInfo(str(i)*4,str(i)*4,'arm fix','a','d','body',('file.c',),'+ source') for i in range(1,6)}
        self.w.repo=NS(path=self.root.resolve(),get_commit=lambda h,*args:self.commits[h])
        self.w.store.put('dataset',dict(linux_dir=str(self.root.resolve()),scanned=5,candidates=5))
        with self.w.store.connect() as db:
            db.executemany('INSERT INTO commits VALUES (?,?,?,?,?,?,?,?)',
                [(h,'arm fix','body','["file.c"]','d',1,'{}',.5) for h in self.commits])
        self.calls=[]
        def create(**kw):self.calls.append(kw);return response()
        self.client=NS(chat=NS(completions=NS(create=create)))
        self.prefetch=ReadingPrefetch(self.w,lambda:self.client)
        self.addCleanup(self.prefetch.close)

    def wait_done(self):
        with self.prefetch.condition:
            self.assertTrue(self.prefetch.condition.wait_for(
                lambda:not self.prefetch.pending and not self.prefetch.in_flight,timeout=5))

    def test_only_current_and_next_and_cache_reuse(self):
        self.assertEqual(self.calls,[])
        hashes=self.w.reading_window('train','1111')
        self.assertEqual(len(hashes),2)
        self.assertEqual(hashes[0],'1111')
        self.prefetch.request('train',hashes);self.wait_done()
        self.assertEqual(len(self.calls),2)
        self.prefetch.request()
        self.prefetch.request('train',hashes);self.wait_done()
        self.assertEqual(len(self.calls),2)
        self.assertEqual(self.w.store.labels('train'),{})
        self.assertFalse((self.w.output/'llm').exists())
        self.assertEqual(self.w.store.reading_assistance(),{})

    def test_recompute_after_label_and_ranking_change(self):
        for h,label in [('1111','related'),('2222','unrelated')]:self.w.store.label(h,'train',label)
        self.w.store.scores({'3333':.9,'4444':.8,'5555':.1})
        self.assertEqual(self.w.reading_window('train','3333'),['3333','4444'])
        self.w.store.label('3333','train','related')
        self.w.store.scores({'4444':.1,'5555':.95})
        self.w.store.put('model_label_digest',digest(self.w.store.labels('train')))
        self.assertEqual(self.w.next_record('train'),'5555')
        self.assertEqual(self.w.reading_window('train','5555'),['5555','4444'])
        self.assertNotIn('3333',self.w.reading_window('train','5555'))

    def test_fixed_queue_two_only_and_assistance_recorded_only_at_label(self):
        hashes=list(self.commits)
        self.w.store.put('audit',{'samples':[{'hash':h} for h in hashes]})
        self.prefetch.request('audit',self.w.reading_window('audit',hashes[0]));self.wait_done()
        self.assertEqual(len(self.calls),2)
        h=hashes[0]
        self.w.store.label(h,'audit','related')
        self.assertEqual(self.w.store.reading_assistance(),{})
        material=self.w.material(h,'audit')
        self.assertIn('summary',material['reading_summary']['content'])
        self.assertEqual(self.w.store.reading_assistance(),{}) # Original label predates aid.
        self.w.store.label(h,'audit','unrelated')
        assistance=self.w.store.reading_assistance()
        self.assertEqual(assistance[(h,'audit')]['model'],'test')
        self.assertNotIn((h,'train'),assistance)
        self.w.store.label(h,'train','related')
        self.assertNotIn((h,'train'),self.w.store.reading_assistance())

    def test_budget_failure_is_not_retried_and_restart_can_resume(self):
        hashes=list(self.commits)
        self.w.store.put('validation',hashes)
        self.w.options=replace(self.w.options,summary_max_requests=1)
        window=self.w.reading_window('validation',hashes[0])
        self.prefetch.request('validation',window);self.wait_done()
        self.assertIn('预算',self.prefetch.snapshot()['error'])
        self.prefetch.request('validation',window);self.wait_done()
        self.assertEqual(len(self.calls),1)
        self.prefetch.close()
        self.w.options=replace(self.w.options,summary_max_requests=10)
        self.prefetch=ReadingPrefetch(self.w,lambda:self.client)
        self.addCleanup(self.prefetch.close)
        self.prefetch.request('validation',window);self.wait_done()
        self.assertEqual(len(self.calls),2)

    def test_failed_auth_does_not_mark_labels_or_expose_secret(self):
        def fail(**kw):
            error=RuntimeError('secret-test-token');error.status_code=401;raise error
        self.client.chat.completions.create=fail
        self.prefetch.request('train',['1111','2222']);self.wait_done()
        self.assertIn('失败',self.prefetch.snapshot()['error'])
        self.assertNotIn('secret-test-token',self.prefetch.snapshot()['error'])
        text=''.join(p.read_text(encoding='utf-8') for p in (self.w.output/'reading_summaries').rglob('*.json'))
        self.assertNotIn('secret-test-token',text)
        self.assertEqual(self.w.store.labels('train'),{})

    def block_first_request(self):
        entered,release=threading.Event(),threading.Event()
        self.addCleanup(release.set)
        def create(**kw):
            self.calls.append(kw)
            if len(self.calls)==1:
                entered.set();release.wait(5)
            return response()
        self.client.chat.completions.create=create
        self.prefetch.request('train',['1111','2222'])
        self.assertTrue(entered.wait(3))
        return release

    def test_navigation_replaces_unstarted_next_and_does_not_duplicate_inflight(self):
        release=self.block_first_request()
        self.prefetch.request('train',['1111','3333'])
        release.set();self.wait_done()
        self.assertEqual(len(self.calls),2)
        prompts=''.join(call['messages'][1]['content'] for call in self.calls)
        self.assertIn('hash: 3333',prompts)
        self.assertNotIn('hash: 2222',prompts)

    def test_disable_discards_next_but_keeps_inflight_cache(self):
        release=self.block_first_request()
        self.prefetch.request()
        release.set();self.wait_done()
        self.assertEqual(len(self.calls),1)
        self.assertIsNotNone(self.w.reading_summary('1111','train'))
        self.assertEqual(self.prefetch.snapshot()['targets'],[])

    def test_label_is_not_blocked_by_summary_and_cancels_old_prefetch(self):
        release=self.block_first_request()
        app=ReviewApplication(self.w)
        app.reading=self.prefetch
        app.dispatch('label',dict(hash='1111',role='train',label='related'))
        app.thread.join(3)
        self.assertFalse(app.busy)
        self.assertIsNone(app.error)
        self.assertEqual(self.w.store.labels('train')['1111']['label'],'related')
        release.set();self.wait_done()
        self.assertEqual(len(self.calls),1)

    def test_last_record_history_and_invalid_scope(self):
        self.w.store.put('validation',['1111','2222'])
        self.w.store.label('1111','validation','related')
        self.assertEqual(self.w.reading_window('validation','2222'),['2222'])
        self.assertEqual(self.w.reading_window('validation','1111'),['1111','2222'])
        with self.assertRaises(ValueError):self.w.reading_window('validation','3333')
        with self.assertRaises(ValueError):self.w.reading_window('unknown','1111')
        with self.assertRaises(ValueError):self.prefetch.request('train',['1111','2222','3333'])
