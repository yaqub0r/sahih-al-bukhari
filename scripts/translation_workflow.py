#!/usr/bin/env python3
"""Dependency-free translation coordinator. Never calls a model or publishes content."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = ('blind', 'critique', 'comparison', 'witness', 'adjudication', 'names', 'audit')
CHECKS = ('omissions', 'additions', 'negation', 'names', 'attribution', 'numbers',
          'structure', 'formulas', 'uncertainty', 'normalization')
MARKER = '<!-- book-translation:v1 '
AUDIT_CHECKS = CHECKS + ('source_alignment', 'public_eligibility', 'independent_expression', 'name_reconciliation')
REQUIRED_POLICIES = ('docs/translation/quality-workflow.md', 'docs/translation/agent-workflow.md',
                     'docs/translation/stage-contracts.md', 'scripts/translation_workflow.py')


class WorkflowError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise WorkflowError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                   separators=(',', ':')).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def closed(value, keys):
    require(isinstance(value, dict) and set(value) == set(keys),
            'unexpected or missing fields: ' + str(keys))


def text(value):
    require(isinstance(value, str) and bool(value.strip()), 'nonempty text required')


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r'[a-z0-9][a-z0-9._-]{2,100}', value),
            'invalid stable identifier')


def safe_path(root, relative):
    require(isinstance(relative, str) and not Path(relative).is_absolute(), 'relative path required')
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()) and path != root.resolve(), 'path escapes root')
    return path


def rights(record, commercial, witness=False):
    closed(record, ('id', 'edition', 'sha256', 'bytes', 'rightsBasis', 'attribution',
                    'publicationAllowed', 'translationAllowed', 'processingAllowed',
                    'commercialAllowed'))
    identifier(record['id'])
    for key in ('edition', 'rightsBasis', 'attribution'):
        text(record[key])
    require(re.fullmatch('[0-9a-f]{64}', record['sha256']) is not None, 'invalid source digest')
    require(type(record['bytes']) is int and record['bytes'] > 0, 'invalid byte length')
    for key in ('publicationAllowed', 'translationAllowed', 'processingAllowed', 'commercialAllowed'):
        require(type(record[key]) is bool, 'rights flags must be booleans')
    require(record['processingAllowed'], 'source processing not authorized')
    if not witness:
        require(record['publicationAllowed'] and record['translationAllowed'],
                'public source and translation eligibility required')
    require(not commercial or record['commercialAllowed'], 'commercial use not authorized')


def load_profile(path):
    profile = read(path)
    closed(profile, ('version', 'workId', 'repository', 'intendedUse', 'source', 'witnesses',
                     'englishComparison', 'methods', 'policyFiles', 'limitations', 'nameLedger', 'coordinatorMethod'))
    require(profile['version'] == 1, 'unsupported profile version')
    identifier(profile['workId'])
    require(re.fullmatch(r'[\w.-]+/[\w.-]+', profile['repository']) is not None, 'invalid repository')
    require(profile['intendedUse'] in ('commercial', 'noncommercial'), 'declare intended use')
    commercial = profile['intendedUse'] == 'commercial'
    rights(profile['source'], commercial)
    ids = []
    for witness in profile['witnesses']:
        rights(witness, commercial, witness=True)
        ids.append(witness['id'])
    require(len(set(ids)) == len(ids) and profile['source']['id'] not in ids, 'duplicate source identity')
    closed(profile['englishComparison'], ('enabled', 'witnessId', 'reason'))
    comp = profile['englishComparison']
    require(type(comp['enabled']) is bool, 'comparison switch must be boolean')
    text(comp['reason'])
    require((comp['enabled'] and comp['witnessId'] in ids) or
            (not comp['enabled'] and comp['witnessId'] is None), 'comparison witness missing')
    active = [s for s in STAGES if s != 'comparison' or comp['enabled']]
    require(set(profile['methods']) == set(active), 'approve each active semantic stage')
    for method in [*profile['methods'].values(), profile['coordinatorMethod']]:
        closed(method, ('id', 'provider', 'model', 'reasoning'))
        for value in method.values():
            text(value)
    require(isinstance(profile['limitations'], list), 'limitations must be a list')
    for value in profile['limitations']:
        text(value)
    require(set(REQUIRED_POLICIES) <= set(profile['policyFiles']), 'required local policy binding missing')
    for relative, expected in profile['policyFiles'].items():
        require(file_hash(safe_path(ROOT, relative)) == expected, 'policy binding drift: ' + relative)
    closed(profile['nameLedger'], ('path', 'sha256'))
    ledger_path = safe_path(ROOT, profile['nameLedger']['path'])
    require(file_hash(ledger_path) == profile['nameLedger']['sha256'], 'name ledger drift')
    ledger = read(ledger_path)
    closed(ledger, ('version', 'identities', 'decisions'))
    require(ledger['version'] == 1, 'unsupported name ledger')
    ids = []
    for name in ledger['identities']:
        closed(name, ('id', 'english', 'arabicForms'))
        identifier(name['id'])
        text(name['english'])
        require(isinstance(name['arabicForms'], list) and bool(name['arabicForms']), 'name Arabic forms required')
        for form in name['arabicForms']:
            text(form)
        ids.append(name['id'])
    require(len(ids) == len(set(ids)), 'duplicate ledger identity')
    for decision in ledger['decisions']:
        closed(decision, ('id', 'kind', 'fromIds', 'toIds', 'basis'))
        identifier(decision['id'])
        require(decision['kind'] in ('merge', 'split', 'correction'), 'invalid identity decision')
        require(bool(decision['fromIds']) and bool(decision['toIds']) and
                set(decision['fromIds'] + decision['toIds']) <= set(ids), 'identity decision has unknown IDs')
        text(decision['basis'])
    return profile


def verify_file(path, record):
    require(Path(path).stat().st_size == record['bytes'] and file_hash(path) == record['sha256'],
            'source hash/length mismatch')


def inventory(path, profile):
    verify_file(path, profile['source'])
    data = read(path)
    closed(data, ('units', 'exclusions'))
    require(isinstance(data['units'], list) and bool(data['units']), 'empty source inventory')
    ids = []
    for unit in data['units']:
        closed(unit, ('id', 'kind', 'location', 'arabic', 'contextIds', 'formulaSpans'))
        identifier(unit['id'])
        ids.append(unit['id'])
        require(unit['kind'] in ('heading', 'chain', 'report', 'comment', 'poetry', 'entry'),
                'unknown unit kind')
        text(unit['location'])
        text(unit['arabic'])
        require(isinstance(unit['contextIds'], list), 'context list required')
        end = 0
        for span in unit['formulaSpans']:
            closed(span, ('start', 'end', 'referent'))
            require(type(span['start']) is int and type(span['end']) is int and
                    end <= span['start'] < span['end'] <= len(unit['arabic']), 'invalid formula span')
            text(span['referent'])
            end = span['end']
    require(len(ids) == len(set(ids)), 'duplicate unit identity')
    for unit in data['units']:
        require(set(unit['contextIds']) <= set(ids) - {unit['id']}, 'unknown/self context')
    require(isinstance(data['exclusions'], list), 'explicit exclusion inventory required')
    for exclusion in data['exclusions']:
        closed(exclusion, ('location', 'reason'))
        text(exclusion['location'])
        text(exclusion['reason'])
    return data


def gh(repository, *arguments):
    result = subprocess.run(['gh', *arguments, '--repo', repository], text=True,
                            capture_output=True, check=False)
    require(result.returncode == 0, 'GitHub operation failed: ' + result.stderr.strip())
    return result.stdout


def assignments(profile):
    issues = json.loads(gh(profile['repository'], 'issue', 'list', '--state', 'open',
                           '--limit', '10000', '--json', 'number,body,assignees'))
    claims = []
    for issue in issues:
        if MARKER not in issue['body']:
            continue
        match = re.search(re.escape(MARKER) + r'(.*?) -->', issue['body'])
        require(match is not None, 'malformed assignment marker')
        claim = json.loads(match[1])
        closed(claim, ('workId', 'sourceSha256', 'unitIds'))
        if claim['workId'] == profile['workId']:
            claims.append({**claim, 'issue': issue['number'],
                           'assignees': [a['login'] for a in issue['assignees']]})
    return claims


def check_claim(profile, units, claims, issue=None):
    for claim in claims:
        if claim['issue'] != issue:
            require(not set(units) & set(claim['unitIds']), 'overlapping live assignment')
    if issue is not None:
        own = [c for c in claims if c['issue'] == issue]
        require(len(own) == 1 and own[0]['sourceSha256'] == profile['source']['sha256'] and
                own[0]['unitIds'] == units and bool(own[0]['assignees']), 'live claim missing or changed')


def select_scope(data, unit_ids):
    require(unit_ids and len(unit_ids) == len(set(unit_ids)), 'unique nonempty scope required')
    chosen = [u for u in data['units'] if u['id'] in unit_ids]
    require([u['id'] for u in chosen] == unit_ids, 'scope must follow source order and known IDs')
    require(not ({c for u in chosen for c in u['contextIds']} - set(unit_ids)),
            'scope must include governing context units; expand claim')
    return chosen


def prepare(profile_path, source_path, unit_ids, issue, claims, coordinator_session):
    profile = load_profile(profile_path)
    data = inventory(source_path, profile)
    chosen = select_scope(data, unit_ids)
    check_claim(profile, unit_ids, claims, issue)
    context_ids = {c for u in chosen for c in u['contextIds']} - set(unit_ids)
    require(not context_ids, 'scope must include governing context units; expand claim')
    text(coordinator_session)
    packet = {'version': 1, 'profileSha256': digest(profile), 'sourceSha256': profile['source']['sha256'],
              'coordinatorSessionId': coordinator_session,
              'issue': issue, 'units': chosen, 'context': [u for u in data['units'] if u['id'] in context_ids],
              'exclusions': data['exclusions'], 'humanReview': 'unreviewed'}
    packet['runId'] = digest(packet)
    return packet


def validate_packet(packet, profile):
    closed(packet, ('version', 'profileSha256', 'sourceSha256', 'issue', 'units', 'context', 'coordinatorSessionId',
                    'exclusions', 'humanReview', 'runId'))
    require(packet['profileSha256'] == digest(profile), 'profile drift')
    require(packet['sourceSha256'] == profile['source']['sha256'], 'source drift')
    require(packet['runId'] == digest({k: v for k, v in packet.items() if k != 'runId'}), 'packet drift')
    require(packet['humanReview'] == 'unreviewed', 'machine work cannot assert human approval')


def stages(profile):
    return [s for s in STAGES if s != 'comparison' or profile['englishComparison']['enabled']]


def stage_input(packet, profile, stage, previous):
    return digest({'packet': packet, 'profile': profile, 'stage': stage, 'previous': previous})


def translated_units(output, packet):
    require(isinstance(output, list) and len(output) == len(packet['units']), 'incomplete translation coverage')
    for candidate, source in zip(output, packet['units']):
        closed(candidate, ('id', 'english', 'formulaTargets'))
        require(candidate['id'] == source['id'], 'unit identity/order mismatch')
        text(candidate['english'])
        targets = candidate['formulaTargets']
        require(len(targets) == len(source['formulaSpans']), 'formula occurrence coverage mismatch')
        end = 0
        for target, span in zip(targets, source['formulaSpans']):
            closed(target, ('start', 'end'))
            require(type(target['start']) is int and type(target['end']) is int and
                    end <= target['start'] < target['end'] <= len(candidate['english']), 'invalid target span')
            require(candidate['english'][target['start']:target['end']] ==
                    source['arabic'][span['start']:span['end']], 'formula must retain exact Arabic form')
            end = target['end']


def findings(output, packet):
    require(isinstance(output, list), 'findings must be a list')
    ids = []
    units = {u['id']: u for u in packet['units']}
    for finding in output:
        closed(finding, ('id', 'unitId', 'category', 'detail', 'start', 'end'))
        identifier(finding['id'])
        ids.append(finding['id'])
        require(finding['unitId'] in units and finding['category'] in CHECKS, 'invalid finding scope')
        require(type(finding['start']) is int and type(finding['end']) is int and
                0 <= finding['start'] < finding['end'] <= len(units[finding['unitId']]['arabic']),
                'finding needs exact source span')
        text(finding['detail'])
    require(len(ids) == len(set(ids)), 'duplicate finding ID')


def all_findings(previous):
    return [f for s in ('critique', 'comparison') if s in previous for f in previous[s]['findings']]


def validate_output(stage, output, packet, profile, previous):
    unit_ids = [u['id'] for u in packet['units']]
    if stage == 'blind':
        closed(output, ('units',))
        translated_units(output['units'], packet)
    elif stage == 'critique':
        closed(output, ('checkedUnitIds', 'checks', 'findings'))
        require(output['checkedUnitIds'] == unit_ids and output['checks'] == list(CHECKS), 'incomplete Arabic critique')
        findings(output['findings'], packet)
    elif stage == 'comparison':
        closed(output, ('coverage', 'findings'))
        findings(output['findings'], packet)
        require(not {f['id'] for f in output['findings']} &
                {f['id'] for f in previous['critique']['findings']}, 'finding ID collision')
        coverage = output['coverage']
        require(isinstance(coverage, list), 'comparison coverage required')
        for unit in packet['units']:
            end = 0
            rows = [r for r in coverage if r.get('unitId') == unit['id']]
            for row in rows:
                closed(row, ('unitId', 'start', 'end', 'referenceLocation', 'status', 'findingIds'))
                require(type(row['start']) is int and type(row['end']) is int and
                        row['start'] == end < row['end'] <= len(unit['arabic']), 'comparison gap/overlap')
                require(row['status'] in ('equivalent', 'difference', 'reference-omits'), 'invalid comparison status')
                if row['status'] == 'reference-omits':
                    require(row['referenceLocation'] is None, 'omitted reference has no location')
                else:
                    text(row['referenceLocation'])
                known = {f['id'] for f in output['findings'] if f['unitId'] == unit['id']}
                require(set(row['findingIds']) <= known, 'unbound comparison finding')
                require(row['status'] == 'equivalent' or bool(row['findingIds']), 'difference needs finding')
                end = row['end']
            require(end == len(unit['arabic']), 'comparison omits Arabic material')
        require(all(r['unitId'] in unit_ids for r in coverage), 'unknown comparison unit')
        require({f['id'] for f in output['findings']} ==
                {i for r in coverage for i in r['findingIds']}, 'unmapped comparison finding')
    elif stage == 'witness':
        closed(output, ('decisions', 'notRequiredReason'))
        expected = [f['id'] for f in all_findings(previous)]
        require([d['findingId'] for d in output['decisions']] == expected, 'witness must address every finding')
        if not expected:
            text(output['notRequiredReason'])
        for decision in output['decisions']:
            closed(decision, ('findingId', 'status', 'basis', 'witnessIds', 'evidence'))
            require(decision['status'] in ('resolved', 'unresolved', 'unavailable'), 'invalid witness state')
            text(decision['basis'])
            require(set(decision['witnessIds']) <= {w['id'] for w in profile['witnesses']}, 'unregistered witness')
            require([e['witnessId'] for e in decision['evidence']] == decision['witnessIds'],
                    'witness retrieval evidence coverage mismatch')
            for evidence in decision['evidence']:
                closed(evidence, ('witnessId', 'status', 'query', 'location', 'sha256'))
                text(evidence['query'])
                require(evidence['status'] in ('retrieved', 'unavailable', 'no_match'), 'invalid retrieval status')
                if evidence['status'] == 'retrieved':
                    text(evidence['location'])
                    require(isinstance(evidence['sha256'], str) and
                            re.fullmatch('[0-9a-f]{64}', evidence['sha256']), 'passage hash required')
                else:
                    require(evidence['location'] is None and evidence['sha256'] is None,
                            'unavailable/no-match evidence cannot assert retrieved passage')
    elif stage == 'adjudication':
        closed(output, ('units', 'decisions'))
        translated_units(output['units'], packet)
        require([d['findingId'] for d in output['decisions']] ==
                [f['id'] for f in all_findings(previous)], 'adjudication must address every finding')
        for decision in output['decisions']:
            closed(decision, ('findingId', 'disposition', 'basis'))
            require(decision['disposition'] in ('corrected', 'retained', 'unresolved'), 'invalid adjudication')
            text(decision['basis'])
    elif stage == 'names':
        closed(output, ('checkedUnitIds', 'names'))
        require(output['checkedUnitIds'] == unit_ids, 'name audit coverage missing')
        sources = {u['id']: u['arabic'] for u in packet['units']}
        targets = {u['id']: u['english'] for u in previous['adjudication']['units']}
        ledger = {n['id']: n for n in read(safe_path(ROOT, profile['nameLedger']['path']))['identities']}
        for name in output['names']:
            closed(name, ('nameId', 'unitId', 'start', 'end', 'targetStart', 'targetEnd', 'english'))
            identifier(name['nameId'])
            require(name['unitId'] in sources, 'unknown name unit')
            for a, b, value in (('start', 'end', sources[name['unitId']]),
                                ('targetStart', 'targetEnd', targets[name['unitId']])):
                require(type(name[a]) is int and type(name[b]) is int and
                        0 <= name[a] < name[b] <= len(value), 'invalid name span')
            require(targets[name['unitId']][name['targetStart']:name['targetEnd']] == name['english'],
                    'name does not match final English')
            require(name['nameId'] in ledger and ledger[name['nameId']]['english'] == name['english'] and
                    sources[name['unitId']][name['start']:name['end']] in ledger[name['nameId']]['arabicForms'],
                    'name differs from registered project identity; review a new ledger revision')
    elif stage == 'audit':
        closed(output, ('checkedUnitIds', 'checks', 'publicEligible', 'unresolved'))
        require(output['checkedUnitIds'] == unit_ids and output['checks'] == list(AUDIT_CHECKS),
                'final independent audit coverage missing')
        require(output['publicEligible'] is True, 'public output eligibility failed')
        expected = [d['findingId'] for d in previous['adjudication']['decisions']
                    if d['disposition'] == 'unresolved']
        require([f['findingId'] for f in output['unresolved']] == expected, 'unresolved inventory mismatch')
        for finding in output['unresolved']:
            closed(finding, ('findingId', 'unitId', 'publicSummary', 'humanOnly'))
            require(finding['humanOnly'] is True, 'exhaust agent-actionable findings before completion')
            source_finding = next(f for f in all_findings(previous) if f['id'] == finding['findingId'])
            require(finding['unitId'] == source_finding['unitId'], 'unresolved unit mismatch')
            text(finding['publicSummary'])
        names = previous['names']['names']
        for name in names:
            require(all(n['english'] == name['english'] for n in names if n['nameId'] == name['nameId']),
                    'inconsistent durable name realization')


def validate_host(host, profile, packet, stage, input_hash, output_hash, sessions):
    # Selected host-written metadata is operational evidence, not a signature.
    closed(host, ('provider', 'model', 'reasoning', 'sessionId', 'context', 'stage',
                  'runId', 'inputSha256', 'outputSha256', 'launch', 'turnId', 'coordinator', 'adapter', 'coordinatorLaunch'))
    method = profile['methods'][stage]
    closed(host['launch'], ('provider', 'model', 'reasoning', 'forkTurns'))
    require(host['adapter'] == 'codex-jsonl-v1' and host['launch']['forkTurns'] == 'none',
            'explicit fresh-worker launch required')
    text(host['turnId'])
    closed(host['coordinator'], ('sessionId', 'turnId', 'provider', 'model', 'reasoning'))
    require(host['coordinator']['sessionId'] == packet['coordinatorSessionId'], 'coordinator identity drift')
    for value in host['coordinator'].values():
        text(value)
    closed(host['coordinatorLaunch'], ('provider', 'model', 'reasoning'))
    for field in ('provider', 'model', 'reasoning'):
        require(host['coordinator'][field] == host['coordinatorLaunch'][field] ==
                profile['coordinatorMethod'][field], 'unapproved/effective coordinator method mismatch')
    for field in ('provider', 'model', 'reasoning'):
        require(host[field] == method[field] == host['launch'][field], 'unapproved/effective method mismatch')
    text(host['sessionId'])
    require(host['sessionId'] not in sessions + [packet['coordinatorSessionId']] and
            host['context'] == 'fresh', 'independent fresh session required')
    require(host['stage'] == stage and host['runId'] == packet['runId'] and
            host['inputSha256'] == input_hash and host['outputSha256'] == output_hash,
            'stale host capture')


def observe_session(path, session_id, turn_id, fresh):
    """Adapt Al-Isabah's selected Codex JSONL metadata; retain no raw log text."""
    metadata, turns, selected = [], [], []
    try:
        with Path(path).open(encoding='utf-8') as handle:
            for line in handle:
                row = json.loads(line)
                require(isinstance(row, dict), 'invalid session record')
                payload = row.get('payload', {})
                if row.get('type') in ('session_meta', 'turn_context'):
                    require(isinstance(payload, dict), 'invalid host metadata')
                if row.get('type') == 'session_meta':
                    metadata.append(payload)
                elif row.get('type') == 'turn_context':
                    text(payload.get('turn_id'))
                    if payload['turn_id'] not in turns:
                        turns.append(payload['turn_id'])
                    if payload['turn_id'] == turn_id:
                        selected.append({'model': payload.get('model'), 'reasoning': payload.get('effort')})
    except (OSError, ValueError, TypeError, KeyError):
        raise WorkflowError('selected host metadata unreadable or malformed') from None
    require(len(metadata) == 1 and bool(selected), 'exact session and turn metadata required')
    meta = metadata[0]
    require(meta.get('id') == session_id, 'session identity mismatch')
    parent = meta.get('session_id', session_id)
    if parent != session_id:
        source = meta.get('source')
        subagent = source.get('subagent') if isinstance(source, dict) else None
        spawn = subagent.get('thread_spawn') if isinstance(subagent, dict) else None
        require(isinstance(parent, str) and meta.get('parent_thread_id') == parent and
                isinstance(spawn, dict) and spawn.get('parent_thread_id') == parent and
                type(spawn.get('depth')) is int and spawn['depth'] == 1 and
                isinstance(meta.get('agent_path'), str) and
                re.fullmatch(r'/root/[a-z0-9_]+', meta['agent_path']) and
                spawn.get('agent_path') == meta['agent_path'], 'parent/session identity mismatch')
    require(all(item == selected[0] for item in selected), 'effective settings changed within selected turn')
    for value in selected[0].values():
        text(value)
    text(meta.get('model_provider'))
    require(not fresh or (turns[0] == turn_id and not
                          (meta.get('forked_from_id') or meta.get('forked_from'))),
            'worker must start at first turn with no inherited context')
    return {'sessionId': session_id, 'turnId': turn_id, 'provider': meta['model_provider'], **selected[0]}


