#!/usr/bin/env python3
"""Complete-collection projection from validated core runs and isnad companions."""
from pathlib import Path
import argparse,json,sys
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import translation_workflow as w
from scripts import hadith_structure as h
from scripts import continued_context as carry
from scripts import release_distribution as d
from scripts.prepare_bukhari_release import project


def content(record):
    return {k:record[k] for k in ['sourceUnitId','sourceOrdinal','kind','arabic','english','arabicSha256','humanReview','machineState','segments','isnad']}


def merge_owned(authority,existing,cohorts):
    """Exactly one owner per occurrence; immutable context reuse adds no records."""
    originals=h.indexed(authority['units']);order=list(originals);positions={uid:i+1 for i,uid in enumerate(order)};records={}
    def admit(record):
        uid=record['sourceUnitId'];h.require(uid in originals and uid not in records,'unknown or multiply owned source occurrence')
        original=originals[uid]
        h.require(record['sourceOrdinal']==positions[uid] and record['arabic']==original['arabic'] and record['kind']==original['kind'],'canonical source/order drift')
        h.require(record['humanReview']=='unreviewed' and record['machineState']=='agent_complete','working records must remain human-unreviewed and complete')
        records[uid]=record
    for record in existing:admit(record)
    for cohort in cohorts:
        h.closed(cohort,'ownedUnitIds contextUnitIds records')
        owned,contexts=cohort['ownedUnitIds'],cohort['contextUnitIds']
        h.require(isinstance(owned,list) and owned and len(set(owned))==len(owned) and isinstance(contexts,list) and len(set(contexts))==len(contexts),'unique ownership and context arrays')
        h.require(set(owned).isdisjoint(contexts),'owned/context overlap')
        projected={r['sourceUnitId']:r for r in cohort['records']}
        h.require(len(projected)==len(cohort['records']) and set(projected)==set(owned)|set(contexts),'cohort projected inventory drift')
        h.require(owned==[uid for uid in order if uid in owned],'owned occurrence order drift')
        for uid in contexts:
            h.require(uid in records and content(projected[uid])==content(records[uid]),'continued source/English/isnad context conflicts with canonical revision')
        for uid in owned:admit(projected[uid])
    h.require(set(records)==set(originals),'complete-collection projection has missing source occurrences')
    return [records[uid] for uid in order]


def private_path(locator):
    path=(ROOT/locator).resolve();h.require(path.is_relative_to(ROOT/'.runtime'),'cohort evidence must stay private');return path


