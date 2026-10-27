"""Focused checks for the offline pilot strata and stable sampling."""

from unittest import TestCase
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory

from experiments.stratified_review.prepare import (
    MinHashSample, batch_quotas, planned_batches, selected_stratum, signals, write_batches,
)
from linux_bug_analyze.models import CommitInfo


def commit(subject: str, body: str = '', files: tuple[str, ...] = ()) -> CommitInfo:
    return CommitInfo('a' * 40, 'a' * 40, subject, '', '', body, files, '')


class StratifiedReviewTests(TestCase):
    def test_high_from_defect_and_explicit_architecture_difference(self):
        s = signals(commit('mm: fix incorrect value on arm64', 'The generic path assumes a 4K page size.'))
        self.assertTrue(s['defect'] and s['architecture_difference'])
        self.assertEqual(selected_stratum(s), 'high')

    def test_single_sided_architecture_fix_stays_at_least_medium(self):
        s = signals(commit('riscv: fix callback result', files=('arch/riscv/kernel/foo.c',)))
        self.assertIn(selected_stratum(s), ('high', 'medium'))

    def test_signature_is_not_architecture_evidence(self):
        s = signals(commit('lib: rename helper', 'Signed-off-by: Person <person@arm.com>'))
        self.assertFalse(s['architecture_text'])
        self.assertEqual(selected_stratum(s), 'low')

    def test_architecture_feature_without_defect_stays_low(self):
        s = signals(commit('riscv: add new callback', 'Provide generic support.', ('arch/riscv/kernel/new.c',)))
        self.assertFalse(s['defect'])
        self.assertEqual(selected_stratum(s), 'low')

    def test_revision_changelog_does_not_supply_defect_or_arch_difference(self):
        s = signals(commit('amdgpu: add timeline',
                           'Introduce a new timeline.\nV4: made the field 64-bit\nV5: bug fix'))
        self.assertFalse(s['defect'])
        self.assertFalse(s['architecture_difference'])
        old = signals(commit('amdgpu: add timeline',
                             'Introduce a new timeline.\nV4: made the field 64-bit\nV5: bug fix'), 'v1')
        self.assertTrue(old['defect'] and old['architecture_difference'])

    def test_fixes_tag_after_revision_changelog_still_counts(self):
        s = signals(commit('amdgpu: correct device capability',
                           'Headless hardware was misreported.\nV2: adjust naming\nFixes: abcdef123456 ("prior")'))
        self.assertTrue(s['defect'] and s['fixes_tag'])

    def test_sampling_is_order_independent_and_unique(self):
        rows = [{'hash': f'{n:040x}'} for n in range(30)]
        a = MinHashSample(5, 20260923)
        b = MinHashSample(5, 20260923)
        for row in rows:
            a.offer(row)
        for row in reversed(rows):
            b.offer(row)
        self.assertEqual(a.rows(), b.rows())
        self.assertEqual(len({row['hash'] for row in a.rows()}), 5)

    def test_batch_quotas_validate_all_cells_and_allow_control_sampling(self):
        args = Namespace(per_stratum=25,
                         batch_quotas='high=2,medium=2,low=1,outside_defect=1,outside_other=0')
        self.assertEqual(sum(batch_quotas(args).values()), 6)
        args.batch_quotas = 'high=2,medium=2,low=1,outside_defect=1'
        with self.assertRaises(ValueError):
            batch_quotas(args)

    def test_planned_batches_have_fixed_order_no_overlap_and_freeze(self):
        cells = ('high', 'medium', 'low', 'outside_defect', 'outside_other')
        quotas = dict.fromkeys(cells, 1)
        samples = [{'hash': f'{i:040x}', 'stratum': cell}
                   for j, cell in enumerate(cells) for i in (j * 2 + 1, j * 2 + 2)]
        manifest = {'batch_quotas': quotas, 'batch_count': 2, 'samples': samples}
        batches = planned_batches(manifest)
        self.assertEqual([len(batch) for batch in batches], [5, 5])
        self.assertEqual(len(set(batches[0]) & set(batches[1])), 0)
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_batches(out, manifest)
            self.assertEqual((out / 'batch-001.txt').read_text(encoding='utf-8').splitlines(), batches[0])
            write_batches(out, manifest)
            (out / 'batch-001.txt').write_text('changed\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                write_batches(out, manifest)
