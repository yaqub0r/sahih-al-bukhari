"""Synthetic whole-prefix guards; no production source content or private evidence."""
import copy,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from scripts import bukhari_prefix_release_adapter_v1 as a
from scripts import prefix_release_v1 as producer
from scripts import release_distribution as d
from tests.test_bukhari_distribution import proposal
ROOT=Path(__file__).resolve().parents[1]


def fixture():
    p=proposal();base=p['records'][0];rows=[]
    divisions=[{'number':1,'startOrdinal':1,'endOrdinal':11},{'number':2,'startOrdinal':12,'endOrdinal':110}]
    start=111
    for n in range(3,17):
        end=1471 if n==16 else start+96
        divisions.append({'number':n,'startOrdinal':start,'endOrdinal':end});start=end+1
    for i in range(1,1472):
        n=next(x['number'] for x in divisions if x['startOrdinal']<=i<=x['endOrdinal'])
        row=copy.deepcopy(base);row.update(sourceUnitId='bukhari-l'+str(900000+i),sourceOrdinal=i,printedHadithNumber=i if i<=836 else None,bookSection='opening' if n==1 else 'faith' if n==2 else 'source-division-'+str(n).zfill(3));rows.append(row)
    sources=[{k:v[k] for k in ['sourceUnitId','sourceOrdinal','kind','printedHadithNumber','arabicSha256']} for v in rows]
    full={'version':1,'authoritySha256':'a'*64,'inventorySha256':'b'*64,'sourceArtifactSha256':p['sourceAuthority']['artifactSha256'],'sourceRevision':p['sourceAuthority']['revision'],'previousProposalSha256':'c'*64,'previousReleaseId':'synthetic-prior','sourceAuthorityId':p['sourceAuthority']['id'],'totalUnits':12059,'sourceUnits':sources+[dict(sources[-1],sourceUnitId='bukhari-l'+str(900000+i),sourceOrdinal=i,printedHadithNumber=None) for i in range(1472,12060)],'sourceDivisions':divisions+[{'number':17,'startOrdinal':1472,'endOrdinal':12059}],'previousRecordDigests':[{'sourceUnitId':r['sourceUnitId'],'recordSha256':d.digest(r)} for r in rows[:110]]}
    policy={k:copy.deepcopy(v) for k,v in full.items() if k not in ['sourceUnits','sourceDivisions','totalUnits']}
    policy.update(fullAdmissionSha256=d.digest(full),targetReleaseId='bukhari-through-prayer-working-2',totalUnits=1471,throughSourceDivision=16,sourceUnits=sources,sourceDivisions=divisions,title='Sahih al-Bukhari through Description of Prayer human-unreviewed',scope={'description':'Partial authority through 16. Later source divisions are excluded.','completeWork':False,'includedUnitIds':[r['sourceUnitId'] for r in rows],'numberedReportCount':836},rightsDecisionId='bukhari-through-prayer-working-2-owner-authorized')
    p.update(releaseId=policy['targetReleaseId'],previousReleaseId=policy['previousReleaseId'],title=policy['title'],scope=copy.deepcopy(policy['scope']),records=rows)
    p['rights'].update(status='approved',originalContentLicense='CC-BY-4.0',decisionId=policy['rightsDecisionId'])
    return p,policy,full


class PrefixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.p,cls.policy,cls.full=fixture()
    def test_closed_policy_uses_exact_frozen_slice_and_whole_endpoint(self):
        a.validate_policy(self.policy,self.full,d.digest(self.full))
        changes=[('totalUnits',1470),('totalUnits',1472),('throughSourceDivision',15),('fullAdmissionSha256','f'*64),('sourceUnits',self.policy['sourceUnits'][:-1]),('sourceDivisions',self.policy['sourceDivisions'][:-1]),('previousRecordDigests',self.policy['previousRecordDigests'][:-1]),('extra','private')]
        for key,value in changes:
            with self.subTest(key=key,value=str(value)[:30]),self.assertRaises(ValueError):a.validate_policy({**self.policy,key:value},self.full,d.digest(self.full))
        changed=copy.deepcopy(self.policy);changed['sourceDivisions'][-1]['endOrdinal']=1470
        with self.assertRaises(ValueError):a.validate_policy(changed,self.full,d.digest(self.full))
    def validate(self,p):
        config=d.read(ROOT/'release/distribution-prefix-v1.config.json');schema,_=d.load_contract(ROOT,config)
        with patch.object(a,'load_policy',return_value=self.policy):d.validate_proposal(p,config,schema,SimpleNamespace(validate_records=a.validate_candidate))
    def test_real_unchanged_schema_and_semantics_accept_synthetic_prefix(self):self.validate(self.p)
    def test_scope_rights_and_state_cannot_drift(self):
        for key,value in [('completeWork',True),('numberedReportCount',835),('description','Complete collection')]:
            p={**self.p,'scope':{**self.p['scope'],key:value}}
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(p)
        for key,value in [('originalContentLicense','CC0-1.0'),('status','pending'),('decisionId','other')]:
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate({**self.p,'rights':{**self.p['rights'],key:value}})
    def test_record_identity_predecessor_private_leak_and_completeness(self):
        for index,key,value in [(110,'sourceOrdinal',9999),(110,'printedHadithNumber',900),(110,'kind','heading'),(110,'humanReview','human-reviewed'),(110,'machineState','draft'),(110,'privateEvidence','hidden'),(0,'english','Replacement synthetic English'),(0,'uncertainties',[{'reportId':None,'category':'translation','summary':'New uncertainty'}])]:
            records=list(self.p['records']);records[index]={**records[index],key:value}
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate({**self.p,'records':records})
        for records in [self.p['records'][:-1],self.p['records']+[self.p['records'][-1]],self.p['records'][1:]]:
            with self.assertRaises(ValueError):self.validate({**self.p,'records':records})
    def test_registry_closes_entire_proposal_policy_and_scope(self):
        registry={'version':1,'entries':[a.registration(self.p,self.policy)]}
        a.validate_registration(self.p,registry,self.policy)
        for key in registry['entries'][0]:
            entry={**registry['entries'][0],key:0 if key in ['recordCount','throughSourceDivision'] else 'f'*64}
            with self.subTest(key=key),self.assertRaises(ValueError):a.validate_registration(self.p,{'version':1,'entries':[entry]},self.policy)
        with self.assertRaises(ValueError):a.validate_registration(self.p,{'version':1,'entries':[]},self.policy)
        for key in ['english','isnad','uncertainties']:
            p=copy.deepcopy(self.p);p['records'][-1][key]='Altered synthetic value'
            with self.assertRaises(ValueError):a.validate_registration(p,registry,self.policy)
    def test_later_cohorts_extras_skips_and_duplicates_rejected(self):
        entries=[{'version':1,'sourceDivision':x['number'],'runDirectory':'.runtime/synthetic','companionManifest':'.runtime/synthetic','continuedContext':None,'ownedUnitIds':[r['sourceUnitId'] for r in self.p['records'][x['startOrdinal']-1:x['endOrdinal']]]} for x in self.policy['sourceDivisions'][2:]]
        producer.validate_entries(entries,self.policy)
        for changed in [entries[:-1],entries+entries[-1:],entries+[dict(entries[-1],sourceDivision=17)],entries[1:]]:
            with self.assertRaises(ValueError):producer.validate_entries(changed,self.policy)
    def test_full_authority_required_and_only_internal_prefix_derived(self):
        arabic=self.p['records'][0]['arabic']
        authority={'units':[{'id':r['sourceUnitId'],'kind':r['kind'],'arabic':arabic} for r in self.full['sourceUnits']]}
        inventory={'sourceSha256':self.policy['sourceArtifactSha256'],'printedReportNumbers':[{'unitId':r['sourceUnitId'],'number':r['printedHadithNumber']} for r in self.full['sourceUnits'] if r['printedHadithNumber'] is not None]}
        prefix,_=producer.derive_authority(authority,inventory,self.policy,self.full);self.assertEqual(len(prefix['units']),1471)
        for units in [authority['units'][:1471],authority['units'][:-1],authority['units']+[authority['units'][-1]],list(reversed(authority['units']))]:
            with self.assertRaises(ValueError):producer.derive_authority({'units':units},inventory,self.policy,self.full)
        authority['units'][-1]['arabic']='Changed invented later authority'
        with self.assertRaises(ValueError):producer.derive_authority(authority,inventory,self.policy,self.full)
    def test_production_surface_stays_disabled_unregistered_and_full_gate_frozen(self):
        self.assertFalse(d.read(ROOT/'release/distribution-prefix-v1.config.json')['publicationEnabled'])
        self.assertEqual(d.read(ROOT/a.REGISTRY),{'version':1,'entries':[]})
        a.load_policy()
        from scripts import bukhari_release_adapter_v2 as full
        with self.assertRaises(ValueError):full.validate_candidate(self.p['records'],self.p)

if __name__=='__main__':unittest.main()
