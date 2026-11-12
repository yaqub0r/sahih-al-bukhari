"""Synthetic title alignments only; no book text, ledger or private evidence."""
import copy
import json
import tempfile
import unittest
import subprocess
import sys
from contextlib import ExitStack
from unittest.mock import patch
from pathlib import Path
from scripts import hadith_structure as h
from scripts import hadith_supplements_v1 as v1
from scripts import hadith_supplements_v2 as v2
from scripts import release_distribution as d


class NamesSupplementV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = {'units':[{'id':'synthetic-one','kind':'report','arabic':'سنا'}, {'id':'synthetic-two','kind':'report','arabic':'نور'}, {'id':'synthetic-unaffected','kind':'report','arabic':'برد'}]}
        self.translation = {'units':[{'id':'synthetic-one','english':'His guide welcomes a guest.'}, {'id':'synthetic-two','english':'His teacher and guide greet a guest.'}, {'id':'synthetic-unaffected','english':'Invented unaffected sentence.'}]}
        self.ledger = {'version':2,'identities':[{'id':'synthetic-guide','english':'His Guide','arabicForms':['سنا','نور'],'renderings':[{'arabic':a,'english':'His Guide'} for a in ['سنا','نور']]}, {'id':'synthetic-other','english':'Other','arabicForms':['برد'],'renderings':[{'arabic':'برد','english':'Other'}]}]}
        self.graph = {'version':1,'units':[]}
        for i,unit in enumerate(self.source['units']):
            n=len(unit['arabic'])
            self.graph['units'].append({'id':unit['id'],'sha256':d.sha(unit['arabic'].encode()),'segments':[{'start':0,'end':n,'kind':'isnad'}],'nodes':[{'id':'n','kind':'narrator','start':0,'end':n,'nameId':'synthetic-guide' if i<2 else 'synthetic-other','status':'resolved','note':'Synthetic occurrence.'}],'edges':[],'paths':[{'id':'p','kind':'primary','nodeIds':['n'],'edgeIds':[],'status':'complete','note':'Synthetic path.'}],'reports':[{'id':'r','start':0,'end':n,'pathIds':['p'],'status':'complete','note':'Synthetic report.'}],'status':'complete','note':'Synthetic fixture.'})
        for key,obj in [('source',self.source),('translation',self.translation),('ledger',self.ledger),('graph',self.graph)]:self.write(key,obj)
        self.inventory={'sourceSha256':self.hash('source'),'ledgerSha256':self.hash('ledger'),'alignmentMentions':[]};self.write('inventory',self.inventory)
        occurrences=[{'unitId':u['id'],'start':0,'end':len(u['arabic']),'arabic':u['arabic'],'nameId':'synthetic-guide'} for u in self.source['units'][:2]]
        self.source_supp={'version':1,'sourceSha256':self.hash('source'),'ledgerSha256':self.hash('ledger'),'baseInventorySha256':self.hash('inventory'),'localGraphSha256':self.hash('graph'),'addedNameOccurrences':occurrences,'contextualIsnads':[]};self.write('source_supp',self.source_supp)
        first={**occurrences[0],'englishStart':0,'englishEnd':9,'english':'His guide','rendering':'His Guide'}
        start=self.translation['units'][1]['english'].index('guide')
        second={**occurrences[1],'englishStart':start,'englishEnd':start+5,'english':'guide','rendering':'His Guide','sharedModifier':{'kind':'shared-possessive','englishStart':0,'englishEnd':3,'english':'His','reason':'Synthetic coordinated possessive scope independently reviewed.'}}
        self.names={'version':2,'sourceSupplementSha256':self.hash('source_supp'),'sourceSha256':self.hash('source'),'translationSha256':self.hash('translation'),'ledgerSha256':self.hash('ledger'),'addedNameAlignments':[first,second]}
        self.write('names',self.names)
    def path(self,name):return self.root/(name+'.json')
    def hash(self,name):return h.file_hash(self.path(name))
    def write(self,name,obj):self.path(name).write_text(json.dumps(obj,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    def validate(self):return v2.validate_names_supplement(self.names,self.path('source_supp'),self.path('source'),self.path('translation'),self.path('ledger'))
    def compile(self,source_proof=None,names_proof=None):
        self.write('names',self.names)
        return v2.compile_supplement(self.path('source_supp'),self.path('names'),self.path('source'),self.path('translation'),self.path('ledger'),self.path('inventory'),self.path('graph'),{'captured':'synthetic-source'} if source_proof is None else source_proof,{'captured':'synthetic-names'} if names_proof is None else names_proof)
    def test_exact_case_and_shared_possessive_preserve_frozen_inputs(self):
        before={name:self.path(name).read_bytes() for name in ['source','translation','ledger','inventory','graph','source_supp']}
        self.assertIs(self.validate(),self.names)
        self.compile()
        self.assertEqual(before,{name:self.path(name).read_bytes() for name in before})
    def test_canonical_rendering_is_exact_registered_pair(self):
        for rendering in ['His guide','HIS GUIDE','His Leader','guide']:
            self.names['addedNameAlignments'][0]['rendering']=rendering
            with self.subTest(rendering=rendering),self.assertRaises(ValueError):self.validate()
    def test_literal_is_exact_even_when_casefold_equivalent(self):
        self.names['addedNameAlignments'][0]['english']='His Guide'
        with self.assertRaisesRegex(ValueError,'literal'):self.validate()
    def test_no_lexical_rewrite_article_or_unrecorded_drop(self):
        original=copy.deepcopy(self.names)
        for text in ['His leader','the guide','guide','His  guide','His guide!']:
            self.names=copy.deepcopy(original);self.translation['units'][0]['english']=text
            self.write('translation',self.translation);self.names['translationSha256']=self.hash('translation')
            self.names['addedNameAlignments'][0].update(english=text,englishStart=0,englishEnd=len(text))
            with self.subTest(text=text),self.assertRaises(ValueError):self.validate()
    def test_shared_modifier_is_mandatory_for_noncontiguous_rendering(self):
        del self.names['addedNameAlignments'][1]['sharedModifier']
        with self.assertRaises(ValueError):self.validate()
    def test_modifier_role_reason_and_closed_shape(self):
        original=copy.deepcopy(self.names)
        for key,value in [('kind','shared-article'),('reason',''),('reason',None),('extra','private')]:
            self.names=copy.deepcopy(original);self.names['addedNameAlignments'][1]['sharedModifier'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.validate()
    def test_modifier_exact_span_bounds_and_earlier_nonoverlap(self):
        original=copy.deepcopy(self.names)
        for values in [{'englishStart':True},{'englishEnd':999},{'englishStart':-1},{'englishEnd':0},{'english':'his'},{'englishStart':16,'englishEnd':21,'english':'guide'}]:
            self.names=copy.deepcopy(original);self.names['addedNameAlignments'][1]['sharedModifier'].update(values)
            with self.subTest(values=values),self.assertRaises(ValueError):self.validate()
        # A later literal possessive is disallowed even with valid exact spans.
        self.names=copy.deepcopy(original);text='guide and His';self.translation['units'][1]['english']=text;self.write('translation',self.translation);self.names['translationSha256']=self.hash('translation')
        row=self.names['addedNameAlignments'][1];row.update(englishStart=0,englishEnd=5);row['sharedModifier'].update(englishStart=10,englishEnd=13)
        with self.assertRaisesRegex(ValueError,'precede'):self.validate()
    def test_only_supported_single_possessive_words(self):
        original=copy.deepcopy(self.names)
        for word in ['the','a','this','His own','His ','their own']:
            self.names=copy.deepcopy(original);text=word+' teacher and guide';self.translation['units'][1]['english']=text;self.write('translation',self.translation);self.names['translationSha256']=self.hash('translation')
            row=self.names['addedNameAlignments'][1];start=text.index('guide');row.update(englishStart=start,englishEnd=start+5);row['sharedModifier'].update(english=word,englishStart=0,englishEnd=len(word))
            with self.subTest(word=word),self.assertRaises(ValueError):self.validate()
    def test_modifier_cannot_be_inside_unicode_word(self):
        original=copy.deepcopy(self.names)
        cases=[('This teacher and guide',1,4),('history teacher and guide',0,3),('éHis teacher and guide',1,4),('\u0301His teacher and guide',1,4),('His\u0301 teacher and guide',0,3),('1His teacher and guide',1,4),('His2 teacher and guide',0,3),('_His teacher and guide',1,4),('His_ teacher and guide',0,3)]
        for text,start,end in cases:
            self.names=copy.deepcopy(original);self.translation['units'][1]['english']=text;self.write('translation',self.translation);self.names['translationSha256']=self.hash('translation')
            row=self.names['addedNameAlignments'][1];a=text.index('guide');row.update(englishStart=a,englishEnd=a+5)
            row['sharedModifier'].update(english=text[start:end],englishStart=start,englishEnd=end)
            with self.subTest(text=text),self.assertRaisesRegex(ValueError,'whole word'):self.validate()
    def test_modifier_punctuation_boundaries_keep_exact_literal(self):
        original=copy.deepcopy(self.names)
        for text,word in [('(His) teacher and guide','His'),('“hIS,” teacher and guide','hIS'),('His: teacher and guide','His')]:
            self.names=copy.deepcopy(original);self.translation['units'][1]['english']=text;self.write('translation',self.translation);self.names['translationSha256']=self.hash('translation')
            row=self.names['addedNameAlignments'][1];a=text.index('guide');row.update(englishStart=a,englishEnd=a+5)
            start=text.index(word);row['sharedModifier'].update(english=word,englishStart=start,englishEnd=start+len(word))
            before=self.path('translation').read_bytes()
            with self.subTest(text=text):self.validate()
            self.assertEqual(self.path('translation').read_bytes(),before)
    def test_all_allowed_possessives_and_case_variants(self):
        for word in ['His','MY','your','Our','THEIR','her','Its']:
            with self.subTest(word=word):
                self.setUp();text=word+' teacher and guide';self.translation['units'][1]['english']=text;self.write('translation',self.translation)
                canonical=word+' Guide';self.ledger['identities'][0]['renderings'][1]['english']=canonical;self.write('ledger',self.ledger)
                self.source_supp['ledgerSha256']=self.hash('ledger');self.write('source_supp',self.source_supp)
                self.names.update(translationSha256=self.hash('translation'),ledgerSha256=self.hash('ledger'),sourceSupplementSha256=self.hash('source_supp'))
                row=self.names['addedNameAlignments'][1];start=text.index('guide');row.update(englishStart=start,englishEnd=start+5,rendering=canonical);row['sharedModifier'].update(english=word,englishEnd=len(word))
                self.validate()
    def test_duplicate_missing_extra_and_wrong_source_occurrence(self):
        original=copy.deepcopy(self.names)
        for rows in [original['addedNameAlignments']*2,original['addedNameAlignments'][:1],[]]:
            self.names=copy.deepcopy(original);self.names['addedNameAlignments']=rows
            with self.assertRaises(ValueError):self.validate()
        for key,value in [('nameId','unknown'),('arabic','other'),('end',999),('start',True),('unitId','outside')]:
            self.names=copy.deepcopy(original);self.names['addedNameAlignments'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate()
    def test_version_and_all_raw_bindings(self):
        for key,value in [('version',1),('version',True),('version',3),('sourceSupplementSha256','f'*64),('sourceSha256','f'*64),('translationSha256','f'*64),('ledgerSha256','f'*64),('unexpected','no')]:
            changed=copy.deepcopy(self.names);changed[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):v2.validate_names_supplement(changed,self.path('source_supp'),self.path('source'),self.path('translation'),self.path('ledger'))
    def test_compiled_lossless_rows_raw_and_proof_hashes_and_no_unaffected_row(self):
        compiled=self.compile()
        self.assertEqual(set(compiled),set('version sourceSupplementSha256 namesSupplementSha256 sourceProofSha256 namesProofSha256 units'.split()))
        self.assertEqual(compiled['version'],2)
        self.assertEqual(compiled['sourceSupplementSha256'],self.hash('source_supp'));self.assertEqual(compiled['namesSupplementSha256'],self.hash('names'))
        self.assertEqual(compiled['sourceProofSha256'],d.digest({'captured':'synthetic-source'}));self.assertEqual(compiled['namesProofSha256'],d.digest({'captured':'synthetic-names'}))
        self.assertEqual([r['unitId'] for r in compiled['units']],['synthetic-one','synthetic-two'])
        self.assertEqual([r['addedNameAlignments'][0] for r in compiled['units']],self.names['addedNameAlignments'])
        self.assertEqual(compiled['units'][1]['addedNameAlignments'][0]['sharedModifier'],self.names['addedNameAlignments'][1]['sharedModifier'])
        compiled['units'][0]['addedNameAlignments'][0]['english']='changed'
        self.assertEqual(self.names['addedNameAlignments'][0]['english'],'His guide')
    def test_empty_proofs_rejected_and_different_proof_changes_only_bound_hash(self):
        for source,names in [({}, {'capture':1}),({'capture':1},{}),([],{'capture':1})]:
            with self.assertRaises(ValueError):self.compile(source,names)
        first=self.compile();second=self.compile(names_proof={'captured':'different'})
        self.assertNotEqual(first['namesProofSha256'],second['namesProofSha256']);self.assertEqual(first['units'],second['units'])
    def test_legacy_source_validation_is_exact_alias(self):
        self.assertIs(v2.validate_source_supplement,v1.validate_source_supplement)
        self.source_supp['localGraphSha256']='f'*64;self.write('source_supp',self.source_supp);self.names['sourceSupplementSha256']=self.hash('source_supp')
        with self.assertRaisesRegex(ValueError,'localGraphSha256'):self.compile()
    def test_stale_english_or_source_supplement_raw_bytes_fail(self):
        self.path('translation').write_text('changed',encoding='utf-8')
        with self.assertRaises(ValueError):self.validate()
        self.write('translation',self.translation);self.path('source_supp').write_text(json.dumps(self.source_supp,indent=2),encoding='utf-8')
        with self.assertRaises(ValueError):self.validate()


class ProjectionAndProducerV2Tests(unittest.TestCase):
    def setUp(self):
        from tests.test_hadith_supplements_v1 import fixture
        self.expected=fixture()
        self.records=[{k:v for k,v in r.items() if k!='contextualIsnad'} for r in self.expected]
        self.compiled={'version':2,'sourceSupplementSha256':'a'*64,'namesSupplementSha256':'b'*64,'sourceProofSha256':d.digest({'capture':'source'}),'namesProofSha256':d.digest({'capture':'names'}),'units':[{'unitId':self.records[1]['sourceUnitId'],'addedNameOccurrences':[{'privatePath':'.runtime/never-public'}],'addedNameAlignments':[{'sharedModifier':{'reason':'PRIVATE-MODIFIER'},'privateProof':'PRIVATE-PROOF'}],'contextualIsnad':copy.deepcopy(self.expected[1]['contextualIsnad'])}]}
    def gate(self):
        return {'book':{'private':'book'},'compiled':copy.deepcopy(self.compiled),'semanticActors':['source-reviewer','names-reviewer'],'sourceProof':{'capture':'source'},'namesProof':{'capture':'names'}}
    def test_v2_projection_preserves_real_artifact_and_only_projects_context(self):
        before=copy.deepcopy(self.compiled);records_before=copy.deepcopy(self.records)
        result=v2.project_contextual_isnads(self.records,self.compiled)
        self.assertEqual(result,self.expected)
        self.assertEqual(self.compiled,before);self.assertEqual(self.records,records_before)
        serialized=json.dumps(result)
        for private in ['never-public','PRIVATE-MODIFIER','PRIVATE-PROOF','sourceProofSha256','addedNameAlignments','addedNameOccurrences']:
            self.assertNotIn(private,serialized)
        self.assertEqual(d.digest(self.compiled),d.digest(before))
    def test_legacy_rejects_real_v2_and_wrapper_rejects_v1(self):
        with self.assertRaises(ValueError):v1.project_contextual_isnads(self.records,self.compiled)
        for version in [1,True,3]:
            changed={**self.compiled,'version':version}
            with self.subTest(version=version),self.assertRaises(ValueError):v2.project_contextual_isnads(self.records,changed)
    def test_projection_closed_keys_hashes_duplicates_and_private_arrays(self):
        original=copy.deepcopy(self.compiled)
        changes=[lambda c:c.update(privatePath='forbidden'),lambda c:c['units'][0].update(privatePath='forbidden'),lambda c:c['units'].append(copy.deepcopy(c['units'][0])),lambda c:c['units'][0].update(addedNameAlignments={}),lambda c:c['units'][0].update(unitId='outside')]
        for key in ['sourceSupplementSha256','namesSupplementSha256','sourceProofSha256','namesProofSha256']:
            changes.append(lambda c,key=key:c.update({key:'not-a-hash'}))
        for mutate in changes:
            changed=copy.deepcopy(original);mutate(changed)
            with self.assertRaises(ValueError):v2.project_contextual_isnads(self.records,changed)
        self.assertEqual(self.compiled,original)
    def test_producer3_rejects_proof_drift_or_wrong_compiled_version_before_admission(self):
        from scripts import prefix_release_v3 as producer
        for key,value in [('sourceProofSha256','f'*64),('namesProofSha256','f'*64),('version',1),('version',True)]:
            gate=self.gate();gate['compiled'][key]=value
            with patch.object(producer.c,'admitted_cohort') as collector,self.subTest(key=key),self.assertRaises(ValueError):
                producer.prepare(None,None,None,None,gate)
            collector.assert_not_called()
    def test_producer3_cli_fails_closed(self):
        root=Path(__file__).resolve().parents[1]
        run=subprocess.run([sys.executable,str(root/'scripts/prefix_release_v3.py')],cwd=root,capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0)
        self.assertIn('authenticated B6 book admission must run before prepare()',run.stderr)
        self.assertNotIn('Traceback',run.stderr)
    def test_producer3_sidecar_binds_actual_v2_not_projection_view(self):
        from scripts import prefix_release_v3 as producer
        from tests.test_bukhari_distribution import proposal
        previous=proposal();previous['records']=self.records
        policy={'authoritySha256':'a'*64,'inventorySha256':'a'*64,'previousProposalSha256':d.digest(previous),'previousReleaseId':previous['releaseId'],'sourceUnits':[{'sourceUnitId':r['sourceUnitId'],'sourceOrdinal':r['sourceOrdinal']} for r in self.records],'targetReleaseId':'synthetic-next','title':'Synthetic next','scope':{'numberedReportCount':2},'rightsDecisionId':'synthetic-rights','fullAdmissionSha256':'f'*64}
        gate=self.gate();before=copy.deepcopy(gate);written={}
        with ExitStack() as stack:
            def patched(obj,name,*args,**kwargs):return stack.enter_context(patch.object(obj,name,*args,**kwargs))
            patched(producer.h,'private',side_effect=lambda p:Path(p))
            patched(producer.a,'load_policy',return_value=policy)
            patched(producer.d,'read',side_effect=lambda p:previous if 'proposals' in str(p) else {'sourceUnits':policy['sourceUnits']})
            patched(producer.h,'file_hash',return_value='a'*64)
            patched(producer.h,'read',return_value=[{'synthetic':'cohort'}])
            patched(producer.legacy,'derive_authority',return_value=({'units':[]},{}))
            patched(producer.legacy,'validate_entries')
            patched(producer.c,'private_path',side_effect=lambda p:Path(p))
            collector=patched(producer.c,'admitted_cohort',return_value={})
            patched(producer.c,'merge_owned',return_value=self.records)
            patched(producer.d,'load_contract',return_value=({},None))
            validator=patched(producer.d,'validate_proposal')
            patched(producer.a,'registration',return_value={'synthetic':'registration'})
            patched(producer.h,'write_new',side_effect=lambda p,obj:written.update({Path(p).name:copy.deepcopy(obj)}))
            result=producer.prepare('authority','inventory','cohorts','synthetic-proposal.json',gate)
            collector.assert_called_once();validator.assert_called_once()
        self.assertEqual(result['records'],self.expected)
        sidecar=written['synthetic-proposal-private-admission.json']
        self.assertEqual(sidecar['version'],3)
        self.assertEqual(sidecar['bookSupplementSha256'],d.digest(self.compiled))
        self.assertNotEqual(sidecar['bookSupplementSha256'],d.digest({**self.compiled,'version':1}))
        self.assertEqual(sidecar['sourceProofSha256'],self.compiled['sourceProofSha256'])
        self.assertEqual(sidecar['namesProofSha256'],self.compiled['namesProofSha256'])
        self.assertEqual(gate,before)


if __name__ == '__main__':unittest.main()
