#!/usr/bin/env python3
"""Deterministic, opt-in book distributions. No network calls or publication."""
from __future__ import annotations
import argparse, hashlib, html, importlib.util, json, re, sys, zipfile
from pathlib import Path

class ReleaseError(ValueError):
    pass

def require(ok, message):
    if not ok: raise ReleaseError(message)

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def digest(value): return hashlib.sha256(canonical(value)).hexdigest()
def sha(data): return hashlib.sha256(data).hexdigest()
def pairs(rows):
    result = {}
    for key, value in rows:
        require(key not in result, 'duplicate JSON key: '+key)
        result[key] = value
    return result

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ReleaseError('non-finite JSON')))

def closed(value, fields, label='object'):
    require(isinstance(value, dict) and set(value)==set(fields.split()), 'closed '+label+' fields required')

def text(value): require(isinstance(value, str) and bool(value.strip()), 'nonempty text required')
def hexsha(value, length=64): require(isinstance(value,str) and re.fullmatch('[a-f0-9]{'+str(length)+'}',value), 'invalid hash')

def safe_payload(value):
    forbidden = {'prompt','prompts','evidence','rawfindings','hostcapture','sessionid','credentials','secret','token','privatepath','sourcepath','location','modeltrace','critique','receipt','logpath'}
    if isinstance(value,dict):
        for key, child in value.items():
            require(re.sub('[^a-z]','',key.lower()) not in forbidden, 'private/operational field prohibited: '+key)
            safe_payload(child)
    elif isinstance(value,list):
        for child in value: safe_payload(child)
    elif isinstance(value,str):
        require(not re.search(r'(?i)((?<![A-Za-z0-9])[a-z]:[\\/]|file://|(?:^|\s)/(?:home|users|tmp|mnt)/|\.runtime[\\/]|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_)',value), 'private locator or credential pattern prohibited')

def lint_schema(schema):
    """Validate every branch, including absent optional properties/unused defs."""
    require(isinstance(schema,dict),'schema object required')
    root=schema
    meta={'$schema','$id','$defs','title','description'}
    common={'type','const','enum'}
    specific={'object':{'properties','required','additionalProperties'},'array':{'items','minItems'},'string':{'minLength','pattern'},'integer':{'minimum'},'boolean':set(),'null':set()}
    def walk(node,active=()):
        require(isinstance(node,dict),'schema node must be object')
        if '$ref' in node:
            require(set(node)=={'$ref'} and isinstance(node['$ref'],str) and node['$ref'].startswith('#/$defs/'),'local refs only')
            key=node['$ref'][8:]
            require(key in root.get('$defs',{}) and key not in active,'unknown or recursive schema reference')
            walk(root['$defs'][key],(*active,key));return
        if 'anyOf' in node:
            require(set(node)=={'anyOf'} and isinstance(node['anyOf'],list) and node['anyOf'],'standalone nonempty anyOf required')
            for option in node['anyOf']:walk(option,active)
            return
        typ=node.get('type');require(isinstance(typ,str) and typ in specific,'supported schema type required')
        require(not set(node)-(meta|common|specific[typ]),'unsupported schema keyword')
        for key in ['$schema','$id','title','description']:
            if key in node:text(node[key])
        if '$schema' in node:require(node['$schema']=='https://json-schema.org/draft/2020-12/schema','unsupported schema dialect')
        if '$defs' in node:
            require(node is root and isinstance(node['$defs'],dict),'definitions must be at schema root')
            for key,value in node['$defs'].items():text(key);walk(value,(key,))
        if 'enum' in node:require(isinstance(node['enum'],list) and bool(node['enum']),'enum list required')
        if typ=='object':
            props=node.get('properties');required=node.get('required',[])
            require(node.get('additionalProperties') is False and isinstance(props,dict),'closed properties object required')
            require(isinstance(required,list) and all(isinstance(k,str) for k in required) and len(set(required))==len(required) and set(required)<=set(props),'invalid required list')
            for key,value in props.items():text(key);walk(value,active)
        if typ=='array':require('items' in node,'array items required');walk(node['items'],active)
        for key in ['minItems','minLength','minimum']:
            if key in node:require(type(node[key]) is int and (key=='minimum' or node[key]>=0),'integer schema bound required')
        if 'pattern' in node:
            text(node['pattern'])
            try:re.compile(node['pattern'])
            except re.error as error:raise ReleaseError('invalid schema pattern') from error
    walk(schema)