def admitted_cohort(entry,ordinals,numbers,sessions):
    h.closed(entry,'version sourceDivision runDirectory companionManifest continuedContext ownedUnitIds')
    h.require(type(entry['version']) is int and entry['version']==1 and type(entry['sourceDivision']) is int and 3<=entry['sourceDivision']<=100,'cohort receipt version/division')
    run=private_path(entry['runDirectory']);config=w.read(run/'workflow-config.json');profile=w.load_profile(ROOT/config['profile']);packet=w.read(run/'packet.json')
    completed=w.completed(run,packet,profile)
    coverage=w.read(ROOT/config['coverage']);h.require(config['coverage'] in profile['policyFiles'] and coverage['sourceSha256']==packet['sourceSha256'] and coverage['ledgerSha256']==profile['nameLedger']['sha256'],'proper-name source qualification drift')
    expected={(x['nameId'],x['unitId'],x['start'],x['end']) for x in coverage['alignmentMentions']}
    actual={(x['nameId'],x['unitId'],x['start'],x['end']) for x in completed['names']['names']}
    h.require(actual==expected and len(actual)==len(completed['names']['names']),'proper-name inventory incomplete')
    # The actual historical submission snapshot is retained; no new live claim
    # is fabricated after its completed issue was closed.
    candidate=w.read(run/'submission.json')
    h.require(candidate==w.submit(run,packet,profile,w.read(run/'claims-submit.json')),'core candidate does not match admitted independent stages')
    manifest_path=private_path(entry['companionManifest']);manifest=h.validate_manifest(h.read(manifest_path))
    translation=ROOT/'.runtime'/manifest['artifacts']['translation']['path']
    h.require(translation.resolve()==(run/'submission.json').resolve(),'isnad companion binds another English candidate')
    h.require(manifest['artifacts']['source']['sha256']==packet['sourceSha256'] and manifest['artifacts']['ledger']['sha256']==profile['nameLedger']['sha256'],'core/isnad source or ledger differs')
    graph=h.read(ROOT/'.runtime'/manifest['artifacts']['structure']['path'])
    core_sessions=[w.read(run/(stage+'.json'))['host']['sessionId'] for stage in w.stages(profile)]
    other=[h.read(ROOT/'.runtime'/manifest['artifacts'][key]['path'])['sessionId'] for key in ['extractionReceipt','auditReceipt']]
    h.require(len(set(core_sessions+other))==len(core_sessions+other) and not set(core_sessions+other)&sessions,'semantic stage session reused across cohort/role')
    sessions.update(core_sessions+other)
    context_ids=[]
    if entry['continuedContext'] is not None:
        h.require(entry['continuedContext']==config['continuedContext'] and entry['continuedContext'] in profile['policyFiles'],'continued context not profile-bound')
        context=h.read(private_path(entry['continuedContext']))
        carry.validate_carried(context,completed['blind'])
        carry.validate_carried(context,completed['adjudication'])
        carry.validate_carried(context,candidate,graph)
        h.require(context['ownedUnitIds']==entry['ownedUnitIds'],'owned context accounting drift');context_ids=context['contextUnitIds']
    else:
        h.require(config['continuedContext'] is None and entry['ownedUnitIds']==[u['id'] for u in packet['units']],'whole-scope ownership cannot omit units')
    records=project('source-division-'+str(entry['sourceDivision']).zfill(3),manifest,ordinals,numbers)
    return {'ownedUnitIds':entry['ownedUnitIds'],'contextUnitIds':context_ids,'records':records}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['authority','inventory','cohorts','output']:p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args();out=h.private(a.output);policy=d.read(ROOT/'release/collection-source-admission.json')
    h.require(h.file_hash(a.authority)==policy['authoritySha256'] and h.file_hash(a.inventory)==policy['inventorySha256'],'full source admission drift')
    authority=h.read(a.authority);inventory=h.read(a.inventory)
    h.require(inventory['sourceSha256']==policy['sourceArtifactSha256'],'raw source provenance drift')
    originals=h.indexed(authority['units']);h.require(len(originals)==policy['totalUnits'],'full authority count drift')
    previous=d.read(ROOT/'release/proposals/bukhari-opening-faith-working-1.json');h.require(d.digest(previous)==policy['previousProposalSha256'],'first-release proposal changed')
    ordinals={uid:i+1 for i,uid in enumerate(originals)}
    printed=inventory['printedReportNumbers'];numbers={r['unitId']:r['number'] for r in printed};h.require(len(numbers)==len(printed),'duplicate report occurrence key')
    entries=h.read(private_path(str(a.cohorts)))
    h.require(isinstance(entries,list) and entries,'complete cohort ledger required')
    sessions=set();cohorts=[admitted_cohort(v,ordinals,numbers,sessions) for v in entries]
    records=merge_owned(authority,previous['records'],cohorts)
    proposal={**previous,'releaseId':'bukhari-complete-working-2','previousReleaseId':previous['releaseId'],'title':'Sahih al-Bukhari — complete retained collection (human-unreviewed working release)','records':records}
    proposal['scope']={'description':'Complete retained classical-text authority: all source divisions, headings, comments, numbered and repeated reports, ordered Arabic isnads and uncertainty disclosures.','completeWork':True,'includedUnitIds':list(originals),'numberedReportCount':len(printed)}
    proposal['sourceAuthority']={**proposal['sourceAuthority'],'limitations':['Text-only transcription; no scan verification.','Source spellings, narrator/genealogy ambiguities and layout material are retained or explicitly disclosed.','Ordered textual chains do not certify historical contact.','All retained source units are included; all records remain human-unreviewed with no human scholarly approval.']}
    proposal['rights']={**proposal['rights'],'decisionId':'bukhari-complete-working-2-owner-authorized','arabicBasis':'Owner-authorized continuation of the underlying-classical-text rationale across independently qualified source scopes, excluding modern apparatus and preserving attribution. Disclosed editorial/database risks accepted; no OpenITI commercial grant or legal clearance claimed.'}
    config=d.read(ROOT/'release/distribution-v2.config.json');schema,adapter=d.load_contract(ROOT,config);d.validate_proposal(proposal,config,schema,SimpleNamespace(validate_records=adapter.validate_candidate))
    h.write_new(out,proposal)
    # This SAFE METADATA candidate is not the active public registry. Promote it
    # only after independent full-projection review and a normal reviewed PR.
    h.write_new(out.with_name(out.stem+'-public-registration-candidate.json'),{'version':1,'entries':[{'releaseId':proposal['releaseId'],'proposalSha256':d.digest(proposal),'sourceAuthoritySha256':policy['authoritySha256'],'recordCount':len(records)}]})
    h.write_new(out.with_name(out.stem+'-private-admission.json'),{'version':1,'proposalSha256':d.digest(proposal),'cohortLedgerSha256':h.file_hash(a.cohorts),'authoritySha256':h.file_hash(a.authority),'recordCount':len(records),'independentSessions':len(sessions),'publicRegistrationPending':True,'publicationPerformed':False})
    print('Complete collection proposal prepared privately; public registration and publication remain separate')

if __name__=='__main__':main()
