"""Closed, partial-work prefix admission; unchanged distribution-v2 records."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import release_distribution as d
from scripts.hadith_structure import require,closed
from scripts.bukhari_release_adapter_v2 import validate_divisions,validate_source_binding
from scripts.bukhari_isnad_adapter_v2 import validate_records as validate_isnads
from scripts.hadith_integrity import validate_public_records
ROOT=Path(__file__).resolve().parents[1]
POLICY='release/prefix-source-admission-v1.json'
FULL='release/collection-source-admission.json'
REGISTRY='release/prefix-projections-v1.json'
FIELDS='version authoritySha256 inventorySha256 sourceArtifactSha256 sourceRevision previousProposalSha256 previousReleaseId sourceAuthorityId fullAdmissionSha256 targetReleaseId totalUnits throughSourceDivision sourceDivisions sourceUnits previousRecordDigests title scope rightsDecisionId'


def validate_policy(policy,full,full_sha):
    closed(policy,FIELDS)
    require(type(policy['version']) is int and policy['version']==1,'prefix policy version')
    require(policy['fullAdmissionSha256']==full_sha,'frozen full admission raw hash drift')
    require(type(policy['totalUnits']) is int and policy['totalUnits']==1471 and type(policy['throughSourceDivision']) is int and policy['throughSourceDivision']==16,'only whole division 16 prefix admitted')
    require(full['totalUnits']==12059 and len(full['sourceUnits'])==12059,'full collection authority required')
    for key in ['authoritySha256','inventorySha256','sourceArtifactSha256','sourceRevision','previousProposalSha256','previousReleaseId','sourceAuthorityId','previousRecordDigests']:
        require(policy[key]==full[key],'prefix/full policy drift: '+key)
    require(len(policy['previousRecordDigests'])==110,'exact predecessor inventory required')
    require(policy['sourceUnits']==full['sourceUnits'][:1471],'prefix source slice drift')
    require(policy['sourceDivisions']==full['sourceDivisions'][:16] and [x['number'] for x in policy['sourceDivisions']]==list(range(1,17)),'whole ordered divisions required')
    cursor=1
    for row in policy['sourceDivisions']:
        closed(row,'number startOrdinal endOrdinal')
        require(type(row['startOrdinal']) is int and type(row['endOrdinal']) is int and row['startOrdinal']==cursor and row['endOrdinal']>=cursor,'contiguous division boundaries required')
        cursor=row['endOrdinal']+1
    require(cursor==1472 and full['sourceDivisions'][16]['startOrdinal']==1472,'prefix must end at whole division boundary')
    require([x['sourceOrdinal'] for x in policy['sourceUnits']]==list(range(1,1472)) and len({x['sourceUnitId'] for x in policy['sourceUnits']})==1471,'exact ordered prefix identity required')
    require(policy['targetReleaseId']=='bukhari-through-prayer-working-2' and policy['rightsDecisionId']=='bukhari-through-prayer-working-2-owner-authorized','prefix release identity')
    scope=policy['scope'];closed(scope,'description completeWork includedUnitIds numberedReportCount')
    require(scope['completeWork'] is False and scope['includedUnitIds']==[x['sourceUnitId'] for x in policy['sourceUnits']],'partial prefix scope required')
    require(type(scope['numberedReportCount']) is int and scope['numberedReportCount']==836==sum(x['printedHadithNumber'] is not None for x in policy['sourceUnits']),'numbered report occurrences drift')
    require(isinstance(scope['description'],str) and scope['description'].startswith('Partial ') and '16' in scope['description'] and 'Later source divisions are excluded.' in scope['description'],'explicit partial scope wording required')
    require(isinstance(policy['title'],str) and 'through Description of Prayer' in policy['title'] and 'human-unreviewed' in policy['title'],'partial working title required')
    return policy


def load_policy():
    return validate_policy(d.read(ROOT/POLICY),d.read(ROOT/FULL),d.sha((ROOT/FULL).read_bytes()))


def validate_candidate(records,proposal):
    policy=load_policy()
    require(proposal['releaseId']==policy['targetReleaseId'] and proposal['previousReleaseId']==policy['previousReleaseId'],'prefix successor/predecessor mismatch')
    require(proposal['scope']==policy['scope'] and proposal['title']==policy['title'],'exact partial scope/title required')
    source=proposal['sourceAuthority']
    require(source['id']==policy['sourceAuthorityId'] and source['artifactSha256']==policy['sourceArtifactSha256'] and source['revision']==policy['sourceRevision'],'prefix source provenance drift')
    rights=proposal['rights']
    require(rights['status']=='approved' and rights['originalContentLicense']=='CC-BY-4.0' and rights['decisionId']==policy['rightsDecisionId'],'scoped CC BY 4.0 owner decision required')
    validate_divisions(records,policy['sourceDivisions'],1471)
    validate_source_binding(records,policy)
    validate_isnads(records,proposal);validate_public_records(records)


def registration(proposal,policy):
    return {'releaseId':proposal['releaseId'],'proposalSha256':d.digest(proposal),'prefixPolicySha256':d.digest(policy),'sourceAuthoritySha256':policy['authoritySha256'],'recordCount':policy['totalUnits'],'throughSourceDivision':policy['throughSourceDivision']}


def validate_registration(proposal,registry,policy):
    closed(registry,'version entries')
    require(type(registry['version']) is int and registry['version']==1 and isinstance(registry['entries'],list),'prefix registry version/entries')
    ids=[]
    for entry in registry['entries']:
        closed(entry,'releaseId proposalSha256 prefixPolicySha256 sourceAuthoritySha256 recordCount throughSourceDivision')
        require(isinstance(entry['releaseId'],str) and type(entry['recordCount']) is int and type(entry['throughSourceDivision']) is int,'prefix registration types')
        for key in ['proposalSha256','prefixPolicySha256','sourceAuthoritySha256']:d.hexsha(entry[key])
        ids.append(entry['releaseId'])
    require(len(ids)==len(set(ids)),'duplicate prefix registrations')
    require([x for x in registry['entries'] if x['releaseId']==proposal['releaseId']]==[registration(proposal,policy)],'exact independently reviewed prefix registration required')


def validate_records(records,proposal):
    validate_candidate(records,proposal)
    validate_registration(proposal,d.read(ROOT/REGISTRY),load_policy())