def schema_check(schema, value, root=None):
    """Small, fail-closed JSON Schema subset; unsupported keywords are errors."""
    root = schema if root is None else root
    allowed={'$schema','$id','$defs','$ref','title','description','type','properties','required','additionalProperties','items','minItems','minLength','minimum','enum','const','pattern','anyOf'}
    require(isinstance(schema,dict) and not set(schema)-allowed, 'unsupported schema keyword')
    if '$ref' in schema:
        require(set(schema)=={'$ref'} and schema['$ref'].startswith('#/$defs/'), 'only local definition refs supported')
        key=schema['$ref'][8:];require(key in root.get('$defs',{}),'unknown definition')
        return schema_check(root['$defs'][key],value,root)
    if 'anyOf' in schema:
        require(set(schema)=={'anyOf'},'anyOf must stand alone')
        for option in schema['anyOf']:
            try: schema_check(option,value,root);return
            except ReleaseError: pass
        raise ReleaseError('no schema alternative matched')
    if 'const' in schema: require(value==schema['const'] and type(value)==type(schema['const']),'constant mismatch')
    if 'enum' in schema: require(any(type(value)==type(v) and value==v for v in schema['enum']),'enum mismatch')
    typ=schema.get('type');require(typ in {'object','array','string','integer','boolean','null'},'schema type required')
    if typ=='object':
        require(isinstance(value,dict),'object required')
        require(schema.get('additionalProperties') is False,'all schema objects must be closed')
        props=schema.get('properties',{});required=schema.get('required',[])
        require(set(required)<=set(value)<=set(props),'missing or unknown record field')
        for k,v in value.items():schema_check(props[k],v,root)
    elif typ=='array':
        require(isinstance(value,list) and len(value)>=schema.get('minItems',0),'array size/type')
        for item in value:schema_check(schema['items'],item,root)
    elif typ=='string':
        require(isinstance(value,str) and len(value)>=schema.get('minLength',0),'string size/type')
        if 'pattern' in schema:require(re.search(schema['pattern'],value) is not None,'string pattern')
    elif typ=='integer':require(type(value) is int and value>=schema.get('minimum',-2**63),'integer range/type')
    elif typ=='boolean':require(type(value) is bool,'boolean required')
    else:require(value is None,'null required')

def contained(root, locator):
    text(locator);require('\\' not in locator and not Path(locator).is_absolute(),'relative POSIX locator required')
    require(not any(p in {'.','..'} for p in locator.split('/')),'unsafe locator')
    path=root/locator
    require(path.resolve().is_relative_to(root.resolve()),'locator escapes root')
    require(not any(p.is_symlink() for p in [path,*path.parents] if p!=root.parent),'symlink locator prohibited')
    return path

def load_contract(root, config):
    closed(config,'version bookId repository contractId recordSchema adapter publicationEnabled exampleOnly approverIds')
    require(type(config['version']) is int and config['version']==1 and type(config['publicationEnabled']) is bool and type(config['exampleOnly']) is bool,'invalid config version/flags')
    require(re.fullmatch('[a-z0-9][a-z0-9-]+',config['bookId']), 'invalid book ID')
    require(re.fullmatch('[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',config['repository']),'invalid repository')
    text(config['contractId']);require(isinstance(config['approverIds'],list) and all(isinstance(v,str) and v for v in config['approverIds']),'approver list')
    schema=read(contained(root,config['recordSchema']));lint_schema(schema)
    adapter_path=contained(root,config['adapter'])
    spec=importlib.util.spec_from_file_location('adopted_release_adapter',adapter_path)
    adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
    require(callable(getattr(adapter,'validate_records',None)),'adopted semantic validator required')
    return schema,adapter

PROPOSAL_FIELDS='version releaseId previousReleaseId bookId title sourceAuthority rights scope records'

