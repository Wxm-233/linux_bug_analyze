"""Frozen strata are validated before the existing DeepSeek entry runs."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import patch

from linux_bug_analyze.fast_screen_cli import interleave_batch, load_batch_selection, main
from linux_bug_analyze.models import CommitInfo


class FastScreenBatchTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plan = self.root / 'manifest.json'
        self.quotas = {'high': 1, 'medium': 0, 'low': 1, 'outside_defect': 0, 'outside_other': 0}
        samples = [
            {'hash': 'a' * 40, 'stratum': 'high'},
            {'hash': 'b' * 40, 'stratum': 'high'},
            {'hash': 'c' * 40, 'stratum': 'low'},
            {'hash': 'd' * 40, 'stratum': 'low'},
        ]
        self.plan.write_text(json.dumps({'batch_count': 2, 'batch_quotas': self.quotas,
                                         'samples': samples, 'seed': 17,
                                         'linux_head': 'f' * 40, 'audit_sha256': '0' * 64,
                                         'stratum_sizes': {name: 100 for name in self.quotas}}), encoding='utf-8')
        (self.root / 'batch-001.txt').write_text('a' * 40 + '\n' + 'c' * 40 + '\n', encoding='utf-8')
        (self.root / 'batch-002.txt').write_text('b' * 40 + '\n' + 'd' * 40 + '\n', encoding='utf-8')

    def test_manifest_batch_hash_order_and_content_are_checked(self):
        path, source = load_batch_selection(self.plan, 2)
        self.assertEqual(path.name, 'batch-002.txt')
        self.assertEqual(source['batch_number'], 2)
        self.assertEqual(source['nominal_sampling_fraction']['high'], 0.01)
        (self.root / 'batch-002.txt').write_text('d' * 40 + '\n' + 'b' * 40 + '\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            load_batch_selection(self.plan, 2)

    def test_plan_only_uses_whole_batch_without_api(self):
        settings = NS(linux_dir=self.root, hashes_file=None,
                      api_key_file=self.root / 'key', base_url=None, context_md=None)
        output = self.root / 'out'
        with patch('linux_bug_analyze.fast_screen_cli.load_settings', return_value=settings), \
             patch('linux_bug_analyze.fast_screen_cli.GitRepository') as repo, \
             patch('linux_bug_analyze.fast_screen_cli.subprocess.run', return_value=NS(stdout='')), \
             patch('linux_bug_analyze.fast_screen_cli.create_openai_client') as client:
            repo.return_value._run.return_value = 'f' * 40
            repo.return_value.resolve_hash.side_effect = lambda h: h
            repo.return_value.get_commit.side_effect = lambda h, _: CommitInfo(h, h, 'subject', '', '', '', (), 'diff')
            self.assertEqual(main(['--batch-manifest', str(self.plan), '--outdir', str(output),
                                   '--max-items', '2', '--plan-only']), 0)
            client.assert_not_called()
        self.assertEqual(json.loads((output / 'batch_source.json').read_text(encoding='utf-8'))['batch_number'], 1)

    def test_execution_interleaves_frozen_strata_without_changing_membership(self):
        commits = [NS(hash=h) for h in 'abcdefg']
        source = {'batch_quotas': {'high': 3, 'medium': 2, 'low': 1, 'outside': 1},
                  'sample_strata': {h: cell for h, cell in zip('abcdefg',
                                     ['high'] * 3 + ['medium'] * 2 + ['low', 'outside'])}}
        self.assertEqual([c.hash for c in interleave_batch(commits, source)],
                         list('adfgbec'))
        self.assertEqual([c.hash for c in commits], list('abcdefg'))
