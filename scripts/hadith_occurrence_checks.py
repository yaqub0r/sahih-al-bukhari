"""Cross-check a hadith graph against qualified literal source occurrences.

These diagnostics supplement semantic review; they do not infer identities from
short-name strings or judge whether every transmission was extracted.
"""
from scripts import hadith_structure as h


def diagnostics(source, structure, inventory):
    """Requires validated source/graph and reviewed, source/ledger-bound inventory.

    Use validate_bound for file-level admission; this object-only function cannot
    reconstruct the original source-file hash. Never infer identity by string.
    """
    originals = h.indexed(source['units'])
    graphs = h.indexed(structure['units'])
    h.require(list(originals) == list(graphs), 'source/graph occurrence order differs')
    mentions = {}
    for row in inventory['alignmentMentions']:
        key = (row['unitId'], row['start'], row['end'])
        h.require(key not in mentions, 'ambiguous reviewed occurrence binding')
        unit = originals[row['unitId']]
        h.span(row, len(unit['arabic']))
        mentions[key] = row['nameId']
    result = []
    for uid, unit in originals.items():
        for node in graphs[uid]['nodes']:
            if node['kind'] != 'narrator' or node['start'] is None:
                continue
            expected = mentions.get((uid, node['start'], node['end']))
            if expected and (node['nameId'] != expected or node['status'] != 'resolved'):
                result.append({'kind': 'reviewed-narrator-identity', 'unitId': uid,
                               'occurrenceId': node['id'], 'expectedNameId': expected})
        for edge in graphs[uid]['edges']:
            if edge['start'] is None:
                continue
            # A protected devotional formula contains no historical receipt.
            # An enclosing phrase requires semantic review and is not rejected.
            if any(f['start'] <= edge['start'] < edge['end'] <= f['end']
                   for f in unit['formulaSpans']):
                result.append({'kind': 'transmission-inside-formula', 'unitId': uid,
                               'occurrenceId': edge['id'], 'start': edge['start'],
                               'end': edge['end']})
    return result



def validate_bound(source_path, structure_path, inventory_path, ledger_path):
    """Enforce file-level qualification before the supplemental occurrence gate."""
    inventory = h.read(inventory_path)
    h.require(inventory['sourceSha256'] == h.file_hash(source_path),
              'reviewed occurrence inventory source drift')
    h.require(inventory['ledgerSha256'] == h.file_hash(ledger_path),
              'reviewed occurrence inventory ledger drift')
    source, structure, ledger = (h.read(p) for p in
                                  (source_path, structure_path, ledger_path))
    if structure.get('version') == 2:
        from scripts import hadith_structure_v2 as engine
    else:
        engine = h
    engine.validate(source, structure, ledger)
    found = diagnostics(source, structure, inventory)
    h.require(not found, 'qualified occurrence conflicts: ' + repr(found))
    return True
