"""Synthetic successor policy tests; no private source or stage evidence."""
import copy
import unittest
from unittest.mock import patch
from scripts import bukhari_friday_release_adapter_v1 as a
from scripts import friday_release_v1 as producer
from scripts import bukhari_release_adapter_v2 as source
from scripts import release_distribution as d
from tests.test_prefix_release import fixture


def friday_fixture():
    previous,old,full=fixture()
    records=copy.deepcopy(previous['records'])
    for i in range(1472,1580):
        row=copy.deepcopy(records[-1])
        row.update(sourceUnitId='bukhari-l'+str(900000+i),sourceOrdinal=i,bookSection='source-division-017',printedHadithNumber=i if i<=1535 else None)
        records.append(row)
    full['sourceUnits']=[{k:r[k] for k in ['sourceUnitId','sourceOrdinal','kind','printedHadithNumber','arabicSha256']} for r in records]+full['sourceUnits'][1579:]
    full['sourceDivisions']=full['sourceDivisions'][:16]+[{'number':17,'startOrdinal':1472,'endOrdinal':1579},{'number':18,'startOrdinal':1580,'endOrdinal':12059}]
    policy=copy.deepcopy(old)
    policy.update(previousProposalSha256=d.digest(previous),previousReleaseId=previous['releaseId'],fullAdmissionSha256=d.digest(full),targetReleaseId='bukhari-through-friday-working-3',rightsDecisionId='bukhari-through-friday-working-3-owner-authorized',totalUnits=1579,throughSourceDivision=17,sourceUnits=copy.deepcopy(full['sourceUnits'][:1579]),sourceDivisions=copy.deepcopy(full['sourceDivisions'][:17]),previousRecordDigests=[{'sourceUnitId':r['sourceUnitId'],'recordSha256':d.digest(r)} for r in previous['records']],title='Sahih al-Bukhari through Friday Prayer human-unreviewed',scope={'description':'Partial authority through 17. Later source divisions are excluded.','completeWork':False,'includedUnitIds':[r['sourceUnitId'] for r in records],'numberedReportCount':900})
    return previous,records,policy,full


class FridayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.previous,cls.records,cls.policy,cls.full=friday_fixture()
    def validate_policy(self,p=None,previous=None):
        return a.validate_policy(p or self.policy,self.full,d.digest(self.full),previous or self.previous)
    def test_exact_whole_friday_policy(self):self.validate_policy()
    def test_closed_scope_and_predecessor_pins(self):
        for key,value in [('totalUnits',1580),('throughSourceDivision',18),('previousProposalSha256','f'*64),('previousReleaseId','other'),('previousRecordDigests',self.policy['previousRecordDigests'][:110]),('sourceUnits',self.policy['sourceUnits'][:-1]),('sourceDivisions',self.policy['sourceDivisions'][:-1]),('extra',True)]:
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate_policy({**self.policy,key:value})
        for index in [0,110,1470]:
            p=copy.deepcopy(self.previous);p['records'][index]['english']='Changed predecessor'
            with self.subTest(index=index),self.assertRaises(ValueError):self.validate_policy(previous=p)
    def test_all_1471_complete_predecessor_records_frozen(self):
        source.validate_source_binding(self.records,self.policy)
        for index in [0,110,1470]:
            records=list(self.records);records[index]={**records[index],'english':'Changed'}
            with self.subTest(index=index),self.assertRaises(ValueError):source.validate_source_binding(records,self.policy)
    def test_new_only_exact_single_ownership(self):
        entry={'version':1,'sourceDivision':17,'runDirectory':'.runtime/synthetic','companionManifest':'.runtime/synthetic.json','continuedContext':None,'ownedUnitIds':[r['sourceUnitId'] for r in self.records[1471:]]}
        producer.validate_entries([entry],self.policy)
        for entries in [[],[entry,entry],[{**entry,'sourceDivision':16}],[{**entry,'ownedUnitIds':entry['ownedUnitIds'][1:]}],[{**entry,'ownedUnitIds':list(reversed(entry['ownedUnitIds']))}]]:
            with self.assertRaises(ValueError):producer.validate_entries(entries,self.policy)
    def test_registration_and_disabled_real_surface(self):
        proposal={'releaseId':self.policy['targetReleaseId']}
        registry={'version':1,'entries':[a.registration(proposal,self.policy)]}
        a.validate_registration(proposal,registry,self.policy)
        with self.assertRaises(ValueError):a.validate_registration(proposal,{'version':1,'entries':[]},self.policy)
        a.load_policy()
        config=d.read(a.ROOT/'release/distribution-friday-v1.config.json')
        if not config['publicationEnabled']:
            self.assertEqual(d.read(a.ROOT/a.REGISTRY),{'version':1,'entries':[]})
        self.assertEqual(config['contractId'],'sahih-al-bukhari-friday-distribution-1')
    def test_producer_rejects_ungated_input(self):
        with self.assertRaises(ValueError):producer.prepare(None,None,None,None,{})


if __name__=='__main__':unittest.main()

