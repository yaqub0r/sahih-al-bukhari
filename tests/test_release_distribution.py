"""Synthetic release boundary, reproducibility and authorization tests."""
import copy,importlib.util,json,tempfile,unittest,zipfile
from pathlib import Path
from scripts import release_distribution as d
ROOT=Path(__file__).resolve().parents[1]

class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.config=d.read(ROOT/'tests/fixtures/distribution/config.json')
        self.proposal=d.read(ROOT/'tests/fixtures/distribution/proposal.json')
        self.schema,self.adapter=d.load_contract(ROOT,self.config)
        self.commit='a'*40
    def compile(self):return d.compile_files(self.proposal,self.config,self.schema,self.adapter,self.commit)
    def test_deterministic_zip_and_hashes(self):
        first=self.compile();second=self.compile();self.assertEqual(first,second)
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/'a.zip';b=Path(td)/'b.zip'
            d.archive_files(first,a);d.archive_files(second,b)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            with zipfile.ZipFile(a) as z:self.assertEqual(z.namelist(),sorted(first))
            self.assertEqual(Path(str(a)+'.sha256').read_text().split()[0],d.sha(a.read_bytes()))
    def test_new_output_exclusive(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'a.zip';d.archive_files(self.compile(),path)
            with self.assertRaises(FileExistsError):d.archive_files(self.compile(),path)
    def test_directory_rejects_tamper_missing_extra(self):
        for operation in ['tamper','missing','extra','reorder']:
            with self.subTest(operation=operation),tempfile.TemporaryDirectory() as td:
                root=Path(td)
                for k,v in self.compile().items():(root/k).write_bytes(v)
                d.validate_directory(root,self.config,self.schema,self.adapter)
                if operation=='tamper':(root/'reader.html').write_text('changed')
                elif operation=='missing':(root/'record-schema.json').unlink()
                elif operation=='extra':(root/'unexpected.json').write_text('{}')
                else:(root/'records.jsonl').write_bytes((root/'records.jsonl').read_bytes()+b'\n')
                with self.assertRaises((d.ReleaseError,ValueError)):d.validate_directory(root,self.config,self.schema,self.adapter)
    def test_identity_coverage_and_order(self):
        for operation in ['duplicate','missing','reverse','ordinal']:
            with self.subTest(operation=operation):
                original=copy.deepcopy(self.proposal)
                if operation=='duplicate':self.proposal['records']*=2
                elif operation=='missing':self.proposal['scope']['includedUnitIds']=[]
                elif operation=='reverse':self.proposal['scope']['includedUnitIds']=['other']
                else:self.proposal['records'][0]['sourceOrdinal']=True
                with self.assertRaises(d.ReleaseError):self.compile()
                self.proposal=original
    def test_nested_private_fields_and_paths_denied(self):
        for value in [{'receipt':'x'},{'safe':[{'hostCapture':'x'}]},'D:\\private\\book','file:///book','.runtime/book','github_pat_'+'x'*40]:
            with self.subTest(value=value),self.assertRaises(d.ReleaseError):d.safe_payload(value)
        self.proposal['records'][0]['unknown']={'arabic':'not allowlisted'}
        with self.assertRaises(d.ReleaseError):self.compile()
    def test_schema_fails_closed(self):
        for schema in [{'type':'string','format':'uri'},{'$ref':'https://example.org/schema'},{'type':'object','properties':{}}]:
            with self.assertRaises(d.ReleaseError):d.schema_check(schema,{})
        with self.assertRaises(d.ReleaseError):d.schema_check({'type':'integer'},True)
    def test_unused_schema_branches_are_checked(self):
        cases=[
            {'type':'object','additionalProperties':False,'properties':{'optional':{'type':'string','format':'uri'}}},
            {'type':'string','$defs':{'unused':{'type':'string','format':'uri'}}},
            {'anyOf':[{'type':'string'},{'type':'string','format':'uri'}]},
            {'type':'string','$defs':{'loop':{'$ref':'#/$defs/loop'}}},
        ]
        for schema in cases:
            with self.subTest(schema=schema),self.assertRaises(d.ReleaseError):d.lint_schema(schema)
        self.schema['properties']['optional']={'type':'string','format':'uri'}
        with self.assertRaises(d.ReleaseError):self.compile()
    def test_reader_escapes_untrusted_text(self):
        self.proposal['records'][0]['english']='<script>alert(1)</script>'
        data=self.compile()['reader.html']
        self.assertNotIn(b'<script>',data);self.assertIn(b'&lt;script&gt;',data)
    def test_candidate_explicitly_held(self):
        m=json.loads(self.compile()['manifest.json'])
        self.assertFalse(m['publicationEligible']);self.assertEqual(m['reviewCounts']['unreviewed'],1)
        self.assertEqual(m['canonicalPromotion'],'unused')
    def test_no_implicit_rights_or_authorization(self):
        self.proposal['rights']['status']='approved'
        with self.assertRaises(d.ReleaseError):self.compile()
        for enabled,example in [(False,False),(True,True)]:
            self.config.update(publicationEnabled=enabled,exampleOnly=example)
            with self.assertRaises(d.ReleaseError):d.authorize(ROOT,Path('missing'),Path('missing'),self.config,self.schema,self.adapter,self.commit,Path('missing'))
    def test_approval_binds_schema_proposal_and_archive(self):
        self.config.update(publicationEnabled=True,exampleOnly=False,approverIds=['owner'])
        self.proposal['rights'].update(status='approved',originalContentLicense='CC-BY-4.0')
        approval={'version':1,'releaseId':self.proposal['releaseId'],'proposalSha256':d.digest(self.proposal),'schemaSha256':d.digest(self.schema),'approvedBy':'owner','decisionId':'synthetic-reviewed','authorized':True}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=root/'proposal.json';a=root/'approval.json';z=root/'release.zip'
            p.write_bytes(d.canonical(self.proposal));a.write_bytes(d.canonical(approval));d.archive_files(self.compile(),z)
            d.authorize(ROOT,p,a,self.config,self.schema,self.adapter,self.commit,z)
            for key,value in [('authorized',False),('approvedBy','unknown'),('proposalSha256','b'*64),('schemaSha256','c'*64)]:
                invalid={**approval,key:value};a.write_bytes(d.canonical(invalid))
                with self.assertRaises(d.ReleaseError):d.authorize(ROOT,p,a,self.config,self.schema,self.adapter,self.commit,z)
            a.write_bytes(d.canonical(approval));z.write_bytes(z.read_bytes()+b'tamper')
            with self.assertRaises(d.ReleaseError):d.authorize(ROOT,p,a,self.config,self.schema,self.adapter,self.commit,z)
    def test_commit_and_contract_major_are_pinned(self):
        first=self.compile()
        self.commit='b'*40;self.assertNotEqual(first,self.compile())
        self.commit='invalid'
        with self.assertRaises(d.ReleaseError):self.compile()
        self.config['version']=2
        with self.assertRaises(d.ReleaseError):d.load_contract(ROOT,self.config)
    def test_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'test.json';p.write_text('{"x":1,"x":2}')
            with self.assertRaises(d.ReleaseError):d.read(p)
    def test_no_network_in_preparation(self):
        source=(ROOT/'scripts/release_distribution.py').read_text()
        self.assertNotIn('urlopen(',source);self.assertNotIn('gh release',source)

if __name__=='__main__':unittest.main()
