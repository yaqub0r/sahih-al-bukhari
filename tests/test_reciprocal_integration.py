"""Synthetic v2 manifest and complete-collection adapter integration tests."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import hadith_structure as legacy
from scripts import hadith_structure_v2 as h
from scripts import release_distribution as d
from scripts import bukhari_isnad_adapter_v2 as public
from scripts import collection_release as collector
from scripts import continued_context_v2 as carry
from tests.test_hadith_structure_v2 import fixture
from tests.test_bukhari_distribution import proposal


class ReciprocalIntegrationTests(unittest.TestCase):
    def test_legacy_public_record_remains_valid_without_declaration_field(self):
        p = proposal(); before = copy.deepcopy(p)
        public.validate_records(p['records'], p)
        self.assertEqual(p, before)

    def test_legacy_context_is_carried_exactly_into_v2(self):
        from tests.test_continued_context import ContinuedBindingTests
        case=ContinuedBindingTests('test_real_companion_validation_binds_inherited_context')
        case.setUp(); self.addCleanup(case.doCleanups)
        scoped,frozen=carry.bind_context(case.source,['next'],case.cut,[case.manifest],case.case.paths['ledger'])
        inherited=frozen['inherited'][0]['record']
        self.assertNotIn('reciprocalCommunications',inherited['structure'])
        output={'units':[inherited['translation'],{'id':'next','english':'Invented next.','formulaTargets':[]}]}
        graph={'version':2,'units':[copy.deepcopy(inherited['structure']),{'id':'next'}]}
        carry.validate_carried(frozen,output,graph)
        graph['units'][0]['reciprocalCommunications']=[]
        with self.assertRaisesRegex(ValueError,'isnad context changed'):
            carry.validate_carried(frozen,output,graph)

    def test_manifest_receipts_projection_and_public_roundtrip(self):
        source, graph, ledger = fixture()
        source['units'][0].update(contextIds=[],formulaSpans=[])
        ledger={'version':2,'identities':[{**v,'english':v['id'],'renderings':[{'arabic':a,'english':v['id']} for a in v['arabicForms']]} for v in ledger['identities']],'decisions':[]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(h, 'ROOT', root), patch.object(legacy, 'ROOT', root), patch.object(collector, 'ROOT', root):
                docs = root / 'docs/translation'; docs.mkdir(parents=True)
                (docs/'hadith-structure.md').write_text('Synthetic legacy contract.')
                (docs/'hadith-structure-v2.md').write_text('Synthetic reciprocal contract.')
                paths = {key: root/'.runtime'/(key+'.json') for key in h.ARTIFACTS}
                for key, value in [('source',source),('structure',graph),('ledger',ledger)]: h.write_new(paths[key],value)
                h.write_new(paths['translation'], {'status':'agent_complete','humanReview':'unreviewed',
                            'sourceSha256':h.file_hash(paths['source']),
                            'units':[{'id':'u','arabic':source['units'][0]['arabic'],'english':'Invented translation.','formulaTargets':[]}],
                            'unresolved':[]})
                h.write_new(paths['audit'], {'verdict':'pass','checkedUnitIds':['u'],'checks':h.CHECKS[:],
                                            'findings':[],'limits':['Synthetic test only.']})
                h.write_new(paths['render'],h.render(source,graph))
                for prefix, stage, session, input_hash, output_hash in [
                    ('extraction','extraction','synthetic-extractor',h.extraction_input_hash(paths['source'],paths['ledger']),h.file_hash(paths['structure'])),
                    ('audit','structure-audit','synthetic-auditor',h.audit_input_hash(*(paths[k] for k in ['source','translation','structure','ledger'])),h.file_hash(paths['audit']))]:
                    host={'stage':stage,'sessionId':session,'context':'fresh','inputSha256':input_hash,'outputSha256':output_hash,
                          'provider':'synthetic','model':'synthetic-no-model','reasoning':'synthetic','turnId':'synthetic-turn',
                          'adapter':'codex-jsonl-v1','launch':{'provider':'synthetic','model':'synthetic-no-model','reasoning':'synthetic','forkTurns':'none'},
                          'coordinator':{'sessionId':'synthetic-coordinator'}}
                    h.write_new(paths[prefix+'Host'],host)
                    receipt={k:host[k] for k in ['stage','sessionId','context','inputSha256','outputSha256']}
                    receipt['hostCaptureSha256']=h.file_hash(paths[prefix+'Host'])
                    h.write_new(paths[prefix+'Receipt'],receipt)
                manifest=h.build_manifest(paths)
                self.assertEqual(manifest['version'],2)
                self.assertEqual(manifest['kind'],'private-hadith-structure-companion-v2')
                self.assertEqual(h.validate_manifest(manifest),manifest)
                companion=root/'.runtime/companion.json'; h.write_new(companion,manifest)
                qualified={'units':[source['units'][0],{'id':'next','kind':'report','arabic':'INVENTED NEXT','contextIds':[]}],'exclusions':[]}
                authority=root/'.runtime/qualified.json';h.write_new(authority,qualified)
                cut=root/'.runtime/cut.json';h.write_new(cut,{'version':1,'verdict':'pass','sourceCanonicalSha256':carry.digest(qualified),'ownedUnitIds':['next'],'additionalContextUnitIds':['u'],'detail':'Synthetic continuation.'})
                scoped,frozen=carry.bind_context(authority,['next'],cut,[companion],paths['ledger'])
                self.assertEqual(frozen['inherited'][0]['record']['structure'],graph['units'][0])
                carried={'units':[h.read(paths['translation'])['units'][0],{'id':'next','english':'Invented next.','formulaTargets':[]}]}
                carry.validate_carried(frozen,carried,{'version':2,'units':[graph['units'][0],{'id':'next'}]})
                changed=copy.deepcopy(carried);changed['units'][0]['english']='Changed carry.'
                with self.assertRaises(ValueError):carry.validate_carried(frozen,changed)

                with self.assertRaises(ValueError): legacy.validate_manifest(manifest)
                rows=collector.project_collection('source-division-004',manifest,{'u':1},{'u':1})
                self.assertEqual(rows[0]['isnad']['reciprocalCommunications'],graph['units'][0]['reciprocalCommunications'])
                public.validate_records(rows,{'scope':{'numberedReportCount':1}})
                schema=d.read(Path(__file__).resolve().parents[1]/'contracts/distribution-v2/hadith-record.schema.json')
                d.lint_schema(schema)
                # Synthetic public identity is made schema-shaped solely for the test.
                rows[0]['sourceUnitId']='bukhari-l999999'
                d.schema_check(schema,rows[0])
                changed=copy.deepcopy(rows);changed[0]['isnad']['reciprocalCommunications']=[]
                with self.assertRaises(ValueError): public.validate_records(changed,{'scope':{'numberedReportCount':1}})
                paths['render'].write_text('Omitted reciprocal paths.')
                with self.assertRaises(ValueError): h.validate_manifest(manifest)


if __name__ == '__main__': unittest.main()
