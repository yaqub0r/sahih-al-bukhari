"""Add-only, hash-bound private metadata and typed textual context supplements.

Validation checks structure and binding; independent captured semantic review is
required separately. Nothing here confers publication or historical authority.
"""
import copy
import re
import unicodedata
from scripts import hadith_structure as h
from scripts import release_distribution as d


def _version(value):
    h.require(type(value) is int and value == 1, 'supplement version')


def _literal(row, arabic):
    h.span(row, len(arabic))
    h.require(row['arabic'] == arabic[row['start']:row['end']], 'supplement literal/span mismatch')


def _unique(rows, key):
    h.require(isinstance(rows, list), 'supplement list required')
    keys = [key(row) for row in rows]
    h.require(len(keys) == len(set(keys)), 'duplicate supplement occurrence')


def _plain(value):
    return ''.join(c for c in unicodedata.normalize('NFC', value) if unicodedata.category(c) != 'Mn')


def validate_contextual_isnads(records):
    """Validate scoped references without merging identities or receipt events.

    All base records must already pass their unchanged v2 schema/graph adapter.
    This routine also works on private projected records with source ordinals.
    """
    h.require(isinstance(records, list), 'record list required')
    by_id = {r['sourceUnitId']: r for r in records}
    h.require(len(by_id) == len(records), 'duplicate contextual record identity')
    for current in records:
        context = current.get('contextualIsnad')
        if context is None:
            continue
        h.closed(context, 'version kind currentArabicSha256 antecedentUnitId antecedentArabicSha256 currentSourceNodeId cues branches uncertainty')
        _version(context['version'])
        h.require(context['kind'] == 'dual-source-continuation', 'unsupported textual context kind')
        h.text(context['uncertainty'])
        h.require(context['currentArabicSha256'] == current['arabicSha256'] == d.sha(current['arabic'].encode('utf-8')), 'current contextual Arabic drift')
        antecedent = by_id.get(context['antecedentUnitId'])
        h.require(antecedent is not None and antecedent['sourceOrdinal'] < current['sourceOrdinal'], 'context must reference an earlier record in this released prefix')
        h.require(context['antecedentArabicSha256'] == antecedent['arabicSha256'] == d.sha(antecedent['arabic'].encode('utf-8')), 'antecedent contextual Arabic drift')
        nodes = h.indexed(antecedent['isnad']['nodes'])
        edges = h.indexed(antecedent['isnad']['edges'])
        current_nodes = h.indexed(current['isnad']['nodes'])
        target = current_nodes.get(context['currentSourceNodeId'])
        h.require(target is not None and target['kind'] == 'narrator' and target['status'] == 'resolved' and target['nameId'] is not None, 'known current printed narrator required')
        _literal(target, current['arabic'])
        cues = context['cues']
        h.require(isinstance(cues, list) and len(cues) == 2, 'dual and attribution cues required')
        for cue, role, wording in zip(cues, ['dual-speakers', 'attribution'], ['قالا', 'وقال']):
            h.closed(cue, 'role start end arabic')
            _literal(cue, current['arabic'])
            h.require(cue['role'] == role and _plain(cue['arabic']) == wording, 'contextual ascription cue required; devotional hearing is not receipt')
        h.require(cues[0]['end'] <= cues[1]['start'] < cues[1]['end'] <= target['start'], 'context cue/source order')
        branches = context['branches']
        h.require(isinstance(branches, list) and len(branches) == 2, 'dual source requires exactly two branches')
        _unique(branches, lambda b: b['id'])
        terminals = []
        for branch in branches:
            h.closed(branch, 'id antecedentNodeIds antecedentEdgeIds currentSourceNodeId relation')
            h.text(branch['id'])
            h.require(branch['currentSourceNodeId'] == target['id'] and branch['relation'] == 'contextual-ascription', 'context cannot assert receipt or identity equality')
            ns, es = branch['antecedentNodeIds'], branch['antecedentEdgeIds']
            h.require(isinstance(ns, list) and len(ns) >= 2 and len(ns) == len(set(ns)) and all(n in nodes for n in ns), 'complete known ordered antecedent nodes required')
            h.require(isinstance(es, list) and len(es) == len(ns)-1 and len(es) == len(set(es)) and all(e in edges for e in es), 'complete ordered antecedent edges required')
            h.require(nodes[ns[0]]['kind'] == 'compiler', 'antecedent prefix must start at compiler root')
            for node_id in ns[1:]:
                node = nodes[node_id]
                h.require(node['kind'] == 'narrator' and node['status'] == 'resolved' and node['nameId'] is not None, 'context may not replace known sources with gaps')
                _literal(node, antecedent['arabic'])
            for i, edge_id in enumerate(es):
                edge = edges[edge_id]
                h.require(edge['from'] == ns[i] and edge['to'] == ns[i+1], 'broken antecedent ordered prefix')
                if edge['start'] is not None:
                    h.require(edge['arabicWording'] == antecedent['arabic'][edge['start']:edge['end']], 'antecedent edge wording mismatch')
            # Every edge belongs to a released ordered path; the second branch
            # may join an embedded path after their shared primary prefix.
            pairs = {(p['nodeIds'][i], p['nodeIds'][i+1], e) for p in antecedent['isnad']['paths'] for i,e in enumerate(p['edgeIds'])}
            h.require(all((ns[i], ns[i+1], e) in pairs for i,e in enumerate(es)), 'antecedent prefix outside released paths')
            terminals.append(ns[-1])
        h.require(len(set(terminals)) == 2, 'dual branches must preserve two distinct source occurrences')
    return records


