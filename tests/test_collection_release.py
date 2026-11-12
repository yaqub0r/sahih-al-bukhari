"""Synthetic complete-release ownership and source-division guards."""
import copy,unittest,hashlib
from scripts import collection_release as c
from scripts.bukhari_release_adapter_v2 import validate_divisions,validate_source_binding,validate_registration
from scripts import release_distribution as d
from tests.test_bukhari_distribution import proposal

class CollectionOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.first=proposal()['records'][0]
        self.next=copy.deepcopy(self.first);self.next.update(sourceUnitId='bukhari-l999998',sourceOrdinal=2,arabic='INVENTED NEXT SOURCE',english='Invented next event.')
        self.authority={'units':[{'id':v['sourceUnitId'],'kind':v['kind'],'arabic':v['arabic']} for v in [self.first,self.next]]}
        self.cohort={'ownedUnitIds':[self.next['sourceUnitId']],'contextUnitIds':[self.first['sourceUnitId']],'records':[copy.deepcopy(self.first),copy.deepcopy(self.next)]}
    def test_complete_projection_reuses_context_without_extra_occurrence(self):
        rows=c.merge_owned(self.authority,[self.first],[self.cohort])
        self.assertEqual(rows,[self.first,self.next]);self.assertEqual(len(rows),2)
    def test_partial_collection_cannot_be_prepared_as_complete(self):
        with self.assertRaises(ValueError):c.merge_owned(self.authority,[self.first],[])
    def test_duplicate_ownership_and_context_overlap_rejected(self):
        with self.assertRaises(ValueError):c.merge_owned(self.authority,[self.first],[self.cohort,self.cohort])
        self.cohort['ownedUnitIds'].append(self.first['sourceUnitId'])
        with self.assertRaises(ValueError):c.merge_owned(self.authority,[self.first],[self.cohort])
    def test_changed_inherited_english_or_isnad_cannot_replace_canonical(self):
        for field,value in [('english','Changed inherited rendition'),('isnad',{'nodes':[]})]:
            cohort=copy.deepcopy(self.cohort);cohort['records'][0][field]=value
            with self.assertRaises(ValueError):c.merge_owned(self.authority,[self.first],[cohort])
    def test_new_source_order_and_review_status_must_be_exact(self):
        for field,value in [('sourceOrdinal',1),('arabic','Different source'),('humanReview','human-reviewed'),('machineState','draft')]:
            cohort=copy.deepcopy(self.cohort);cohort['records'][1][field]=value
            with self.assertRaises(ValueError):c.merge_owned(self.authority,[self.first],[cohort])
    def test_projection_cannot_hide_unowned_record_or_unknown_context(self):
        cohort=copy.deepcopy(self.cohort);cohort['contextUnitIds']=[]
        with self.assertRaises(ValueError):c.merge_owned(self.authority,[self.first],[cohort])
        cohort=copy.deepcopy(self.cohort);cohort['contextUnitIds']=['unavailable']
        with self.assertRaises(ValueError):c.merge_owned(self.authority,[self.first],[cohort])
    def test_public_uncertainty_of_prior_revision_is_not_silently_replaced(self):
        cohort=copy.deepcopy(self.cohort);cohort['records'][0]['uncertainties']=[{'reportId':None,'category':'translation','summary':'A later contextual audit wording.'}]
        rows=c.merge_owned(self.authority,[self.first],[cohort])
        self.assertEqual(rows[0]['uncertainties'],self.first['uncertainties'])

class CollectionDivisionTests(unittest.TestCase):
    def test_complete_division_mapping_and_gap_rejection(self):
        rows=[{'sourceOrdinal':1,'bookSection':'opening'},{'sourceOrdinal':2,'bookSection':'source-division-003'}]
        divisions=[{'number':1,'startOrdinal':1,'endOrdinal':1},{'number':3,'startOrdinal':2,'endOrdinal':2}]
        validate_divisions(rows,divisions,2)
        with self.assertRaises(ValueError):validate_divisions(rows[:1],divisions,2)
        rows[1]['bookSection']='faith'
        with self.assertRaises(ValueError):validate_divisions(rows,divisions,2)
    def test_overlapping_or_incomplete_division_policy_rejected(self):
        rows=[{'sourceOrdinal':1,'bookSection':'opening'}]
        with self.assertRaises(ValueError):validate_divisions(rows,[{'number':1,'startOrdinal':1,'endOrdinal':1},{'number':2,'startOrdinal':1,'endOrdinal':1}],1)
        with self.assertRaises(ValueError):validate_divisions(rows,[{'number':1,'startOrdinal':2,'endOrdinal':2}],1)
class ExactPublicAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.record=proposal()['records'][0]
        self.policy={'authoritySha256':'a'*64,'totalUnits':1,'sourceUnits':[{k:self.record[k] for k in ['sourceUnitId','sourceOrdinal','kind','arabicSha256','printedHadithNumber']}],'previousRecordDigests':[{'sourceUnitId':self.record['sourceUnitId'],'recordSha256':d.digest(self.record)}]}
    def test_frozen_source_predecessor_and_machine_review_state(self):
        validate_source_binding([self.record],self.policy)
        for field,value in [('sourceUnitId','bukhari-l888888'),('arabic','Different invented source'),('printedHadithNumber',2),('humanReview','human-reviewed'),('english','Replacement rendition'),('isnad',{'nodes':[]})]:
            changed={**self.record,field:value}
            with self.subTest(field=field),self.assertRaises(ValueError):validate_source_binding([changed],self.policy)
    def test_unregistered_or_changed_projection_cannot_compile(self):
        p=proposal();registry={'version':1,'entries':[]}
        with self.assertRaises(ValueError):validate_registration(p,registry,self.policy)
        registry['entries']=[{'releaseId':p['releaseId'],'proposalSha256':d.digest(p),'sourceAuthoritySha256':self.policy['authoritySha256'],'recordCount':1}]
        validate_registration(p,registry,self.policy)
        p['records'][0]['english']='Unreviewed replacement'
        with self.assertRaises(ValueError):validate_registration(p,registry,self.policy)

if __name__=='__main__':unittest.main()
