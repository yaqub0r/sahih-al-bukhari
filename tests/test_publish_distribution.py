"""Publisher preflight tests. All Git/GitHub operations are mocked."""
import copy,json,tempfile,types,unittest,contextlib,io
from pathlib import Path
from unittest.mock import patch
from scripts import publish_distribution as publisher
from scripts import release_distribution as d
ROOT=Path(__file__).resolve().parents[1]

class PublisherTests(unittest.TestCase):
    def execute(self,*,enabled=True,event='workflow_dispatch',main=True,checks=True,immutable=True,checksum=True,existing=False,prepare=False,validation=True,environment_approved=True,workflow=True,receipt_valid=True,config_path=None,config_receipt=True,closure_drift=False,untracked=False):
        config=d.read(ROOT/'tests/fixtures/distribution/config.json');config.update(publicationEnabled=enabled,exampleOnly=False,approverIds=['owner'])
        schema,adapter=d.load_contract(ROOT,config);proposal=d.read(ROOT/'tests/fixtures/distribution/proposal.json');proposal['rights'].update(status='approved',originalContentLicense='CC-BY-4.0')
        commit='a'*40;files=d.compile_files(proposal,config,schema,adapter,commit);commands=[]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'release/proposals').mkdir(parents=True);(root/'release/approvals').mkdir()
            selected=config_path or publisher.DEFAULT_CONFIG
            if selected in publisher.SUPPORTED_CONFIGS:(root/selected).write_bytes(d.canonical(config))
            for locator in [config['recordSchema'],config['adapter'],*publisher.SUPPORTED_CONFIGS.get(selected,())]:
                target=root/locator;target.parent.mkdir(parents=True,exist_ok=True);target.write_text('{}',encoding='utf-8')
            binding=publisher.config_binding(root,selected,config) if config_path is not None and selected in publisher.SUPPORTED_CONFIGS else None
            if closure_drift:(root/config['adapter']).write_text('changed',encoding='utf-8')
            prop=root/'release/proposals/synthetic-working-1.json';prop.write_bytes(d.canonical(proposal))
            approval={'version':1,'releaseId':proposal['releaseId'],'proposalSha256':d.digest(proposal),'schemaSha256':d.digest(schema),'approvedBy':'owner','decisionId':'synthetic-decision','authorized':True}
            (root/'release/approvals/synthetic-working-1.json').write_bytes(d.canonical(approval))
            archive=root/'expected.zip';d.archive_files(files,archive);expected=d.sha(archive.read_bytes()) if checksum else '0'*64
            def run(*args):
                commands.append(args)
                if untracked and args[:3]==('git','ls-files','--error-unmatch'):raise ValueError('untracked input')
                if args==('git','rev-parse','HEAD'):return commit
                if args==('git','rev-parse','origin/main'):return commit if main else 'b'*40
                if args[:3]==('git','status','--porcelain'):return ''
                if args[:3]==('git','ls-remote','--tags'):return ''
                if args[:3]==('gh','run','view'):
                    receipt={'version':1,'runId':'123','repositoryCommit':commit,'proposalPath':'release/proposals/synthetic-working-1.json','proposalSha256':d.digest(proposal),'schemaSha256':d.digest(schema),'archiveSha256':expected if receipt_valid else 'f'*64}
                    if binding is not None:receipt.update(version=2,**binding)
                    if not config_receipt:receipt['configPath']='release/other.config.json'
                    return 'prepare\tstep\t2026-01-01T00:00:00Z RELEASE_VALIDATION_RECEIPT='+json.dumps(receipt)
                if args[:2]==('gh','api'):
                    if args[2]=='user':return json.dumps({'id':1,'login':'owner','type':'User'})
                    if args[2].endswith('/approvals'):return json.dumps([{'state':'approved' if environment_approved else 'rejected','user':{'id':1},'environments':[{'name':'public-release'}]}])
                    if '/actions/runs/' in args[2]:return json.dumps({'event':'workflow_dispatch','head_branch':'main','head_sha':commit,'path':'.github/workflows/publish-public-distribution.yml' if workflow else 'other.yml','status':'completed','conclusion':'success' if validation else 'failure'})
                    if args[2].endswith('/check-runs'):return json.dumps({'check_runs':[{'name':'contracts-and-policy','conclusion':'success' if checks else 'failure'}]})
                    if args[2].endswith('/immutable-releases'):return json.dumps({'enabled':immutable})
                    if args[2].endswith('/git/refs'):return json.dumps({'object':{'sha':commit}})
                    return json.dumps({'immutable':True,'draft':False,'html_url':'https://example.invalid/synthetic'})
                return ''
            with patch.object(Path,'cwd',return_value=root),patch.object(publisher,'run',side_effect=run),patch.object(publisher.d,'load_contract',return_value=(schema,adapter)),patch.object(publisher.subprocess,'run',return_value=types.SimpleNamespace(returncode=0 if existing else 1,stderr='' if existing else 'HTTP 404')),patch.dict(publisher.os.environ,{'GITHUB_EVENT_NAME':event,'GITHUB_REF':'refs/heads/main','GITHUB_REPOSITORY':config['repository'],'GITHUB_ACTIONS':'','GITHUB_RUN_ID':'123'}),patch('sys.argv',['publish','--commit',commit,'--proposal','release/proposals/synthetic-working-1.json','--expected-sha256',expected]+(['--config',config_path] if config_path is not None else [])+(['--prepare-only'] if prepare else ['--validation-run-id','123'])),contextlib.redirect_stdout(io.StringIO()):
                try:publisher.main();error=None
                except ValueError as e:error=e
        return commands,error
    def test_valid_preflight_creates_draft_then_publishes(self):
        commands,error=self.execute();self.assertIsNone(error)
        mutations=[v for v in commands if v[:2]==('gh','release')]
        self.assertEqual([v[2] for v in mutations],['create','edit']);self.assertIn('--draft',mutations[0]);self.assertIn('--verify-tag',mutations[0])
        writes=[v for v in commands if '--method' in v]
        self.assertEqual(len(writes),1);self.assertIn('sha='+'a'*40,writes[0])
    def test_ci_preparation_has_no_admin_read_or_remote_mutation(self):
        commands,error=self.execute(prepare=True,immutable=False)
        self.assertIsNone(error)
        self.assertFalse(any(v[:2]==('gh','release') or '--method' in v or any('/immutable-releases' in part for part in v) for v in commands))
    def test_failures_never_mutate_remote(self):
        for args in [{'enabled':False},{'event':'push','prepare':True},{'main':False},{'checks':False},{'immutable':False},{'checksum':False},{'existing':True},{'validation':False},{'environment_approved':False},{'workflow':False},{'receipt_valid':False}]:
            with self.subTest(args=args):
                commands,error=self.execute(**args);self.assertIsNotNone(error)
                self.assertFalse(any(v[:2]==('gh','release') or '--method' in v for v in commands))

    def test_explicit_configs_bind_exact_selection_and_inputs(self):
        for locator in publisher.SUPPORTED_CONFIGS:
            with self.subTest(locator=locator):
                commands,error=self.execute(config_path=locator);self.assertIsNone(error)
                self.assertTrue(any(v[:2]==('gh','release') for v in commands))
    def test_config_and_contract_drift_fail_before_mutation(self):
        for args in [
            {'config_path':'release/distribution-prefix-v1.config.json','config_receipt':False},
            {'config_path':'release/distribution-prefix-v1.config.json','closure_drift':True},
            {'config_path':'release/distribution-prefix-v1.config.json','untracked':True},
            {'config_path':'release/other.config.json'},
            {'config_path':'../release/distribution.config.json'},
        ]:
            with self.subTest(args=args):
                commands,error=self.execute(**args);self.assertIsNotNone(error)
                self.assertFalse(any(v[:2]==('gh','release') or '--method' in v for v in commands))

    def test_supported_config_is_contained_and_all_contract_inputs_are_tracked(self):
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'release').mkdir()
            locator='release/distribution-prefix-v1.config.json'
            config=d.read(ROOT/'release/distribution-prefix-v1.config.json')
            (root/locator).write_bytes(d.canonical(config))
            tracked=Mock(side_effect=lambda root,path:path)
            with patch.object(publisher,'tracked',tracked),patch.object(d,'load_contract',return_value=({},object())):
                publisher.selected_config(root,locator)
            paths=[call.args[1].relative_to(root).as_posix() for call in tracked.call_args_list]
            self.assertEqual(set(paths),{locator,config['recordSchema'],config['adapter'],*publisher.SUPPORTED_CONFIGS[locator]})
            for name in [locator,config['recordSchema'],config['adapter'],*publisher.SUPPORTED_CONFIGS[locator]]:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
                if not path.exists():path.write_text('{}',encoding='utf-8')
            before=publisher.config_binding(root,locator,config)
            for name in publisher.SUPPORTED_CONFIGS[locator]:
                path=root/name;old=path.read_bytes();path.write_bytes(old+b' ')
                self.assertNotEqual(before,publisher.config_binding(root,locator,config));path.write_bytes(old)

if __name__=='__main__':unittest.main()
