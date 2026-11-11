"""Publisher preflight tests. All Git/GitHub operations are mocked."""
import copy,json,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import publish_distribution as publisher
from scripts import release_distribution as d
ROOT=Path(__file__).resolve().parents[1]

class PublisherTests(unittest.TestCase):
    def execute(self,*,enabled=True,event='workflow_dispatch',main=True,checks=True,immutable=True,checksum=True,existing=False):
        config=d.read(ROOT/'tests/fixtures/distribution/config.json');config.update(publicationEnabled=enabled,exampleOnly=False,approverIds=['owner'])
        schema,adapter=d.load_contract(ROOT,config);proposal=d.read(ROOT/'tests/fixtures/distribution/proposal.json');proposal['rights'].update(status='approved',originalContentLicense='CC-BY-4.0')
        commit='a'*40;files=d.compile_files(proposal,config,schema,adapter,commit);commands=[]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'release/proposals').mkdir(parents=True);(root/'release/approvals').mkdir()
            (root/'release/distribution.config.json').write_bytes(d.canonical(config))
            prop=root/'release/proposals/synthetic-working-1.json';prop.write_bytes(d.canonical(proposal))
            approval={'version':1,'releaseId':proposal['releaseId'],'proposalSha256':d.digest(proposal),'schemaSha256':d.digest(schema),'approvedBy':'owner','decisionId':'synthetic-decision','authorized':True}
            (root/'release/approvals/synthetic-working-1.json').write_bytes(d.canonical(approval))
            archive=root/'expected.zip';d.archive_files(files,archive);expected=d.sha(archive.read_bytes()) if checksum else '0'*64
            def run(*args):
                commands.append(args)
                if args==('git','rev-parse','HEAD'):return commit
                if args==('git','rev-parse','origin/main'):return commit if main else 'b'*40
                if args[:3]==('git','status','--porcelain'):return ''
                if args[:3]==('git','ls-remote','--tags'):return ''
                if args[:2]==('gh','api'):
                    if args[2].endswith('/check-runs'):return json.dumps({'check_runs':[{'name':'contracts-and-policy','conclusion':'success' if checks else 'failure'}]})
                    if args[2].endswith('/immutable-releases'):return json.dumps({'enabled':immutable})
                    if args[2].endswith('/git/refs'):return json.dumps({'object':{'sha':commit}})
                    return json.dumps({'immutable':True,'draft':False,'html_url':'https://example.invalid/synthetic'})
                return ''
            with patch.object(Path,'cwd',return_value=root),patch.object(publisher,'run',side_effect=run),patch.object(publisher.d,'load_contract',return_value=(schema,adapter)),patch.object(publisher.subprocess,'run',return_value=types.SimpleNamespace(returncode=0 if existing else 1,stderr='' if existing else 'HTTP 404')),patch.dict(publisher.os.environ,{'GITHUB_EVENT_NAME':event,'GITHUB_REF':'refs/heads/main','GITHUB_REPOSITORY':config['repository']}),patch('sys.argv',['publish','--commit',commit,'--proposal','release/proposals/synthetic-working-1.json','--expected-sha256',expected]):
                try:publisher.main();error=None
                except ValueError as e:error=e
        return commands,error
    def test_valid_preflight_creates_draft_then_publishes(self):
        commands,error=self.execute();self.assertIsNone(error)
        mutations=[v for v in commands if v[:2]==('gh','release')]
        self.assertEqual([v[2] for v in mutations],['create','edit']);self.assertIn('--draft',mutations[0]);self.assertIn('--verify-tag',mutations[0])
        writes=[v for v in commands if '--method' in v]
        self.assertEqual(len(writes),1);self.assertIn('sha='+'a'*40,writes[0])
    def test_failures_never_mutate_remote(self):
        for args in [{'enabled':False},{'event':'push'},{'main':False},{'checks':False},{'immutable':False},{'checksum':False},{'existing':True}]:
            with self.subTest(args=args):
                commands,error=self.execute(**args);self.assertIsNotNone(error)
                self.assertFalse(any(v[:2]==('gh','release') or '--method' in v for v in commands))

if __name__=='__main__':unittest.main()
