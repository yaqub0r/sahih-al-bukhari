"""Synthetic negative provenance-admission checks for release preparation."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from scripts import prepare_bukhari_release as p
from scripts import release_distribution as d

class SourceAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.authority={'units':[{'id':'synthetic-report','kind':'report','arabic':'INVENTED SOURCE'}]}
        self.inventory={'sourceSha256':'a'*64,'printedReportNumbers':[{'unitId':'synthetic-report','number':1}]}
        self.a=self.root/'authority.json';self.i=self.root/'inventory.json';self.m={k:self.root/(k+'.json') for k in ['opening','faith']}
        self.a.write_bytes(d.canonical(self.authority));self.i.write_bytes(d.canonical(self.inventory))
        for path in self.m.values():path.write_text('{}')
        self.admission={'version':1,'authoritySha256':p.h.file_hash(self.a),'inventorySha256':p.h.file_hash(self.i),'sourceArtifactSha256':'a'*64,'sourceRevision':'b'*40,'companionSha256':{k:p.h.file_hash(v) for k,v in self.m.items()}}
    def admit(self):return p.admitted_inputs(self.a,self.i,self.m,self.admission)
    def test_exact_frozen_inputs_admitted(self):self.assertEqual(self.admit(),(self.authority,self.inventory))
    def test_stale_authority_inventory_or_companion_rejected(self):
        for path in [self.a,self.i,*self.m.values()]:
            with self.subTest(path=path):
                before=path.read_bytes();path.write_bytes(before+b' ')
                with self.assertRaises(ValueError):self.admit()
                path.write_bytes(before)
    def test_inventory_upstream_must_agree(self):
        self.admission['sourceArtifactSha256']='c'*64
        with self.assertRaises(ValueError):self.admit()
    def test_duplicate_authority_or_inventory_units_rejected(self):
        self.authority['units']*=2;self.a.write_bytes(d.canonical(self.authority));self.admission['authoritySha256']=p.h.file_hash(self.a)
        with self.assertRaises(ValueError):self.admit()
        self.authority['units']=self.authority['units'][:1];self.a.write_bytes(d.canonical(self.authority));self.admission['authoritySha256']=p.h.file_hash(self.a)
        self.inventory['printedReportNumbers']*=2;self.i.write_bytes(d.canonical(self.inventory));self.admission['inventorySha256']=p.h.file_hash(self.i)
        with self.assertRaises(ValueError):self.admit()
    def test_inventory_cannot_describe_nonreport(self):
        self.authority['units'][0]['kind']='heading';self.a.write_bytes(d.canonical(self.authority));self.admission['authoritySha256']=p.h.file_hash(self.a)
        with self.assertRaises(ValueError):self.admit()

if __name__=='__main__':unittest.main()
