"""Commit review orchestration; CLI and web handlers only call these operations."""
from dataclasses import asdict
import csv
import io
import json
import math
import threading
from pathlib import Path

from .commit_source import iter_mainline_commits
from .config import DEFAULT_API_KEY_FILE, DEFAULT_BASE_URL, DEFAULT_MODEL, resolve_api_key, ConfigurationError
from .fast_screening import FastScreener, digest, save
from .git_repository import GitRepository
from .hash_filter import compile_rules, evaluate_commit, DEFAULT_CROSS_ARCH_INCLUDE
from .reporting import write_text_atomic
from .review_audit import make_audit_plan, audit_statistics
from .review_learning import ReviewRanker, choose_next, score_stratified_sample
from .review_store import ReviewStore, now
from .review_reading import ReadingSummarizer
from .screening import StopRun


def csv_text(rows, fields):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        # Commit messages are untrusted spreadsheet cells, not Excel formulas.
        safe = {k: ("'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@', '\t', '\r')) else v)
                for k, v in row.items()}
        writer.writerow(safe)
    return '\ufeff' + stream.getvalue()


class ReviewWorkflow:
    def __init__(self, settings, output=None):
        self.settings = settings
        self.options = settings.review
        self.output = output or self.options.output_dir or (settings.source.parent if settings.source else Path.cwd()) / 'review_workspace'
        self.store = ReviewStore(self.output)
        self.ranker = ReviewRanker(self.options.random_seed)
        self.progress = '就绪'
        self.runner = None
        self.reading_runner = None
        self.cancel = threading.Event()
        self.repo = GitRepository(settings.linux_dir) if settings.linux_dir else None

    def require_ready(self):
        if not self.store.get('dataset'):
            raise ValueError('请先准备候选数据。')
        if not self.repo or str(self.repo.path) != self.store.get('dataset')['linux_dir']:
            raise ValueError('linux_dir 与当前项目不一致，请恢复配置或使用新的 review.output_dir。')

    def prepare(self):
        if self.store.get('dataset'):
            self.require_ready()
            if not self.store.get('frozen'):
                self.train()
            self.progress = '继续使用已冻结的候选集合；新时间范围请使用新 output_dir。'
            return
        if not self.repo:
            raise ValueError('请先在 settings.toml 中设置 linux_dir。')
        self.repo.validate()
        source, rules_config = self.settings.commit_source, self.settings.hash_filter
        if source.ref.startswith('-'):
            raise ValueError('commit_source.ref 不能以 - 开头')
        ref = self.repo._run(['rev-parse', '--verify', source.ref + '^{commit}']).strip()
        if rules_config.match != 'any' or rules_config.exclude:
            raise ValueError('高召回工作台要求 hash_filter.match="any" 且 exclude=[]。')
        # Existing settings often spell out older rules: union prevents silently
        # losing new default architecture/semantic aliases when upgrading.
        include = tuple(dict.fromkeys(DEFAULT_CROSS_ARCH_INCLUDE + rules_config.include))
        rules = compile_rules(include, (), rules_config.fields, match='any',
                              case_sensitive=rules_config.case_sensitive)
        scanned = candidates = 0
        with self.store.connect() as db:
            db.execute('DELETE FROM commits')  # Only an uninitialized, unlabeled dataset.
            for commit in iter_mainline_commits(self.repo.path, ref, since=source.since,
                    until=source.until, no_merges=source.no_merges, reverse=source.reverse,
                    max_count=source.max_count):
                if self.cancel.is_set():
                    raise ValueError('扫描已停止，未完成扫描已回滚；下次点击准备可重新开始。')
                if 'diff' in rules.fields:
                    commit = self.repo.get_commit(commit.hash, 0)
                decision = evaluate_commit(scanned, commit, rules)
                db.execute('INSERT INTO commits VALUES (?,?,?,?,?,?,?,NULL)', (
                    commit.hash, commit.subject, commit.body, json.dumps(commit.files, ensure_ascii=False),
                    commit.date, int(decision.selected), json.dumps(decision.to_dict(), ensure_ascii=False)))
                scanned += 1
                candidates += decision.selected
                if scanned % 1000 == 0:
                    self.progress = f'扫描 {scanned}，候选 {candidates}'
            manifest = dict(created=now(), linux_dir=str(self.repo.path), resolved_ref=ref,
                            source=asdict(source), include=include, fields=rules.fields,
                            case_sensitive=rules_config.case_sensitive, scanned=scanned, candidates=candidates,
                            feature_material='subject + body + paths; full diff available for human/LLM review')
            # Paths in source config are provenance only.
            manifest = json.loads(json.dumps(manifest, default=str))
            self.store.set_meta(db, 'dataset', manifest)
        self.export_dataset()
        self.progress = f'准备完成：扫描 {scanned}，候选 {candidates}。开始人工标注。'

    def export_dataset(self):
        records = self.store.records()
        write_text_atomic(self.output / 'candidate_hashes.txt', ''.join(r['hash'] + '\n' for r in records if r['candidate']))
        write_text_atomic(self.output / 'regex_rejected_hashes.txt', ''.join(r['hash'] + '\n' for r in records if not r['candidate']))
        rows = [dict(hash=r['hash'], title=r['subject'], abstract=r['body'] + '\n' + r['files'],
                     url='https://git.kernel.org/torvalds/c/' + r['hash'], included='')
                for r in records if r['candidate']]
        write_text_atomic(self.output / 'asreview_dataset.csv', csv_text(rows, ['hash','title','abstract','url','included']))
        save(self.output / 'dataset.json', self.store.get('dataset'))

    def train(self):
        self.require_ready()
        if self.store.get('frozen'):
            raise ValueError('本轮模型已冻结，不能再改变训练标签。新实验请使用新目录。')
        labels = self.store.labels('train')
        if {v['label'] for v in labels.values()} >= {'related', 'unrelated'}:
            scores, model = self.ranker.fit_predict(self.store.records(True), labels)
            self.store.scores(scores)
            self.store.put('model', model)
            self.store.put('model_label_digest', digest(labels))
        else:
            self.store.put('model', None)
            with self.store.connect() as db:
                db.execute('UPDATE commits SET score=NULL')
            self.store.put('model_label_digest', digest(labels))

    def label(self, h, role, label, note=''):
        self.require_ready()
        if role == 'train':
            if self.store.get('frozen') or not self.store.record(h)['candidate']:
                raise ValueError('当前记录不能用于本轮训练。')
        elif role == 'validation':
            if self.store.get('selection') is not None or h not in self.store.get('validation', []):
                raise ValueError('不在可编辑的阈值检查集合内。')
        elif role == 'audit':
            if h not in [v['hash'] for v in self.store.get('audit', {}).get('samples', [])]:
                raise ValueError('不在抽样复核集合内。')
        else:
            raise ValueError('无效标注阶段')
        self.store.label(h, role, label, note)
        if role == 'train':
            self.train()
        self.export(full=False)

    def freeze(self):
        self.require_ready()
        if self.store.get('frozen'):
            return
        labels = self.store.labels('train')
        if len(labels) < self.options.training_target:
            raise ValueError(f'请先完成人工训练标注目标 {self.options.training_target} 条（可在 [review] 调整）。')
        self.train()
        if not self.store.get('model'):
            raise ValueError('训练标签必须包含相关和不相关两类。')
        records = self.store.records(True)
        validation = score_stratified_sample([r for r in records if r['hash'] not in labels],
                                            self.options.validation_size, self.options.random_seed)
        snapshot = dict(created=now(), model=self.store.get('model'), labels=labels,
                        scores={r['hash']: r['score'] for r in records},
                        dataset=digest(self.store.get('dataset')), validation=validation,
                        training_target=self.options.training_target,
                        exploration_every=self.options.exploration_every)
        with self.store.connect() as db:
            self.store.set_meta(db, 'frozen', snapshot)
            self.store.set_meta(db, 'validation', validation)
        save(self.output / 'model_snapshot.json', snapshot)
        self.export()

    def human_labels(self):
        labels = {}
        for role in ('train', 'validation', 'audit'):
            labels.update(self.store.labels(role))
        return labels

    def threshold_preview(self, threshold):
        if type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError('阈值必须在 [0,1] 内')
        if not self.store.get('frozen'):
            raise ValueError('请先冻结模型并进行阈值检查。')
        human = self.human_labels()
        records = self.store.records(True)
        selected = [r['hash'] for r in records if r['score'] >= threshold
                    and human.get(r['hash'], {}).get('label') not in ('related', 'unrelated')]
        validation = self.store.labels('validation')
        above = [validation[r['hash']]['label'] for r in records
                 if r['score'] >= threshold and r['hash'] in validation]
        below = [validation[r['hash']]['label'] for r in records
                 if r['score'] < threshold and r['hash'] in validation]
        return dict(threshold=threshold, hashes=selected, count=len(selected),
                    validation_above={k: above.count(k) for k in ('related','unrelated','uncertain')},
                    validation_below={k: below.count(k) for k in ('related','unrelated','uncertain')})

    def select(self, threshold):
        if self.store.get('selection') is not None:
            raise ValueError('本轮清单已冻结；如需改变阈值，请另建实验目录。')
        validation = self.store.get('validation', [])
        if not validation or any(h not in self.store.labels('validation') for h in validation):
            raise ValueError('请先完成阈值检查集的标注；若候选全部用于训练，请增加候选范围。')
        preview = self.threshold_preview(threshold)
        selection = dict(created=now(), **preview)
        self.store.put('selection', selection)
        save(self.output / 'selection.json', selection)
        write_text_atomic(self.output / 'llm_hashes.txt', ''.join(h + '\n' for h in preview['hashes']))
        self.export()

    def screen(self, client=None):
        self.require_ready()
        selection = self.store.get('selection')
        if selection is None:
            raise ValueError('请先确认阈值并生成 LLM 清单。')
        if self.store.get('audit'):
            raise ValueError('抽样已冻结；本轮 LLM 结果不能再改变。')
        output = self.output / 'llm'
        output.mkdir(exist_ok=True)
        if client is None and selection['hashes']:
            from .llm import create_openai_client
            client = create_openai_client(resolve_api_key(None, self.settings.api_key_file or DEFAULT_API_KEY_FILE),
                                           self.settings.base_url or DEFAULT_BASE_URL)
        context = self.settings.context_md.read_text(encoding='utf-8') if self.settings.context_md else ''
        self.runner = FastScreener(client, output, model=self.settings.model or DEFAULT_MODEL,
                                   endpoint=self.settings.base_url or DEFAULT_BASE_URL, context=context,
                                   workers=self.options.workers, max_requests=self.options.max_requests,
                                   token_budget=self.options.token_budget)
        if self.cancel.is_set():
            self.runner.budget.stopped.set()
        try:
            self.progress = '短判断运行中；可停止派发，已发出的请求会完成并保存。'
            self.runner.run_hashes(selection['hashes'], lambda h: self.repo.get_commit(h, 0))
        finally:
            results = {}
            for h in selection['hashes']:
                path = output / 'results' / (h + '.json')
                if path.exists():
                    results[h] = json.loads(path.read_text(encoding='utf-8'))
            self.store.put('llm_results', results)
            self.runner = None
            self.export()

    def sample(self):
        if self.store.get('audit'):
            return  # Never resample an already inspected audit batch.
        selection = self.store.get('selection')
        if selection is None:
            raise ValueError('请先冻结待判断清单。')
        results = self.store.get('llm_results', {})
        plan = make_audit_plan(self.store.records(), selection['hashes'], results,
                              self.human_labels(), rate=self.options.audit_rate,
                              minimum=self.options.audit_minimum, boundary=self.options.boundary_sample,
                              seed=self.options.random_seed)
        plan.update(created=now(), selection_digest=digest(selection), results_digest=digest(results))
        self.store.put('audit', plan)
        save(self.output / 'audit_plan.json', plan)
        self.export()

    def next_record(self, role):
        labels = self.store.labels(role)
        if role == 'train':
            if self.store.get('frozen'):
                return None
            # Recover after a crash between committing a label and updating scores.
            if labels and self.store.get('model_label_digest') != digest(labels):
                raise ValueError('上次标注已保存，但排序尚未更新，请点击“重算排序”。')
            return choose_next(self.store.records(True), labels, self.options.random_seed,
                               self.options.exploration_every)
        if role == 'validation':
            pool = self.store.get('validation', [])
        elif role == 'audit':
            pool = [r['hash'] for r in self.store.get('audit', {}).get('samples', [])]
        else:
            raise ValueError('无效队列')
        return next((h for h in pool if h not in labels), None)

    def reading_summarizer(self):
        return ReadingSummarizer(self.output / 'reading_summaries',
            model=self.settings.model or DEFAULT_MODEL, endpoint=self.settings.base_url or DEFAULT_BASE_URL,
            max_requests=self.options.summary_max_requests, token_budget=self.options.summary_token_budget,
            diff_chars=self.options.summary_diff_chars)

    def reading_queue(self, role):
        self.require_ready()
        if role == 'train':
            if self.store.get('frozen'):
                return list(self.store.labels('train'))
            labels = self.store.labels('train')
            remaining = max(0, self.options.training_target - len(labels))
            # Snapshot the current ranking; later feedback can change membership.
            records = self.store.records(True)
            chosen = []
            simulated = dict(labels)
            for _ in range(remaining):
                h = choose_next(records, simulated, self.options.random_seed, self.options.exploration_every)
                if h is None:
                    break
                chosen.append(h)
                simulated[h] = {'label':'uncertain'}
            return chosen
        if role == 'validation':
            return self.store.get('validation', [])
        if role == 'audit':
            return [r['hash'] for r in self.store.get('audit', {}).get('samples', [])]
        raise ValueError('无效队列')

    def summarize_queue(self, role, client=None, include_hash=None):
        hashes = self.reading_queue(role)
        if include_hash is not None and include_hash not in hashes:
            if role != 'train' or not self.store.record(include_hash)['candidate']:
                raise ValueError('当前例子不属于该人工队列。')
            hashes.insert(0,include_hash)
        if not hashes:
            raise ValueError('当前队列为空；请先准备候选、冻结模型或生成抽样清单。')
        runner = self.reading_summarizer()
        self.reading_runner = runner
        batch = dict(role=role, hashes=hashes, completed=[], failed={}, status='running')
        path = self.output / 'reading_summaries' / f'{role}_batch.json'
        save(path, batch)
        def get_client():
            nonlocal client
            if client is None:
                from .llm import create_openai_client
                client = create_openai_client(resolve_api_key(None,self.settings.api_key_file or DEFAULT_API_KEY_FILE),
                                              self.settings.base_url or DEFAULT_BASE_URL)
            return client
        try:
            for i,h in enumerate(hashes):
                if self.cancel.is_set():
                    break
                self.progress = f'批量摘要 {role}：{i+1}/{len(hashes)}；已有有效缓存直接复用'
                try:
                    runner.generate(self.repo.get_commit(h,0), get_client)
                    batch['completed'].append(h)
                except StopRun:
                    break
                except Exception as exc:
                    # Do not persist API error messages containing credentials.
                    batch['failed'][h] = type(exc).__name__
                    if isinstance(exc,ConfigurationError) or not isinstance(exc,(ValueError,TypeError,AttributeError,IndexError)):
                        break
                save(path,batch)
        finally:
            batch['pending'] = [h for h in hashes if h not in batch['completed']]
            batch['status'] = 'completed' if not batch['pending'] else 'partial'
            save(path,batch)
            self.reading_runner = None
        if batch['pending']:
            raise ValueError(f'摘要已完成 {len(batch["completed"])}/{len(hashes)}，其余尚未完成。请检查摘要预算/接口或停止状态后再次批量生成；已完成项不会重复收费。')

    def material(self, h, role='train'):
        self.require_ready()
        row = self.store.record(h)
        commit = self.repo.get_commit(h, 0)
        reading = self.reading_summarizer().cached(commit)
        if reading:
            self.store.reading_provided(h,role,reading)
        # No predicted label, score, stratum, or model reasoning in the blind view.
        return dict(hash=h, subject=row['subject'], body=row['body'], date=row['date'],
                    files=json.loads(row['files']), diff=commit.diff,
                    url='https://git.kernel.org/torvalds/c/' + h, reading_summary=reading)

    def summary(self):
        dataset = self.store.get('dataset')
        labels = {role: self.store.labels(role) for role in ('train','validation','audit')}
        counts = {role: {k: sum(v['label'] == k for v in rows.values())
                         for k in ('related','unrelated','uncertain')} for role, rows in labels.items()}
        selection = self.store.get('selection')
        results = self.store.get('llm_results', {})
        llm = {k: 0 for k in ('related','unrelated','uncertain','failed','pending')}
        for h in selection['hashes'] if selection else []:
            r = results.get(h)
            llm['pending' if not r else 'failed' if r['status'] != 'success' else r['decision']['relevance']] += 1
        plan = self.store.get('audit')
        assisted = self.store.reading_assistance()
        return dict(dataset=dataset, labels=counts, frozen=bool(self.store.get('frozen')),
                    summary_assisted_labels={role:sum(r == role for h,r in assisted) for role in labels},
                    training_target=self.options.training_target,
                    validation_total=len(self.store.get('validation', [])),
                    selected=selection['count'] if selection else None,
                    threshold=selection['threshold'] if selection else None, llm=llm,
                    audit_total=len(plan['samples']) if plan else None,
                    audit=audit_statistics(plan, labels['audit']) if plan else None,
                    output_dir=str(self.output), model=self.store.get('model', {}).get('engine') if self.store.get('model') else None)

    def export(self, full=True):
        if not self.store.get('dataset'):
            return
        human = self.human_labels()
        results = self.store.get('llm_results', {})
        selected = set(self.store.get('selection', {}).get('hashes', []))
        confirmed = [h for h, v in human.items() if v['label'] == 'related']
        provisional = [h for h, v in results.items() if v.get('status') == 'success'
                       and v['decision']['relevance'] == 'related'
                       and human.get(h, {}).get('label') not in ('related', 'unrelated')]
        rows = []
        for r in self.store.records() if full else []:
            h = r['hash']
            label = human.get(h, {}).get('label', '')
            result = results.get(h, {})
            decision = result.get('decision', {}) if result.get('status') == 'success' else {}
            rows.append(dict(hash=h, subject=r['subject'], candidate=r['candidate'], score=r['score'],
                             human_label=label, human_role=human.get(h, {}).get('role', ''),
                             llm_selected=h in selected, llm_status=result.get('status', 'pending' if h in selected else ''),
                             llm_label=decision.get('relevance', ''), needs_review=decision.get('needs_review', ''),
                             reason=decision.get('reason','')))
        fields = ['hash','subject','candidate','score','human_label','human_role','llm_selected',
                  'llm_status','llm_label','needs_review','reason']
        if full:
            write_text_atomic(self.output / 'results.csv', csv_text(rows, fields))
        assistance = self.store.reading_assistance()
        all_labels = [{**row, 'summary_assisted': (row['hash'],role) in assistance,
                      'summary_model': assistance.get((row['hash'],role),{}).get('model',''),
                      'summary_fingerprint': assistance.get((row['hash'],role),{}).get('fingerprint','')}
                     for role in ('train','validation','audit') for row in self.store.labels(role).values()]
        write_text_atomic(self.output / 'labels.csv', csv_text(all_labels,
            ['hash','role','label','note','updated','summary_assisted','summary_model','summary_fingerprint']))
        write_text_atomic(self.output / 'label_events.csv', csv_text(self.store.events(), ['id','hash','role','label','note','updated']))
        for name, hashes in (('confirmed_related_hashes.txt', confirmed), ('provisional_related_hashes.txt', provisional)):
            write_text_atomic(self.output / name, ''.join(h + '\n' for h in hashes))
        summary = self.summary()
        summary.update(confirmed_related=len(confirmed), provisional_related=len(provisional))
        save(self.output / 'summary.json', summary)
        lines = ['# 人机协同筛选统计', '', f'- 扫描：{summary["dataset"]["scanned"]}；正则候选：{summary["dataset"]["candidates"]}',
                 f'- 人工确认相关：{len(confirmed)}；仅 LLM 判相关、尚未人工确认：{len(provisional)}',
                 f'- 本轮 LLM 清单：{summary["selected"]}；状态：{summary["llm"]}',
                 '', '## 人工标注', '', '| 阶段 | 相关 | 不相关 | 不确定 |', '|---|---:|---:|---:|']
        for role, c in summary['labels'].items():
            lines.append(f'| {role} | {c["related"]} | {c["unrelated"]} | {c["uncertain"]} |')
        lines += ['', f'标注前已提供 LLM 摘要的记录数：{summary["summary_assisted_labels"]}。',
                  '摘要只辅助阅读，不自动生成标签。使用摘要的复核属于 LLM 辅助人工复核，不能称为完全独立盲审；此计数记录页面曾提供摘要，不证明实际阅读。']
        if summary['audit']:
            stats = summary['audit']
            lines += ['', '## 抽样复核', '', '| 分层 | 总体 | 抽样 | 已复核 | 人工相关/可确定 | 相关比例的 95% Wilson 区间 |',
                      '|---|---:|---:|---:|---:|---|']
            for k, c in stats['strata'].items():
                ci = c['related_fraction_ci95']
                interval = f'{ci[0]:.1%}–{ci[1]:.1%}' if ci else '暂无'
                lines.append(f'| {k} | {c["population"]} | {c["sampled"]} | {c["reviewed"]} | {c["human_related"]}/{c["resolved"]} | {interval} |')
            accuracy = stats['weighted_binary_accuracy']
            lines += ['', '加权二分类准确率：' + (f'{accuracy:.1%}' if accuracy is not None else '暂不估计（未完成或存在人工不确定）。'),
                      '', '分层复核尚未全部解决时，比例和区间仅描述已确定样本。总体准确率按分层规模加权，排除 LLM 不确定。']
        lines += ['', '## 解释边界', '', '- 排序分数未经概率校准；低分表示暂缓，不是不相关。',
                  '- 复核只评价本轮 LLM 集合；正则未命中/低分抽查不能证明全流程召回率。',
                  '- 阈值检查标签未用于训练，但用于选择阈值，不是独立测试集。',
                  '- 训练特征为标题、正文与路径；人工和 LLM 判断可查看实际 diff。',
                  '- confirmed_related_hashes.txt 是人工确认集合；provisional_related_hashes.txt 仍需复核。', '']
        write_text_atomic(self.output / 'summary.md', '\n'.join(lines))
