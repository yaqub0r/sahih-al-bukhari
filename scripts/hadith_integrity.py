"""Supplemental graph diagnostics; frozen private companion-v1 stays unchanged."""
import hashlib,json,re,unicodedata
from scripts import hadith_structure as h


def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()

def letter(value):return unicodedata.category(value).startswith(('L','M'))

def diagnostics(source,structure):
    originals=h.indexed(source['units']);graphs=h.indexed(structure['units']);h.require(list(originals)==list(graphs),'source/graph coverage mismatch')
    findings=[]
    for uid,g in graphs.items():
        arabic=originals[uid]['arabic'];nodes=h.indexed(g['nodes'])
        for report in g['reports']:
            for key in ['start','end']:
                pos=report[key]
                if 0<pos<len(arabic) and letter(arabic[pos-1]) and letter(arabic[pos]):
                    findings.append({'unitId':uid,'kind':'report-word-split','itemId':report['id'],'position':pos,'detail':'Report '+key+' splits a printed word or combining sequence.'})
        seen_nodes={}
        for node in g['nodes']:
            if node['kind']!='narrator' or node['start'] is None:continue
            key=(node['start'],node['end'])
            if key in seen_nodes:findings.append({'unitId':uid,'kind':'duplicate-narrator-occurrence','itemId':node['id'],'position':node['start'],'detail':'Same printed narrator occurrence already represented by '+seen_nodes[key]+'. Share the occurrence node.'})
            seen_nodes[key]=node['id']
        def physical(node):return tuple(node[key] for key in ['kind','start','end','nameId'])
        seen_edges={}
        for edge in g['edges']:
            if edge['start'] is None:continue
            key=(edge['start'],edge['end'],physical(nodes[edge['from']]),physical(nodes[edge['to']]),edge['mode'])
            if key in seen_edges:findings.append({'unitId':uid,'kind':'duplicate-physical-transmission','itemId':edge['id'],'position':edge['start'],'detail':'Identical printed phrase and physical endpoint roles already represented by '+seen_edges[key]+'. Share the edge; different coordinated recipients remain distinct.'})
            seen_edges[key]=edge['id']
    return findings


def validate(source,structure,ledger=None):
    if ledger is not None:h.validate(source,structure,ledger)
    findings=diagnostics(source,structure)
    h.require(not findings,'supplemental hadith integrity holds: '+json.dumps(findings,ensure_ascii=False))

# A deliberately broad candidate finder, NOT a semantic transmission parser.
# Exact positions reference unchanged source; normalized token text is used only
# to find possible cues. False positives must be classified by a source reader.
TOKEN=re.compile(r'[\u0621-\u065f\u0671-\u06d3]+')
CUE=re.compile(r'^(?:حدث|حديث|أحاديث|أخبر|اخبر|أنبأ|انبأ|سمع|يسمع|أسمع|اسمع|حفظ|أحفظ|احفظ|شهد|أشهد|اشهد|قال|قلت|قيل|يقول|تقول|يحدث|كتب|قرأت|قرأ|قرئ|يروي|روى|رواية|بلغ|ذكر|حكى|يحكي|عن$|أن$|أنه$|أنها$|أنهم$|أنك$|أراني|اراني)')

def cue_inventory(source):
    candidates=[]
    for unit in source['units']:
        for match in TOKEN.finditer(unit['arabic']):
            plain=''.join(c for c in match[0] if unicodedata.category(c)!='Mn').lstrip('وف')
            if CUE.search(plain):candidates.append({'id':unit['id']+'-'+str(match.start())+'-'+str(match.end()),'unitId':unit['id'],'start':match.start(),'end':match.end(),'arabic':match[0]})
    return {'version':1,'sourceCanonicalSha256':digest(source),'candidates':candidates}


def validate_cue_review(source,structure,inventory,review):
    h.require(inventory==cue_inventory(source),'cue inventory source/scanner drift')
    h.closed(review,'version inventorySha256 structureCanonicalSha256 candidates limits')
    h.require(type(review['version']) is int and review['version']==1 and review['inventorySha256']==digest(inventory) and review['structureCanonicalSha256']==digest(structure),'cue review binding drift')
    rows=h.indexed(review['candidates']);h.require(list(rows)==[v['id'] for v in inventory['candidates']],'cue review incomplete/out of order')
    h.require(isinstance(review['limits'],list) and review['limits'],'cue review limits required')
    for value in review['limits']:h.text(value)
    graphs=h.indexed(structure['units'])
    for candidate in inventory['candidates']:
        row=rows[candidate['id']];h.closed(row,'id classification graphRefs basis')
        h.require(row['classification'] in ['transmission','reported-speech','authorial-comment','reference','non-transmission','uncertain'],'unsupported cue classification');h.text(row['basis'])
        h.require(isinstance(row['graphRefs'],list),'cue graph reference list required')
        if row['classification']=='transmission':h.require(row['graphRefs'],'a transmission requires an explicit graph reference')
        for ref in row['graphRefs']:
            h.text(ref);kind,sep,key=ref.partition(':');h.require(sep and kind in ['nodes','edges','paths','reports','segments'],'unsupported graph reference')
            if kind=='segments':h.require(key.isdigit() and int(key)<len(graphs[candidate['unitId']]['segments']),'unknown segment index')
            else:h.require(key in h.indexed(graphs[candidate['unitId']][kind]),'unknown graph occurrence reference')
    return True


def validate_public_records(records):
    source={'units':[]};graph={'version':1,'units':[]}
    for r in records:
        source['units'].append({'id':r['sourceUnitId'],'arabic':r['arabic']})
        g=r['isnad'];graph['units'].append({'id':r['sourceUnitId'],'nodes':[{k:v for k,v in n.items() if k!='arabic'} for n in g['nodes']],'edges':[{k:v for k,v in e.items() if k!='arabicWording'} for e in g['edges']],'reports':g['reports']})
    validate(source,graph)