def _project(source, graph):
    originals = h.indexed(source['units'])
    h.require(list(originals) == [g['id'] for g in graph['units']], 'source/local graph coverage drift')
    records = []
    for i,g in enumerate(graph['units']):
        arabic = originals[g['id']]['arabic']
        records.append({'sourceUnitId':g['id'], 'sourceOrdinal':i+1, 'arabic':arabic, 'arabicSha256':g['sha256'], 'isnad':{**g, 'nodes':[{**n,'arabic':None if n['start'] is None else arabic[n['start']:n['end']]} for n in g['nodes']], 'edges':[{**e,'arabicWording':None if e['start'] is None else arabic[e['start']:e['end']]} for e in g['edges']]}})
    return records


def validate_source_supplement(supplement, source_path, ledger_path, base_inventory_path, local_graph_path):
    h.closed(supplement, 'version sourceSha256 ledgerSha256 baseInventorySha256 localGraphSha256 addedNameOccurrences contextualIsnads')
    _version(supplement['version'])
    for key,path in [('sourceSha256',source_path), ('ledgerSha256',ledger_path), ('baseInventorySha256',base_inventory_path), ('localGraphSha256',local_graph_path)]:
        h.require(supplement[key] == h.file_hash(path), 'source supplement raw pin drift: '+key)
    source,ledger,inventory,graph = [h.read(p) for p in [source_path,ledger_path,base_inventory_path,local_graph_path]]
    h.require(inventory['sourceSha256'] == supplement['sourceSha256'] and inventory['ledgerSha256'] == supplement['ledgerSha256'], 'base name inventory binding drift')
    from scripts import hadith_structure_v2 as h2
    (h2 if graph['version'] == 2 else h).validate(source, graph, ledger)
    units,identities = h.indexed(source['units']),h.indexed(ledger['identities'])
    existing = {(r['unitId'],r['start'],r['end']) for r in inventory['alignmentMentions']}
    added = supplement['addedNameOccurrences']
    _unique(added, lambda r:(r['unitId'],r['start'],r['end']))
    for row in added:
        h.closed(row, 'unitId start end arabic nameId')
        h.require(row['unitId'] in units and row['nameId'] in identities, 'unregistered supplement source/name')
        _literal(row, units[row['unitId']]['arabic'])
        h.require(row['arabic'] in identities[row['nameId']]['arabicForms'], 'unregistered Arabic name form')
        h.require((row['unitId'],row['start'],row['end']) not in existing, 'name supplement is add-only')
    contexts = supplement['contextualIsnads']
    _unique(contexts, lambda r:r['unitId'])
    records = _project(source,graph);indexed = {r['sourceUnitId']:r for r in records}
    for row in contexts:
        h.closed(row, 'unitId contextualIsnad')
        h.require(row['unitId'] in indexed, 'unknown contextual unit')
        indexed[row['unitId']]['contextualIsnad'] = copy.deepcopy(row['contextualIsnad'])
    validate_contextual_isnads(records)
    return supplement


