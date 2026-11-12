"""Entirely invented source/English records; no private book evidence."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from scripts import hadith_supplements_v1 as s
from scripts import release_distribution as d
from scripts import bukhari_isnad_adapter_v2 as local
from scripts import bukhari_prefix_release_adapter_v2 as prefix
from scripts import prefix_release_v2 as producer
ROOT = Path(__file__).resolve().parents[1]


def fixture():
    def node(nid, text, name, arabic):
        a = arabic.index(text)
        return {'id':nid,'kind':'narrator','start':a,'end':a+len(text),'nameId':name,'status':'resolved','note':'Invented source occurrence.','arabic':text}
    def edge(eid, a, b, text, arabic):
        pos = None if text is None else arabic.index(text)
        return {'id':eid,'from':a,'to':b,'start':pos,'end':None if pos is None else pos+len(text),'mode':'implicit' if pos is None else 'explicit','note':'Invented textual attribution.','arabicWording':text}
    def path(pid, ns, es):return {'id':pid,'kind':'primary','nodeIds':ns,'edgeIds':es,'status':'complete','note':'Invented path.'}
    def record(uid, ordinal, arabic, nodes, edges, paths):
        return {'sourceUnitId':uid,'sourceOrdinal':ordinal,'bookSection':'opening','printedHadithNumber':ordinal,'kind':'report','arabic':arabic,'english':'Invented: A B C D X.','arabicSha256':d.sha(arabic.encode()),'humanReview':'unreviewed','machineState':'agent_complete','segments':[{'start':0,'end':len(arabic),'kind':'isnad','arabic':arabic}],'isnad':{'nodes':nodes,'edges':edges,'paths':paths,'reports':[{'id':'r','start':0,'end':len(arabic),'pathIds':[p['id'] for p in paths],'status':'complete','note':'Invented envelope.'}],'status':'complete','note':'Synthetic only.'},'uncertainties':[]}
    a = 'A tells B and C. X'
    compiler = {'id':'compiler','kind':'compiler','start':None,'end':None,'nameId':None,'status':'implicit','note':'Implicit synthetic root.','arabic':None}
    first = record('bukhari-l990001',1,a,[compiler,node('a','A','synthetic-a',a),node('b','B','synthetic-b',a),node('c','C','synthetic-c',a)],[edge('root','compiler','a',None,a),edge('ab','a','b','tells',a),edge('ac','a','c','and',a)],[path('p1',['compiler','a','b'],['root','ab']),path('p2',['a','c'],['ac'])])
    b = 'قالا وقال D; synthetic prayer سمع الله لمن حمده. X'
    second = record('bukhari-l990002',2,b,[node('d','D','synthetic-d',b)],[],[path('p1',['d'],[])])
    second['contextualIsnad'] = {'version':1,'kind':'dual-source-continuation','currentArabicSha256':second['arabicSha256'],'antecedentUnitId':first['sourceUnitId'],'antecedentArabicSha256':first['arabicSha256'],'currentSourceNodeId':'d','cues':[{'role':'dual-speakers','start':0,'end':4,'arabic':'قالا'},{'role':'attribution','start':5,'end':9,'arabic':'وقال'}],'branches':[{'id':'left','antecedentNodeIds':['compiler','a','b'],'antecedentEdgeIds':['root','ab'],'currentSourceNodeId':'d','relation':'contextual-ascription'},{'id':'right','antecedentNodeIds':['compiler','a','c'],'antecedentEdgeIds':['root','ac'],'currentSourceNodeId':'d','relation':'contextual-ascription'}],'uncertainty':'Invented contextual ascription only; historical contact is not inferred.'}
    return [first,second]


class ContextTests(unittest.TestCase):
    def setUp(self):self.records = fixture()
    def validate(self):return s.validate_contextual_isnads(self.records)
    def test_dual_context_and_unchanged_v2_base(self):
        self.validate()
        schema = d.read(ROOT/'contracts/distribution-v3/hadith-record.schema.json');d.lint_schema(schema)
        for record in self.records:d.schema_check(schema,record)
        local.validate_records(self.records,{'scope':{'numberedReportCount':2}})
        old = d.read(ROOT/'contracts/distribution-v2/hadith-record.schema.json')
        d.schema_check(old,self.records[0])
        with self.assertRaises(ValueError):d.schema_check(old,self.records[1])
    def test_unknown_nested_fields_are_closed(self):
        schema = d.read(ROOT/'contracts/distribution-v3/hadith-record.schema.json')
        for part in [self.records[1]['contextualIsnad'],self.records[1]['contextualIsnad']['branches'][0],self.records[1]['contextualIsnad']['cues'][0]]:
            part['privatePath'] = '.runtime/never-public'
            with self.assertRaises(ValueError):d.schema_check(schema,self.records[1])
            del part['privatePath']
    def test_cross_record_pins_order_scope_and_current_reference(self):
        ctx = self.records[1]['contextualIsnad']
        for key,value in [('currentArabicSha256','a'*64),('antecedentArabicSha256','a'*64),('antecedentUnitId','outside'),('antecedentUnitId',self.records[1]['sourceUnitId']),('currentSourceNodeId','missing')]:
            before=ctx[key];ctx[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate()
            ctx[key]=before
        self.records[0]['sourceOrdinal']=3
        with self.assertRaises(ValueError):self.validate()
    def test_both_complete_branches_required_without_gap_or_identity_merge(self):
        original = copy.deepcopy(self.records)
        mutations = [lambda c:c['branches'].pop(),lambda c:c['branches'].append(copy.deepcopy(c['branches'][0])),lambda c:c['branches'][0].update(antecedentNodeIds=['a','b'],antecedentEdgeIds=['ab']),lambda c:c['branches'][0]['antecedentEdgeIds'].reverse(),lambda c:c['branches'][1].update(antecedentNodeIds=['compiler','a','b'],antecedentEdgeIds=['root','ab']),lambda c:c['branches'][0].update(relation='historical-receipt'),lambda c:c['branches'][0].update(currentSourceNodeId='a')]
        for mutate in mutations:
            self.records=copy.deepcopy(original);mutate(self.records[1]['contextualIsnad'])
            with self.assertRaises(ValueError):self.validate()
        for key,value in [('kind','gap'),('nameId',None),('status','unresolved')]:
            self.records=copy.deepcopy(original);self.records[0]['isnad']['nodes'][2][key]=value
            with self.assertRaises(ValueError):self.validate()
    def test_prayer_hearing_is_not_contextual_receipt_and_exact_cues_required(self):
        ctx=self.records[1]['contextualIsnad'];text=self.records[1]['arabic'];a=text.index('سمع')
        ctx['cues'][1].update(start=a,end=a+3,arabic='سمع')
        with self.assertRaises(ValueError):self.validate()
        self.records=fixture();self.records[1]['contextualIsnad']['cues'][0]['end']=3
        with self.assertRaises(ValueError):self.validate()
    def test_renderer_hydrates_chains_and_escapes_all_text(self):
        p={'title':'Synthetic <title>','rights':{},'sourceAuthority':{},'scope':{},'records':self.records}
        self.records[1]['contextualIsnad']['uncertainty']='<script>not executable</script>'
        text=d.reader(p).decode()
        self.assertIn('href="#bukhari-l990001"',text)
        self.assertIn('Contextual ascription:',text);self.assertIn('tells',text);self.assertIn('and',text)
        self.assertIn('&lt;script&gt;not executable&lt;/script&gt;',text)
        self.assertNotIn('<script>not executable</script>',text)
        self.assertEqual(text.count('<h4>'),2)
    def test_five_file_archive_determinism_and_reader_parity(self):
        from tests.test_bukhari_distribution import proposal
        p=proposal();p['records']=self.records;p['scope'].update(includedUnitIds=[r['sourceUnitId'] for r in self.records],numberedReportCount=2)
        config=d.read(ROOT/'release/distribution-prefix-v1.config.json');schema=d.read(ROOT/config['recordSchema'])
        def validate(records,proposal):
            local.validate_records(records,proposal);s.validate_contextual_isnads(records)
        adapter=SimpleNamespace(validate_records=validate)
        files=d.compile_files(p,config,schema,adapter,'a'*40)
        self.assertEqual(set(files),{'manifest.json','records.jsonl','record-schema.json','reader.html','release-closure.json'})
        self.assertEqual(files,d.compile_files(p,config,schema,adapter,'a'*40))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bundle=root/'bundle';bundle.mkdir()
            for name,data in files.items():(bundle/name).write_bytes(data)
            d.validate_directory(bundle,config,schema,adapter)
            for name in ['one.zip','two.zip']:d.archive_files(files,root/name)
            self.assertEqual((root/'one.zip').read_bytes(),(root/'two.zip').read_bytes())
            (bundle/'reader.html').write_bytes(files['reader.html'].replace(b'Contextual ascription:',b'Hidden contextual chain:'))
            with self.assertRaisesRegex(ValueError,'reader.html'):d.validate_directory(bundle,config,schema,adapter)
    def test_schema_three_is_additive_and_old_base_defs_identical(self):
        old=d.read(ROOT/'contracts/distribution-v2/hadith-record.schema.json');new=d.read(ROOT/'contracts/distribution-v3/hadith-record.schema.json')
        self.assertEqual(old['required'],new['required'])
        for name,value in old['properties'].items():self.assertEqual(value,new['properties'][name])
        for name,value in old['$defs'].items():self.assertEqual(value,new['$defs'][name])
        self.assertEqual(set(new['properties'])-set(old['properties']),{'contextualIsnad'})
    def test_required_known_context_cannot_be_base_only(self):
        records=[{k:v for k,v in r.items() if k!='contextualIsnad'} for r in self.records]
        records[1]['sourceUnitId']=prefix.REQUIRED_CONTEXT
        with patch.object(prefix.base,'validate_candidate'),self.assertRaisesRegex(ValueError,'base-only'):
            prefix.validate_candidate(records,{'records':records})
    def test_ungated_producer_result_rejected_before_collection(self):
        with self.assertRaises(ValueError):producer.prepare(None,None,None,None,{})


class SupplementTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.records=fixture()
        self.source={'units':[{'id':r['sourceUnitId'],'kind':r['kind'],'arabic':r['arabic']} for r in self.records]}
        self.graph=copy.deepcopy({'version':1,'units':[{'id':r['sourceUnitId'],'sha256':r['arabicSha256'],'segments':[{k:v for k,v in x.items() if k!='arabic'} for x in r['segments']],**r['isnad']} for r in self.records]})
        for g in self.graph['units']:
            for n in g['nodes']:n.pop('arabic')
            for e in g['edges']:e.pop('arabicWording')
        self.ledger={'version':2,'identities':[{'id':'synthetic-'+x.lower(),'english':x,'arabicForms':[x],'renderings':[{'arabic':x,'english':x}]} for x in 'ABCDX']}
        self.translation={'units':[{'id':r['sourceUnitId'],'english':r['english']} for r in self.records]}
        self.inventory={'sourceSha256':self.write('source',self.source),'ledgerSha256':self.write('ledger',self.ledger),'alignmentMentions':[]}
        self.write('translation',self.translation);self.write('inventory',self.inventory);self.write('graph',self.graph)
        first=self.records[0];pos=first['arabic'].index('X')
        self.source_supp={'version':1,'sourceSha256':self.hash('source'),'ledgerSha256':self.hash('ledger'),'baseInventorySha256':self.hash('inventory'),'localGraphSha256':self.hash('graph'),'addedNameOccurrences':[{'unitId':first['sourceUnitId'],'start':pos,'end':pos+1,'arabic':'X','nameId':'synthetic-x'}],'contextualIsnads':[{'unitId':self.records[1]['sourceUnitId'],'contextualIsnad':self.records[1]['contextualIsnad']}]}
        self.write('source_supp',self.source_supp);english=first['english'];pos=english.index('X')
        self.names={'version':1,'sourceSupplementSha256':self.hash('source_supp'),'sourceSha256':self.hash('source'),'translationSha256':self.hash('translation'),'ledgerSha256':self.hash('ledger'),'addedNameAlignments':[{**self.source_supp['addedNameOccurrences'][0],'englishStart':pos,'englishEnd':pos+1,'english':'X','rendering':'X'}]}
        self.write('names',self.names)
    def path(self,name):return self.root/(name+'.json')
    def hash(self,name):return d.sha(self.path(name).read_bytes())
    def write(self,name,obj):
        self.path(name).write_text(json.dumps(obj,ensure_ascii=False)+'\n',encoding='utf-8');return self.hash(name)
    def validate_source(self):return s.validate_source_supplement(self.source_supp,self.path('source'),self.path('ledger'),self.path('inventory'),self.path('graph'))
    def validate_names(self):return s.validate_names_supplement(self.names,self.path('source_supp'),self.path('source'),self.path('translation'),self.path('ledger'))
    def test_compiles_lossless_rows_and_allowlist_projects_context_only(self):
        self.validate_source();self.validate_names()
        compiled=s.compile_supplement(self.path('source_supp'),self.path('names'),self.path('source'),self.path('translation'),self.path('ledger'),self.path('inventory'),self.path('graph'),{'captured':'source-review'},{'captured':'names-review'})
        self.assertEqual(compiled['units'][0]['addedNameOccurrences'],self.source_supp['addedNameOccurrences'])
        self.assertEqual(compiled['units'][0]['addedNameAlignments'],self.names['addedNameAlignments'])
        base=[{k:v for k,v in r.items() if k!='contextualIsnad'} for r in self.records]
        projected=s.project_contextual_isnads(base,compiled)
        self.assertEqual(projected,self.records);self.assertEqual(projected[0],base[0]);self.assertNotIn('contextualIsnad',base[1])
        compiled['privatePath']='forbidden'
        with self.assertRaises(ValueError):s.project_contextual_isnads(base,compiled)
    def test_raw_pins_and_source_spans_names_and_duplicates(self):
        original=copy.deepcopy(self.source_supp)
        for key in ['sourceSha256','ledgerSha256','baseInventorySha256','localGraphSha256']:
            self.source_supp={**original,key:'f'*64}
            with self.assertRaises(ValueError):self.validate_source()
        for key,value in [('nameId','invented'),('arabic','Y'),('start',True),('end',999),('private','hidden')]:
            self.source_supp=copy.deepcopy(original);self.source_supp['addedNameOccurrences'][0][key]=value
            with self.assertRaises(ValueError):self.validate_source()
        self.source_supp=copy.deepcopy(original);self.source_supp['addedNameOccurrences']*=2
        with self.assertRaises(ValueError):self.validate_source()
    def test_duplicate_existing_inventory_is_not_add_only(self):
        self.inventory['alignmentMentions']=self.source_supp['addedNameOccurrences'];self.write('inventory',self.inventory);self.source_supp['baseInventorySha256']=self.hash('inventory')
        with self.assertRaises(ValueError):self.validate_source()
    def test_names_exact_english_spans_rendering_and_full_inventory(self):
        original=copy.deepcopy(self.names)
        for key,value in [('english','Y'),('rendering','Y'),('englishStart',True),('englishEnd',999),('nameId','invented'),('arabic','Y')]:
            self.names=copy.deepcopy(original);self.names['addedNameAlignments'][0][key]=value
            with self.assertRaises(ValueError):self.validate_names()
        self.names=copy.deepcopy(original);self.names['addedNameAlignments']=[]
        with self.assertRaises(ValueError):self.validate_names()
        self.names=copy.deepcopy(original);self.names['addedNameAlignments']*=2
        with self.assertRaises(ValueError):self.validate_names()
    def test_immutable_translation_and_raw_source_supplement_drift(self):
        self.path('translation').write_text('changed',encoding='utf-8')
        with self.assertRaises(ValueError):self.validate_names()
        self.write('translation',self.translation);self.path('source_supp').write_text(json.dumps(self.source_supp,indent=2),encoding='utf-8')
        with self.assertRaises(ValueError):self.validate_names()


if __name__ == '__main__':unittest.main()
