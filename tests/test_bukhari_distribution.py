"""Synthetic hadith public projection tests; no real source or translation."""
import copy,hashlib,unittest
from pathlib import Path
from scripts import release_distribution as d
from tests.test_hadith_structure import fixture
ROOT=Path(__file__).resolve().parents[1]

def proposal():
    source,graph,ledger=fixture();s=source['units'][0];g=graph['units'][0];a=s['arabic']
    r={'sourceUnitId':'bukhari-l999999','sourceOrdinal':1,'bookSection':'opening','printedHadithNumber':1,'kind':'report','arabic':a,'english':'Invented test event only.','arabicSha256':g['sha256'],'humanReview':'unreviewed','machineState':'agent_complete','segments':[{**v,'arabic':a[v['start']:v['end']]} for v in g['segments']],'isnad':{k:copy.deepcopy(g[k]) for k in ['nodes','edges','paths','reports','status','note']},'uncertainties':[]}
    for n in r['isnad']['nodes']:n['arabic']=a[n['start']:n['end']]
    for e in r['isnad']['edges']:e['arabicWording']=a[e['start']:e['end']]
    p=d.read(ROOT/'tests/fixtures/distribution/proposal.json');p.update(bookId='sahih-al-bukhari',records=[r]);p['scope'].update(includedUnitIds=[r['sourceUnitId']],numberedReportCount=1)
    return p

class HadithDistributionTests(unittest.TestCase):
    def setUp(self):
        self.config=d.read(ROOT/'release/distribution.config.json');self.schema,self.adapter=d.load_contract(ROOT,self.config);self.proposal=proposal();self.r=self.proposal['records'][0]
    def validate(self):d.validate_proposal(self.proposal,self.config,self.schema,self.adapter)
    def test_synthetic_hadith_public_contract(self):self.validate()
    def test_unknown_nested_field_rejected(self):
        self.r['isnad']['nodes'][0]['evidence']='private'
        with self.assertRaises(d.ReleaseError):self.validate()
    def test_exact_arabic_occurrence_required(self):
        for part,key in [('nodes','arabic'),('edges','arabicWording')]:
            before=self.r['isnad'][part][0][key];self.r['isnad'][part][0][key]='changed'
            with self.assertRaises(ValueError):self.validate()
            self.r['isnad'][part][0][key]=before
    def test_broken_order_or_branch_rejected(self):
        self.r['isnad']['paths'][0]['nodeIds'].reverse()
        with self.assertRaises(ValueError):self.validate()
    def test_missing_or_fabricated_links_not_connected(self):
        g=self.r['isnad'];g['nodes'][0].update(kind='gap',nameId=None,status='unresolved')
        with self.assertRaises(ValueError):self.validate()
        g['edges'][0]['mode']='suspended';g['paths'][0]['status']='uncertain';g['reports'][0]['status']='uncertain';g['status']='uncertain'
        with self.assertRaises(ValueError):self.validate()
        self.r['uncertainties']=[{'reportId':g['reports'][0]['id'],'category':'structure','summary':'Synthetic omitted link; number unknown.'}]
        self.validate()
    def test_missing_report_or_segmentation_rejected(self):
        self.r['isnad']['reports']=[]
        with self.assertRaises(ValueError):self.validate()
    def test_disclosure_cannot_point_to_missing_report(self):
        self.r['uncertainties']=[{'reportId':'missing','category':'structure','summary':'Invented'}]
        with self.assertRaises(ValueError):self.validate()
    def test_count_and_source_digest_must_agree(self):
        self.proposal['scope']['numberedReportCount']=2
        with self.assertRaises(ValueError):self.validate()
        self.proposal['scope']['numberedReportCount']=1;self.r['arabicSha256']='a'*64
        with self.assertRaises(ValueError):self.validate()

if __name__=='__main__':unittest.main()