def capture_host(packet, profile, stage, previous, output, worker_log, worker_session,
                 worker_turn, coordinator_log, coordinator_turn, launch, coordinator_launch):
    worker = observe_session(worker_log, worker_session, worker_turn, fresh=True)
    coordinator = observe_session(coordinator_log, packet['coordinatorSessionId'], coordinator_turn, fresh=False)
    host = {**worker, 'context': 'fresh', 'stage': stage, 'runId': packet['runId'],
            'inputSha256': stage_input(packet, profile, stage, previous), 'outputSha256': digest(output),
            'launch': launch, 'coordinator': coordinator, 'adapter': 'codex-jsonl-v1',
            'coordinatorLaunch': coordinator_launch}
    sessions = []  # record() checks the full earlier-session set again.
    validate_host(host, profile, packet, stage, host['inputSha256'], host['outputSha256'], sessions)
    return host


def history(run, packet, profile):
    validate_packet(packet, profile)
    previous, sessions = {}, []
    missing = False
    for stage in stages(profile):
        path = run / (stage + '.json')
        if not path.exists():
            missing = True
            continue
        require(not missing, 'stage sequence gap')
        receipt = read(path)
        closed(receipt, ('inputSha256', 'output', 'outputSha256', 'host', 'hostSha256', 'methodId'))
        expected = stage_input(packet, profile, stage, previous)
        require(receipt['inputSha256'] == expected and receipt['outputSha256'] == digest(receipt['output']),
                'stale stage receipt')
        require(receipt['hostSha256'] == digest(receipt['host']) and
                receipt['methodId'] == profile['methods'][stage]['id'], 'host/method binding drift')
        validate_host(receipt['host'], profile, packet, stage, expected, receipt['outputSha256'], sessions)
        validate_output(stage, receipt['output'], packet, profile, previous)
        sessions.append(receipt['host']['sessionId'])
        previous[stage] = receipt['output']
    return previous, sessions


