from types import SimpleNamespace as NS
from unittest import TestCase
from linux_bug_analyze.semantic_signals import source_signals


class SignalTests(TestCase):
    def test_permissions_need_explanation_and_code_change(self):
        c = NS(subject='Restore WO permissions', body='Second-stage permits write-only.',
               diff='-pte = prot | READ;\n+pte = prot;')
        self.assertEqual(source_signals(c)[0]['family'], 'mapping_permissions')
        c.diff = '-/* permissions */\n+/* permissions corrected */'
        self.assertEqual(source_signals(c), [])

    def test_page_geometry_records_source_anchors(self):
        c = NS(subject='Fix 64K page size', body='Headers exceed a page.',
               diff='-hd_per_page = n;\n+hd_per_page = min(n, hd_per_wqe);')
        signals = source_signals(c)
        self.assertEqual(signals[0]['family'], 'page_geometry')
        self.assertIn('Fix 64K page size', signals[0]['explanation'])

    def test_directory_names_do_not_trigger(self):
        c = NS(subject='Fix typo in arch/arm', body='DMA typo.',
               diff='--- a/arch/arm/page.c\n+++ b/arch/arm/page.c\n-/* DAM */\n+/* DMA */')
        self.assertEqual(source_signals(c), [])

    def test_context_lines_do_not_count_as_changes(self):
        c = NS(subject='Fix 64K page size', body='', diff=' context page_size\n-old = 1;\n+old = 2;')
        self.assertEqual(source_signals(c), [])
