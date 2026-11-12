"""Synthetic tests for occurrence ownership and immutable bilingual context."""
import copy,unittest,json
from pathlib import Path
from scripts import hadith_structure as h
from tests import test_hadith_structure as fixtures
from scripts import continued_context as c
class ContinuedContextTests(unittest.TestCase):
    def setUp(self):
        self.source={'units':[{'id':'book','kind':'heading','arabic':'SYNTHETIC BOOK','contextIds':[]},{'id':'chapter','kind':'heading','arabic':'SYNTHETIC CHAPTER','contextIds':['book']},{'id':'report','kind':'report','arabic':'INVENTED REPORT','contextIds':['book','chapter']}],'exclusions':[]}
        self.review={'version':1,'verdict':'pass','sourceCanonicalSha256':c.digest(self.source),'ownedUnitIds':['report'],'additionalContextUnitIds':[],'detail':'Synthetic semantic cut review.'}
    def test_context_closure_preserves_occurrences(self):
        p=c.plan(self.source,['report'],self.review)
        self.assertEqual(p['contextUnitIds'],['book','chapter']);self.assertEqual(p['ownedUnitIds'],['report'])
        self.assertEqual(p['source'],self.source)
    def test_missing_or_unreviewed_boundary_holds(self):
        for field,value in [('sourceCanonicalSha256','0'*64),('verdict','hold'),('ownedUnitIds',['chapter']),('additionalContextUnitIds',['absent'])]:
            review={**self.review,field:value}
            with self.assertRaises(ValueError):c.plan(self.source,['report'],review)
    def test_no_future_context_or_omitted_owned_units(self):
        self.source['units'][0]['contextIds']=['report']
        review={**self.review,'ownedUnitIds':['book']}
        with self.assertRaises(ValueError):c.plan(self.source,['book'],review)
        with self.assertRaises(ValueError):c.plan(self.source,['book','report'],{**review,'ownedUnitIds':['book','report']})
    def test_cross_authority_reference_holds(self):
        self.source['units'][-1]['contextIds'].append('other-book')
        with self.assertRaises(ValueError):c.plan(self.source,['report'],self.review)
    def test_old_name_history_and_renderings_cannot_be_repurposed(self):
        ledger={'version':2,'identities':[{'id':'synthetic','english':'Synthetic','arabicForms':['A'],'renderings':[{'arabic':'A','english':'Synthetic'}]}],'decisions':[]}
        new=copy.deepcopy(ledger);new['identities'][0]['arabicForms'].append('B');new['identities'][0]['renderings'].append({'arabic':'B','english':'Short'})
        c.validate_extension(ledger,new)
        new['identities'][0]['renderings'][0]['english']='Changed'
        with self.assertRaises(ValueError):c.validate_extension(ledger,new)
    def test_carry_is_reuse_not_new_translation_or_new_isnad(self):
        frozen={'id':'book','arabic':'SYNTHETIC BOOK','english':'Synthetic book.','formulaTargets':[]}
        graph={'id':'book','nodes':[]}
        m={'version':1,'kind':'private-continued-context-v1','ownedUnitIds':['report'],'contextUnitIds':['book'],'inherited':[{'unitId':'book','record':{'translation':frozen,'structure':graph}}]}
        output={'units':[copy.deepcopy(frozen),{'id':'report','english':'Invented event.','formulaTargets':[]}]}
        self.assertEqual([x['id'] for x in c.validate_carried(m,output,{'units':[graph,{'id':'report'}]})],['report'])
        output['units'][0]['english']='Rewritten book.'
        with self.assertRaises(ValueError):c.validate_carried(m,output)
class ContinuedBindingTests(unittest.TestCase):
    def setUp(self):
        # Reuse the established synthetic host/receipt builder, without running
        # or inheriting its unrelated test methods.
        self.case=fixtures.ManifestTests('test_valid_manifest_and_hash_drift');self.case.setUp();self.addCleanup(self.case.doCleanups)
        case=self.case
        case.source['units'][0]['contextIds']=[]
        case.ledger={'version':2,'identities':[{**v,'english':v['id'],'renderings':[{'arabic':a,'english':v['id']} for a in v['arabicForms']]} for v in case.ledger['identities']],'decisions':[]}
        case.rewrite('source',case.source);case.rewrite('ledger',case.ledger)
        case.translation['sourceSha256']=h.file_hash(case.paths['source']);case.translation['units'][0]['formulaTargets']=[]
        case.rewrite('translation',case.translation)
        for prefix,stage in [('extraction','extraction'),('audit','structure-audit')]:
            input_hash=h.extraction_input_hash(case.paths['source'],case.paths['ledger']) if prefix=='extraction' else h.audit_input_hash(case.paths['source'],case.paths['translation'],case.paths['structure'],case.paths['ledger'])
            host=h.read(case.paths[prefix+'Host']);host['inputSha256']=input_hash;case.rewrite(prefix+'Host',host)
            receipt=h.read(case.paths[prefix+'Receipt']);receipt['inputSha256']=input_hash;receipt['hostCaptureSha256']=h.file_hash(case.paths[prefix+'Host']);case.rewrite(prefix+'Receipt',receipt)
        self.manifest=case.root/'.runtime/companion.json';h.write_new(self.manifest,h.build_manifest(case.paths))
        source={'units':[case.source['units'][0],{'id':'next','kind':'report','arabic':'INVENTED NEXT EVENT','contextIds':[]}],'exclusions':[]}
        self.source=case.root/'.runtime/qualified.json';h.write_new(self.source,source)
        self.cut=case.root/'.runtime/cut.json';h.write_new(self.cut,{'version':1,'verdict':'pass','sourceCanonicalSha256':c.digest(source),'ownedUnitIds':['next'],'additionalContextUnitIds':['synthetic-unit'],'detail':'Synthetic event narrative continuation.'})
    def bind(self):return c.bind_context(self.source,['next'],self.cut,[self.manifest],self.case.paths['ledger'])
    def test_real_companion_validation_binds_inherited_context(self):
        source,manifest=self.bind()
        self.assertEqual([u['id'] for u in source['units']],['synthetic-unit','next'])
        self.assertEqual(manifest['ownedUnitIds'],['next']);self.assertEqual(manifest['contextUnitIds'],['synthetic-unit'])
        self.assertEqual(manifest['inherited'][0]['record']['translation'],self.case.translation['units'][0])
    def test_stale_companion_cannot_be_used_for_carry(self):
        self.case.paths['translation'].write_text('{}',encoding='utf-8')
        with self.assertRaises(ValueError):self.bind()
    def test_missing_context_and_changed_name_mapping_hold_binding(self):
        with self.assertRaises(ValueError):c.bind_context(self.source,['next'],self.cut,[],self.case.paths['ledger'])
        ledger=copy.deepcopy(self.case.ledger);ledger['identities'][0]['english']='Repurposed'
        newer=self.case.root/'.runtime/repurposed.json';h.write_new(newer,ledger)
        with self.assertRaises(ValueError):c.bind_context(self.source,['next'],self.cut,[self.manifest],newer)

if __name__=='__main__':unittest.main()
