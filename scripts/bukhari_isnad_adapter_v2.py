"""Complete-collection public graph semantics, including explicit reciprocal communications. Does not authenticate historical transmission."""
from pathlib import Path
import hashlib,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import hadith_structure_v2 as h

def validate_records(records,proposal):
    source={'units':[]};structure={'version':2,'units':[]};forms={}
    for r in records:
        arabic=r['arabic'];uid=r['sourceUnitId'];g=r['isnad']
        h.require(r['arabicSha256']==hashlib.sha256(arabic.encode('utf-8')).hexdigest(),'Arabic digest mismatch')
        source['units'].append({'id':uid,'kind':r['kind'],'arabic':arabic})
        segments=[];nodes=[];edges=[]
        for value in r['segments']:
            h.require(value['arabic']==arabic[value['start']:value['end']],'segment Arabic mismatch')
            segments.append({k:v for k,v in value.items() if k!='arabic'})
        for n in g['nodes']:
            h.require(n['arabic']==(None if n['start'] is None else arabic[n['start']:n['end']]),'narrator Arabic mismatch')
            nodes.append({k:v for k,v in n.items() if k!='arabic'})
            if n['nameId'] is not None:forms.setdefault(n['nameId'],set()).add(n['arabic'])
        for e in g['edges']:
            h.require(e['arabicWording']==(None if e['start'] is None else arabic[e['start']:e['end']]),'transmission Arabic mismatch')
            edges.append({k:v for k,v in e.items() if k!='arabicWording'})
        structure['units'].append({'id':uid,'sha256':r['arabicSha256'],'segments':segments,'nodes':nodes,'edges':edges,'paths':g['paths'],'reports':g['reports'],'status':g['status'],'note':g['note'],'reciprocalCommunications':g.get('reciprocalCommunications',[])})
        report_ids={x['id'] for x in g['reports']}
        for u in r['uncertainties']:
            h.require(u['reportId'] is None or u['reportId'] in report_ids,'unbound public uncertainty')
        for report in g['reports']:
            if report['status']=='uncertain':
                h.require(any(u['category']=='structure' and u['reportId']==report['id'] for u in r['uncertainties']),'uncertain report disclosure missing')
        if g['status']=='uncertain' and not any(v['status']=='uncertain' for v in g['reports']):
            h.require(any(u['category']=='structure' and u['reportId'] is None for u in r['uncertainties']),'uncertain unit disclosure missing')
        h.require(r['printedHadithNumber'] is None or r['kind']=='report','printed label must describe report')
    # This ledger only permits structural revalidation of released mentions.
    # Identity admission itself came from the separately audited private ledger.
    h.validate(source,structure,{'identities':[{'id':k,'arabicForms':sorted(v)} for k,v in forms.items()]})
    h.require(sum(r['printedHadithNumber'] is not None for r in records)==proposal['scope']['numberedReportCount'],'numbered report inventory mismatch')
