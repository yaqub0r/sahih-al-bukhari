#!/usr/bin/env python3
"""Private, source-bound hadith structure companion; never alters translation files."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = ['source_segmentation', 'report_inventory', 'transmission_wording', 'narrator_identity',
          'ordered_paths', 'branches_and_gaps', 'quoted_people', 'heading_commentary', 'translation_alignment']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def closed(obj, fields):
    require(isinstance(obj, dict) and set(obj) == set(fields.split()), 'unexpected or missing fields: ' + fields)


def text(value):
    require(isinstance(value, str) and bool(value.strip()), 'nonempty text required')


def sha(value):
    return hashlib.sha256(value).hexdigest()


def file_hash(path):
    return sha(Path(path).read_bytes())


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)


def private(path):
    path = Path(path).resolve()
    runtime = (ROOT / '.runtime').resolve()
    require(path != runtime and path.is_relative_to(runtime), 'output must stay inside private .runtime')
    return path


def write_new(path, value):
    path = private(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def span(obj, size, nullable=False):
    a, b = obj['start'], obj['end']
    if nullable and a is None and b is None:
        return False
    require(type(a) is int and type(b) is int and 0 <= a < b <= size, 'unbound source span')
    return True


def indexed(items):
    require(isinstance(items, list), 'list required')
    result = {}
    for item in items:
        require(isinstance(item, dict), 'object required')
        text(item.get('id'))
        require(item['id'] not in result, 'duplicate occurrence ID')
        result[item['id']] = item
    return result


def validate(source, structure, ledger):
    closed(structure, 'version units')
    require(type(structure['version']) is int and structure['version'] == 1, 'unsupported version')
    require(isinstance(source, dict) and isinstance(ledger, dict), 'source and ledger objects required')
    authority = indexed(source.get('units'))
    units = indexed(structure['units'])
    require(list(units) == list(authority), 'exact source unit order and coverage required')
    identities = indexed(ledger.get('identities'))
    for uid, unit in units.items():
        closed(unit, 'id sha256 segments nodes edges paths reports status note')
        original = authority[uid]
        size = len(original['arabic'])
        require(unit['sha256'] == sha(original['arabic'].encode('utf-8')), 'unit digest drift')
        text(unit['note'])
        require(unit['status'] in ('complete', 'uncertain'), 'invalid unit status')
        require(isinstance(unit['segments'], list) and unit['segments'], 'segmentation required')
        cursor = 0
        for segment in unit['segments']:
            closed(segment, 'start end kind')
            span(segment, size)
            require(segment['start'] == cursor, 'segments must partition source in order')
            require(segment['kind'] in ('isnad', 'matn', 'comment', 'heading', 'uncertain'), 'invalid segment kind')
            cursor = segment['end']
        require(cursor == size, 'incomplete segmentation')
        nodes, edges, paths, reports = (indexed(unit[key]) for key in ('nodes', 'edges', 'paths', 'reports'))
        for node in nodes.values():
            closed(node, 'id kind start end nameId status note')
            text(node['note'])
            require(node['kind'] in ('compiler', 'narrator', 'gap'), 'invalid node kind')
            require(node['status'] in ('resolved', 'unresolved', 'implicit'), 'invalid node status')
            bound = span(node, size, True)
            if node['kind'] == 'compiler':
                require(not bound and node['status'] == 'implicit' and node['nameId'] is None, 'compiler must be explicitly implicit')
            elif node['kind'] == 'gap':
                require(node['status'] == 'unresolved' and node['nameId'] is None, 'gap must remain unresolved')
            else:
                require(bound and node['status'] != 'implicit', 'narrator must be source-bound')
                if node['status'] == 'resolved':
                    require(isinstance(node['nameId'], str) and node['nameId'] in identities, 'unknown stable narrator identity')
                    require(original['arabic'][node['start']:node['end']] in identities[node['nameId']]['arabicForms'], 'name span not registered')
                else:
                    require(node['nameId'] is None, 'unresolved narrator cannot assert identity')
        adjacency = {nid: [] for nid in nodes}
        for edge in edges.values():
            closed(edge, 'id from to start end mode note')
            text(edge['note'])
            require(isinstance(edge['from'], str) and isinstance(edge['to'], str) and edge['from'] in nodes and edge['to'] in nodes and edge['from'] != edge['to'], 'dangling or self link')
            require(edge['mode'] in ('explicit', 'implicit', 'suspended', 'uncertain'), 'invalid transmission mode')
            bound = span(edge, size, True)
            require(edge['mode'] != 'explicit' or bound, 'explicit wording requires exact phrase span')
            if nodes[edge['from']]['kind'] == 'gap' or nodes[edge['to']]['kind'] == 'gap':
                require(edge['mode'] in ('suspended', 'uncertain'), 'gap cannot imply an explicit link')
            adjacency[edge['from']].append(edge['to'])
        visited, active = set(), set()
        def visit(nid):
            require(nid not in active, 'transmission cycle')
            if nid in visited:
                return
            active.add(nid)
            for target in adjacency[nid]:
                visit(target)
            active.remove(nid)
            visited.add(nid)
        for nid in nodes:
            visit(nid)
        used_nodes, used_edges = set(), set()
        for path in paths.values():
            closed(path, 'id kind nodeIds edgeIds status note')
            text(path['note'])
            require(path['kind'] in ('primary', 'parallel', 'embedded', 'commentary', 'heading'), 'invalid path kind')
            require(path['status'] in ('complete', 'uncertain'), 'invalid path status')
            ns, es = path['nodeIds'], path['edgeIds']
            require(isinstance(ns, list) and ns and all(isinstance(n, str) for n in ns) and len(set(ns)) == len(ns) and all(n in nodes for n in ns), 'invalid path nodes')
            require(isinstance(es, list) and all(isinstance(e, str) for e in es) and len(es) == len(ns) - 1 and all(e in edges for e in es), 'invalid path edges')
            for index, eid in enumerate(es):
                require((edges[eid]['from'], edges[eid]['to']) == (ns[index], ns[index + 1]), 'path order disagrees with edges')
            if any(nodes[n]['status'] == 'unresolved' for n in ns) or any(edges[e]['mode'] in ('suspended', 'uncertain') for e in es):
                require(path['status'] == 'uncertain', 'incomplete structural claim')
            used_nodes.update(ns)
            used_edges.update(es)
        require(used_nodes == set(nodes) and used_edges == set(edges), 'orphan nodes or edges')
        referenced = set()
        end = 0
        for report in reports.values():
            closed(report, 'id start end pathIds status note')
            span(report, size)
            text(report['note'])
            require(report['start'] >= end, 'reports must be nonoverlapping in textual order')
            end = report['end']
            require(report['status'] in ('complete', 'uncertain'), 'invalid report status')
            ids = report['pathIds']
            require(isinstance(ids, list) and all(isinstance(p, str) for p in ids) and len(set(ids)) == len(ids) and all(p in paths for p in ids), 'dangling report path')
            if not ids or any(paths[p]['status'] == 'uncertain' for p in ids):
                require(report['status'] == 'uncertain', 'missing chain must be explicitly uncertain')
            for pid in ids:
                for nid in paths[pid]['nodeIds']:
                    node = nodes[nid]
                    if node['start'] is not None:
                        require(report['start'] <= node['start'] < node['end'] <= report['end'], 'narrator outside report')
                for eid in paths[pid]['edgeIds']:
                    edge = edges[eid]
                    if edge['start'] is not None:
                        require(report['start'] <= edge['start'] < edge['end'] <= report['end'], 'phrase outside report')
            referenced.update(ids)
        require(referenced == set(paths), 'unaccounted narration path')
        require(original['kind'] != 'report' or reports, 'every source report needs report inventory')
        for segment in unit['segments']:
            if segment['kind'] in ('isnad', 'matn'):
                require(any(r['start'] <= segment['start'] and segment['end'] <= r['end'] for r in reports.values()), 'unaccounted report text')
        if any(s['kind'] == 'uncertain' for s in unit['segments']) or any(r['status'] == 'uncertain' for r in reports.values()):
            require(unit['status'] == 'uncertain', 'unit conceals structural uncertainty')
    return structure


def render(source, structure):
    lines = ['PRIVATE HADITH STRUCTURE — unreviewed; textual order is not proof of historical contact.', '']
    originals = indexed(source['units'])
    for unit in structure['units']:
        arabic = originals[unit['id']]['arabic']
        lines.extend([unit['id'] + ' [' + unit['status'] + ']', unit['note']])
        for segment in unit['segments']:
            lines.append(f"  {segment['kind']} [{segment['start']}:{segment['end']}]: " + arabic[segment['start']:segment['end']])
        nodes, edges = indexed(unit['nodes']), indexed(unit['edges'])
        for report in unit['reports']:
            lines.append('  REPORT ' + report['id'] + ' [' + report['status'] + '] ' + report['note'])
            for pid in report['pathIds']:
                path = next(p for p in unit['paths'] if p['id'] == pid)
                lines.append('    PATH ' + pid + ' (' + path['kind'] + ', ' + path['status'] + '): ' + path['note'])
                for index, nid in enumerate(path['nodeIds']):
                    node = nodes[nid]
                    label = arabic[node['start']:node['end']] if node['start'] is not None else '[' + node['kind'] + ']'
                    lines.append('      ' + nid + ': ' + label + ' / ' + str(node['nameId']) + ' / ' + node['status'] + ' / ' + node['note'])
                    if index < len(path['edgeIds']):
                        edge = edges[path['edgeIds'][index]]
                        phrase = arabic[edge['start']:edge['end']] if edge['start'] is not None else '[no explicit source phrase]'
                        lines.append('        -> ' + edge['mode'] + ': ' + phrase + ' / ' + edge['note'])
    return '\n'.join(lines) + '\n'


def contract_hash():
    value = {'scriptSha256': file_hash(Path(__file__)),
             'specSha256': file_hash(ROOT / 'docs/translation/hadith-structure.md')}
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def extraction_input_hash(source, ledger):
    value = {'sourceSha256': file_hash(source), 'ledgerSha256': file_hash(ledger), 'contractSha256': contract_hash()}
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def audit_input_hash(source, translation, structure, ledger):
    value = {key + 'Sha256': file_hash(path) for key, path in
             (('source', source), ('translation', translation), ('structure', structure), ('ledger', ledger))}
    value['contractSha256'] = contract_hash()
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def validate_audit(structure, audit):
    closed(audit, 'verdict checkedUnitIds checks findings limits')
    require(audit['verdict'] == 'pass', 'independent audit hold blocks binding')
    require(isinstance(audit['limits'], list) and audit['limits'], 'audit limitations required')
    for limitation in audit['limits']:
        text(limitation)
    require(isinstance(audit['checkedUnitIds'], list) and isinstance(audit['checks'], list), 'audit arrays required')
    require(audit['checkedUnitIds'] == [u['id'] for u in structure['units']], 'incomplete audit unit coverage')
    require(audit['checks'] == CHECKS, 'incomplete audit checks')
    units = indexed(structure['units'])
    findings = indexed(audit['findings'])
    covered = set()
    for finding in findings.values():
        closed(finding, 'id unitId reportId status detail')
        require(finding['unitId'] in units, 'unknown audit unit')
        reports = indexed(units[finding['unitId']]['reports'])
        require(finding['reportId'] is None or finding['reportId'] in reports, 'unknown audit report')
        require(finding['status'] in ('resolved', 'human-only'), 'agent-actionable audit defect holds binding')
        text(finding['detail'])
        if finding['status'] == 'human-only':
            covered.add((finding['unitId'], finding['reportId']))
    for unit in units.values():
        uncertain = [r for r in unit['reports'] if r['status'] == 'uncertain']
        for report in uncertain:
            require((unit['id'], report['id']) in covered, 'uncertain report lacks audit disclosure')
        if unit['status'] == 'uncertain' and not uncertain:
            require((unit['id'], None) in covered, 'uncertain unit lacks audit disclosure')


def validate_receipt(receipt, host, stage, input_hash, output_hash):
    closed(receipt, 'stage sessionId context inputSha256 outputSha256 hostCaptureSha256')
    require(receipt['stage'] == stage and receipt['context'] == 'fresh', 'invalid companion stage/context')
    text(receipt['sessionId'])
    require(receipt['inputSha256'] == input_hash and receipt['outputSha256'] == output_hash, 'receipt digest drift')
    require(receipt['hostCaptureSha256'] == file_hash(host), 'host capture drift')
    capture = read(host)
    require(isinstance(capture, dict), 'normalized host capture object required')
    for key in ('stage', 'sessionId', 'context', 'inputSha256', 'outputSha256'):
        require(capture.get(key) == receipt[key], 'host capture/receipt disagreement')
    for key in ('provider', 'model', 'reasoning', 'turnId'):
        text(capture.get(key))
    require(capture.get('adapter') == 'codex-jsonl-v1', 'existing host adapter required')
    launch = capture.get('launch')
    require(isinstance(launch, dict) and launch.get('forkTurns') == 'none', 'fresh host launch required')
    require(all(launch.get(k) == capture[k] for k in ('provider', 'model', 'reasoning')), 'host launch/settings disagree')
    coordinator = capture.get('coordinator')
    require(isinstance(coordinator, dict), 'host coordinator metadata required')
    text(coordinator.get('sessionId'))
    require(coordinator['sessionId'] != receipt['sessionId'], 'worker cannot be its coordinator')
    # The existing adapter/coordinator qualifies authentic observed settings.
    # These consistency checks do not establish authenticity or approved methods.
    return receipt['sessionId']


ARTIFACTS = ('source', 'translation', 'structure', 'ledger', 'extractionReceipt', 'auditReceipt',
             'extractionHost', 'auditHost', 'audit', 'render')


def build_manifest(paths):
    require(set(paths) == set(ARTIFACTS), 'exact companion artifacts required')
    for path in paths.values():
        private(path)
    source, structure, ledger = (read(paths[k]) for k in ('source', 'structure', 'ledger'))
    validate(source, structure, ledger)
    translation = read(paths['translation'])
    require(isinstance(translation, dict), 'translation candidate object required')
    require(translation.get('status') == 'agent_complete' and translation.get('humanReview') == 'unreviewed', 'completed unreviewed candidate required')
    require(translation.get('sourceSha256') == file_hash(paths['source']), 'translation source digest mismatch')
    translated = indexed(translation.get('units'))
    originals = indexed(source['units'])
    require(list(translated) == list(originals), 'translation unit coverage/order mismatch')
    for uid, original in originals.items():
        require(translated[uid].get('arabic') == original['arabic'], 'translation Arabic differs from source')
        text(translated[uid].get('english'))
    validate_audit(structure, read(paths['audit']))
    require(Path(paths['render']).read_text(encoding='utf-8') == render(source, structure), 'render drift')
    extraction = validate_receipt(read(paths['extractionReceipt']), paths['extractionHost'], 'extraction',
                                  extraction_input_hash(paths['source'], paths['ledger']), file_hash(paths['structure']))
    audit = validate_receipt(read(paths['auditReceipt']), paths['auditHost'], 'structure-audit',
                            audit_input_hash(*(paths[k] for k in ('source', 'translation', 'structure', 'ledger'))),
                            file_hash(paths['audit']))
    require(extraction != audit, 'extraction and audit must use distinct fresh sessions')
    coordinators = {read(paths[key])['coordinator']['sessionId'] for key in ('extractionHost', 'auditHost')}
    require(extraction not in coordinators and audit not in coordinators, 'semantic worker cannot be a capture coordinator')
    return {'version': 1, 'kind': 'private-hadith-structure-companion', 'humanReview': 'unreviewed', 'contractSha256': contract_hash(),
            'artifacts': {key: {'path': str(private(paths[key]).relative_to((ROOT / '.runtime').resolve())).replace('\\', '/'),
                               'sha256': file_hash(paths[key])} for key in ARTIFACTS}}


def validate_manifest(manifest):
    closed(manifest, 'version kind humanReview contractSha256 artifacts')
    require(manifest['contractSha256'] == contract_hash(), 'companion contract drift')
    require(type(manifest['version']) is int and manifest['version'] == 1 and
            manifest['kind'] == 'private-hadith-structure-companion' and manifest['humanReview'] == 'unreviewed', 'invalid private manifest')
    closed(manifest['artifacts'], ' '.join(ARTIFACTS))
    paths = {}
    for key, record in manifest['artifacts'].items():
        closed(record, 'path sha256')
        text(record['path'])
        require(not Path(record['path']).is_absolute(), 'relative runtime locator required')
        path = private(ROOT / '.runtime' / record['path'])
        require(file_hash(path) == record['sha256'], 'companion artifact digest drift: ' + key)
        paths[key] = path
    require(build_manifest(paths) == manifest, 'manifest mismatch')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('validate', 'render', 'bind', 'validate-manifest', 'input-hashes'))
    for key in ARTIFACTS:
        parser.add_argument('--' + ''.join(('-' + c.lower()) if c.isupper() else c for c in key), dest=key)
    parser.add_argument('--manifest')
    parser.add_argument('--output')
    args = parser.parse_args()
    if args.command == 'validate-manifest':
        require(args.manifest is not None, 'manifest required')
        validate_manifest(read(args.manifest))
    elif args.command == 'bind':
        require(args.output is not None and all(getattr(args, k) for k in ARTIFACTS), 'all artifacts/output required')
        write_new(args.output, build_manifest({k: getattr(args, k) for k in ARTIFACTS}))
    elif args.command == 'input-hashes':
        require(args.source and args.ledger, 'source and ledger required')
        result = {'contractSha256': contract_hash(), 'extractionInputSha256': extraction_input_hash(args.source, args.ledger)}
        if args.translation and args.structure:
            result['auditInputSha256'] = audit_input_hash(args.source, args.translation, args.structure, args.ledger)
        print(json.dumps(result, sort_keys=True))
        return
    else:
        require(args.source and args.structure and args.ledger, 'source, structure and ledger required')
        source = read(args.source)
        structure = validate(source, read(args.structure), read(args.ledger))
        if args.command == 'render':
            require(args.output is not None, 'render requires private output')
            write_new(args.output, render(source, structure))
    print('Private companion validated; host qualification and scholarly review remain separate.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as error:
        import sys
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
