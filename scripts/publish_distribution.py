#!/usr/bin/env python3
"""Protected CI preparation and owner-authenticated immutable publication."""
from pathlib import Path
import argparse,json,os,re,subprocess,tempfile,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import release_distribution as d

def run(*args):return subprocess.check_output(args,text=True).strip()

def tracked(root,path):
    run('git','ls-files','--error-unmatch','--',path.relative_to(root).as_posix())
    return path

DEFAULT_CONFIG='release/distribution.config.json'
# Reviewed publication surfaces only; callers cannot select an arbitrary adapter.
SUPPORTED_CONFIGS={
    DEFAULT_CONFIG: (),
    'release/distribution-v2.config.json': ('release/collection-source-admission.json','release/collection-projections.json'),
    'release/distribution-prefix-v1.config.json': ('release/prefix-source-admission-v1.json','release/prefix-projections-v1.json','release/collection-source-admission.json'),
}


def selected_config(root,locator):
    d.require(locator in SUPPORTED_CONFIGS,'unsupported publication config')
    path=tracked(root,d.contained(root,locator));config=d.read(path)
    # load_contract also lints the closed configuration and schema.
    schema,adapter=d.load_contract(root,config)
    for key in ['recordSchema','adapter']:tracked(root,d.contained(root,config[key]))
    for name in SUPPORTED_CONFIGS[locator]:tracked(root,d.contained(root,name))
    return config,schema,adapter


def config_binding(root,locator,config):
    names=[locator,config['recordSchema'],config['adapter'],*SUPPORTED_CONFIGS[locator]]
    inputs={name:d.sha(d.contained(root,name).read_bytes()) for name in sorted(set(names))}
    return {'configPath':locator,'configSha256':inputs[locator],'contractId':config['contractId'],'contractInputsSha256':d.digest(inputs)}