def validate_names_supplement(supplement, source_supplement, source_path, translation_path, ledger_path):
    h.closed(supplement, 'version sourceSupplementSha256 sourceSha256 translationSha256 ledgerSha256 addedNameAlignments')
    _version(supplement['version'])
    # The source supplement argument is a PATH: its exact raw bytes are bound.
    h.require(supplement['sourceSupplementSha256'] == h.file_hash(source_supplement), 'source supplement raw digest drift')
    src = h.read(source_supplement)
    for key,path in [('sourceSha256',source_path),('translationSha256',translation_path),('ledgerSha256',ledger_path)]:
        h.require(supplement[key] == h.file_hash(path), 'names supplement raw pin drift: '+key)
    h.require(src['sourceSha256'] == supplement['sourceSha256'] and src['ledgerSha256'] == supplement['ledgerSha256'], 'source/names supplement binding drift')
    source,translation,ledger = [h.read(p) for p in [source_path,translation_path,ledger_path]]
    units,targets,identities = h.indexed(source['units']),h.indexed(translation['units']),h.indexed(ledger['identities'])
    rows = supplement['addedNameAlignments']
    _unique(rows, lambda r:(r['unitId'],r['start'],r['end']))
    expected = {(r['unitId'],r['start'],r['end'],r['arabic'],r['nameId']) for r in src['addedNameOccurrences']}
    actual = set()
    for row in rows:
        h.closed(row, 'unitId start end arabic nameId englishStart englishEnd english rendering')
        h.require(row['unitId'] in units and row['unitId'] in targets and row['nameId'] in identities, 'unknown name alignment unit/identity')
        _literal(row, units[row['unitId']]['arabic'])
        english = targets[row['unitId']]['english'];a,b = row['englishStart'],row['englishEnd']
        h.require(type(a) is int and type(b) is int and 0 <= a < b <= len(english), 'invalid English name span')
        h.require(row['english'] == row['rendering'] == english[a:b], 'immutable English name alignment differs')
        identity = identities[row['nameId']]
        h.require(row['arabic'] in identity['arabicForms'], 'unregistered Arabic alignment form')
        registered = identity['english'] == row['rendering'] if ledger['version'] == 1 else {'arabic':row['arabic'],'english':row['rendering']} in identity['renderings']
        h.require(registered, 'unregistered English rendering')
        actual.add((row['unitId'],row['start'],row['end'],row['arabic'],row['nameId']))
    h.require(actual == expected, 'exact added source/name alignment inventory required')
    return supplement


def compile_supplement(source_supplement_path, names_supplement_path, source_path, translation_path, ledger_path, base_inventory_path, local_graph_path, source_proof, names_proof):
    """Caller must first qualify BOTH authentic independent semantic proofs.

    Proof objects are canonical-digest bound here, never interpreted as authority.
    The resulting rows retain complete spans and names without private paths.
    """
    source = validate_source_supplement(h.read(source_supplement_path), source_path, ledger_path, base_inventory_path, local_graph_path)
    names = validate_names_supplement(h.read(names_supplement_path), source_supplement_path, source_path, translation_path, ledger_path)
    h.require(isinstance(source_proof,dict) and source_proof and isinstance(names_proof,dict) and names_proof, 'both qualified semantic proofs required')
    units = {}
    def unit(uid):
        return units.setdefault(uid, {'unitId':uid,'addedNameOccurrences':[],'addedNameAlignments':[]})
    for row in source['addedNameOccurrences']:unit(row['unitId'])['addedNameOccurrences'].append(copy.deepcopy(row))
    for row in names['addedNameAlignments']:unit(row['unitId'])['addedNameAlignments'].append(copy.deepcopy(row))
    for row in source['contextualIsnads']:unit(row['unitId'])['contextualIsnad']=copy.deepcopy(row['contextualIsnad'])
    order = [u['id'] for u in h.read(source_path)['units']]
    return {'version':1,'sourceSupplementSha256':h.file_hash(source_supplement_path),'namesSupplementSha256':h.file_hash(names_supplement_path),'sourceProofSha256':d.digest(source_proof),'namesProofSha256':d.digest(names_proof),'units':[units[uid] for uid in order if uid in units]}


def project_contextual_isnads(records, compiled):
    """Strict allowlist projection; no proof, paths or names metadata is public."""
    h.closed(compiled, 'version sourceSupplementSha256 namesSupplementSha256 sourceProofSha256 namesProofSha256 units')
    _version(compiled['version'])
    for key in ['sourceSupplementSha256','namesSupplementSha256','sourceProofSha256','namesProofSha256']:d.hexsha(compiled[key])
    result = copy.deepcopy(records);indexed = {r['sourceUnitId']:r for r in result}
    h.require(len(indexed) == len(result), 'duplicate projection record')
    _unique(compiled['units'],lambda r:r['unitId'])
    for row in compiled['units']:
        h.require(set(row) in [set('unitId addedNameOccurrences addedNameAlignments'.split()),set('unitId addedNameOccurrences addedNameAlignments contextualIsnad'.split())], 'unexpected compiled unit fields')
        h.require(row['unitId'] in indexed, 'supplement outside projection')
        if 'contextualIsnad' in row:
            target = indexed[row['unitId']]
            h.require('contextualIsnad' not in target, 'context projection cannot overwrite')
            target['contextualIsnad'] = copy.deepcopy(row['contextualIsnad'])
    validate_contextual_isnads(result)
    return result