def validate_proposal(proposal, config, schema, adapter):
    closed(proposal,PROPOSAL_FIELDS,'proposal');safe_payload(proposal);lint_schema(schema)
    require(type(proposal['version']) is int and proposal['version']==1 and proposal['bookId']==config['bookId'],'proposal version/book mismatch')
    for key in ['releaseId','previousReleaseId']:
        if proposal[key] is not None:require(re.fullmatch('[a-z0-9][a-z0-9.-]{2,100}',proposal[key]),'invalid release identity')
    require(proposal['releaseId'] is not None and proposal['releaseId']!=proposal['previousReleaseId'],'release must have new identity')
    text(proposal['title'])
    a=proposal['sourceAuthority'];closed(a,'id revision artifactSha256 edition attribution limitations')
    for k in ['id','revision','edition','attribution']:text(a[k])
    hexsha(a['artifactSha256']);require(isinstance(a['limitations'],list) and bool(a['limitations']),'source limits required')
    for v in a['limitations']:text(v)
    rights=proposal['rights'];closed(rights,'decisionId status originalContentLicense arabicBasis attribution excludedMaterial residualRisk')
    text(rights['decisionId']);require(rights['status'] in ['pending','approved'],'rights status')
    require(rights['originalContentLicense'] is None or rights['originalContentLicense'] in ['CC-BY-4.0','CC-BY-SA-4.0','CC0-1.0','CC-BY-NC-SA-4.0'],'explicit supported content license')
    if rights['status']=='approved':require(rights['originalContentLicense'] is not None,'approved rights need content license')
    for k in ['arabicBasis','attribution','residualRisk']:text(rights[k])
    require(isinstance(rights['excludedMaterial'],list),'excluded material list')
    for v in rights['excludedMaterial']:text(v)
    scope=proposal['scope'];closed(scope,'description completeWork includedUnitIds numberedReportCount')
    text(scope['description']);require(type(scope['completeWork']) is bool and type(scope['numberedReportCount']) is int and scope['numberedReportCount']>=0,'scope types')
    records=proposal['records'];require(isinstance(records,list) and records,'records required')
    ids=[];ordinals=[]
    for record in records:
        schema_check(schema,record);ids.append(record['sourceUnitId']);ordinals.append(record['sourceOrdinal'])
        require(record['humanReview'] in ['unreviewed','human-reviewed'],'human review state')
        require(record['machineState']=='agent_complete','incomplete machine record')
    require(len(set(ids))==len(ids) and ids==scope['includedUnitIds'],'exact ordered scope required')
    require(len(set(ordinals))==len(ordinals) and ordinals==sorted(ordinals),'unique increasing ordinals required')
    adapter.validate_records(records,proposal)

def contextual_reader(record, records):
    """Display the full referenced chains, not only opaque machine identifiers."""
    context = record.get('contextualIsnad')
    if context is None:
        return ''
    antecedent = records[context['antecedentUnitId']]
    nodes = {n['id']:n for n in antecedent['isnad']['nodes']}
    edges = {e['id']:e for e in antecedent['isnad']['edges']}
    current = next(n for n in record['isnad']['nodes'] if n['id'] == context['currentSourceNodeId'])
    esc = html.escape
    parts = ['<div class="contextual-isnad"><h3>Textual continuation from <a href="#'+esc(antecedent['sourceUnitId'], quote=True)+'">'+esc(antecedent['sourceUnitId'])+'</a></h3>', '<p>These are two contextual ascriptions to the distinct narrator occurrence printed here. They do not assert a new hearing event, identity merger, or historical contact.</p>', '<p>Current wording: <span lang="ar" dir="rtl">'+esc(' / '.join(c['arabic'] for c in context['cues']))+'</span></p>']
    for branch in context['branches']:
        parts.append('<h4>'+esc(branch['id'])+'</h4><ol>')
        for i,node_id in enumerate(branch['antecedentNodeIds']):
            node = nodes[node_id]
            label = node['arabic'] if node['arabic'] is not None else '[implicit compiler]'
            parts.append('<li><span lang="ar" dir="rtl">'+esc(label)+'</span> <small>'+esc(node_id)+'</small>')
            if i < len(branch['antecedentEdgeIds']):
                edge = edges[branch['antecedentEdgeIds'][i]]
                wording = edge['arabicWording'] if edge['arabicWording'] is not None else '[unprinted wording]'
                parts.append(' <span lang="ar" dir="rtl">'+esc(wording)+'</span> <small>'+esc(edge['mode'])+'</small>')
            parts.append('</li>')
        parts.append('<li>Contextual ascription: <span lang="ar" dir="rtl">'+esc(current['arabic'])+'</span> <small>distinct current occurrence '+esc(current['id'])+'</small></li></ol>')
    parts.append('<p>Uncertainty and limits: '+esc(context['uncertainty'])+'</p></div>')
    return ''.join(parts)