def record(run, packet, profile, stage, output, host):
    previous, sessions = history(run, packet, profile)
    require(len(previous) < len(stages(profile)) and stages(profile)[len(previous)] == stage, 'stage out of order')
    input_hash = stage_input(packet, profile, stage, previous)
    validate_host(host, profile, packet, stage, input_hash, digest(output), sessions)
    validate_output(stage, output, packet, profile, previous)
    receipt = {'inputSha256': input_hash, 'output': output, 'outputSha256': digest(output),
               'host': host, 'hostSha256': digest(host), 'methodId': profile['methods'][stage]['id']}
    write_new(run / (stage + '.json'), receipt)


def completed(run, packet, profile):
    previous, _ = history(run, packet, profile)
    require(list(previous) == stages(profile), 'autonomous stages incomplete')
    return previous


def render(packet, previous, profile):
    rows = ['<!doctype html><html lang="en"><meta charset="utf-8"><title>Bilingual working translation</title>',
            '<style>.pair{display:grid;grid-template-columns:1fr 1fr;gap:2rem}@media(max-width:600px){.pair{display:block}}</style>',
            '<body><h1>Working translation — human review: unreviewed</h1>']
    rows.append('<p>Source: ' + html.escape(profile['source']['edition'] + ' · ' +
                                         profile['source']['attribution']) + '</p>')
    for limitation in profile['limitations']:
        rows.append('<p>Limitation: ' + html.escape(limitation) + '</p>')
    for source, target in zip(packet['units'], previous['adjudication']['units']):
        rows.append('<section><h2>' + html.escape(source['id'] + ' · ' + source['location']) + '</h2>' +
                    '<div class="pair"><p>' + html.escape(target['english']) + '</p><p lang="ar" dir="rtl">' +
                    html.escape(source['arabic']) + '</p></div></section>')
    unresolved = [d['findingId'] for d in previous['adjudication']['decisions'] if d['disposition'] == 'unresolved']
    for finding in previous['audit']['unresolved']:
        rows.append('<p>' + html.escape(finding['unitId'] + ': ' + finding['publicSummary']) + '</p>')
    rows.append('<p>Unresolved finding IDs: ' + html.escape(', '.join(unresolved) or 'none') + '</p></body></html>')
    return '\n'.join(rows)