def verified_validation(repo,run_id,commit,expected):
    d.require(re.fullmatch('[0-9]+',run_id),'numeric validation run required')
    base='repos/'+repo+'/actions/runs/'+run_id
    evidence=json.loads(run('gh','api',base))
    d.require(evidence.get('event')=='workflow_dispatch' and evidence.get('head_branch')=='main' and evidence.get('head_sha')==commit,'validation run identity mismatch')
    d.require(evidence.get('path')=='.github/workflows/publish-public-distribution.yml','unexpected validation workflow')
    d.require(evidence.get('status')=='completed' and evidence.get('conclusion')=='success','successful protected validation required')
    actor=json.loads(run('gh','api','user'))
    d.require(actor.get('type')=='User' and bool(actor.get('login')),'authenticated owner user required')
    approvals=json.loads(run('gh','api',base+'/approvals'))
    d.require(any(a.get('state')=='approved' and a.get('user',{}).get('id')==actor['id'] and any(e.get('name')=='public-release' for e in a.get('environments',[])) for a in approvals),'normal environment approval by authenticated maintainer required')
    logs=run('gh','run','view',run_id,'--repo',repo,'--log')
    marker='RELEASE_VALIDATION_RECEIPT='
    receipts=[json.loads(line.split(marker,1)[1]) for line in logs.splitlines() if marker in line]
    d.require(len(receipts)==1 and receipts[0]==expected,'protected validation input/checksum receipt mismatch')
    return evidence

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config');p.add_argument('--commit',required=True);p.add_argument('--proposal',required=True);p.add_argument('--expected-sha256',required=True)
    mode=p.add_mutually_exclusive_group(required=True);mode.add_argument('--prepare-only',action='store_true');mode.add_argument('--validation-run-id')
    a=p.parse_args();d.hexsha(a.commit,40);d.hexsha(a.expected_sha256)
    root=Path.cwd().resolve();locator=a.config or DEFAULT_CONFIG;config,schema,adapter=selected_config(root,locator)
    binding=config_binding(root,locator,config) if a.config is not None else None
    if a.prepare_only:
        d.require(os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch' and os.environ.get('GITHUB_REF')=='refs/heads/main','manual main dispatch required')
        d.require(os.environ.get('GITHUB_REPOSITORY')==config['repository'],'workflow repository mismatch')
    else:
        d.require(os.environ.get('GITHUB_ACTIONS')!='true','owner finalization runs outside Actions; no admin secret in CI')
    d.require(config['publicationEnabled'] and not config['exampleOnly'],'publication disabled')
    d.require(re.fullmatch(r'release/proposals/[a-z0-9][a-z0-9.-]+\.json',a.proposal),'reviewed public proposal path required')
    proposal_path=tracked(root,d.contained(root,a.proposal));proposal=d.read(proposal_path)
    approval=tracked(root,d.contained(root,'release/approvals/'+proposal['releaseId']+'.json'))
    d.require(run('git','rev-parse','HEAD')==a.commit,'checkout commit mismatch')
    run('git','fetch','origin','main');d.require(run('git','rev-parse','origin/main')==a.commit,'main advanced; prepare/review new archive')
    d.require(not run('git','status','--porcelain'),'dirty checkout')
    checks=json.loads(run('gh','api','repos/'+config['repository']+'/commits/'+a.commit+'/check-runs'))['check_runs']
    required=[r for r in checks if r['name']=='contracts-and-policy']
    d.require(required and all(r['conclusion']=='success' for r in required),'contracts-and-policy success required')
    runtime=root/'.runtime';runtime.mkdir(exist_ok=True);work=Path(tempfile.mkdtemp(prefix='release-publish-',dir=runtime))
    archive=work/(config['bookId']+'-public-distribution-'+a.commit+'.zip')
    files=d.compile_files(proposal,config,schema,adapter,a.commit);d.archive_files(files,archive)
    verification=work/'verification.zip';d.archive_files(d.compile_files(proposal,config,schema,adapter,a.commit),verification)
    d.require(archive.read_bytes()==verification.read_bytes(),'reproducibility failed')
    d.require(d.sha(archive.read_bytes())==a.expected_sha256,'reviewed archive checksum mismatch')
    d.authorize(root,proposal_path,approval,config,schema,adapter,a.commit,archive)
    receipt={'version':1,'runId':os.environ.get('GITHUB_RUN_ID') if a.prepare_only else a.validation_run_id,'repositoryCommit':a.commit,'proposalPath':a.proposal,'proposalSha256':d.digest(proposal),'schemaSha256':d.digest(schema),'archiveSha256':a.expected_sha256}
    if binding is not None:receipt.update(version=2,**binding)
    if a.prepare_only:
        d.require(isinstance(receipt['runId'],str) and receipt['runId'].isdigit(),'genuine CI run identity required')
        print('RELEASE_VALIDATION_RECEIPT='+d.canonical(receipt).decode('utf-8'))
        print('Protected validation passed; no tag/release created. Owner finalization requires this successful run ID and the same commit/checksum.')
        return
    verified_validation(config['repository'],a.validation_run_id,a.commit,receipt)
    # Only the real authenticated owner client can read this administration API.
    # This check stays mandatory immediately before any release mutation.
    immutable=json.loads(run('gh','api','repos/'+config['repository']+'/immutable-releases'))
    d.require(immutable.get('enabled') is True,'enable repository release immutability before publishing')
    tag='public-working-'+a.commit
    d.require(not run('git','ls-remote','--tags','origin','refs/tags/'+tag),'release tag already exists; never reuse')
    existing=subprocess.run(['gh','api','repos/'+config['repository']+'/releases/tags/'+tag],capture_output=True,text=True)
    d.require(existing.returncode!=0 and 'HTTP 404' in existing.stderr,'release exists or state could not be verified')
    notes=work/'release-notes.md'
    notes.write_text('Public-working release; **human-unreviewed** records: '+str(sum(r['humanReview']=='unreviewed' for r in proposal['records']))+'.\n\nOriginal English and project-authored structure/notes: '+proposal['rights']['originalContentLicense']+'. Source attribution, exclusions and accepted residual risks are in manifest.json. This does not grant third-party source rights or claim human scholarly approval or historical isnad authentication.\n\nWork scope: '+proposal['scope']['description']+'\n\nVerify the ZIP with the attached SHA-256 checksum. Protected validation run: https://github.com/'+config['repository']+'/actions/runs/'+a.validation_run_id+'\n',encoding='utf-8',newline='\n')
    created=json.loads(run('gh','api','repos/'+config['repository']+'/git/refs','--method','POST','-f','ref=refs/tags/'+tag,'-f','sha='+a.commit))
    d.require(created.get('object',{}).get('sha')==a.commit,'new tag target mismatch; reconcile remote state')
    print('Exact-commit tag created; preserve it on any later failure: '+tag,flush=True)
    run('gh','release','create',tag,str(archive),str(archive)+'.sha256','--repo',config['repository'],'--target',a.commit,'--verify-tag','--title',proposal['title'],'--notes-file',str(notes),'--draft','--prerelease')
    print('Draft created; preserve it if final publication fails: '+tag,flush=True)
    run('gh','release','edit',tag,'--repo',config['repository'],'--draft=false')
    actual=json.loads(run('gh','api','repos/'+config['repository']+'/releases/tags/'+tag))
    d.require(actual.get('immutable') is True and actual.get('draft') is False,'verify published release immutability manually')
    with (work/'publication-receipt.json').open('x',encoding='utf-8') as f:json.dump({'release':actual,'validationRunId':a.validation_run_id,'archiveSha256':d.sha(archive.read_bytes())},f,indent=2)
    print(actual['html_url'])

if __name__=='__main__':main()
