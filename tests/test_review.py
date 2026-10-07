import csv
from dataclasses import replace
from importlib.util import find_spec
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
from types import SimpleNamespace as NS
from unittest import TestCase, skipUnless
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from linux_bug_analyze.config import load_settings, ConfigurationError, FileSettings, CommitSourceSettings
from linux_bug_analyze.review_config import ReviewSettings, parse_review_settings
from linux_bug_analyze.review_audit import make_audit_plan, audit_statistics, wilson
from linux_bug_analyze.review_learning import ReviewRanker, choose_next, score_stratified_sample
from linux_bug_analyze.review_store import ReviewStore
from linux_bug_analyze.review_workflow import ReviewWorkflow, csv_text
from linux_bug_analyze.review_web import ReviewApplication, make_server
from linux_bug_analyze.hash_filter import DEFAULT_CROSS_ARCH_INCLUDE, compile_rules, evaluate_commit
from linux_bug_analyze.models import CommitInfo
from tests.test_commit_source import _git, _commit
from tests.test_screening import response


class ReviewConfigTests(TestCase):
    def test_expanded_high_recall_aliases_and_code_identifiers(self):
        rules=compile_rules(DEFAULT_CROSS_ARCH_INCLUDE,(),('subject','body','files'))
        for word in ('RV64GC','ppc64le','CONFIG_ARCH_FOO','smp_store_release','PAGE_SIZE',
                     'numa','READ_ONCE','cpu_to_be32','le64_to_cpu'):
            with self.subTest(word=word):
                commit=CommitInfo('abcd','abcd','Fix '+word,'a','d','',('kernel/foo.c',),'')
                self.assertTrue(evaluate_commit(0,commit,rules).selected)

    def test_config_paths_defaults_and_rejection(self):
        with TemporaryDirectory() as d:
            path = Path(d) / 'settings.toml'
            path.write_text('[review]\noutput_dir="work"\naudit_rate=0.02\n', encoding='utf-8')
            s = load_settings(path, required=True)
            self.assertEqual(s.review.output_dir, Path(d).resolve() / 'work')
            self.assertEqual(s.review.training_target, 160)
            self.assertEqual(s.review.audit_rate, .02)
            path.write_text('[review]\naudit_rate=nan\n', encoding='utf-8')
            with self.assertRaises(ConfigurationError):
                load_settings(path)
        for data in ({'port': 70000}, {'workers': 17}, {'training_target': 1}, {'audit_rate': True},
                     {'audit_minimum': 0}, {'unknown': 2}, {'validation_size': False}, {'output_dir': 9}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                parse_review_settings(data, Path('.'))

    def test_example_settings_remain_loadable(self):
        self.assertEqual(load_settings(Path('settings.example.toml')).review.audit_minimum, 100)


class ReviewAuditTests(TestCase):
    def test_strata_reproducible_no_duplicates_boundaries(self):
        selection = [str(i) for i in range(120)]
        results = {h: dict(status='success', decision={'relevance': 'related' if int(h) < 20 else 'unrelated'}) for h in selection}
        records = [dict(hash=str(i), candidate=i < 130) for i in range(140)]
        kw = dict(rate=.01, minimum=30, boundary=3, seed=42)
        a = make_audit_plan(records, selection, results, {}, **kw)
        self.assertEqual(a, make_audit_plan(records, selection, results, {}, **kw))
        self.assertEqual(len(a['samples']), 36)
        self.assertEqual(len({r['hash'] for r in a['samples']}), 36)
        for row in a['samples']:
            self.assertEqual(row['inclusion_probability'], row['sample_size']/row['population'])
        self.assertEqual(a['populations']['regex_rejected'], 10)

    def test_failure_blocks_audit_and_empty_selection_still_checks_boundaries(self):
        for results in ({}, {'a': {'status':'validation_failed'}}):
            with self.assertRaises(ValueError):
                make_audit_plan([], ['a'], results, {}, rate=.01, minimum=1, boundary=1, seed=1)
        result = make_audit_plan([{'hash':'a','candidate':False}], [], {}, {},
                                 rate=.01, minimum=100, boundary=1, seed=1)
        self.assertEqual(result['samples'][0]['stratum'], 'regex_rejected')

    def test_weighted_accuracy_and_unresolved_are_not_dropped(self):
        plan = {'populations': dict(related=90, unrelated=10, uncertain=0, below_threshold=0, regex_rejected=0),
                'samples': [{'hash':'a','stratum':'related'}, {'hash':'b','stratum':'unrelated'}]}
        labels = {'a':{'label':'related'}, 'b':{'label':'related'}}
        s = audit_statistics(plan, labels)
        self.assertAlmostEqual(s['weighted_binary_accuracy'], .9)  # Not naive 50%.
        self.assertEqual(s['strata']['unrelated']['related_fraction'], 1)
        labels['b']['label'] = 'uncertain'
        self.assertIsNone(audit_statistics(plan, labels)['weighted_binary_accuracy'])
        del labels['b']
        self.assertIsNone(audit_statistics(plan, labels)['weighted_binary_accuracy'])
        self.assertIsNone(wilson(0, 0))
        self.assertGreater(wilson(10, 10)[0], .7)

    def test_small_samples_preserve_all_nonempty_strata(self):
        results={str(i):dict(status='success',decision={'relevance':label})
                 for i,label in enumerate(('related','unrelated','uncertain'))}
        p=make_audit_plan([],list(results),results,{},rate=.01,minimum=1,boundary=0,seed=1)
        self.assertEqual(len(p['samples']),3)


class ReviewLearningTests(TestCase):
    def test_queue_exploration_and_deferred(self):
        records=[dict(hash=str(i),score=i/10) for i in range(8)]
        labels={'0':{'label':'related'},'1':{'label':'unrelated'},'7':{'label':'uncertain'}}
        self.assertEqual(choose_next(records,labels,42,5),'6')
        self.assertIsNone(choose_next(records,{r['hash']:{} for r in records},42,5))
        sample=score_stratified_sample(records,5,42)
        self.assertEqual(len(set(sample)),5)
        self.assertEqual(sample,score_stratified_sample(records,5,42))

    @skipUnless(find_spec('asreview'), 'optional review dependencies')
    def test_real_asreview_scores_and_uncertain_not_training(self):
        records=[dict(hash=str(i),subject=s,body='',files='[]') for i,s in enumerate(
            ['arm cache barrier','x86 cache memory','fix spelling document','update typo docs'])]
        scores, model=ReviewRanker().fit_predict(records,{'0':{'label':'related'},'2':{'label':'unrelated'},'1':{'label':'uncertain'}})
        self.assertGreater(scores['0'],scores['2'])
        self.assertEqual(model['training_labels'],{'0':1,'2':0})
        self.assertTrue(all(0 <= p <= 1 for p in scores.values()))
        with self.assertRaises(ValueError):
            ReviewRanker().fit_predict(records,{'0':{'label':'related'}})


class ReviewStoreTests(TestCase):
    def test_labels_events_and_csv_formula_safety(self):
        with TemporaryDirectory() as d:
            store=ReviewStore(Path(d))
            with store.connect() as db:
                db.execute('INSERT INTO commits VALUES (?,?,?,?,?,?,?,?)',('a','subject','','[]','',1,'{}',None))
            store.label('a','train','related','first')
            store.label('a','train','unrelated','corrected')
            store.label('a','audit','related','independent')
            self.assertEqual(ReviewStore(Path(d)).labels('train')['a']['label'],'unrelated')
            self.assertEqual(len(store.events()),3)
            with self.assertRaises(ValueError):store.label('missing','train','related')
            with self.assertRaises(ValueError):store.label('a','train','bogus')
        text=csv_text([{'title':'=HYPERLINK("bad")'}],['title'])
        self.assertTrue(next(csv.DictReader(io.StringIO(text.lstrip('\ufeff'))))['title'].startswith("'="))


@skipUnless(find_spec('asreview'), 'optional review dependencies')
class ReviewWorkflowTests(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.repo=self.root/'linux';self.repo.mkdir()
        _git('init',cwd=self.repo);_git('config','user.email','tests@example.test',cwd=self.repo)
        _git('config','user.name','Tests',cwd=self.repo)
        self.hashes=[_commit(self.repo,'kernel/test.c',f'line {i}\n',title) for i,title in enumerate([
            'arm memory ordering bug','x86 fix spelling','riscv cache fix','arm64 page table fix',
            'mips alignment issue','dma portable update','s390 interrupt fix','plain typo cleanup'])]
        self.settings=FileSettings(linux_dir=self.repo,
            commit_source=CommitSourceSettings(since='2000-01-01',until='2035-01-01'),
            review=ReviewSettings(output_dir=self.root/'work',training_target=2,validation_size=2,
                                  audit_minimum=2,boundary_sample=1,max_requests=100))
        self.w=ReviewWorkflow(self.settings);self.w.prepare()

    def freeze_select(self):
        self.w.label(self.hashes[0],'train','related','evidence')
        self.w.label(self.hashes[1],'train','unrelated','typo only')
        self.w.freeze()
        for h in self.w.store.get('validation'):
            self.w.label(h,'validation','unrelated')
        self.w.select(0)

    def test_full_flow_with_mock_api_resume_audit_and_exports(self):
        self.assertEqual(self.w.store.get('dataset')['scanned'],8)
        self.assertEqual(self.w.store.get('dataset')['candidates'],7)
        self.assertIn(self.hashes[7],(self.w.output/'regex_rejected_hashes.txt').read_text())
        self.freeze_select()
        selected=self.w.store.get('selection')['hashes']
        self.assertEqual(len(selected),3)
        self.assertNotIn(self.hashes[0],selected)
        calls=[]
        def create(**kwargs):calls.append(kwargs);return response('related')
        self.w.screen(NS(chat=NS(completions=NS(create=create))))
        self.assertEqual(len(calls),3)
        self.w=ReviewWorkflow(self.settings)
        self.w.screen(NS(chat=NS(completions=NS(create=lambda **kw:self.fail('cache must prevent API')))))
        self.w.sample();plan=self.w.store.get('audit')
        self.w.sample();self.assertEqual(plan,self.w.store.get('audit'))
        for row in plan['samples']:
            self.w.label(row['hash'],'audit','related','blind evidence')
        self.w.export()
        report=(self.w.output/'summary.md').read_text(encoding='utf-8')
        self.assertIn('加权二分类准确率：100.0%',report)
        self.assertIn('不能证明全流程召回率',report)
        self.assertIn(self.hashes[0],(self.w.output/'confirmed_related_hashes.txt').read_text())
        self.assertEqual(len(self.w.store.labels('train')),2)
        with self.assertRaises(ValueError):self.w.screen(None)

    def test_budget_stop_pending_then_resume(self):
        self.freeze_select()
        calls=[]
        def create(**kw):calls.append(kw);return response('related')
        client=NS(chat=NS(completions=NS(create=create)))
        self.w.options=replace(self.w.options,max_requests=1,workers=1)
        self.w.screen(client)
        self.assertEqual(len(calls),1)
        self.assertEqual(self.w.summary()['llm']['pending'],2)
        with self.assertRaises(ValueError):self.w.sample()
        self.w.options=replace(self.w.options,max_requests=10)
        self.w.screen(client)
        self.assertEqual(len(calls),3)
        self.assertEqual(self.w.summary()['llm']['pending'],0)

    def test_freeze_guards_and_blind_material(self):
        with self.assertRaises(ValueError):self.w.freeze()
        self.w.label(self.hashes[0],'train','related')
        self.w.label(self.hashes[1],'train','unrelated')
        self.w.freeze()
        with self.assertRaises(ValueError):self.w.label(self.hashes[0],'train','unrelated')
        with self.assertRaises(ValueError):self.w.select(.5)
        material=self.w.material(self.hashes[0])
        self.assertFalse({'score','label','stratum','decision'} & set(material))
        self.assertIn('+line 0',material['diff'])
        with self.assertRaises(ValueError):self.w.threshold_preview(float('nan'))
        with self.assertRaises(ValueError):self.w.label(self.hashes[0],'validation','related')

    def test_existing_dataset_is_not_rescanned_and_repo_mismatch_rejected(self):
        manifest=self.w.store.get('dataset')
        _commit(self.repo,'arch/arm/test.c','new','arm new commit')
        self.w.prepare()
        self.assertEqual(manifest,self.w.store.get('dataset'))
        wrong=ReviewWorkflow(replace(self.settings,linux_dir=self.root))
        with self.assertRaises(ValueError):wrong.prepare()

    def test_cancelled_prepare_rolls_back_and_can_restart(self):
        w=ReviewWorkflow(self.settings,self.root/'cancelled')
        w.cancel.set()
        with self.assertRaisesRegex(ValueError,'已停止'):w.prepare()
        self.assertIsNone(w.store.get('dataset'))
        self.assertEqual(w.store.records(),[])
        w.cancel.clear();w.prepare()
        self.assertEqual(w.store.get('dataset')['scanned'],8)

    def test_labels_stay_separate_and_model_positive_can_be_rejected_by_auditor(self):
        self.freeze_select()
        self.w.screen(NS(chat=NS(completions=NS(create=lambda **kw:response('related')))))
        self.w.sample()
        sample=next(s for s in self.w.store.get('audit')['samples'] if s['stratum']=='related')
        self.w.label(sample['hash'],'audit','unrelated')
        self.assertNotIn(sample['hash'],(self.w.output/'provisional_related_hashes.txt').read_text())
        self.assertEqual(len(self.w.store.labels('train')),2)
        self.assertEqual(self.w.store.get('llm_results')[sample['hash']]['decision']['relevance'],'related')

    def test_crash_between_label_and_training_is_visible_and_recoverable(self):
        self.w.store.label(self.hashes[0],'train','related')
        with self.assertRaisesRegex(ValueError,'重算排序'):self.w.next_record('train')
        self.w.train()
        self.assertIsNotNone(self.w.next_record('train'))


class ReviewWebTests(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.w=ReviewWorkflow(FileSettings(review=ReviewSettings(output_dir=Path(self.tmp.name))))
        self.app=ReviewApplication(self.w);self.server=make_server(self.app,0)
        self.thread=threading.Thread(target=self.server.serve_forever);self.thread.start()
        self.addCleanup(self.close)
        self.url=f'http://127.0.0.1:{self.server.server_port}'

    def close(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
        if self.app.thread:self.app.thread.join()

    def request(self,path,headers=None,data=None):
        return urlopen(Request(self.url+path,headers=headers or {},data=data),timeout=5)

    def test_loopback_auth_origin_download_restrictions_and_static(self):
        with self.request('/') as r:self.assertIn('筛选工作台',r.read().decode())
        with self.assertRaises(HTTPError) as err:self.request('/api/status')
        self.assertEqual(err.exception.code,403)
        err.exception.close()
        headers={'X-Review-Token':self.app.token}
        with self.request('/api/status',headers) as r:self.assertIsNone(json.load(r)['summary']['dataset'])
        for bad in ({**headers,'Origin':'https://evil.example'},{**headers,'Host':'evil.example'}):
            with self.assertRaises(HTTPError) as err:self.request('/api/status',bad)
            self.assertEqual(err.exception.code,403)
            err.exception.close()
        with self.assertRaises(HTTPError) as err:self.request('/api/download?name=../../settings.toml',headers)
        self.assertEqual(err.exception.code,400)
        err.exception.close()

    def test_single_background_writer(self):
        entered=threading.Event();release=threading.Event()
        def prepare():entered.set();release.wait(5)
        with patch.object(self.w,'prepare',prepare):
            self.app.dispatch('prepare',{})
            self.assertTrue(entered.wait(2))
            try:
                with self.assertRaises(ValueError):self.app.dispatch('freeze',{})
            finally:release.set();self.app.thread.join(5)
        self.assertFalse(self.app.busy)