def submit(run, packet, profile, claims):
    check_claim(profile, [u['id'] for u in packet['units']], claims, packet['issue'])
    previous = completed(run, packet, profile)
    presentation = render(packet, previous, profile)
    require((run / 'review.html').read_text(encoding='utf-8') == presentation, 'presentation stale/missing')
    # Deliberate allowlist: no critique, reference wording, host metadata, private paths, or decision prose.
    return {'version': 1, 'workId': profile['workId'], 'runId': packet['runId'], 'issue': packet['issue'],
            'profileSha256': digest(profile), 'sourceSha256': packet['sourceSha256'],
            'status': 'agent_complete', 'humanReview': 'unreviewed', 'remainingAgentUnits': 0,
            'comparisonPerformed': profile['englishComparison']['enabled'],
            'source': {k: profile['source'][k] for k in ('id', 'edition', 'sha256', 'attribution')},
            'limitations': profile['limitations'],
            'units': [{'id': u['id'], 'kind': u['kind'], 'location': u['location'], 'arabic': u['arabic'],
                       'english': t['english'], 'formulaTargets': t['formulaTargets']} for u, t in
                      zip(packet['units'], previous['adjudication']['units'])],
            'names': previous['names']['names'],
            'unresolved': previous['audit']['unresolved'],
            'unresolvedFindingIds': [d['findingId'] for d in previous['adjudication']['decisions']
                                     if d['disposition'] == 'unresolved'],
            'stageHashes': {s: digest(previous[s]) for s in previous},
            'presentationSha256': hashlib.sha256(presentation.encode()).hexdigest()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('doctor', 'hydrate', 'status', 'claim', 'prepare',
                                            'stage-input', 'capture-host', 'record', 'validate', 'render', 'submit'))
    parser.add_argument('--profile', required=True)
    parser.add_argument('--source')
    parser.add_argument('--url')
    parser.add_argument('--units', nargs='+')
    parser.add_argument('--issue', type=int)
    parser.add_argument('--assignee')
    parser.add_argument('--run', default='.runtime/translation/run')
    parser.add_argument('--stage', choices=STAGES)
    parser.add_argument('--output')
    parser.add_argument('--host')
    parser.add_argument('--witness-file')
    parser.add_argument('--coordinator-session')
    parser.add_argument('--session-log')
    parser.add_argument('--session')
    parser.add_argument('--turn')
    parser.add_argument('--coordinator-log')
    parser.add_argument('--coordinator-turn')
    parser.add_argument('--launch')
    parser.add_argument('--coordinator-launch')
    args = parser.parse_args(argv)
    try:
        profile = load_profile(args.profile)
        run = Path(args.run).resolve()
        runtime = (ROOT / '.runtime').resolve()
        require(run.is_relative_to(runtime) and run != runtime, 'run must be below ignored .runtime/')
        if args.command == 'doctor':
            require(subprocess.run(['git', 'check-ignore', '-q', str(run / 'packet.json')], cwd=ROOT).returncode == 0,
                    '.runtime must be ignored')
            print('policy/rights/methods valid; trusted-host provenance; no model invoked')
        elif args.command == 'hydrate':
            require(args.url and args.url.startswith('https://'), 'HTTPS source URL required')
            path = run / 'source.json'
            require(not path.exists(), 'source destination exists')
            with urllib.request.urlopen(args.url, timeout=30) as response:
                data = response.read(profile['source']['bytes'] + 1)
            require(len(data) == profile['source']['bytes'] and hashlib.sha256(data).hexdigest() ==
                    profile['source']['sha256'], 'download differs from pinned source')
            run.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as handle:
                handle.write(data)
        elif args.command in ('status', 'claim', 'prepare'):
            claims = assignments(profile)
            if args.command == 'status':
                print(json.dumps(claims))
            else:
                require(args.source and args.units, '--source and --units required')
                data = inventory(args.source, profile)
                select_scope(data, args.units)
                if args.command == 'claim':
                    check_claim(profile, args.units, claims)
                    require(args.assignee, '--assignee required')
                    body = MARKER + json.dumps({'workId': profile['workId'], 'sourceSha256': profile['source']['sha256'],
                                               'unitIds': args.units}) + ' -->'
                    result = gh(profile['repository'], 'issue', 'create', '--title', 'Translate ' + profile['workId'],
                                '--body', body, '--assignee', args.assignee)
                    print(result)
                    created_issue = int(result.strip().rstrip('/').split('/')[-1])
                    check_claim(profile, args.units, assignments(profile), issue=created_issue)
                else:
                    require(args.issue is not None and args.issue > 0, 'assigned issue required')
                    packet = prepare(args.profile, args.source, args.units, args.issue, claims, args.coordinator_session)
                    write_new(run / 'packet.json', packet)
        else:
            packet = read(run / 'packet.json')
            previous, _ = history(run, packet, profile)
            if args.command == 'stage-input':
                require(args.stage in stages(profile) and len(previous) < len(stages(profile)) and
                        stages(profile)[len(previous)] == args.stage, 'not the next stage')
                payload = {'runId': packet['runId'], 'stage': args.stage,
                           'inputSha256': stage_input(packet, profile, args.stage, previous),
                           'packet': packet, 'previous': previous}
                if args.stage == 'comparison':
                    require(args.witness_file, 'comparison needs qualified witness file')
                    witness = next(w for w in profile['witnesses'] if w['id'] == profile['englishComparison']['witnessId'])
                    verify_file(args.witness_file, witness)
                    payload['reference'] = Path(args.witness_file).read_text(encoding='utf-8')
                print(json.dumps(payload, ensure_ascii=False))
            elif args.command == 'capture-host':
                require(all((args.stage, args.output, args.host, args.session_log, args.session, args.turn,
                             args.coordinator_log, args.coordinator_turn, args.launch,
                             args.coordinator_launch)), 'capture arguments missing')
                require(len(previous) < len(stages(profile)) and stages(profile)[len(previous)] == args.stage,
                        'not the next stage')
                host = capture_host(packet, profile, args.stage, previous, read(args.output), args.session_log,
                                    args.session, args.turn, args.coordinator_log, args.coordinator_turn,
                                    read(args.launch), read(args.coordinator_launch))
                destination = Path(args.host).resolve()
                require(destination.is_relative_to(runtime), 'host capture must remain private in .runtime/')
                write_new(destination, host)
            elif args.command == 'record':
                require(args.stage and args.output and args.host, '--stage --output --host required')
                if args.stage == 'comparison':
                    require(args.witness_file, 'comparison needs qualified witness file')
                    witness = next(w for w in profile['witnesses'] if w['id'] == profile['englishComparison']['witnessId'])
                    verify_file(args.witness_file, witness)
                record(run, packet, profile, args.stage, read(args.output), read(args.host))
            elif args.command == 'validate':
                completed(run, packet, profile)
                print('agent stages complete; humanReview=unreviewed; not a publication authorization')
            elif args.command == 'render':
                presentation = render(packet, completed(run, packet, profile), profile)
                path = run / 'review.html'
                with path.open('x', encoding='utf-8', newline='\n') as handle:
                    handle.write(presentation)
            elif args.command == 'submit':
                proposal = submit(run, packet, profile, assignments(profile))
                write_new(run / 'submission.json', proposal)
                print('Private submission saved. Review public eligibility before promotion; no GitHub write performed.')
        return 0
    except (WorkflowError, OSError, ValueError, KeyError, TypeError, StopIteration) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
