"""Versioned context binding for exact legacy and reciprocal companions.

The frozen v1 planner, extension and exact carry validators remain unchanged.
Only manifest admission dispatch changes; inherited records are copied exactly.
"""
from scripts import hadith_structure as h
from scripts import hadith_structure_v2 as h2
from scripts.continued_context import digest, plan, validate_extension, validate_carried


def bind_context(qualified_source_path,owned_ids,cut_review_path,companion_paths,ledger_path):
    """Admit exact earlier source/English/graph; every companion validates first."""
    qualified=h.read(qualified_source_path);review=h.read(cut_review_path);result=plan(qualified,owned_ids,review)
    required=set(result['contextUnitIds']);available={};ledger=h.read(ledger_path)
    for manifest_path in companion_paths:
        manifest=h.read(manifest_path)
        engine=h2 if manifest.get('kind')=='private-hadith-structure-companion-v2' else h
        engine.validate_manifest(manifest)
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

