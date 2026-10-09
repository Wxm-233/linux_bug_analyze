from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
from unittest import TestCase

from linux_bug_analyze.config import FileSettings
from linux_bug_analyze.models import CommitInfo
from linux_bug_analyze.review_config import ReviewSettings, parse_review_settings
from linux_bug_analyze.review_reading import ReadingSummarizer
from linux_bug_analyze.review_workflow import ReviewWorkflow
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


class BatchReadingTests(TestCase):
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

    def test_training_only_remaining_target_batch_and_resume(self):
        self.w.summarize_queue('train',self.client)
        self.assertEqual(len(self.calls),2)
        self.w.summarize_queue('train',self.client)
        self.assertEqual(len(self.calls),2)
        self.assertEqual(self.w.store.labels('train'),{})
        self.assertFalse((self.w.output/'llm').exists())
        self.assertEqual(self.w.store.reading_assistance(),{})

    def test_manually_opened_seed_is_also_included(self):
        selected=set(self.w.reading_queue('train'))
        h=next(h for h in self.commits if h not in selected)
        self.w.summarize_queue('train',self.client,include_hash=h)
        self.assertEqual(len(self.calls),3)
        self.assertIsNotNone(self.w.material(h)['reading_summary'])
        with self.assertRaises(ValueError):self.w.summarize_queue('audit',self.client,include_hash=h)

    def test_fixed_queue_all_processed_and_assistance_recorded_only_at_label(self):
        hashes=list(self.commits)
        self.w.store.put('audit',{'samples':[{'hash':h} for h in hashes]})
        self.w.summarize_queue('audit',self.client)
        self.assertEqual(len(self.calls),5)
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

    def test_budget_pending_and_restart_finish(self):
        hashes=list(self.commits)
        self.w.store.put('validation',hashes)
        self.w.options=replace(self.w.options,summary_max_requests=2)
        with self.assertRaisesRegex(ValueError,'2/5'):self.w.summarize_queue('validation',self.client)
        batch=json.loads((self.w.output/'reading_summaries/validation_batch.json').read_text(encoding='utf-8'))
        self.assertEqual(len(batch['pending']),3)
        self.w.options=replace(self.w.options,summary_max_requests=10)
        self.w.summarize_queue('validation',self.client)
        self.assertEqual(len(self.calls),5)

    def test_stop_and_failed_auth_do_not_mark_labels_or_expose_secret(self):
        self.w.cancel.set()
        with self.assertRaises(ValueError):self.w.summarize_queue('train',self.client)
        self.assertEqual(self.calls,[])
        self.w.cancel.clear()
        def fail(**kw):
            error=RuntimeError('secret-test-token');error.status_code=401;raise error
        with self.assertRaises(ValueError):self.w.summarize_queue('train',NS(chat=NS(completions=NS(create=fail))))
        text=''.join(p.read_text(encoding='utf-8') for p in (self.w.output/'reading_summaries').rglob('*.json'))
        self.assertNotIn('secret-test-token',text)
        self.assertEqual(self.w.store.labels('train'),{})
