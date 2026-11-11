"""Deterministic OpenITI hadith inventory; private outputs only, no translation.

A report is a source paragraph including its complete chains and appended comments.
No semantic chain/body split is inferred. Source byte ranges and raw lines remain
in a separate lossless ledger; removal events are formatting/furniture only.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re

PAGE = re.compile(r'PageV(\d+)P(\d+)')
FURNITURE = re.compile(r'PageV\d+P\d+|\bms\d+\b|@QB@|@QE@|\\\s*\d+\s*\\|\*')
FORMULA = re.compile(r'صلى الله عليه وسلم|رضي الله (?:عنهما|عنهم|عنهن|عنها|عنه)|رحمه الله(?: تعالى)?|عليه(?:ما|م)? السلام|عز وجل|جل ذكره|سبحانه وتعالى|تبارك وتعالى|رحمهم الله')
FORMULA_CANDIDATE = re.compile(r'صلى|رضي|رحمه|رحمهم|السلام|سبحانه|تعالى|جل|عز')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def dump(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f'refusing to overwrite changed immutable output: {path.name}')
    path.write_bytes(data)
    return sha(data)

def inventory(raw):
    text = raw.decode('utf-8')
    lines = text.splitlines(keepends=True)
    units, exclusions, ledger, headings, findings = [], [], [], [], []
    page_events, numbers = [], []
    header = True
    byte_offset = 0
    active = None
    parts = []

    def finish():
        nonlocal active, parts
        if active is None:
            return
        arabic = ' '.join(parts)
        active['arabic'] = arabic
        active['formulaSpans'] = []
        for m in FORMULA.finditer(arabic):
            phrase = m.group()
            referent = ('prophet-muhammad' if phrase == 'صلى الله عليه وسلم'
                        else 'allah' if phrase in {'عز وجل', 'جل ذكره', 'سبحانه وتعالى', 'تبارك وتعالى'}
                        else 'unresolved-source-referent')
            active['formulaSpans'].append({'start': m.start(), 'end': m.end(), 'referent': referent})
            if referent == 'unresolved-source-referent':
                findings.append({'kind': 'formula-referent-needs-review', 'unitId': active['id'], 'start': m.start(), 'end': m.end()})
        for m in FORMULA_CANDIDATE.finditer(arabic):
            if not any(s['start'] <= m.start() < s['end'] for s in active['formulaSpans']):
                findings.append({'kind': 'possible-formula-needs-review', 'unitId': active['id'], 'start': m.start(), 'end': m.end()})
        if not arabic:
            if active['kind'] != 'comment':
                raise ValueError('empty substantive unit')
            for row in ledger:
                if row.get('unitId') == active['id']:
                    row['disposition'] = 'excluded'
                    del row['unitId']
                    exclusions.append({'location': f"line:{row['line']}", 'reason': 'marker-only formatting paragraph'})
            active, parts = None, []
            return
        units.append(active)
        active, parts = None, []

    for line_no, raw_line in enumerate(lines, 1):
        content = raw_line.rstrip('\r\n')
        entry = {'line': line_no, 'byteStart': byte_offset, 'byteEnd': byte_offset + len(raw_line.encode('utf-8')), 'raw': raw_line, 'events': []}
        byte_offset = entry['byteEnd']
        ledger.append(entry)
        if header:
            reason = 'OpenITI metadata header'
            if content == '#META#Header#End#':
                header = False
            entry['disposition'] = 'excluded'
            exclusions.append({'location': f'line:{line_no}', 'reason': reason})
            continue
        if not content.strip():
            entry['disposition'] = 'excluded'
            exclusions.append({'location': f'line:{line_no}', 'reason': 'blank formatting line'})
            continue
        h = re.match(r'^(###)\s+(\|+)\s*', content)
        p = re.match(r'^#\s+', content)
        cont = re.match(r'^~~', content)
        if h or p:
            finish()
            kind = 'heading' if h else 'comment'
            prefix = h.end() if h else p.end()
            number = re.match(r'(\d+)\s+', content[prefix:]) if p else None
            inferred_heading = bool(number and re.match(r'(?:ms\d+\s+)?باب(?:\s|$)', content[prefix + number.end():]))
            if inferred_heading:
                kind = 'heading'
                findings.append({'kind': 'chapter-heading-with-paragraph-marker', 'line': line_no})
                number = None
            if number:
                kind = 'report'
                numbers.append({'number': int(number[1]), 'line': line_no, 'unitId': f'bukhari-l{line_no:06d}'})
                prefix += number.end()
            if h or inferred_heading:
                level = len(h[2]) if h else 2
                headings[:] = [(depth, uid) for depth, uid in headings if depth < level]
            active = {'id': f'bukhari-l{line_no:06d}', 'kind': kind, 'location': f'lines:{line_no}-{line_no}', 'contextIds': [uid for _, uid in headings], 'formulaSpans': []}
            if h or inferred_heading:
                headings.append((level, active['id']))
            entry['events'].append({'start': 0, 'end': prefix, 'before': content[:prefix], 'after': '', 'rule': 'OpenITI paragraph/heading prefix and printed report-number metadata'})
        elif cont:
            if active is None:
                raise ValueError(f'orphan continuation at {line_no}')
            prefix = cont.end()
            entry['events'].append({'start': 0, 'end': prefix, 'before': content[:prefix], 'after': '', 'rule': 'OpenITI continuation prefix'})
        else:
            # Unknown source syntax is preserved rather than silently discarded.
            if active is None:
                active = {'id': f'bukhari-l{line_no:06d}', 'kind': 'comment', 'location': f'lines:{line_no}-{line_no}', 'contextIds': [uid for _, uid in headings], 'formulaSpans': []}
            prefix = 0
            findings.append({'kind': 'unrecognized-line-syntax-preserved', 'line': line_no})
        for m in PAGE.finditer(content):
            page_events.append({'line': line_no, 'start': m.start(), 'volume': int(m[1]), 'page': int(m[2]), 'marker': m.group()})
        # Events use offsets in the untouched raw line, excluding its newline.
        for m in FURNITURE.finditer(content, prefix):
            entry['events'].append({'start': m.start(), 'end': m.end(), 'before': m.group(), 'after': '', 'rule': 'OpenITI page/milestone/quotation/apparatus separator marker'})
        cursor, cleaned = prefix, []
        for event in entry['events'][1:] if prefix else entry['events']:
            cleaned.append(content[cursor:event['start']])
            cursor = event['end']
        cleaned.append(content[cursor:])
        intermediate = ''.join(cleaned)
        normalized = re.sub(r'\s+', ' ', intermediate).strip()
        entry.update({'disposition': 'unit', 'unitId': active['id'], 'normalized': normalized, 'whitespaceRule': 'collapse whitespace runs to one ASCII space, strip line edges, join nonempty lines with one ASCII space'})
        if normalized:
            parts.append(normalized)
        active['location'] = active['location'].split('-')[0] + f'-{line_no}'
    if header:
        raise ValueError('missing explicit header terminator')
    finish()
    counts = collections.Counter(n['number'] for n in numbers)
    max_number = max(counts, default=0)
    audit = {
        'sourceSha256': sha(raw), 'sourceBytes': len(raw), 'sourceLines': len(lines),
        'unitCounts': dict(collections.Counter(u['kind'] for u in units)),
        'printedReportNumbers': numbers,
        'missingPrintedNumbers': [n for n in range(1, max_number + 1) if n not in counts],
        'duplicatePrintedNumbers': {str(n): c for n, c in sorted(counts.items()) if c > 1},
        'nonIncreasingPrintedNumbers': [{'previous': a, 'current': b} for a, b in zip(numbers, numbers[1:]) if b['number'] <= a['number']],
        'pages': page_events, 'volumes': sorted({p['volume'] for p in page_events}),
        'headings': [{'id': u['id'], 'location': u['location'], 'arabic': u['arabic']} for u in units if u['kind'] == 'heading'],
        'findings': findings,
        'limitations': ['Structured transcription authority only; no same-edition facsimile verification.', 'Report units preserve entire source paragraphs including chains, embedded reports, follow-ups and comments; no inferred semantic split.', 'Heading-associated commentary remains separate and is retained in initial scope.', 'Formula recognition is conservative and incomplete; unresolved referents and candidates require independent Arabic review before translation.', 'Printed report numbers are metadata; stable IDs derive from pinned raw-line starts.', 'OpenITI cleaned source already omits paratext; importer cannot restore absent material.'],
    }
    return {'units': units, 'exclusions': exclusions}, {'version': 1, 'sourceSha256': sha(raw), 'lines': ledger}, audit

def first_scope(authority, audit):
    numbers = audit['printedReportNumbers']
    if [n['number'] for n in numbers[:8]] != list(range(1, 9)):
        raise ValueError('first-scope requires initial numbered reports 1 through 8')
    cutoff = next(i for i, u in enumerate(authority['units']) if u['id'] == numbers[7]['unitId'])
    # End before the next top-level section heading, so it is not stranded in
    # the scope for the first book. All material through report 7 is retained.
    seventh = next(i for i, u in enumerate(authority['units']) if u['id'] == numbers[6]['unitId'])
    following_headings = [i for i in range(seventh + 1, cutoff) if authority['units'][i]['kind'] == 'heading']
    if following_headings:
        cutoff = following_headings[0]
    units = authority['units'][:cutoff]
    selected = {u['id'] for u in units}
    if any(c not in selected for u in units for c in u['contextIds']):
        raise ValueError('scope not context closed')
    last_line = int(authority['units'][-1]['location'].split('-')[-1])
    next_line = int(authority['units'][cutoff]['location'].split(':')[1].split('-')[0])
    scoped_exclusions = [e for e in authority['exclusions'] if int(e['location'].split(':')[1]) < next_line]
    scoped_exclusions.append({'location': f'lines:{next_line}-{last_line}', 'reason': 'Outside the admitted Beginning of Revelation scope; retained in full-book authority, not omitted from book inventory.'})
    return {'units': units, 'exclusions': scoped_exclusions}, {'unitIds': [u['id'] for u in units], 'start': units[0]['location'], 'end': units[-1]['location'], 'nextUnitId': authority['units'][cutoff]['id'], 'reportNumbers': list(range(1, 8)), 'contextClosed': True, 'selectionRule': 'All substantive units from body start through report 7; stop at first subsequent heading, otherwise before report 8.'}

def apply_formula_review(authority, review, source_hash):
    """Apply independently reviewable exact occurrence inventories, never text edits."""
    if review['sourceSha256'] != source_hash:
        raise ValueError('formula review source mismatch')
    indexed = {u['id']: u for u in authority['units']}
    seen = set()
    for row in review['units']:
        if row['id'] in seen:
            raise ValueError('duplicate formula review unit')
        seen.add(row['id'])
        unit = indexed[row['id']]
        if sha(unit['arabic'].encode('utf-8')) != row['arabicSha256']:
            raise ValueError('formula review unit text mismatch')
        spans = row['formulaSpans']
        previous = 0
        for span in spans:
            if not (previous <= span['start'] < span['end'] <= len(unit['arabic'])) or not span['referent']:
                raise ValueError('invalid reviewed formula span')
            previous = span['end']
        if not {(x['start'], x['end']) for x in unit['formulaSpans']} <= {(x['start'], x['end']) for x in spans}:
            raise ValueError('formula review must preserve every inventoried occurrence')
        unit['formulaSpans'] = spans
    return authority


def private_output_path(output, repository_root):
    runtime = (repository_root / '.runtime').resolve()
    resolved = output.resolve()
    if resolved == runtime or not resolved.is_relative_to(runtime):
        raise ValueError('output must resolve inside this repository private .runtime storage')
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--formula-review', type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    if sha(raw) != args.expected_sha256:
        parser.error('raw source SHA-256 mismatch')
    # Prevent accidental tracked outputs: require an ignored private runtime root.
    try:
        args.output = private_output_path(args.output, Path(__file__).resolve().parents[1])
    except ValueError as exc:
        parser.error(str(exc))
    authority, ledger, audit = inventory(raw)
    if args.formula_review:
        review_raw = args.formula_review.read_bytes()
        authority = apply_formula_review(authority, json.loads(review_raw), sha(raw))
        audit['formulaReviewSha256'] = sha(review_raw)
        audit['formulaReviewNote'] = 'Review overlay resolves only its explicitly listed units; baseline findings remain as historical candidate evidence.'
    scope, boundary = first_scope(authority, audit)
    args.output.mkdir(parents=True, exist_ok=True)
    hashes = {name: dump(args.output / name, value) for name, value in [('authority.json', authority), ('alignment-ledger.json', ledger), ('audit.json', audit), ('scope.json', scope), ('scope-boundary.json', boundary)]}
    dump(args.output / 'manifest.json', {'version': 1, 'sourceSha256': sha(raw), 'parserSha256': sha(Path(__file__).read_bytes()), 'outputs': hashes})
    print(json.dumps({'unitCounts': audit['unitCounts'], 'sourceSha256': sha(raw), 'scopeUnits': len(scope['units']), 'missingNumbers': len(audit['missingPrintedNumbers']), 'duplicateNumbers': audit['duplicatePrintedNumbers'], 'findings': len(audit['findings']), 'outputs': hashes}, indent=2))

if __name__ == '__main__':
    main()

