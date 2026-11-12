#!/usr/bin/env python3
"""Private, hash-bound continued-context adapter; never changes core v1 packets."""
from pathlib import Path
import hashlib,json
from scripts import hadith_structure as h


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()


def validate_extension(previous,current):
    """Old identities and mappings remain usable by immutable context records."""
    h.require(previous['version']==current['version']==2,'version2 name ledgers required')
    old=h.indexed(previous['identities']);new=h.indexed(current['identities'])
    h.require(set(old)<=set(new),'inherited identities cannot disappear')
    h.require(current['decisions'][:len(previous['decisions'])]==previous['decisions'],'ledger decision history changed')
    for name_id,before in old.items():
        after=new[name_id]
        h.require(before['english']==after['english'],'inherited canonical name repurposed')
        h.require(set(before['arabicForms'])<=set(after['arabicForms']),'inherited Arabic form removed')
        for pair in before['renderings']:
            h.require(pair in after['renderings'],'inherited name rendering changed')


def plan(source,owned_ids,cut_review):
    """Mechanical closure after a separate semantic boundary/continuation review."""
    h.closed(cut_review,'version verdict sourceCanonicalSha256 ownedUnitIds additionalContextUnitIds detail')
    h.require(type(cut_review['version']) is int and cut_review['version']==1 and cut_review['verdict']=='pass','semantic cut review must pass')
    h.text(cut_review['detail'])
    h.require(cut_review['sourceCanonicalSha256']==digest(source),'semantic cut review source drift')
    indexed=h.indexed(source['units']);order=list(indexed)
    h.require(isinstance(owned_ids,list) and owned_ids and len(set(owned_ids))==len(owned_ids),'unique owned units required')
    h.require(owned_ids==[uid for uid in order if uid in owned_ids],'owned source order/coverage mismatch')
    h.require(owned_ids==cut_review['ownedUnitIds'],'cut review does not bind this owned scope')
    indexes=[order.index(uid) for uid in owned_ids]
    h.require(indexes==list(range(indexes[0],indexes[-1]+1)),'owned units must form a contiguous occurrence scope')
    additional=cut_review['additionalContextUnitIds']
    h.require(isinstance(additional,list) and len(set(additional))==len(additional) and all(uid in indexed for uid in additional),'invalid additional context IDs')
    required=set(owned_ids)|set(additional)
    while True:
        expanded=required|{cid for uid in required for cid in indexed[uid]['contextIds']}
        h.require(expanded<=set(indexed),'context escapes qualified authority')
        if expanded==required:break
        required=expanded
    for uid in required:
        h.require(all(order.index(cid)<order.index(uid) for cid in indexed[uid]['contextIds']),'governing context must precede its occurrence')
    context=[uid for uid in order if uid in required and uid not in owned_ids]
    h.require(all(order.index(uid)<indexes[0] for uid in context),'continuation requires already completed earlier context')
    selected=[indexed[uid] for uid in order if uid in required]
    return {'source':{'units':selected,'exclusions':source['exclusions']},'ownedUnitIds':owned_ids,'contextUnitIds':context}


def bind_context(qualified_source_path,owned_ids,cut_review_path,companion_paths,ledger_path):
    """Admit exact earlier source/English/graph; every companion validates first."""
    qualified=h.read(qualified_source_path);review=h.read(cut_review_path);result=plan(qualified,owned_ids,review)
    required=set(result['contextUnitIds']);available={};ledger=h.read(ledger_path)
    for manifest_path in companion_paths:
        manifest=h.validate_manifest(h.read(manifest_path))
        def load(key):return h.read(h.ROOT/'.runtime'/manifest['artifacts'][key]['path'])
        source,translation,structure,old_ledger=(load(key) for key in ['source','translation','structure','ledger'])
        validate_extension(old_ledger,ledger)
        for s,t,g in zip(source['units'],translation['units'],structure['units']):
            uid=s['id']
            if uid not in required:continue
            record={'source':s,'translation':t,'structure':g}
            if uid in available:h.require(available[uid]['record']==record,'conflicting inherited canonical revision')
            else:available[uid]={'record':record,'companionSha256':h.file_hash(manifest_path)}
    h.require(set(available)==required,'missing audited continued context')
    indexed=h.indexed(qualified['units'])
    carried=[]
    for uid in result['contextUnitIds']:
        value=available[uid];h.require(value['record']['source']==indexed[uid],'qualified/inherited context source drift')
        carried.append({'unitId':uid,**value})
    manifest={'version':1,'kind':'private-continued-context-v1','qualifiedSourceSha256':h.file_hash(qualified_source_path),'cutReviewSha256':h.file_hash(cut_review_path),'ledgerSha256':h.file_hash(ledger_path),'ownedUnitIds':owned_ids,'contextUnitIds':result['contextUnitIds'],'inherited':carried}
    return result['source'],manifest


def validate_carried(manifest,translation,structure=None):
    """Run on blind/adjudicated/final outputs and again before public projection."""
    h.require(type(manifest['version']) is int and manifest['version']==1 and manifest['kind']=='private-continued-context-v1','unsupported continued-context manifest')
    targets=h.indexed(translation['units']);graphs=h.indexed(structure['units']) if structure is not None else None
    h.require(set(manifest['ownedUnitIds']).isdisjoint(manifest['contextUnitIds']),'owned/context overlap')
    h.require(set(targets)==set(manifest['ownedUnitIds'])|set(manifest['contextUnitIds']),'owned/context output inventory mismatch')
    h.require([v['unitId'] for v in manifest['inherited']]==manifest['contextUnitIds'],'continued context inventory drift')
    for inherited in manifest['inherited']:
        uid=inherited['unitId'];frozen=inherited['record']['translation'];candidate=targets[uid]
        h.require(candidate['english']==frozen['english'] and candidate['formulaTargets']==frozen['formulaTargets'],'continued bilingual context changed')
        if 'arabic' in candidate:h.require(candidate['arabic']==frozen['arabic'],'continued Arabic context changed')
        if graphs is not None:h.require(graphs[uid]==inherited['record']['structure'],'continued isnad context changed')
    return [targets[uid] for uid in manifest['ownedUnitIds']]
