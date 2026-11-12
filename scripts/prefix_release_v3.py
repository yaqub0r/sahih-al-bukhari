#!/usr/bin/env python3
"""Qualified private prefix projection for compiled version 2 supplements.

The owning private wrapper must authenticate the B6 book gate FIRST, then call
prepare with its qualified return object. There is deliberately no ungated CLI.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
from scripts import prefix_release_v1 as legacy
from scripts import bukhari_prefix_release_adapter_v2 as a
from scripts import collection_release as c
from scripts import hadith_structure as h
from scripts import hadith_supplements_v2 as supplements
from scripts import release_distribution as d
ROOT = Path(__file__).resolve().parents[1]


def prepare(authority_path, inventory_path, cohorts_path, output_path, qualified_book_supplement):
    """Only the authenticated private admission owner may call this API.

    Accepts B6 validate_book_supplement's return, not a verdict-only file.
    Qualification/authenticity remains the caller's mandatory prior gate.
    """
    gate = qualified_book_supplement
    h.require(isinstance(gate,dict) and all(k in gate for k in ['book','compiled','semanticActors','sourceProof','namesProof']), 'authenticated book supplement result required')
    compiled = gate['compiled']
    h.require(isinstance(compiled, dict) and type(compiled.get('version')) is int and compiled['version'] == 2, 'producer 3 requires actual compiled supplement version 2')
    h.require(compiled['sourceProofSha256'] == d.digest(gate['sourceProof']) and compiled['namesProofSha256'] == d.digest(gate['namesProof']), 'compiled semantic proof binding drift')
    actors = gate['semanticActors']
    h.require(isinstance(actors,list) and len(actors) >= 2, 'independent book supplement actors required')
    out = h.private(output_path);policy = a.load_policy();full = d.read(ROOT/a.FULL)
    h.require(h.file_hash(authority_path) == policy['authoritySha256'] and h.file_hash(inventory_path) == policy['inventorySha256'], 'full authority/inventory raw pin drift')
    prefix,numbers = legacy.derive_authority(h.read(authority_path),h.read(inventory_path),policy,full)
    previous = d.read(ROOT/'release/proposals/bukhari-opening-faith-working-1.json')
    h.require(d.digest(previous) == policy['previousProposalSha256'], 'immutable predecessor proposal changed')
    entries = h.read(c.private_path(str(cohorts_path)));legacy.validate_entries(entries,policy)
    ordinals = {x['sourceUnitId']:x['sourceOrdinal'] for x in full['sourceUnits']};sessions = set()
    cohorts = [c.admitted_cohort(entry,ordinals,numbers,sessions) for entry in entries]
    records = supplements.project_contextual_isnads(c.merge_owned(prefix,previous['records'],cohorts),compiled)
    proposal = {**previous,'releaseId':policy['targetReleaseId'],'previousReleaseId':previous['releaseId'],'title':policy['title'],'scope':policy['scope'],'records':records}
    proposal['sourceAuthority'] = {**previous['sourceAuthority'],'limitations':['Text-only transcription; no scan verification.','Partial authority through source division 16 only; later divisions are excluded.','Source spellings and narrator ambiguities are retained or disclosed. Ordered textual chains do not certify historical contact.','All records remain human-unreviewed with no human scholarly approval.']}
    proposal['rights'] = legacy.scoped_rights(previous['rights'],policy)
    config = d.read(ROOT/'release/distribution-prefix-v1.config.json');schema,_ = d.load_contract(ROOT,config)
    d.validate_proposal(proposal,config,schema,SimpleNamespace(validate_records=a.validate_candidate))
    h.write_new(out,proposal)
    h.write_new(out.with_name(out.stem+'-public-registration-candidate.json'),{'version':1,'entries':[a.registration(proposal,policy)]})
    h.write_new(out.with_name(out.stem+'-private-admission.json'),{'version':3,'proposalSha256':d.digest(proposal),'prefixPolicySha256':d.digest(policy),'fullAdmissionSha256':policy['fullAdmissionSha256'],'authoritySha256':policy['authoritySha256'],'inventorySha256':policy['inventorySha256'],'cohortLedgerSha256':h.file_hash(cohorts_path),'bookSupplementSha256':d.digest(compiled),'sourceProofSha256':compiled['sourceProofSha256'],'namesProofSha256':compiled['namesProofSha256'],'recordCount':len(records),'independentSessions':len(sessions),'publicRegistrationPending':True,'publicationPerformed':False})
    return proposal


if __name__ == '__main__':
    raise SystemExit('Use the owning private prefix wrapper: authenticated B6 book admission must run before prepare().')