def reader(proposal):
    parts=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(proposal['title'])+'</title><style>body{max-width:980px;margin:2rem auto;padding:0 1rem;font:17px/1.6 system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere;unicode-bidi:plaintext}section{border-top:1px solid #ccc;margin-top:2rem}.arabic{font-size:1.3em}</style>', '<h1>'+html.escape(proposal['title'])+'</h1>', '<p>Public-working release candidate. Human review is disclosed per record. Textual chains do not certify historical continuity.</p>', '<h2>Rights and source limits</h2><pre>'+html.escape(json.dumps({'rights':proposal['rights'],'sourceAuthority':proposal['sourceAuthority'],'scope':{k:v for k,v in proposal['scope'].items() if k!='includedUnitIds'}},ensure_ascii=False,sort_keys=True,indent=2))+'</pre>']
    indexed_records = {r['sourceUnitId']:r for r in proposal['records']}
    for r in proposal['records']:
        parts+=['<section id="'+html.escape(r['sourceUnitId'],quote=True)+'"><h2>'+html.escape(r['sourceUnitId'])+'</h2><p>'+html.escape(r['humanReview'])+'</p>','<pre>'+html.escape(r['english'])+'</pre>','<pre class="arabic" lang="ar" dir="rtl">'+html.escape(r['arabic'])+'</pre>','<details><summary>Ordered structure and disclosed uncertainties</summary><pre>'+html.escape(json.dumps({k:v for k,v in r.items() if k not in ['arabic','english']},ensure_ascii=False,sort_keys=True,indent=2))+'</pre></details>'+contextual_reader(r,indexed_records)+'</section>']
    return ('\n'.join(parts)+'</html>\n').encode('utf-8')

def compile_files(proposal,config,schema,adapter,commit):
    hexsha(commit,40);validate_proposal(proposal,config,schema,adapter)
    records=b''.join(canonical(r)+b'\n' for r in proposal['records'])
    counts={state:sum(r['humanReview']==state for r in proposal['records']) for state in ['unreviewed','human-reviewed']}
    files={'records.jsonl':records,'record-schema.json':canonical(schema)+b'\n','reader.html':reader(proposal)}
    manifest={'version':1,'contractId':config['contractId'],'bookId':config['bookId'],'repository':config['repository'],'repositoryCommit':commit,'releaseId':proposal['releaseId'],'releaseClass':'public-working','canonicalPromotion':'unused','publicationEligible':proposal['rights']['status']=='approved','proposalSha256':digest(proposal),'proposal':{k:v for k,v in proposal.items() if k!='records'},'recordCount':len(proposal['records']),'reviewCounts':counts,'artifacts':{n:{'sha256':sha(b),'bytes':len(b)} for n,b in sorted(files.items())}}
    files['manifest.json']=canonical(manifest)+b'\n'
    files['release-closure.json']=canonical({'version':1,'releaseId':proposal['releaseId'],'previousReleaseId':proposal['previousReleaseId'],'repositoryCommit':commit,'artifacts':{n:{'sha256':sha(b),'bytes':len(b)} for n,b in sorted(files.items())}})+b'\n'
    return files

