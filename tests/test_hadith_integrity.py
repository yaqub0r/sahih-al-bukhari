"""Synthetic regression tests for demonstrated graph completeness diagnostics."""
import copy,unittest
from scripts import hadith_integrity as q
from tests.test_hadith_structure import fixture
class HadithIntegrityTests(unittest.TestCase):
    def setUp(self):self.source,self.graph,self.ledger=fixture();self.unit=self.graph['units'][0]
    def test_existing_valid_structure_passes(self):q.validate(self.source,self.graph,self.ledger)
    def test_report_envelope_cannot_split_a_word(self):
        self.unit['reports'][0]['end']=23
        with self.assertRaises(ValueError):q.validate(self.source,self.graph)
    def test_shared_prefix_must_share_physical_edge(self):
        compiler={'id':'c','kind':'compiler','start':None,'end':None,'nameId':None,'status':'implicit','note':'Synthetic root'}
        self.unit['nodes'].extend([compiler,{**compiler,'id':'c2'}])
        edge={'id':'ca','from':'c','to':'a','start':2,'end':7,'mode':'explicit','note':'Synthetic prefix'}
        self.unit['edges'].extend([edge,{**edge,'id':'ca2','from':'c2'}])
        self.assertTrue(any(v['kind']=='duplicate-physical-transmission' for v in q.diagnostics(self.source,self.graph)))
    def test_coordinated_predicate_with_different_recipients_is_not_duplicate(self):
        self.unit['nodes'].append({'id':'c','kind':'narrator','start':20,'end':21,'nameId':'synthetic-c','status':'resolved','note':'Synthetic distinct receiver'})
        self.unit['edges'].append({**self.unit['edges'][0],'id':'ac','to':'c'})
        self.assertFalse(q.diagnostics(self.source,self.graph))
    def test_duplicate_printed_narrator_is_detected(self):
        self.unit['nodes'].append({**self.unit['nodes'][0],'id':'a-copy'})
        self.assertTrue(any(v['kind']=='duplicate-narrator-occurrence' for v in q.diagnostics(self.source,self.graph)))
    def test_cue_inventory_covers_internal_hearing_and_preserves_source(self):
        s={'units':[{'id':'synthetic','arabic':'سمعته أذناي وقال حفظت من فلان'}]};before=copy.deepcopy(s);inventory=q.cue_inventory(s)
        self.assertEqual([v['arabic'] for v in inventory['candidates']],['سمعته','وقال','حفظت'])
        self.assertEqual(s,before)
    def test_cue_review_requires_all_candidates_and_exact_graph(self):
        source={'units':[{'id':'synthetic','arabic':'قال'}]};graph={'version':1,'units':[{'id':'synthetic','segments':[{'start':0,'end':3,'kind':'comment'}],'nodes':[],'edges':[],'paths':[],'reports':[]}]};inventory=q.cue_inventory(source)
        review={'version':1,'inventorySha256':q.digest(inventory),'structureCanonicalSha256':q.digest(graph),'candidates':[{'id':inventory['candidates'][0]['id'],'classification':'authorial-comment','graphRefs':['segments:0'],'basis':'Synthetic author statement, not a transmission.'}],'limits':['Lexical inventory is not semantic completeness proof.']}
        q.validate_cue_review(source,graph,inventory,review)
        review['candidates']=[]
        with self.assertRaises(ValueError):q.validate_cue_review(source,graph,inventory,review)
if __name__=='__main__':unittest.main()
