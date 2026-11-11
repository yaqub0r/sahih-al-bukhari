"""Synthetic-only regression checks for exact alignment and scope boundaries."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('audit_bukhari_source', Path(__file__).parents[1] / 'scripts' / 'audit_bukhari_source.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def fixture():
    return ('######OpenITI#\r\n#META#Header#End#\r\n\r\n'
            '# Synthetic title PageV01P001\r\n### | Synthetic section\r\n'
            '# Synthetic introduction\r\n### || Synthetic chapter\r\n' +
            ''.join(f'# {n} Synthetic chain * repeated report @QB@ quoted @QE@\r\n~~continued ms0001 PageV01P00{n} \\ 1 \\\r\n' for n in range(1, 8)) +
            '### | Second section\r\n# 8 Synthetic next report\r\n').encode()


class AuditTests(unittest.TestCase):
    def test_alignment_reconstructs_every_original_byte(self):
        raw = fixture()
        authority, ledger, audit = M.inventory(raw)
        self.assertEqual(raw, ''.join(row['raw'] for row in ledger['lines']).encode())
        for row in ledger['lines']:
            self.assertEqual(raw[row['byteStart']:row['byteEnd']], row['raw'].encode())
            if row['disposition'] != 'unit':
                continue
            original = row['raw'].rstrip('\r\n')
            cursor, fragments = 0, []
            for event in row['events']:
                self.assertEqual(original[event['start']:event['end']], event['before'])
                fragments.extend([original[cursor:event['start']], event['after']])
                cursor = event['end']
            fragments.append(original[cursor:])
            self.assertEqual(M.re.sub(r'\s+', ' ', ''.join(fragments)).strip(), row['normalized'])
        self.assertEqual(len(ledger['lines']), len(raw.splitlines()))
        self.assertEqual(audit['missingPrintedNumbers'], [])
        self.assertEqual(audit['duplicatePrintedNumbers'], {})

    def test_preserves_repetitions_chains_comments_and_context(self):
        authority, _, audit = M.inventory(fixture())
        reports = [u for u in authority['units'] if u['kind'] == 'report']
        self.assertEqual(len(reports), 8)
        self.assertEqual(reports[0]['arabic'], reports[1]['arabic'])
        self.assertNotEqual(reports[0]['id'], reports[1]['id'])
        self.assertIn('Synthetic chain repeated report quoted continued', reports[0]['arabic'])
        self.assertEqual(len(reports[0]['contextIds']), 2)
        self.assertEqual(reports[-1]['contextIds'], [u['id'] for u in authority['units'] if u['kind'] == 'heading'][-1:])
        scope, boundary = M.first_scope(authority, audit)
        self.assertEqual([u['id'] for u in scope['units'] if u['kind'] == 'report'], [u['id'] for u in reports[:7]])
        self.assertTrue(boundary['contextClosed'])
        self.assertNotIn('Second section', str(scope))
        self.assertEqual(len([u for u in scope['units'] if u['kind'] == 'comment']), 2)

    def test_anomalies_are_reported_without_losing_content(self):
        raw = b'#META#Header#End#\n# 1 one\n# 3 three\n# 3 repeated\nodd syntax preserved\n'
        authority, _, audit = M.inventory(raw)
        self.assertEqual(audit['missingPrintedNumbers'], [2])
        self.assertEqual(audit['duplicatePrintedNumbers'], {'3': 2})
        self.assertEqual(len(audit['nonIncreasingPrintedNumbers']), 1)
        self.assertIn('odd syntax preserved', authority['units'][-1]['arabic'])
        self.assertTrue(any(f['kind'] == 'unrecognized-line-syntax-preserved' for f in audit['findings']))

    def test_rejects_orphan_and_missing_header(self):
        for raw in [b'no header', b'#META#Header#End#\n~~orphan']:
            with self.assertRaises(ValueError):
                M.inventory(raw)

    def test_unicode_formula_offsets_and_uncertainty(self):
        # These short formula tokens test Unicode offsets; no book passages.
        text = '#META#Header#End#\n# 1 X صلى الله\n~~عليه وسلم Y رضي الله عنها Z تعالى\n'
        authority, _, audit = M.inventory(text.encode())
        unit = authority['units'][0]
        self.assertEqual([unit['arabic'][s['start']:s['end']] for s in unit['formulaSpans']], ['صلى الله عليه وسلم', 'رضي الله عنها'])
        self.assertEqual(unit['formulaSpans'][0]['referent'], 'prophet-muhammad')
        self.assertTrue(any(f['kind'] == 'formula-referent-needs-review' for f in audit['findings']))
        self.assertTrue(any(f['kind'] == 'possible-formula-needs-review' for f in audit['findings']))

    def test_marker_only_paragraph_is_explicit_exclusion(self):
        authority, ledger, audit = M.inventory(b'#META#Header#End#\n# PageV02P020\n# 1 text\n')
        self.assertEqual(len(authority['units']), 1)
        self.assertEqual(ledger['lines'][1]['disposition'], 'excluded')
        self.assertTrue(any(e['reason'] == 'marker-only formatting paragraph' for e in authority['exclusions']))
        self.assertEqual(audit['volumes'], [2])

    def test_review_overlay_is_hash_bound_and_cannot_omit_occurrences(self):
        authority, _, audit = M.inventory('#META#Header#End#\n# 1 X صلى الله عليه وسلم\n'.encode())
        u = authority['units'][0]
        row = {'id': u['id'], 'arabicSha256': M.sha(u['arabic'].encode()), 'formulaSpans': list(u['formulaSpans'])}
        review = {'sourceSha256': audit['sourceSha256'], 'units': [row]}
        self.assertEqual(M.apply_formula_review(authority, review, audit['sourceSha256']), authority)
        for bad in ['wrong-hash', audit['sourceSha256']]:
            if bad == audit['sourceSha256']:
                row['formulaSpans'] = []
            with self.assertRaises(ValueError):
                M.apply_formula_review(authority, review, bad)

    def test_numbered_chapter_with_paragraph_marker_is_not_a_report(self):
        authority, _, audit = M.inventory('#META#Header#End#\n### | book\n# 2 باب Synthetic chapter\n# 1 Synthetic report\n'.encode())
        self.assertEqual([u['kind'] for u in authority['units']], ['heading', 'heading', 'report'])
        self.assertTrue(authority['units'][1]['arabic'].startswith('2 باب'))
        self.assertEqual([r['number'] for r in audit['printedReportNumbers']], [1])
        self.assertEqual(authority['units'][2]['contextIds'], [u['id'] for u in authority['units'][:2]])

    def test_private_output_rejects_traversal_and_unrelated_runtime(self):
        root = Path.cwd() / 'synthetic-repository'
        good = root / '.runtime' / 'audit'
        self.assertEqual(M.private_output_path(good, root), good.resolve())
        for bad in [root / '.runtime', root / '.runtime' / '..' / '..' / 'public', root.parent / 'other' / '.runtime' / 'audit']:
            with self.assertRaises(ValueError):
                M.private_output_path(bad, root)

    def test_deterministic(self):
        self.assertEqual(M.inventory(fixture()), M.inventory(fixture()))


if __name__ == '__main__':
    unittest.main()
