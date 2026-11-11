"""Synthetic-only end-to-end workflow and adversarial boundary tests."""
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

from scripts import translation_workflow as w


class TranslationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patch = patch.object(w, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        (self.root / 'policy.md').write_text('Synthetic test policy only.', encoding='utf-8')
        for relative in w.REQUIRED_POLICIES:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Synthetic binding target.', encoding='utf-8')
        self.source = self.root / 'source.json'
        w.write_new(self.source, {'units': [
            {'id': 'syn-heading', 'kind': 'heading', 'location': 'synthetic:1',
             'arabic': 'SYNTHETIC HEADING', 'contextIds': [], 'formulaSpans': []},
            {'id': 'syn-report', 'kind': 'report', 'location': 'synthetic:2',
             'arabic': 'SYNTHETIC ۞ REPORT', 'contextIds': ['syn-heading'],
             'formulaSpans': [{'start': 10, 'end': 11, 'referent': 'synthetic-symbol'}]}],
            'exclusions': [{'location': 'synthetic:cover', 'reason': 'Synthetic excluded furniture'}]})
        self.reference = self.root / 'reference.txt'
        self.reference.write_text('SYNTHETIC RESTRICTED REFERENCE CANARY', encoding='utf-8')
        def source_record(path, identity, public):
            return {'id': identity, 'edition': 'synthetic edition', 'sha256': w.file_hash(path),
                    'bytes': path.stat().st_size, 'rightsBasis': 'Synthetic test permission, no real rights grant',
                    'attribution': 'Synthetic test', 'publicationAllowed': public,
                    'translationAllowed': public, 'processingAllowed': True, 'commercialAllowed': True}
        self.profile = {'version': 1, 'workId': 'syn-work', 'repository': 'synthetic/book',
                        'intendedUse': 'commercial', 'source': source_record(self.source, 'syn-source', True),
                        'witnesses': [source_record(self.reference, 'syn-reference', False)],
                        'englishComparison': {'enabled': True, 'witnessId': 'syn-reference',
                                              'reason': 'Synthetic comparison path'},
                        'methods': {s: {'id': 'syn-method-' + s, 'provider': 'synthetic',
                                        'model': 'synthetic-no-model', 'reasoning': 'synthetic'} for s in w.STAGES},
                        'policyFiles': {relative: w.file_hash(self.root / relative)
                                        for relative in (*w.REQUIRED_POLICIES, 'policy.md')},
                        'limitations': ['Synthetic input; no facsimile verification or scholarly claim.']}
        self.profile_path = self.root / 'profile.json'
        self.profile['coordinatorMethod'] = {'id': 'syn-coordinator', 'provider': 'synthetic',
                                             'model': 'synthetic-no-model', 'reasoning': 'synthetic'}
        self.ledger = self.root / 'names.json'
        w.write_new(self.ledger, {'version': 1, 'identities': [], 'decisions': []})
        self.profile['nameLedger'] = {'path': 'names.json', 'sha256': w.file_hash(self.ledger)}
        self.save_profile()
        self.ids = ['syn-heading', 'syn-report']
        self.claims = [{'workId': 'syn-work', 'sourceSha256': self.profile['source']['sha256'],
                        'unitIds': self.ids, 'issue': 3, 'assignees': ['synthetic-owner']}]
        self.run = self.root / '.runtime' / 'run'
        self.packet = w.prepare(self.profile_path, self.source, self.ids, 3, self.claims, 'synthetic-coordinator')
        w.write_new(self.run / 'packet.json', self.packet)
        translated = [{'id': 'syn-heading', 'english': 'SYNTHETIC HEADING', 'formulaTargets': []},
                      {'id': 'syn-report', 'english': 'SYNTHETIC ۞ REPORT',
                       'formulaTargets': [{'start': 10, 'end': 11}]}]
        self.outputs = {
            'blind': {'units': translated},
            'critique': {'checkedUnitIds': self.ids, 'checks': list(w.CHECKS), 'findings': []},
            'comparison': {'coverage': [{'unitId': u['id'], 'start': 0, 'end': len(u['arabic']),
                                        'referenceLocation': 'synthetic:reference', 'status': 'equivalent',
                                        'findingIds': []} for u in self.packet['units']], 'findings': []},
            'witness': {'decisions': [], 'notRequiredReason': 'No material uncertainty in synthetic fixture.'},
            'adjudication': {'units': translated, 'decisions': []},
            'names': {'checkedUnitIds': self.ids, 'names': []},
            'audit': {'checkedUnitIds': self.ids, 'checks': list(w.AUDIT_CHECKS),
                      'publicEligible': True, 'unresolved': []}}

    def save_profile(self):
        self.profile_path.write_text(json.dumps(self.profile), encoding='utf-8')

    def host(self, stage, output=None):
        previous, _ = w.history(self.run, self.packet, self.profile)
        method = self.profile['methods'][stage]
        return {**{k: method[k] for k in ('provider', 'model', 'reasoning')},
                'sessionId': 'synthetic-session-' + stage, 'context': 'fresh', 'stage': stage,
                'turnId': 'synthetic-turn', 'adapter': 'codex-jsonl-v1',
                'coordinator': {'sessionId': 'synthetic-coordinator', 'turnId': 'synthetic-coordinator-turn',
                                'provider': 'synthetic', 'model': 'synthetic-no-model', 'reasoning': 'synthetic'},
                'coordinatorLaunch': {'provider': 'synthetic', 'model': 'synthetic-no-model', 'reasoning': 'synthetic'},
                'runId': self.packet['runId'],
                'inputSha256': w.stage_input(self.packet, self.profile, stage, previous),
                'outputSha256': w.digest(output or self.outputs[stage]),
                'launch': {**{k: method[k] for k in ('provider', 'model', 'reasoning')}, 'forkTurns': 'none'}}

    def record(self, stage):
        w.record(self.run, self.packet, self.profile, stage, self.outputs[stage], self.host(stage))

    def until(self, stage):
        for name in w.stages(self.profile):
            if name == stage:
                break
            self.record(name)

    def finish(self):
        self.until('never')
        previous = w.completed(self.run, self.packet, self.profile)
        (self.run / 'review.html').write_text(w.render(self.packet, previous, self.profile), encoding='utf-8')
        return w.submit(self.run, self.packet, self.profile, self.claims)

    def test_complete_comparison_path_has_private_evidence_and_public_allowlist(self):
        submission = self.finish()
        self.assertEqual('agent_complete', submission['status'])
        self.assertEqual('unreviewed', submission['humanReview'])
        self.assertEqual(0, submission['remainingAgentUnits'])
        self.assertTrue(submission['comparisonPerformed'])
        self.assertNotIn('CANARY', json.dumps(submission))
        self.assertNotIn('sessionId', json.dumps(submission))
        self.assertEqual(self.profile['source']['sha256'], submission['sourceSha256'])
        self.assertEqual(7, len(submission['stageHashes']))

    def test_complete_without_english_witness(self):
        self.profile['englishComparison'] = {'enabled': False, 'witnessId': None, 'reason': 'No qualified English witness'}
        del self.profile['methods']['comparison']
        self.save_profile()
        self.packet = w.prepare(self.profile_path, self.source, self.ids, 3, self.claims, 'synthetic-coordinator')
        self.assertFalse(self.finish()['comparisonPerformed'])

    def test_missing_stage_cannot_complete(self):
        self.record('blind')
        with self.assertRaises(w.WorkflowError):
            w.completed(self.run, self.packet, self.profile)

    def test_comparison_cannot_precede_arabic_critique(self):
        with self.assertRaises(w.WorkflowError):
            self.record('comparison')

    def test_wrong_effective_method_or_inherited_context_rejected(self):
        for key, bad in [('model', 'other-model'), ('context', 'inherited'), ('inputSha256', '0' * 64)]:
            with self.subTest(key=key):
                host = self.host('blind')
                host[key] = bad
                with self.assertRaises(w.WorkflowError):
                    w.record(self.run, self.packet, self.profile, 'blind', self.outputs['blind'], host)

    def test_reused_session_rejected(self):
        self.record('blind')
        host = self.host('critique')
        host['sessionId'] = 'synthetic-session-blind'
        with self.assertRaises(w.WorkflowError):
            w.record(self.run, self.packet, self.profile, 'critique', self.outputs['critique'], host)

    def test_coordinator_cannot_self_certify_worker_stage(self):
        host = self.host('blind')
        host['sessionId'] = 'synthetic-coordinator'
        with self.assertRaises(w.WorkflowError):
            w.record(self.run, self.packet, self.profile, 'blind', self.outputs['blind'], host)

    def test_changed_upstream_invalidates_downstream(self):
        self.until('witness')
        receipt_path = self.run / 'blind.json'
        receipt = w.read(receipt_path)
        receipt['output']['units'][0]['english'] += ' CHANGED'
        receipt_path.write_text(json.dumps(receipt), encoding='utf-8')
        with self.assertRaises(w.WorkflowError):
            w.history(self.run, self.packet, self.profile)

    def test_receipts_are_append_only(self):
        self.record('blind')
        with self.assertRaises(w.WorkflowError):
            self.record('blind')

    def test_source_bytes_are_frozen(self):
        self.source.write_text('changed', encoding='utf-8')
        with self.assertRaises(w.WorkflowError):
            w.prepare(self.profile_path, self.source, self.ids, 3, self.claims, 'synthetic-coordinator')

    def test_policy_changes_require_reviewed_binding_update(self):
        (self.root / 'policy.md').write_text('changed', encoding='utf-8')
        with self.assertRaises(w.WorkflowError):
            w.load_profile(self.profile_path)

    def test_commercial_and_processing_rights_fail_closed(self):
        for record, key in [('source', 'commercialAllowed'), ('source', 'publicationAllowed'),
                            ('source', 'translationAllowed'), ('reference', 'processingAllowed'),
                            ('reference', 'commercialAllowed')]:
            with self.subTest(record=record, key=key):
                original = copy.deepcopy(self.profile)
                target = self.profile['source'] if record == 'source' else self.profile['witnesses'][0]
                target[key] = False
                self.save_profile()
                with self.assertRaises(w.WorkflowError):
                    w.load_profile(self.profile_path)
                self.profile = original

    def test_nonboolean_rights_flag_rejected(self):
        self.profile['source']['commercialAllowed'] = 'yes'
        self.save_profile()
        with self.assertRaises(w.WorkflowError):
            w.load_profile(self.profile_path)

    def test_overlap_missing_assignee_and_changed_claim_rejected(self):
        for claims in [self.claims + [{**self.claims[0], 'issue': 4}],
                       [{**self.claims[0], 'assignees': []}],
                       [{**self.claims[0], 'sourceSha256': '0' * 64}]]:
            with self.assertRaises(w.WorkflowError):
                w.prepare(self.profile_path, self.source, self.ids, 3, claims, 'synthetic-coordinator')

    def test_missing_governing_context_rejected(self):
        claims = [{**self.claims[0], 'unitIds': ['syn-report']}]
        with self.assertRaises(w.WorkflowError):
            w.prepare(self.profile_path, self.source, ['syn-report'], 3, claims, 'synthetic-coordinator')

    def test_invalid_claim_scope_does_not_write_github_issue(self):
        for scope in [['unknown-id'], ['syn-report'], ['syn-report', 'syn-heading'],
                      ['syn-heading', 'syn-heading']]:
            with patch.object(w, 'assignments', return_value=[]), patch.object(w, 'gh') as github:
                with redirect_stderr(io.StringIO()):
                    self.assertEqual(1, w.main(['claim', '--profile', str(self.profile_path),
                                              '--source', str(self.source), '--units', *scope,
                                              '--assignee', 'synthetic-owner']))
                github.assert_not_called()

    def test_name_ledger_prevents_cross_run_identity_drift(self):
        self.ledger.write_text(json.dumps({'version': 1, 'identities': [
            {'id': 'syn-person', 'english': 'SYNTHETIC', 'arabicForms': ['SYNTHETIC']}], 'decisions': []}),
            encoding='utf-8')
        self.profile['nameLedger']['sha256'] = w.file_hash(self.ledger)
        self.save_profile()
        self.packet = w.prepare(self.profile_path, self.source, self.ids, 3, self.claims, 'synthetic-coordinator')
        self.outputs['names']['names'] = [{'nameId': 'syn-person', 'unitId': 'syn-report', 'start': 0,
                                           'end': 9, 'targetStart': 0, 'targetEnd': 9, 'english': 'SYNTHETIC'}]
        self.until('names')
        self.record('names')
        previous, _ = w.history(self.run, self.packet, self.profile)
        bad = copy.deepcopy(self.outputs['names'])
        bad['names'][0]['nameId'] = 'unregistered-person'
        with self.assertRaises(w.WorkflowError):
            w.validate_output('names', bad, self.packet, self.profile, previous)
        self.ledger.write_text('changed ledger', encoding='utf-8')
        with self.assertRaises(w.WorkflowError):
            w.load_profile(self.profile_path)

    def variant_ledger(self, version=2):
        identity = {'id': 'syn-person', 'english': 'SYNTHETIC',
                    'arabicForms': ['SYNTHETIC', 'REPORT']}
        if version == 2:
            identity['renderings'] = [{'arabic': 'SYNTHETIC', 'english': 'SYNTHETIC'},
                                      {'arabic': 'REPORT', 'english': 'REPORT'}]
        return {'version': version, 'identities': [identity], 'decisions': []}

    def install_name_ledger(self, ledger):
        self.ledger.write_text(json.dumps(ledger), encoding='utf-8')
        self.profile['nameLedger']['sha256'] = w.file_hash(self.ledger)
        self.save_profile()
        return w.load_profile(self.profile_path)

    def variant_mentions(self):
        return {'checkedUnitIds': self.ids, 'names': [
            {'nameId': 'syn-person', 'unitId': 'syn-report', 'start': start, 'end': end,
             'targetStart': start, 'targetEnd': end, 'english': english}
            for start, end, english in [(0, 9, 'SYNTHETIC'), (12, 18, 'REPORT')]]}

    def test_v2_registered_variants_preserve_identity_through_audit(self):
        self.install_name_ledger(self.variant_ledger())
        previous = copy.deepcopy(self.outputs)
        previous['names'] = self.variant_mentions()
        w.validate_output('names', previous['names'], self.packet, self.profile, previous)
        w.validate_output('audit', self.outputs['audit'], self.packet, self.profile, previous)
        for mutation in ('target', 'source', 'identity'):
            with self.subTest(mutation=mutation):
                bad = copy.deepcopy(previous)
                mention = bad['names']['names'][1]
                if mutation == 'target':
                    bad['adjudication']['units'][1]['english'] = 'SYNTHETIC ۞ OTHER!'
                    mention['english'] = 'OTHER!'
                elif mutation == 'source':
                    mention.update(start=10, end=11)
                else:
                    mention['nameId'] = 'syn-unknown'
                with self.assertRaises(w.WorkflowError):
                    w.validate_output('names', bad['names'], self.packet, self.profile, bad)
                with self.assertRaises(w.WorkflowError):
                    w.validate_output('audit', self.outputs['audit'], self.packet, self.profile, bad)

    def test_v2_invalid_rendering_maps_rejected(self):
        for mutation in ('missing', 'duplicate', 'conflict', 'unknown-form', 'extra-field',
                         'duplicate-form', 'no-renderings', 'empty', 'identity-field'):
            with self.subTest(mutation=mutation):
                ledger = self.variant_ledger()
                identity = ledger['identities'][0]
                mappings = identity['renderings']
                if mutation == 'missing':
                    mappings.pop()
                elif mutation in ('duplicate', 'conflict'):
                    mappings.append({'arabic': 'REPORT', 'english': 'OTHER' if mutation == 'conflict' else 'REPORT'})
                elif mutation == 'unknown-form':
                    mappings[1]['arabic'] = 'UNKNOWN'
                elif mutation == 'extra-field':
                    mappings[1]['extra'] = 'unexpected'
                elif mutation == 'duplicate-form':
                    identity['arabicForms'].append('REPORT')
                elif mutation == 'no-renderings':
                    del identity['renderings']
                elif mutation == 'empty':
                    identity['renderings'] = []
                else:
                    identity['extra'] = 'unexpected'
                with self.assertRaises(w.WorkflowError):
                    self.install_name_ledger(ledger)

    def test_v1_keeps_single_realization_and_rejects_v2_fields(self):
        self.install_name_ledger(self.variant_ledger(1))
        previous = copy.deepcopy(self.outputs)
        previous['names'] = self.variant_mentions()
        with self.assertRaises(w.WorkflowError):
            w.validate_output('names', previous['names'], self.packet, self.profile, previous)
        with self.assertRaises(w.WorkflowError):
            w.validate_output('audit', self.outputs['audit'], self.packet, self.profile, previous)
        ledger = self.variant_ledger()
        ledger['version'] = 1
        with self.assertRaises(w.WorkflowError):
            self.install_name_ledger(ledger)

    def test_missing_unit_and_formula_modification_rejected(self):
        for mutate in [lambda units: units.pop(),
                       lambda units: units[1].update(english='SYNTHETIC X REPORT'),
                       lambda units: units[1].update(formulaTargets=[])]:
            output = copy.deepcopy(self.outputs['blind'])
            mutate(output['units'])
            with self.assertRaises(w.WorkflowError):
                w.record(self.run, self.packet, self.profile, 'blind', output, self.host('blind', output))

    def test_reference_omission_is_not_silently_dropped(self):
        self.until('comparison')
        row = self.outputs['comparison']['coverage'][1]
        row['status'] = 'reference-omits'
        row['referenceLocation'] = None
        with self.assertRaises(w.WorkflowError):
            self.record('comparison')

    def test_reference_omission_and_retrieval_evidence_reach_adjudication(self):
        row = self.outputs['comparison']['coverage'][1]
        row.update(status='reference-omits', referenceLocation=None, findingIds=['syn-omission'])
        self.outputs['comparison']['findings'] = [{'id': 'syn-omission', 'unitId': 'syn-report',
            'category': 'omissions', 'detail': 'Synthetic reference lacks this report', 'start': 0,
            'end': len(self.packet['units'][1]['arabic'])}]
        self.outputs['witness']['decisions'] = [{'findingId': 'syn-omission', 'status': 'resolved',
            'basis': 'Retain complete Arabic despite reference omission', 'witnessIds': ['syn-reference'],
            'evidence': [{'witnessId': 'syn-reference', 'status': 'no_match', 'query': 'synthetic report',
                          'location': None, 'sha256': None}]}]
        self.outputs['adjudication']['decisions'] = [{'findingId': 'syn-omission', 'disposition': 'retained',
            'basis': 'Arabic inventory confirms independent translation is complete'}]
        self.assertTrue(self.finish()['comparisonPerformed'])

    def test_witness_cannot_omit_retrieval_evidence(self):
        self.outputs['critique']['findings'] = [{'id': 'syn-finding', 'unitId': 'syn-report',
            'category': 'uncertainty', 'detail': 'Synthetic concern', 'start': 0, 'end': 1}]
        self.outputs['witness']['decisions'] = [{'findingId': 'syn-finding', 'status': 'unavailable',
            'basis': 'Synthetic unavailable reference', 'witnessIds': ['syn-reference'], 'evidence': []}]
        self.until('witness')
        with self.assertRaises(w.WorkflowError):
            self.record('witness')

    def test_comparison_gap_rejected(self):
        self.until('comparison')
        self.outputs['comparison']['coverage'][1]['start'] = 1
        with self.assertRaises(w.WorkflowError):
            self.record('comparison')

    def test_human_only_uncertainty_preserved_without_human_review_gate(self):
        finding = {'id': 'syn-finding', 'unitId': 'syn-report', 'category': 'uncertainty',
                   'detail': 'SYNTHETIC PRIVATE FINDING CANARY', 'start': 0, 'end': 1}
        self.outputs['critique']['findings'] = [finding]
        self.outputs['witness']['decisions'] = [{'findingId': 'syn-finding', 'status': 'unavailable',
                                                'basis': 'Synthetic unavailable witness', 'witnessIds': [], 'evidence': []}]
        self.outputs['adjudication']['decisions'] = [{'findingId': 'syn-finding', 'disposition': 'unresolved',
                                                     'basis': 'Synthetic human-only judgment after exhaustion'}]
        self.outputs['audit']['unresolved'] = [{'findingId': 'syn-finding', 'unitId': 'syn-report',
                                              'publicSummary': 'Synthetic disclosed uncertainty', 'humanOnly': True}]
        submission = self.finish()
        self.assertEqual(['syn-finding'], submission['unresolvedFindingIds'])
        self.assertNotIn('CANARY', json.dumps(submission))
        self.assertIn('Synthetic disclosed uncertainty', (self.run / 'review.html').read_text(encoding='utf-8'))

    def test_public_eligibility_failure_and_agent_actionable_findings_hold(self):
        self.until('audit')
        self.outputs['audit']['publicEligible'] = False
        with self.assertRaises(w.WorkflowError):
            self.record('audit')

    def test_stale_presentation_and_live_claim_hold_submission(self):
        self.finish()
        with self.assertRaises(w.WorkflowError):
            w.submit(self.run, self.packet, self.profile, [])
        (self.run / 'review.html').write_text('stale', encoding='utf-8')
        with self.assertRaises(w.WorkflowError):
            w.submit(self.run, self.packet, self.profile, self.claims)

    def test_cli_prepare_record_render_validate_submit_end_to_end(self):
        # Exercise argument parsing and file operations without external side effects.
        run = self.root / '.runtime' / 'cli-run'
        common = ['--profile', str(self.profile_path), '--run', str(run)]
        with patch.object(w, 'assignments', return_value=self.claims):
            self.assertEqual(0, w.main(['prepare', *common, '--source', str(self.source), '--units', *self.ids,
                                        '--issue', '3', '--coordinator-session', 'synthetic-coordinator']))
            self.run = run
            self.packet = w.read(run / 'packet.json')
            for stage in w.stages(self.profile):
                output_path, host_path = run / (stage + '-output.json'), run / (stage + '-host.json')
                w.write_new(output_path, self.outputs[stage])
                w.write_new(host_path, self.host(stage))
                extra = ['--witness-file', str(self.reference)] if stage == 'comparison' else []
                self.assertEqual(0, w.main(['record', *common, '--stage', stage, '--output', str(output_path),
                                            '--host', str(host_path), *extra]))
            with redirect_stdout(io.StringIO()):
                for command in ('validate', 'render', 'submit'):
                    self.assertEqual(0, w.main([command, *common]))
            self.assertEqual('agent_complete', w.read(run / 'submission.json')['status'])

    def test_hydrate_rejects_wrong_bytes_without_persisting_download(self):
        import contextlib
        response = contextlib.nullcontext(io.BytesIO(b'wrong download'))
        with patch.object(w.urllib.request, 'urlopen', return_value=response), redirect_stderr(io.StringIO()):
            self.assertEqual(1, w.main(['hydrate', '--profile', str(self.profile_path),
                                        '--run', str(self.run), '--url', 'https://synthetic.invalid/source.json']))
        self.assertFalse((self.run / 'source.json').exists())

    def host_log(self, session, extra_meta=None, extra_rows=None):
        path = self.root / (session + '.jsonl')
        rows = [{'type': 'session_meta', 'payload': {'id': session, 'model_provider': 'synthetic',
                                                    **(extra_meta or {})}},
                {'type': 'turn_context', 'payload': {'turn_id': 'synthetic-turn',
                                                    'model': 'synthetic-no-model', 'effort': 'synthetic'}},
                {'type': 'event_msg', 'payload': {'text': 'SYNTHETIC PRIVATE PROMPT CANARY'}}]
        rows.extend(extra_rows or [])
        path.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
        return path

    def test_selected_host_metadata_adapter_captures_without_private_expression(self):
        worker = self.host_log('synthetic-worker')
        coordinator = self.host_log('synthetic-coordinator')
        host = w.capture_host(self.packet, self.profile, 'blind', {}, self.outputs['blind'], worker,
                              'synthetic-worker', 'synthetic-turn', coordinator, 'synthetic-turn',
                              self.host('blind')['launch'], self.host('blind')['coordinatorLaunch'])
        self.assertNotIn('CANARY', json.dumps(host))
        self.assertNotIn(str(self.root), json.dumps(host))
        w.record(self.run, self.packet, self.profile, 'blind', self.outputs['blind'], host)

    def test_host_adapter_rejects_forks_later_turns_and_inconsistent_settings(self):
        for meta, extra, selected_turn in [
            ({'forked_from_id': 'synthetic-parent'}, [], 'synthetic-turn'),
            ({}, [{'type': 'turn_context', 'payload': {'turn_id': 'later-turn',
                    'model': 'synthetic-no-model', 'effort': 'synthetic'}}], 'later-turn'),
            ({}, [{'type': 'turn_context', 'payload': {'turn_id': 'synthetic-turn',
                    'model': 'other-model', 'effort': 'synthetic'}}], 'synthetic-turn')]:
            path = self.host_log('synthetic-worker', meta, extra)
            with self.assertRaises(w.WorkflowError):
                w.observe_session(path, 'synthetic-worker', selected_turn, fresh=True)

    def test_cli_capture_host_and_coordinator_configuration(self):
        worker = self.host_log('synthetic-worker')
        coordinator = self.host_log('synthetic-coordinator')
        output, launch, coordinator_launch = (self.run / 'out.json', self.run / 'launch.json', self.run / 'task.json')
        w.write_new(output, self.outputs['blind'])
        w.write_new(launch, self.host('blind')['launch'])
        w.write_new(coordinator_launch, self.host('blind')['coordinatorLaunch'])
        destination = self.run / 'capture.json'
        self.assertEqual(0, w.main(['capture-host', '--profile', str(self.profile_path), '--run', str(self.run),
            '--stage', 'blind', '--output', str(output), '--host', str(destination), '--session-log', str(worker),
            '--session', 'synthetic-worker', '--turn', 'synthetic-turn', '--coordinator-log', str(coordinator),
            '--coordinator-turn', 'synthetic-turn', '--launch', str(launch), '--coordinator-launch', str(coordinator_launch)]))
        host = w.read(destination)
        host['coordinator']['model'] = 'wrong-coordinator-model'
        with self.assertRaises(w.WorkflowError):
            w.record(self.run, self.packet, self.profile, 'blind', self.outputs['blind'], host)

    def test_cli_stage_input_withholds_reference_until_comparison(self):
        for stage in ('blind', 'critique', 'comparison'):
            stream = io.StringIO()
            args = ['stage-input', '--profile', str(self.profile_path), '--run', str(self.run), '--stage', stage,
                    '--witness-file', str(self.reference)]
            with redirect_stdout(stream):
                self.assertEqual(0, w.main(args))
            payload = json.loads(stream.getvalue())
            self.assertEqual(stage == 'comparison', 'reference' in payload)
            self.record(stage)

    def test_cli_rejects_unpinned_reference_and_runtime_escape(self):
        self.until('comparison')
        self.reference.write_text('wrong reference', encoding='utf-8')
        with redirect_stderr(io.StringIO()):
            self.assertEqual(1, w.main(['stage-input', '--profile', str(self.profile_path), '--run', str(self.run),
                                        '--stage', 'comparison', '--witness-file', str(self.reference)]))
            self.assertEqual(1, w.main(['doctor', '--profile', str(self.profile_path), '--run', str(self.root)]))

    def test_html_escapes_text_and_pairs_english_before_arabic(self):
        self.outputs['adjudication']['units'][0]['english'] = '<script>synthetic</script>'
        self.finish()
        page = (self.run / 'review.html').read_text(encoding='utf-8')
        self.assertNotIn('<script>', page)
        self.assertIn('&lt;script&gt;', page)
        self.assertLess(page.index('&lt;script&gt;'), page.index('dir="rtl"'))


class TemplateStarterTests(unittest.TestCase):
    def test_example_has_current_local_bindings_but_grants_no_production_authority(self):
        root = Path(__file__).resolve().parents[1]
        profile = w.read(root / 'profiles/translation-profile.example.json')
        self.assertTrue(set(w.REQUIRED_POLICIES) <= set(profile['policyFiles']))
        for relative, expected in profile['policyFiles'].items():
            self.assertEqual(expected, w.file_hash(root / relative), relative)
        self.assertEqual(profile['nameLedger']['sha256'], w.file_hash(root / profile['nameLedger']['path']))
        self.assertFalse(profile['source']['processingAllowed'])
        self.assertEqual({}, profile['methods'])
        with self.assertRaises(w.WorkflowError):
            w.load_profile(root / 'profiles/translation-profile.example.json')


if __name__ == '__main__':
    unittest.main()
