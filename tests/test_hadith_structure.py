"""Synthetic-only private hadith structure contract tests."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import hadith_structure as h


def fixture():
    source = {'units': [{'id': 'synthetic-unit', 'kind': 'report', 'arabic': 'A tells B: invented event.'}]}
    ledger = {'identities': [{'id': 'synthetic-a', 'arabicForms': ['A']}, {'id': 'synthetic-b', 'arabicForms': ['B']}]}
    structure = {'version': 1, 'units': [{
        'id': 'synthetic-unit', 'sha256': h.sha(source['units'][0]['arabic'].encode()),
        'segments': [{'start': 0, 'end': 10, 'kind': 'isnad'}, {'start': 10, 'end': 26, 'kind': 'matn'}],
        'nodes': [
            {'id': 'a', 'kind': 'narrator', 'start': 0, 'end': 1, 'nameId': 'synthetic-a', 'status': 'resolved', 'note': 'Synthetic speaker.'},
            {'id': 'b', 'kind': 'narrator', 'start': 8, 'end': 9, 'nameId': 'synthetic-b', 'status': 'resolved', 'note': 'Synthetic source.'}],
        'edges': [{'id': 'ab', 'from': 'a', 'to': 'b', 'start': 2, 'end': 7, 'mode': 'explicit', 'note': 'Synthetic wording.'}],
        'paths': [{'id': 'primary', 'kind': 'primary', 'nodeIds': ['a', 'b'], 'edgeIds': ['ab'], 'status': 'complete', 'note': 'Textual path only.'}],
        'reports': [{'id': 'report', 'start': 0, 'end': 26, 'pathIds': ['primary'], 'status': 'complete', 'note': 'One synthetic report.'}],
        'status': 'complete', 'note': 'Synthetic fixture, no historical assertion.'}]}
    # The explicit fixture offsets deliberately use Unicode code points, never bytes.
    size = len(source['units'][0]['arabic'])
    structure['units'][0]['segments'][-1]['end'] = size
    structure['units'][0]['reports'][0]['end'] = size
    return source, structure, ledger


class StructureTests(unittest.TestCase):
    def setUp(self):
        self.source, self.structure, self.ledger = fixture()
        self.unit = self.structure['units'][0]

    def validate(self):
        return h.validate(self.source, self.structure, self.ledger)

    def test_valid_and_render_exact_source(self):
        self.validate()
        rendered = h.render(self.source, self.structure)
        self.assertIn('explicit: tells', rendered)
        self.assertIn('invented event.', rendered)
        self.assertIn('not proof of historical contact', rendered)

    def test_unknown_and_missing_fields(self):
        self.unit['extra'] = 1
        with self.assertRaises(ValueError): self.validate()
        del self.unit['extra']
        del self.unit['note']
        with self.assertRaises(ValueError): self.validate()

    def test_hash_and_order_drift(self):
        self.source['units'][0]['arabic'] += '!'
        with self.assertRaises(ValueError): self.validate()
        self.source, self.structure, self.ledger = fixture()
        self.structure['units'].append(copy.deepcopy(self.structure['units'][0]))
        with self.assertRaises(ValueError): self.validate()

    def test_segmentation_holes_overlap_and_unbound(self):
        for bad in (-1, 8, 11, True):
            with self.subTest(bad=bad):
                self.unit['segments'][1]['start'] = bad
                with self.assertRaises(ValueError): self.validate()

    def test_dangling_and_cycles(self):
        self.unit['edges'][0]['to'] = 'missing'
        with self.assertRaises(ValueError): self.validate()
        self.unit['edges'][0]['to'] = 'b'
        self.unit['edges'].append({'id': 'ba', 'from': 'b', 'to': 'a', 'start': None, 'end': None, 'mode': 'implicit', 'note': 'Cycle.'})
        with self.assertRaises(ValueError): self.validate()

    def test_order_and_orphans(self):
        self.unit['paths'][0]['nodeIds'] = ['b', 'a']
        with self.assertRaises(ValueError): self.validate()
        self.unit['paths'][0]['nodeIds'] = ['a', 'b']
        self.unit['reports'][0]['pathIds'] = []
        self.unit['reports'][0]['status'] = 'uncertain'
        with self.assertRaises(ValueError): self.validate()

    def test_no_invented_identity(self):
        self.unit['nodes'][0]['nameId'] = 'unknown'
        with self.assertRaises(ValueError): self.validate()
        self.unit['nodes'][0]['nameId'] = None
        self.unit['nodes'][0]['status'] = 'unresolved'
        with self.assertRaises(ValueError): self.validate()
        self.unit['paths'][0]['status'] = 'uncertain'
        self.unit['reports'][0]['status'] = 'uncertain'
        self.unit['status'] = 'uncertain'
        self.validate()

    def test_gap_and_shared_paths(self):
        self.unit['nodes'].append({'id': 'gap', 'kind': 'gap', 'start': None, 'end': None, 'nameId': None, 'status': 'unresolved', 'note': 'Unknown number of omitted links.'})
        self.unit['edges'].append({'id': 'bg', 'from': 'b', 'to': 'gap', 'start': None, 'end': None, 'mode': 'suspended', 'note': 'Unprinted continuation.'})
        self.unit['paths'].append({'id': 'parallel', 'kind': 'parallel', 'nodeIds': ['a', 'b', 'gap'], 'edgeIds': ['ab', 'bg'], 'status': 'uncertain', 'note': 'Shared prefix.'})
        self.unit['reports'][0]['pathIds'].append('parallel')
        self.unit['reports'][0]['status'] = 'uncertain'
        self.unit['status'] = 'uncertain'
        self.validate()
        self.unit['nodes'][-1]['nameId'] = 'fabricated'
        with self.assertRaises(ValueError): self.validate()

    def test_compiler_and_explicit_phrase(self):
        self.unit['edges'][0]['start'] = None
        self.unit['edges'][0]['end'] = None
        with self.assertRaises(ValueError): self.validate()
        self.unit['edges'][0]['mode'] = 'implicit'
        self.validate()
        self.unit['nodes'].insert(0, {'id': 'compiler', 'kind': 'compiler', 'start': None, 'end': None, 'nameId': None, 'status': 'implicit', 'note': 'Unprinted compiler root only.'})
        self.unit['edges'].append({'id': 'ca', 'from': 'compiler', 'to': 'a', 'start': None, 'end': None, 'mode': 'implicit', 'note': 'Layout root, no meeting claim.'})
        self.unit['paths'][0]['nodeIds'].insert(0, 'compiler')
        self.unit['paths'][0]['edgeIds'].insert(0, 'ca')
        self.validate()

    def test_all_source_reports_accounted(self):
        self.unit['reports'] = []
        self.unit['nodes'] = []
        self.unit['edges'] = []
        self.unit['paths'] = []
        with self.assertRaises(ValueError): self.validate()

    def test_private_write_once_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(h, 'ROOT', Path(directory)):
            target = Path(directory) / '.runtime' / 'view.txt'
            h.write_new(target, 'private')
            with self.assertRaises(FileExistsError): h.write_new(target, 'replace')
            with self.assertRaises(ValueError): h.write_new(Path(directory) / 'public.txt', 'leak')
            duplicate = Path(directory) / 'duplicate.json'
            duplicate.write_text('{"x":1,"x":2}', encoding='utf-8')
            with self.assertRaises(ValueError): h.read(duplicate)



class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patcher = patch.object(h, 'ROOT', self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        (self.root / 'docs/translation').mkdir(parents=True)
        (self.root / 'docs/translation/hadith-structure.md').write_text('Synthetic spec.', encoding='utf-8')
        self.paths = {key: self.root / '.runtime' / (key + '.json') for key in h.ARTIFACTS}
        self.source, self.structure, self.ledger = fixture()
        self.translation = {'status': 'agent_complete', 'humanReview': 'unreviewed', 'sourceSha256': None,
                            'units': [{'id': 'synthetic-unit', 'arabic': self.source['units'][0]['arabic'], 'english': 'Synthetic translation.'}]}
        self.audit = {'verdict': 'pass', 'checkedUnitIds': ['synthetic-unit'], 'checks': h.CHECKS[:], 'findings': [], 'limits': ['Synthetic test, no scholarly authentication.']}
        for key, value in [('source', self.source), ('structure', self.structure), ('ledger', self.ledger)]:
            h.write_new(self.paths[key], value)
        self.translation['sourceSha256'] = h.file_hash(self.paths['source'])
        h.write_new(self.paths['translation'], self.translation)
        h.write_new(self.paths['audit'], self.audit)
        h.write_new(self.paths['render'], h.render(self.source, self.structure))
        for prefix, stage, session, input_hash, output_hash in [
            ('extraction', 'extraction', 'synthetic-extractor', h.extraction_input_hash(self.paths['source'], self.paths['ledger']), h.file_hash(self.paths['structure'])),
            ('audit', 'structure-audit', 'synthetic-auditor', h.audit_input_hash(*(self.paths[k] for k in ('source', 'translation', 'structure', 'ledger'))), h.file_hash(self.paths['audit']))]:
            host = {'stage': stage, 'sessionId': session, 'context': 'fresh', 'inputSha256': input_hash, 'outputSha256': output_hash,
                    'provider': 'synthetic', 'model': 'synthetic-no-model', 'reasoning': 'synthetic', 'turnId': 'synthetic-turn',
                    'adapter': 'codex-jsonl-v1', 'launch': {'provider': 'synthetic', 'model': 'synthetic-no-model', 'reasoning': 'synthetic', 'forkTurns': 'none'},
                    'coordinator': {'sessionId': 'synthetic-coordinator'}}
            h.write_new(self.paths[prefix + 'Host'], host)
            receipt = {k: host[k] for k in ('stage', 'sessionId', 'context', 'inputSha256', 'outputSha256')}
            receipt['hostCaptureSha256'] = h.file_hash(self.paths[prefix + 'Host'])
            h.write_new(self.paths[prefix + 'Receipt'], receipt)

    def rewrite(self, key, value):
        # Test-only adversarial tampering; production writers are exclusively write-once.
        self.paths[key].write_text(json.dumps(value), encoding='utf-8')

    def test_valid_manifest_and_hash_drift(self):
        manifest = h.build_manifest(self.paths)
        self.assertEqual(h.validate_manifest(manifest), manifest)
        self.paths['translation'].write_text('tamper', encoding='utf-8')
        with self.assertRaises(ValueError): h.validate_manifest(manifest)

    def test_reject_unrelated_or_incomplete_translation(self):
        for key, value in [('sourceSha256', '0' * 64), ('status', 'draft'), ('humanReview', 'reviewed'), ('units', [])]:
            with self.subTest(key=key):
                candidate = copy.deepcopy(self.translation)
                candidate[key] = value
                self.rewrite('translation', candidate)
                with self.assertRaises(ValueError): h.build_manifest(self.paths)
        for key, value in [('arabic', 'Altered'), ('english', ''), ('id', 'other')]:
            candidate = copy.deepcopy(self.translation)
            candidate['units'][0][key] = value
            self.rewrite('translation', candidate)
            with self.assertRaises(ValueError): h.build_manifest(self.paths)

    def test_capture_identity_and_observed_settings(self):
        original = h.read(self.paths['extractionHost'])
        for key, value in [('sessionId', 'different'), ('adapter', 'invented-adapter'), ('provider', ''), ('context', 'forked'), ('stage', 'other'), ('turnId', '')]:
            with self.subTest(key=key):
                host = copy.deepcopy(original)
                host[key] = value
                self.rewrite('extractionHost', host)
                receipt = h.read(self.paths['extractionReceipt'])
                receipt['hostCaptureSha256'] = h.file_hash(self.paths['extractionHost'])
                self.rewrite('extractionReceipt', receipt)
                with self.assertRaises(ValueError): h.build_manifest(self.paths)
        host = copy.deepcopy(original)
        host['launch']['model'] = 'different'
        self.rewrite('extractionHost', host)
        receipt['hostCaptureSha256'] = h.file_hash(self.paths['extractionHost'])
        self.rewrite('extractionReceipt', receipt)
        with self.assertRaises(ValueError): h.build_manifest(self.paths)

    def test_same_worker_session_and_coordinator_rejected(self):
        host = h.read(self.paths['auditHost'])
        receipt = h.read(self.paths['auditReceipt'])
        host['sessionId'] = receipt['sessionId'] = 'synthetic-extractor'
        self.rewrite('auditHost', host)
        receipt['hostCaptureSha256'] = h.file_hash(self.paths['auditHost'])
        self.rewrite('auditReceipt', receipt)
        with self.assertRaises(ValueError): h.build_manifest(self.paths)
        host['coordinator']['sessionId'] = host['sessionId']
        self.rewrite('auditHost', host)
        receipt['hostCaptureSha256'] = h.file_hash(self.paths['auditHost'])
        self.rewrite('auditReceipt', receipt)
        with self.assertRaises(ValueError): h.build_manifest(self.paths)

    def test_audit_coverage_hold_and_uncertainty(self):
        for key, value in [('verdict', 'hold'), ('checkedUnitIds', []), ('checks', []), ('limits', [])]:
            audit = copy.deepcopy(self.audit)
            audit[key] = value
            with self.assertRaises(ValueError): h.validate_audit(self.structure, audit)
        self.structure['units'][0]['status'] = 'uncertain'
        self.structure['units'][0]['reports'][0]['status'] = 'uncertain'
        with self.assertRaises(ValueError): h.validate_audit(self.structure, self.audit)
        self.audit['findings'] = [{'id': 'finding', 'unitId': 'synthetic-unit', 'reportId': 'report', 'status': 'human-only', 'detail': 'Synthetic uncertainty preserved.'}]
        h.validate_audit(self.structure, self.audit)
        self.audit['findings'][0]['status'] = 'actionable'
        with self.assertRaises(ValueError): h.validate_audit(self.structure, self.audit)

    def test_render_and_contract_drift(self):
        self.paths['render'].write_text('Missing chain.', encoding='utf-8')
        with self.assertRaises(ValueError): h.build_manifest(self.paths)
        self.paths['render'].write_text(h.render(self.source, self.structure), encoding='utf-8')
        manifest = h.build_manifest(self.paths)
        (self.root / 'docs/translation/hadith-structure.md').write_text('Changed spec.', encoding='utf-8')
        with self.assertRaises(ValueError): h.validate_manifest(manifest)

    def test_malformed_arrays(self):
        for value in (None, {}, 'not-an-array'):
            structure = copy.deepcopy(self.structure)
            structure['units'][0]['paths'][0]['nodeIds'] = value
            with self.assertRaises(ValueError): h.validate(self.source, structure, self.ledger)
        structure = copy.deepcopy(self.structure)
        structure['units'][0]['paths'][0]['nodeIds'] = [{}]
        with self.assertRaises(ValueError): h.validate(self.source, structure, self.ledger)


if __name__ == '__main__':
    unittest.main()
