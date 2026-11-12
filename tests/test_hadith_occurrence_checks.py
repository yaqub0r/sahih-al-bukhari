import unittest
from scripts import hadith_occurrence_checks as checks


class OccurrenceChecksTests(unittest.TestCase):
    def setUp(self):
        self.source = {'units': [{'id': 'u', 'arabic': 'A name FORMULA tail',
                                 'formulaSpans': [{'start': 7, 'end': 14}]}]}
        self.node = {'id': 'n', 'kind': 'narrator', 'start': 2, 'end': 6,
                     'nameId': 'qualified-person', 'status': 'resolved'}
        self.graph = {'units': [{'id': 'u', 'nodes': [self.node], 'edges': []}]}
        self.inventory = {'alignmentMentions': [{'unitId': 'u', 'start': 2,
                                                'end': 6, 'nameId': 'qualified-person'}]}

    def test_accepts_reviewed_identity(self):
        self.assertEqual(checks.diagnostics(self.source, self.graph, self.inventory), [])

    def test_reports_known_occurrence_as_unresolved(self):
        self.node.update(nameId=None, status='unresolved')
        self.assertEqual(checks.diagnostics(self.source, self.graph, self.inventory)[0]['kind'],
                         'reviewed-narrator-identity')

    def test_reports_wrong_resolved_identity(self):
        self.node['nameId'] = 'different-person'
        self.assertEqual(len(checks.diagnostics(self.source, self.graph, self.inventory)), 1)

    def test_does_not_guess_identity_for_other_physical_occurrence(self):
        self.node.update(start=15, end=19, nameId=None, status='unresolved')
        self.assertEqual(checks.diagnostics(self.source, self.graph, self.inventory), [])

    def test_flags_internal_formula_substring_not_adjacent_predicate(self):
        self.graph['units'][0]['edges'] = [
            {'id': 'inside', 'start': 8, 'end': 10},
            {'id': 'adjacent', 'start': 0, 'end': 1},
            {'id': 'enclosing', 'start': 6, 'end': 15},
            {'id': 'implicit', 'start': None, 'end': None}]
        found = checks.diagnostics(self.source, self.graph, self.inventory)
        self.assertEqual([r['occurrenceId'] for r in found], ['inside'])

    def test_rejects_ambiguous_reviewed_binding(self):
        self.inventory['alignmentMentions'].append(dict(self.inventory['alignmentMentions'][0],
                                                       nameId='other'))
        with self.assertRaises(ValueError):
            checks.diagnostics(self.source, self.graph, self.inventory)

class BoundOccurrenceChecksTests(unittest.TestCase):
    def test_file_bindings_and_occurrence_conflict(self):
        import json
        import tempfile
        from pathlib import Path
        from scripts import hadith_structure as h
        from tests.test_hadith_structure import fixture
        source, graph, ledger = fixture()
        source['units'][0]['formulaSpans'] = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / name for name in ['source.json', 'graph.json', 'inventory.json', 'ledger.json']]
            def write(path, value):
                path.write_text(json.dumps(value), encoding='utf-8')
            for path, value in zip([paths[0], paths[1], paths[3]], [source, graph, ledger]):
                write(path, value)
            inventory = {'sourceSha256': h.file_hash(paths[0]),
                         'ledgerSha256': h.file_hash(paths[3]),
                         'alignmentMentions': [{'unitId': 'synthetic-unit', 'start': 0,
                                                'end': 1, 'nameId': 'synthetic-a'}]}
            write(paths[2], inventory)
            self.assertTrue(checks.validate_bound(*paths))
            for key in ['sourceSha256', 'ledgerSha256']:
                changed = dict(inventory, **{key: '0' * 64})
                write(paths[2], changed)
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'inventory .* drift'):
                    checks.validate_bound(*paths)
            write(paths[2], inventory)
            graph['units'][0]['nodes'][0].update(nameId=None, status='unresolved')
            graph['units'][0]['paths'][0]['status'] = 'uncertain'
            graph['units'][0]['reports'][0]['status'] = 'uncertain'
            graph['units'][0]['status'] = 'uncertain'
            write(paths[1], graph)
            with self.assertRaisesRegex(ValueError, 'qualified occurrence conflicts'):
                checks.validate_bound(*paths)


if __name__ == '__main__':
    unittest.main()
