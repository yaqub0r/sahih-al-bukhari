#!/usr/bin/env python3
"""Project audited companions into a private, allowlisted release proposal."""
from pathlib import Path
import argparse,hashlib,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import hadith_structure as h
from scripts import release_distribution as d

ROOT=Path(__file__).resolve().parents[1]

def admitted_inputs(authority_path,inventory_path,manifests,admission):
    d.closed(admission,'version authoritySha256 inventorySha256 sourceArtifactSha256 sourceRevision companionSha256')
    d.require(type(admission['version']) is int and admission['version']==1,'source admission version')
    for key in ['authoritySha256','inventorySha256','sourceArtifactSha256']:d.hexsha(admission[key])
    d.hexsha(admission['sourceRevision'],40)
    d.require(h.file_hash(authority_path)==admission['authoritySha256'],'frozen full authority digest mismatch')
    d.require(h.file_hash(inventory_path)==admission['inventorySha256'],'frozen inventory digest mismatch')
    d.closed(admission['companionSha256'],'opening faith')
    for section,path in manifests.items():
        d.require(h.file_hash(path)==admission['companionSha256'][section],'frozen companion admission mismatch')
    authority,inventory=h.read(authority_path),h.read(inventory_path)
    d.require(inventory['sourceSha256']==admission['sourceArtifactSha256'],'inventory/upstream provenance mismatch')
    ids=[u['id'] for u in authority['units']]
    d.require(len(set(ids))==len(ids),'duplicate authority unit')
    rows=inventory['printedReportNumbers'];number_ids=[r['unitId'] for r in rows]
    d.require(len(set(number_ids))==len(number_ids),'duplicate report inventory unit')
    originals={u['id']:u for u in authority['units']}
    d.require(all(r['unitId'] in originals and originals[r['unitId']]['kind']=='report' for r in rows),'report inventory outside authority')
    return authority,inventory

def project(section,manifest,ordinals,numbers):
    h.validate_manifest(manifest)
    def load(k):return h.read(ROOT/'.runtime'/manifest['artifacts'][k]['path'])
    source,translation,graph,audit=(load(k) for k in ['source','translation','structure','audit'])
    result=[]
    for s,t,g in zip(source['units'],translation['units'],graph['units']):
        uid=s['id'];arabic=s['arabic'];uncertainties=[]
        for f in translation['unresolved']:
            if f['unitId']==uid:uncertainties.append({'reportId':None,'category':'translation','summary':f['publicSummary']})
        for f in audit['findings']:
            if f['unitId']==uid and f['status']=='human-only':uncertainties.append({'reportId':f['reportId'],'category':'structure','summary':f['detail']})
        nodes=[{**n,'arabic':None if n['start'] is None else arabic[n['start']:n['end']]} for n in g['nodes']]
        edges=[{**e,'arabicWording':None if e['start'] is None else arabic[e['start']:e['end']]} for e in g['edges']]
        result.append({'sourceUnitId':uid,'sourceOrdinal':ordinals[uid],'bookSection':section,'printedHadithNumber':numbers.get(uid),'kind':s['kind'],'arabic':arabic,'english':t['english'],'arabicSha256':g['sha256'],'humanReview':'unreviewed','machineState':'agent_complete','segments':[{**v,'arabic':arabic[v['start']:v['end']]} for v in g['segments']],'isnad':{'nodes':nodes,'edges':edges,'paths':g['paths'],'reports':g['reports'],'status':g['status'],'note':g['note']},'uncertainties':uncertainties})
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--authority',required=True,type=Path);p.add_argument('--inventory',required=True,type=Path)
    p.add_argument('--opening-manifest',required=True,type=Path);p.add_argument('--faith-manifest',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();out=h.private(a.output);d.require(not out.exists(),'write-once proposal output')
    admission=d.read(ROOT/'release/bukhari-source-admission.json')
    authority,inventory=admitted_inputs(a.authority,a.inventory,{'opening':a.opening_manifest,'faith':a.faith_manifest},admission)
    ordinals={u['id']:i+1 for i,u in enumerate(authority['units'])};numbers={v['unitId']:v['number'] for v in inventory['printedReportNumbers']}
    records=[]
    for section,path in [('opening',a.opening_manifest),('faith',a.faith_manifest)]:
        rows=project(section,h.read(path),ordinals,numbers)
        originals={u['id']:u for u in authority['units']}
        for r in rows:d.require(r['arabic']==originals[r['sourceUnitId']]['arabic'],'full authority/source drift')
        records+=rows
    d.require(len(records)==110 and [r['sourceOrdinal'] for r in records]==list(range(1,111)),'first-release complete opening/Faith scope required')
    d.require([r['printedHadithNumber'] for r in records if r['printedHadithNumber'] is not None]==list(range(1,59)),'first-release printed inventory mismatch')
    proposal={'version':1,'releaseId':'bukhari-opening-faith-working-1','previousReleaseId':None,'bookId':'sahih-al-bukhari','title':'Sahih al-Bukhari — Beginning of Revelation and Book of Faith','sourceAuthority':{'id':'openiti-bukhari-jk000110','revision':admission['sourceRevision'],'artifactSha256':admission['sourceArtifactSha256'],'edition':'Mustafa Dib al-Bugha; Dar Ibn Kathir / al-Yamama, Beirut; third edition, 1407 AH / 1987 CE; six volumes.','attribution':'Classical Arabic: Muhammad ibn Ismail al-Bukhari; transcription from OpenITI JK000110, pinned revision. Independently authored working English by the Sahih al-Bukhari project.','limitations':['Text-only transcription; no scan verification.','Source spellings, ambiguous references and layout markers are retained.','Ordered chains record textual transmission, not proof of historical contact.','All included records remain human-unreviewed; this is a partial-work candidate.']},'rights':{'decisionId':'bukhari-first-distribution-rights-pending','status':'pending','originalContentLicense':None,'arabicBasis':'Proposed reliance on the underlying classical text, with modern apparatus excluded. No commercial grant from OpenITI is claimed.','attribution':'OpenITI transcription corpus is offered under CC BY-NC-SA 4.0; that license is not represented as permission for commercial reuse. Original project English and structure licensing remains for owner decision.','excludedMaterial':['Modern introductions, footnotes, editorial discussion, indices and corpus annotations','Private translation/review/execution evidence and restricted English witnesses'],'residualRisk':'Owner accepted proportionate residual risk for private processing. External distribution and a commercial-compatible grant require a separate reviewed decision concerning editorial and possible database rights; no legal clearance is claimed.'},'scope':{'description':'Beginning of Revelation and Book of Faith; numbered reports 1–58 with every intervening heading and authorial comment.','completeWork':False,'includedUnitIds':[r['sourceUnitId'] for r in records],'numberedReportCount':58},'records':records}
    config=d.read(ROOT/'release/distribution.config.json');schema,adapter=d.load_contract(ROOT,config);d.validate_proposal(proposal,config,schema,adapter)
    h.write_new(out,proposal)
    receipt={'version':1,'proposalSha256':d.digest(proposal),'inputs':{str(path.relative_to(ROOT) if path.is_absolute() else path):h.file_hash(path) for path in [a.authority,a.inventory,a.opening_manifest,a.faith_manifest]},'recordCount':110,'numberedReports':58,'sourceAdmissionSha256':h.file_hash(ROOT/'release/bukhari-source-admission.json'),'publicationPerformed':False}
    h.write_new(out.with_name(out.stem+'-private-admission.json'),receipt)
    print('Prepared110 records /58 numbered reports; rights pending; publication disabled')

if __name__=='__main__':main()
