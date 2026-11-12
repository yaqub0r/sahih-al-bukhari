#!/usr/bin/env python3
"""Privately derive the owner-authorized whole-division prefix from full authority."""
from pathlib import Path
from types import SimpleNamespace
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import collection_release as c
from scripts import bukhari_prefix_release_adapter_v1 as a
from scripts import hadith_structure as h
from scripts import release_distribution as d
ROOT=Path(__file__).resolve().parents[1]


def derive_authority(authority,inventory,policy,full):
    originals=h.indexed(authority['units'])
    h.require(len(originals)==12059 and list(originals)==[x['sourceUnitId'] for x in full['sourceUnits']],'full authority ordered inventory required')
    h.require(inventory['sourceSha256']==policy['sourceArtifactSha256'],'raw source provenance drift')
    printed=inventory['printedReportNumbers'];numbers={x['unitId']:x['number'] for x in printed}
    h.require(len(numbers)==len(printed),'duplicate printed report occurrence')
    for unit,row in zip(authority['units'],full['sourceUnits']):
        h.require(unit['kind']==row['kind'] and d.sha(unit['arabic'].encode('utf-8'))==row['arabicSha256'] and numbers.get(unit['id'])==row['printedHadithNumber'],'full source identity/hash/label drift')
    return {**authority,'units':authority['units'][:policy['totalUnits']]},numbers


def validate_entries(entries,policy):
    h.require(isinstance(entries,list) and entries,'complete private prefix cohort ledger required')
    allowed={x['sourceUnitId']:x['sourceOrdinal'] for x in policy['sourceUnits']}
    divisions={x['number']:x for x in policy['sourceDivisions']}
    owned=[]
    for entry in entries:
        h.closed(entry,'version sourceDivision runDirectory companionManifest continuedContext ownedUnitIds')
        n=entry['sourceDivision'];h.require(type(n) is int and 3<=n<=16,'later or predecessor cohort forbidden')
        ids=entry['ownedUnitIds'];h.require(isinstance(ids,list) and ids and all(isinstance(v,str) and v in allowed for v in ids),'owned units outside prefix')
        row=divisions[n];h.require(all(row['startOrdinal']<=allowed[v]<=row['endOrdinal'] for v in ids),'cohort division ownership mismatch')
        owned.extend(ids)
    h.require(owned==[x['sourceUnitId'] for x in policy['sourceUnits'][110:]],'exact ordered single ownership of every new prefix occurrence required')


def scoped_rights(previous,policy):
    return {**previous,'decisionId':policy['rightsDecisionId'],'arabicBasis':a.ARABIC_BASIS}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['authority','inventory','cohorts','output']:p.add_argument('--'+key,required=True,type=Path)
    args=p.parse_args();out=h.private(args.output);policy=a.load_policy();full=d.read(ROOT/a.FULL)
    h.require(h.file_hash(args.authority)==policy['authoritySha256'] and h.file_hash(args.inventory)==policy['inventorySha256'],'full authority/inventory raw pin drift')
    prefix,numbers=derive_authority(h.read(args.authority),h.read(args.inventory),policy,full)
    previous=d.read(ROOT/'release/proposals/bukhari-opening-faith-working-1.json')
    h.require(d.digest(previous)==policy['previousProposalSha256'],'immutable predecessor proposal changed')
    entries=h.read(c.private_path(str(args.cohorts)));validate_entries(entries,policy)
    ordinals={x['sourceUnitId']:x['sourceOrdinal'] for x in full['sourceUnits']};sessions=set()
    cohorts=[c.admitted_cohort(entry,ordinals,numbers,sessions) for entry in entries]
    records=c.merge_owned(prefix,previous['records'],cohorts)
    proposal={**previous,'releaseId':policy['targetReleaseId'],'previousReleaseId':previous['releaseId'],'title':policy['title'],'scope':policy['scope'],'records':records}
    proposal['sourceAuthority']={**previous['sourceAuthority'],'limitations':['Text-only transcription; no scan verification.','Partial authority through source division 16 only; later divisions are excluded.','Source spellings and narrator ambiguities are retained or disclosed. Ordered textual chains do not certify historical contact.','All records remain human-unreviewed with no human scholarly approval.']}
    proposal['rights']=scoped_rights(previous['rights'],policy)
    config=d.read(ROOT/'release/distribution-prefix-v1.config.json');schema,_=d.load_contract(ROOT,config)
    d.validate_proposal(proposal,config,schema,SimpleNamespace(validate_records=a.validate_candidate))
    h.write_new(out,proposal)
    h.write_new(out.with_name(out.stem+'-public-registration-candidate.json'),{'version':1,'entries':[a.registration(proposal,policy)]})
    h.write_new(out.with_name(out.stem+'-private-admission.json'),{'version':1,'proposalSha256':d.digest(proposal),'prefixPolicySha256':d.digest(policy),'fullAdmissionSha256':policy['fullAdmissionSha256'],'authoritySha256':policy['authoritySha256'],'inventorySha256':policy['inventorySha256'],'cohortLedgerSha256':h.file_hash(args.cohorts),'recordCount':len(records),'independentSessions':len(sessions),'publicRegistrationPending':True,'publicationPerformed':False})
    print('Prefix prepared privately; independent projection review and public registration remain pending')

if __name__=='__main__':main()
