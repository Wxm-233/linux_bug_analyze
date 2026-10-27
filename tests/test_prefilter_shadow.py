from unittest import TestCase

from experiments.prefilter_shadow.run import proposed_rules


class PrefilterShadowTests(TestCase):
    def row(self, subject, **changes):
        signals = dict.fromkeys(('defect', 'architecture_difference', 'boundary',
                                 'architecture_path'), False)
        signals.update(changes)
        return {'subject': subject, 'signals': signals}

    def test_binding_capability_is_not_editorial(self):
        rules = proposed_rules(self.row('dt-bindings: firmware: Document arm,no-completion-irq'),
                               ('Documentation/devicetree/bindings/firmware/arm,scmi.yaml',))
        self.assertIn('docs_metadata_only', rules)
        self.assertNotIn('metadata_or_editorial_only', rules)

    def test_maintainers_only_is_editorial_candidate(self):
        rules = proposed_rules(self.row('MAINTAINERS: update entry'), ('MAINTAINERS',))
        self.assertIn('metadata_or_editorial_only', rules)

    def test_test_only_is_separate_from_safe_editorial_candidate(self):
        rules = proposed_rules(self.row('selftests/mm: test page-size assumption', defect=True),
                               ('tools/testing/selftests/mm/example.c',))
        self.assertIn('selftest_only', rules)
        self.assertNotIn('metadata_or_editorial_only', rules)

    def test_feature_without_signals_is_only_a_risky_baseline(self):
        rules = proposed_rules(self.row('PCI: Enable ACS after configuring IOMMU for OF platforms'),
                               ('drivers/pci/pci.c',))
        self.assertIn('feature_without_static_signal', rules)
        self.assertNotIn('metadata_or_editorial_only', rules)
