"""Complete collection: exact source, predecessor and registered projection."""
from pathlib import Path
import json,sys,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.bukhari_release_adapter import validate_records as validate_isnads
from scripts.hadith_structure import require,closed
from scripts.hadith_integrity import validate_public_records
from scripts import release_distribution as d
ROOT=Path(__file__).resolve().parents[1]

def validate_divisions(records,divisions,total):
    expected={}
    for row in divisions:
        require(type(row['number']) is int and 1<=row['number']<=100,'invalid source division')
        section='opening' if row['number']==1 else 'faith' if row['number']==2 else 'source-division-'+str(row['number']).zfill(3)
        for ordinal in range(row['startOrdinal'],row['endOrdinal']+1):
            require(ordinal not in expected,'overlapping source divisions');expected[ordinal]=section
    require(set(expected)==set(range(1,total+1)),'source division coverage mismatch')
    require(len(records)==total and [r['sourceOrdinal'] for r in records]==list(range(1,total+1)),'complete ordered collection required')
    for r in records:require(r['bookSection']==expected[r['sourceOrdinal']],'record assigned to wrong source division')

def validate_source_binding(records,policy):
    require(len(records)==len(policy['sourceUnits']),'exact source occurrence count required')
    indexed={r['sourceUnitId']:r for r in records}
    require(len(indexed)==len(records),'duplicate source occurrence')
    for record,source in zip(records,policy['sourceUnits']):
        require(record['humanReview']=='unreviewed' and record['machineState']=='agent_complete','unsupported human review or incomplete machine state')
        require(all(record[k]==source[k] for k in ['sourceUnitId','sourceOrdinal','kind','printedHadithNumber']),'record identity/order/type/printed label differs from frozen authority')
        require(record['arabicSha256']==source['arabicSha256']==hashlib.sha256(record['arabic'].encode('utf-8')).hexdigest(),'Arabic differs from admitted source occurrence')
    for previous in policy['previousRecordDigests']:
        require(previous['sourceUnitId'] in indexed and d.digest(indexed[previous['sourceUnitId']])==previous['recordSha256'],'immutable predecessor record changed')

def validate_registration(proposal,registry,policy):
    closed(registry,'version entries');require(type(registry['version']) is int and registry['version']==1,'projection registry version')
    require(isinstance(registry['entries'],list),'projection registry entries')
    for entry in registry['entries']:closed(entry,'releaseId proposalSha256 sourceAuthoritySha256 recordCount')
    found=[v for v in registry['entries'] if v['releaseId']==proposal['releaseId']]
    require(len(found)==1 and found[0]['proposalSha256']==d.digest(proposal) and found[0]['sourceAuthoritySha256']==policy['authoritySha256'] and found[0]['recordCount']==policy['totalUnits'],'public projection is not the exact reviewed registered candidate')

def validate_candidate(records,proposal):
    """Private producer check; does not admit an archive for publication."""
    policy=d.read(ROOT/'release/collection-source-admission.json')
    require(policy['version']==1 and policy['totalUnits']==12059 and [v['number'] for v in policy['sourceDivisions']]==list(range(1,101)),'unreviewed collection division policy')
    require(proposal['releaseId']==policy['targetReleaseId'] and proposal['previousReleaseId']==policy['previousReleaseId'],'successor/predecessor release identity mismatch')
    require(proposal['sourceAuthority']['id']==policy['sourceAuthorityId'],'source authority identity mismatch')
    require(proposal['scope']['completeWork'] is True,'collection-v2 is a complete-work contract')
    validate_divisions(records,policy['sourceDivisions'],policy['totalUnits']);validate_source_binding(records,policy)
    require(proposal['sourceAuthority']['artifactSha256']==policy['sourceArtifactSha256'] and proposal['sourceAuthority']['revision']==policy['sourceRevision'],'source provenance mismatch')
    validate_isnads(records,proposal);validate_public_records(records)

def validate_records(records,proposal):
    """Only the independently reviewed public registration admits a bundle."""
    validate_candidate(records,proposal)
    validate_registration(proposal,d.read(ROOT/'release/collection-projections.json'),d.read(ROOT/'release/collection-source-admission.json'))