def validate_directory(directory,config,schema,adapter):
    directory=Path(directory)
    expected={'manifest.json','records.jsonl','record-schema.json','reader.html','release-closure.json'}
    require(directory.is_dir() and {p.name for p in directory.iterdir()}==expected,'missing/extra distribution artifact')
    require(all(p.is_file() and not p.is_symlink() for p in directory.iterdir()),'regular artifacts only')
    m=read(directory/'manifest.json')
    closed(m,'version contractId bookId repository repositoryCommit releaseId releaseClass canonicalPromotion publicationEligible proposalSha256 proposal recordCount reviewCounts artifacts','manifest')
    records=[json.loads(line,object_pairs_hook=pairs) for line in (directory/'records.jsonl').read_text(encoding='utf-8').splitlines()]
    proposal={**m['proposal'],'records':records}
    files=compile_files(proposal,config,schema,adapter,m['repositoryCommit'])
    for name,data in files.items():require((directory/name).read_bytes()==data,'distribution drift: '+name)
    return m

def archive_files(files, archive):
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_STORED) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16
            z.writestr(info,data)
    checksum=Path(str(archive)+'.sha256')
    with checksum.open('x',encoding='ascii',newline='\n') as f:f.write(sha(Path(archive).read_bytes())+'  '+Path(archive).name+'\n')

def authorize(root,proposal_path,approval_path,config,schema,adapter,commit,archive):
    require(config['publicationEnabled'] and not config['exampleOnly'],'publication disabled or template fixture')
    p=read(proposal_path);validate_proposal(p,config,schema,adapter)
    require(p['rights']['status']=='approved','rights decision pending')
    a=read(approval_path);closed(a,'version releaseId proposalSha256 schemaSha256 approvedBy decisionId authorized')
    require(type(a['version']) is int and a['version']==1 and a['authorized'] is True and a['approvedBy'] in config['approverIds'],'release approval authority')
    text(a['decisionId'])
    require(a['releaseId']==p['releaseId'] and a['proposalSha256']==digest(p) and a['schemaSha256']==digest(schema),'approval binding drift')
    # Compare the exact archive bytes, not merely its checksum sidecar.
    import io
    expected=io.BytesIO()
    with zipfile.ZipFile(expected,'w',compression=zipfile.ZIP_STORED) as z:
        for name,data in sorted(compile_files(p,config,schema,adapter,commit).items()):
            i=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));i.create_system=3;i.external_attr=0o100644<<16;z.writestr(i,data)
    require(Path(archive).read_bytes()==expected.getvalue(),'approved inputs/archive mismatch')
    return p

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['build','validate','authorize'])
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--config',default='release/distribution.config.json')
    for key in ['proposal','directory','archive','commit','approval']:parser.add_argument('--'+key)
    args=parser.parse_args();root=args.root.resolve();config=read(contained(root,args.config));schema,adapter=load_contract(root,config)
    if args.command=='build':
        require(all([args.proposal,args.directory,args.archive,args.commit]),'build arguments required')
        files=compile_files(read(args.proposal),config,schema,adapter,args.commit)
        directory=Path(args.directory);archive=Path(args.archive)
        for output in [directory,archive]:
            require(output.resolve().is_relative_to((root/'.runtime').resolve()) and output.resolve()!=(root/'.runtime').resolve(),'prepare outputs must stay in private .runtime')
            require(not output.is_symlink(),'symlink output prohibited')
        require(not directory.exists() and not archive.exists() and not Path(str(archive)+'.sha256').exists(),'exclusive new outputs required')
        directory.mkdir(parents=True)
        for name,data in files.items():(directory/name).write_bytes(data)
        archive.parent.mkdir(parents=True,exist_ok=True);archive_files(files,archive);validate_directory(directory,config,schema,adapter)
        print('Prepared '+sha(archive.read_bytes())+'; no publication performed')
    elif args.command=='validate':
        require(args.directory,'directory required');m=validate_directory(args.directory,config,schema,adapter);print('Validated '+m['releaseId'])
    else:
        require(all([args.proposal,args.approval,args.archive,args.commit]),'authorization arguments required')
        p=authorize(root,args.proposal,args.approval,config,schema,adapter,args.commit,args.archive);print(p['releaseId'])

if __name__=='__main__':
    try:main()
    except (ReleaseError,OSError,ValueError,KeyError,TypeError) as error:
        print('release validation failed: '+str(error),file=sys.stderr);sys.exit(1)
