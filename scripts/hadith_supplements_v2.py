"""Additive name alignment for case and independently reviewed shared possessives.

This validates bindings and literal spans, never the semantic scope of a modifier.
Authentic independent source/names review remains the admitting caller's duty.
"""
import copy
import unicodedata
from scripts import hadith_structure as h
from scripts import hadith_supplements_v1 as legacy
from scripts import release_distribution as d

validate_source_supplement = legacy.validate_source_supplement
POSSESSIVES = frozenset(['his', 'my', 'your', 'our', 'their', 'her', 'its'])
ROW_FIELDS = 'unitId start end arabic nameId englishStart englishEnd english rendering'


def _version(value):
    h.require(type(value) is int and value == 2, 'names supplement version 2 required')


def _english_span(row, english):
    a, b = row['englishStart'], row['englishEnd']
    h.require(type(a) is int and type(b) is int and 0 <= a < b <= len(english), 'invalid English name/modifier span')
    h.require(isinstance(row['english'], str) and row['english'] == english[a:b], 'immutable English literal span differs')


def validate_names_supplement(supplement, source_supplement, source_path, translation_path, ledger_path):
    """Validate v2 names; source_supplement is its exact raw file PATH."""
    h.closed(supplement, 'version sourceSupplementSha256 sourceSha256 translationSha256 ledgerSha256 addedNameAlignments')
    _version(supplement['version'])
    h.require(supplement['sourceSupplementSha256'] == h.file_hash(source_supplement), 'source supplement raw digest drift')
    src = h.read(source_supplement)
    for key, path in [('sourceSha256', source_path), ('translationSha256', translation_path), ('ledgerSha256', ledger_path)]:
        h.require(supplement[key] == h.file_hash(path), 'names supplement raw pin drift: ' + key)
    h.require(src['sourceSha256'] == supplement['sourceSha256'] and src['ledgerSha256'] == supplement['ledgerSha256'], 'source/names supplement binding drift')
    source, translation, ledger = [h.read(p) for p in [source_path, translation_path, ledger_path]]
    units, targets, identities = h.indexed(source['units']), h.indexed(translation['units']), h.indexed(ledger['identities'])
    rows = supplement['addedNameAlignments']
    legacy._unique(rows, lambda r: (r['unitId'], r['start'], r['end']))
    expected = {(r['unitId'], r['start'], r['end'], r['arabic'], r['nameId']) for r in src['addedNameOccurrences']}
    actual = set()
    for row in rows:
        h.closed(row, ROW_FIELDS + (' sharedModifier' if 'sharedModifier' in row else ''))
        h.require(row['unitId'] in units and row['unitId'] in targets and row['nameId'] in identities, 'unknown name alignment unit/identity')
        legacy._literal(row, units[row['unitId']]['arabic'])
        english = targets[row['unitId']]['english']
        _english_span(row, english)
        h.text(row['rendering'])
        identity = identities[row['nameId']]
        h.require(row['arabic'] in identity['arabicForms'], 'unregistered Arabic alignment form')
        registered = identity['english'] == row['rendering'] if ledger['version'] == 1 else {'arabic': row['arabic'], 'english': row['rendering']} in identity['renderings']
        h.require(registered, 'unregistered canonical English rendering')
        literal = row['english']
        if 'sharedModifier' in row:
            modifier = row['sharedModifier']
            h.closed(modifier, 'kind englishStart englishEnd english reason')
            h.require(modifier['kind'] == 'shared-possessive', 'only shared possessives are supported')
            h.text(modifier['reason'])
            _english_span(modifier, english)
            h.require(modifier['english'].casefold() in POSSESSIVES, 'modifier must be one supported possessive word')
            def word_character(char):
                return char == '_' or unicodedata.category(char).startswith(('L', 'M', 'N'))
            start, end = modifier['englishStart'], modifier['englishEnd']
            h.require((start == 0 or not word_character(english[start-1])) and
                      (end == len(english) or not word_character(english[end])),
                      'shared possessive must be a whole word with Unicode boundaries')
            h.require(modifier['englishEnd'] <= row['englishStart'], 'shared modifier must precede and not overlap target')
            literal = modifier['english'] + ' ' + literal
        h.require(literal.casefold() == row['rendering'].casefold(), 'only case differences or an explicit shared possessive are allowed')
        actual.add((row['unitId'], row['start'], row['end'], row['arabic'], row['nameId']))
    h.require(actual == expected, 'exact added source/name alignment inventory required')
    return supplement


def compile_supplement(source_supplement_path, names_supplement_path, source_path, translation_path, ledger_path, base_inventory_path, local_graph_path, source_proof, names_proof):
    """Bind v1 source + v2 names after BOTH authentic proofs are qualified.

    Proofs are canonical-digest bound, not authenticated here. Preserve all
    affected rows, including modifier spans/reasons, without rewriting prose.
    """
    source = validate_source_supplement(h.read(source_supplement_path), source_path, ledger_path, base_inventory_path, local_graph_path)
    names = validate_names_supplement(h.read(names_supplement_path), source_supplement_path, source_path, translation_path, ledger_path)
    h.require(isinstance(source_proof, dict) and source_proof and isinstance(names_proof, dict) and names_proof, 'both qualified semantic proofs required')
    units = {}
    def unit(uid):
        return units.setdefault(uid, {'unitId': uid, 'addedNameOccurrences': [], 'addedNameAlignments': []})
    for row in source['addedNameOccurrences']:
        unit(row['unitId'])['addedNameOccurrences'].append(copy.deepcopy(row))
    for row in names['addedNameAlignments']:
        unit(row['unitId'])['addedNameAlignments'].append(copy.deepcopy(row))
    for row in source['contextualIsnads']:
        unit(row['unitId'])['contextualIsnad'] = copy.deepcopy(row['contextualIsnad'])
    order = [u['id'] for u in h.read(source_path)['units']]
    return {'version': 2, 'sourceSupplementSha256': h.file_hash(source_supplement_path), 'namesSupplementSha256': h.file_hash(names_supplement_path), 'sourceProofSha256': d.digest(source_proof), 'namesProofSha256': d.digest(names_proof), 'units': [units[uid] for uid in order if uid in units]}


def project_contextual_isnads(records, compiled):
    """Project compiled v2 through the unchanged legacy field allowlist.

    The temporary deep-copied version-1 VIEW is only a projection adapter, not
    semantic compilation or v1 proof qualification. The real v2 artifact and
    its proof/artifact digests are never rewritten, returned or rehashed here.
    Private name/modifier/proof/path data cannot enter public records.
    """
    h.closed(compiled, 'version sourceSupplementSha256 namesSupplementSha256 sourceProofSha256 namesProofSha256 units')
    _version(compiled['version'])
    for key in ['sourceSupplementSha256', 'namesSupplementSha256', 'sourceProofSha256', 'namesProofSha256']:
        d.hexsha(compiled[key])
    legacy._unique(compiled['units'], lambda row: row['unitId'])
    for row in compiled['units']:
        h.closed(row, 'unitId addedNameOccurrences addedNameAlignments' + (' contextualIsnad' if 'contextualIsnad' in row else ''))
        h.text(row['unitId'])
        h.require(isinstance(row['addedNameOccurrences'], list) and isinstance(row['addedNameAlignments'], list), 'compiled private name arrays required')
    projection_view = copy.deepcopy(compiled)
    projection_view['version'] = 1
    return legacy.project_contextual_isnads(records, projection_view)
