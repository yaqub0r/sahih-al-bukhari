"""Prefix contract major 2: unchanged v2 base plus typed textual continuation."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import bukhari_prefix_release_adapter_v1 as base
from scripts import hadith_supplements_v1 as supplements
from scripts import release_distribution as d
from scripts.hadith_structure import require

ROOT = Path(__file__).resolve().parents[1]
POLICY, FULL, REGISTRY = base.POLICY, base.FULL, base.REGISTRY
ARABIC_BASIS = base.ARABIC_BASIS
load_policy = base.load_policy
registration = base.registration
validate_registration = base.validate_registration
REQUIRED_CONTEXT = 'bukhari-l004871'
REQUIRED_ANTECEDENT = 'bukhari-l004862'


def validate_candidate(records, proposal):
    schema = d.read(ROOT/'contracts/distribution-v2/hadith-record.schema.json')
    stripped = [{k:v for k,v in r.items() if k != 'contextualIsnad'} for r in records]
    for record in stripped:
        d.schema_check(schema, record)
    # All original source, predecessor, rights, graph and integrity gates remain.
    # The extension never relaxes local-v2 admission.
    base.validate_candidate(stripped, {**proposal,'records':stripped})
    supplements.validate_contextual_isnads(records)
    index = {r['sourceUnitId']:r for r in records}
    if REQUIRED_CONTEXT in index:
        require('contextualIsnad' in index[REQUIRED_CONTEXT], 'known dual-source continuation requires typed context; base-only release forbidden')
        require(index[REQUIRED_CONTEXT]['contextualIsnad']['antecedentUnitId'] == REQUIRED_ANTECEDENT, 'known continuation must preserve its qualified antecedent')
    # Hash complete extended records too, including unchanged predecessors.
    from scripts.bukhari_release_adapter_v2 import validate_source_binding
    validate_source_binding(records, load_policy())


def validate_records(records, proposal):
    validate_candidate(records, proposal)
    validate_registration(proposal, d.read(ROOT/REGISTRY), load_policy())
