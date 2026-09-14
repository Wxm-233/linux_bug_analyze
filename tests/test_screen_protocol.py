import json
from unittest import TestCase

from linux_bug_analyze.screen_protocol import evidence_lines, parse_response, exclusion_guard


class ProtocolTests(TestCase):
    def payload(self, **kwargs):
        return json.dumps(dict(relevance='unrelated', reason='修正注释拼写，执行逻辑不变。',
            evidence_ids=[1], needs_review=False, vertical='absent', horizontal='absent',
            exclusion_basis='cleanup', **kwargs))

    def test_line_resolution_preserves_quotes_and_bounds_long_lines(self):
        source = 'if ("x")\n\t' + 'x' * 700
        lines = evidence_lines(source)
        self.assertTrue(all(len(line) <= 300 and line in source for line in lines))
        decision, _ = parse_response(self.payload(), lines)
        self.assertEqual(decision['evidence'], ['if ("x")'])

    def test_invalid_ids_rejected(self):
        for ids in ([True], [0], [2], ['1'], [1, 1], []):
            data = json.loads(self.payload()); data['evidence_ids'] = ids
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                parse_response(json.dumps(data), ['source'])

    def test_unknown_boundary_cannot_be_excluded(self):
        decision, audit = parse_response(self.payload(), ['source'])
        audit['vertical'] = 'unknown'
        checked, flags = exclusion_guard(decision, audit)
        self.assertEqual(checked['relevance'], 'uncertain')
        self.assertTrue(checked['needs_review'])
        self.assertIn('boundary_not_ruled_out', flags)
        self.assertEqual(decision['relevance'], 'unrelated')

    def test_source_lead_is_retained_even_with_absent_fields(self):
        decision, audit = parse_response(self.payload(), ['source'])
        decision['reason'] = '仅修改驱动内部流程，没有改变公共接口。'
        checked, flags = exclusion_guard(decision, audit, [{'family': 'mapping_permissions'}])
        self.assertEqual(checked['relevance'], 'uncertain')
        self.assertIn('source_semantic_lead', flags)

    def test_comment_wording_alone_does_not_trigger_guard(self):
        decision, audit = parse_response(self.payload(), ['source'])
        decision['reason'] = '仅注释拼写修正，不涉及公共接口。'
        self.assertEqual(exclusion_guard(decision, audit), (decision, []))

    def test_generic_cleanup_can_remain_excluded(self):
        decision, audit = parse_response(self.payload(), ['source'])
        self.assertEqual(exclusion_guard(decision, audit), (decision, []))

    def test_no_cross_arch_is_not_exclusion_basis(self):
        decision, audit = parse_response(self.payload(), ['source'])
        audit['exclusion_basis'] = 'no_cross_arch'
        self.assertTrue(exclusion_guard(decision, audit)[0]['needs_review'])
