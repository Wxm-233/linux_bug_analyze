import copy
import unittest
from replay import canonical_analysis


class VocabularyBridgeTests(unittest.TestCase):
    def test_only_registered_categories_change_and_input_is_untouched(self):
        packet = {'events': [{'id': 'e1', 'kind': 'load', 'field': {'field': 'different_name', 'access': 'read'}},
                             {'id': 'e2', 'kind': 'store', 'field': {'access': 'write'}},
                             {'id': 'e3', 'kind': 'branch'}, {'id': 'e4', 'kind': 'scalar_assign'},
                             {'id': 'e5', 'kind': 'opaque'}],
                  'dependencies': [{'use_event': 'e4', 'definition_event': 'e1', 'region': 4}]}
        before = copy.deepcopy(packet)
        result = canonical_analysis(packet)
        self.assertEqual(packet, before)
        self.assertEqual([e['kind'] for e in result['events']],
                         ['field_load', 'field_store', 'condition', 'assignment', 'opaque'])
        self.assertEqual(result['dependencies'], packet['dependencies'])

    def test_indexed_access_without_member_metadata_never_becomes_field_access(self):
        packet = {'events': [{'id': 'a', 'kind': 'load', 'indexed': {'base': 'vector'}},
                             {'id': 'b', 'kind': 'store', 'field': {'access': 'read'}}]}
        result = canonical_analysis(packet)
        self.assertEqual([e['kind'] for e in result['events']], ['load', 'store'])


if __name__ == '__main__':
    unittest.main()
