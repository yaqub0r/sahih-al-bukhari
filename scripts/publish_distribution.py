#!/usr/bin/env python3
"""Explicit maintainer-dispatched publisher; never called by builds or tests."""
from pathlib import Path
import argparse, json, os, re, subprocess, tempfile, sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import release_distribution as d

def run(*args): return subprocess.check_output(args,text=True).strip()

def tracked(root,path):
    relative=path.relative_to(root).as_posix()
    run('git','ls-files','--error-unmatch','--',relative)
    return path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--commit',required=True);p.add_argument('--proposal',required=True);p.add_argument('--expected-sha256',required=True)
    a=p.parse_args();d.hexsha(a.commit,40);d.hexsha(a.expected_sha256)
    root=Path.cwd().resolve()
    d.require(os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch' and os.environ.get('GITHUB_REF')=='refs/heads/main','manual main dispatch required')
    config=d.read(root/'release/distribution.config.json');schema,adapter=d.load_contract(root,config)
    d.require(os.environ.get('GITHUB_REPOSITORY')==config['repository'],'workflow repository mismatch')
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
    immutable=json.loads(run('gh','api','repos/'+config['repository']+'/immutable-releases'))
    d.require(immutable.get('enabled') is True,'enable repository release immutability before publishing')
    tag='public-working-'+a.commit
    # Fail on API errors other than the known nonexistence of a release.
    refs=run('git','ls-remote','--tags','origin','refs/tags/'+tag)
    d.require(not refs,'release tag already exists; never reuse')
    existing=subprocess.run(['gh','api','repos/'+config['repository']+'/releases/tags/'+tag],capture_output=True,text=True)
    d.require(existing.returncode!=0 and 'HTTP 404' in existing.stderr,'release exists or state could not be verified')
    runtime=root/'.runtime';runtime.mkdir(exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='release-publish-',dir=runtime))
    archive=work/(config['bookId']+'-public-distribution-'+a.commit+'.zip')
    files=d.compile_files(proposal,config,schema,adapter,a.commit)
    d.archive_files(files,archive)
    verification=work/'verification.zip';d.archive_files(d.compile_files(proposal,config,schema,adapter,a.commit),verification)
    d.require(archive.read_bytes()==verification.read_bytes(),'reproducibility failed')
    d.require(d.sha(archive.read_bytes())==a.expected_sha256,'reviewed archive checksum mismatch')
    d.authorize(root,proposal_path,approval,config,schema,adapter,a.commit,archive)
    # All checks precede any remote mutation. A failed publication is reconciled
    # manually from the retained draft; never overwrite/retry an uncertain result.
    created=json.loads(run('gh','api','repos/'+config['repository']+'/git/refs','--method','POST','-f','ref=refs/tags/'+tag,'-f','sha='+a.commit))
    d.require(created.get('object',{}).get('sha')==a.commit,'new tag target mismatch; reconcile remote state')
    print('Exact-commit tag created; preserve it on any later failure: '+tag,flush=True)
    run('gh','release','create',tag,str(archive),str(archive)+'.sha256','--repo',config['repository'],'--target',a.commit,'--verify-tag','--title',proposal['title'],'--notes','Public-working distribution. Review status and rights are disclosed in manifest.json. Not canonical promotion. Verify the attached SHA-256 checksum.','--draft','--prerelease')
    print('Draft created; preserve it if final publication fails: '+tag,flush=True)
    run('gh','release','edit',tag,'--repo',config['repository'],'--draft=false')
    actual=json.loads(run('gh','api','repos/'+config['repository']+'/releases/tags/'+tag))
    d.require(actual.get('immutable') is True and actual.get('draft') is False,'verify published release immutability manually')
    print(actual['html_url'])

if __name__=='__main__':main()
