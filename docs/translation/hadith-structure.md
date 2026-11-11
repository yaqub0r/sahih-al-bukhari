# Private hadith structure companion, version 1

This contract supplements immutable translation candidates. It changes none of
source authority, translation submission, or public metadata version 1. All real
text, structure, name occurrences, receipts and renderings remain in ignored
`.runtime/`. It is not a book-text distribution schema. No public release,
human scholarly approval or historical chain authentication follows validation.

## Extraction record

The JSON root is exactly `{version: 1, units: [...]}`. Units follow the exact
source authority order with no omissions, additions or duplicate IDs. All spans
are Python Unicode code points, start inclusive and end exclusive, against the
unchanged authority unit's `arabic`. `sha256` hashes that string's UTF-8 bytes.
Do not normalize spelling, punctuation, whitespace or transmission wording.

Every object is closed: unknown and missing fields fail validation. Required
notes are nonempty explanations, not additional authority text.

Each unit has exactly `id, sha256, segments, nodes, edges, paths, reports,
status, note`. Unit `status` is `complete` or `uncertain`. Complete describes
extraction of textual structure, never proof that transmitters met or that a
historical chain is connected.

- Segment: `{start, end, kind}`, with kind `isnad|matn|comment|heading|uncertain`.
  Segments partition every source character without overlap or gaps, including
  separators and incidental material. Split at report boundaries where needed.
- Node: `{id, kind, start, end, nameId, status, note}`. Kind is
  `compiler|narrator|gap`; status is `resolved|unresolved|implicit`. Narrator
  occurrences have real nonempty source spans. Resolved occurrences use a frozen
  ledger identity ID and an exact registered `arabicForms` match; unresolved
  occurrences have null nameId. Repeated mentions are separate occurrence nodes
  even if their durable identity agrees. Compiler roots are optional, unprinted,
  null-span, null-nameId, explicitly `implicit` nodes. Never use them to imply
  unprinted historical contact. A gap has null nameId, unresolved status, and
  either an exact source cue span or null spans for an unprinted missing link.
  One gap may represent an unknown number of missing transmitters. Never guess
  identities or cardinality.
- Edge: `{id, from, to, start, end, mode, note}`. Direction follows the text's
  ordered narration from narrator to the source attributed to that narrator.
  Mode is `explicit|implicit|suspended|uncertain`. Exact contiguous transmission
  phrase spans are mandatory for explicit links and may also accompany other
  modes when there is an attested cue. Both offsets are null only when no
  printed phrase is available; explain why in note. Include the entire attested
  transmission phrase, without swallowing narrator names or matn. Do not convert
  ordinary quoted speech into a transmission link. Edges involving gap nodes
  must be suspended or uncertain. No self-links, dangling links or cycles.
- Path: `{id, kind, nodeIds, edgeIds, status, note}`. Kind is
  `primary|parallel|embedded|commentary|heading`; status complete or uncertain.
  Each path has one or more ordered node IDs and exactly one edge between each
  consecutive pair. Every edge's endpoints must agree. Shared nodes and edges
  permit shared prefixes, suffixes and branches. There is no requirement to
  start every path with the compiler. Embedded and supplementary transmissions
  belong here too; each path names its role explicitly. Gaps, unresolved
  narrator identity, suspended or uncertain links force uncertain path status.
- Report: `{id, start, end, pathIds, status, note}`. Reports are nonoverlapping
  envelopes in textual order. A report envelope can contain multiple parallel,
  embedded or supplemental paths. All referenced path source spans must lie
  inside its envelope. A missing chain is represented by empty pathIds and
  uncertain status with an explanation, never an invented transmitter. A source
  unit whose kind is report must contain at least one inventoried report.

IDs need only be nonempty strings and are unique within each unit's respective
node/edge/path/report lists. Every node and edge must be used by a path; every
path must be assigned to a report envelope. All isnad/matn segments must lie
inside a report envelope. A heading or authorial comment can contain a report
and heading/commentary paths. Narrated events and quoted people remain matn
unless the source actually makes them transmission participants. Report
uncertainty propagates to unit status. An uncertain segment forces uncertain
unit status. A complete extraction may explicitly preserve genuine uncertainty.

Deterministic checks cannot discover an omitted embedded report, decide narrator
identity, certify segment meanings, or prove a phrase is a transmission verb.
Fresh semantic extraction and independent source-based audit must assess those
facts. The frozen source, ledger, and this contract must be available before
final extraction; a proposed ledger extension requires reviewed preparation
before extraction is finalized.

## Separate audit and execution receipts

Audit JSON is exactly `{verdict, checkedUnitIds, checks, findings, limits}`.
Verdict is pass or hold. `checkedUnitIds` is the exact ordered source unit IDs.
`checks` is exactly the following ordered list:

```json
["source_segmentation", "report_inventory", "transmission_wording", "narrator_identity", "ordered_paths", "branches_and_gaps", "quoted_people", "heading_commentary", "translation_alignment"]
```

Each finding is `{id, unitId, reportId, status, detail}`; reportId may be null for
a unit-level finding. Status is resolved or human-only. Limits is a nonempty
list of nonempty strings describing actual limits, including the difference
between textual extraction and historical authentication. A hold, unknown
finding status or remaining actionable defect prevents binding. Every uncertain
report needs a human-only finding against its report ID. An uncertain unit with
no uncertain report needs a human-only unit finding. Resolved findings retain
reasons; corrections require a new immutable extraction attempt before binding.
Human-only means the agent cannot resolve the substantive uncertainty, not that
routine extraction or agent-actionable correction was deferred.

Extraction and audit each have a separate closed receipt:
`{stage, sessionId, context, inputSha256, outputSha256, hostCaptureSha256}`.
Stage is extraction or structure-audit. Context is fresh. Distinct session IDs
are mandatory. Output SHA-256 hashes raw structure/audit file bytes respectively.
Actual host data stays in separate hash-bound capture files. The coordinator
must qualify approved effective settings and fresh independent execution using
the existing `observe_session` host adapter. This companion checks the normalized capture's sessionId, context, stage,
inputSha256 and outputSha256 against the receipt, requires nonempty observed
provider/model/reasoning/turnId, adapter codex-jsonl-v1, launch forkTurns none,
observed settings equal launch settings, and coordinator session distinct from
both semantic workers. Other normalized capture fields are retained unchanged.
These are consistency checks on existing-adapter output, not a new raw-log
exporter. Hash agreement does not attest authenticity, host honesty or approved
settings. Never generate observed host values
from intended settings or worker self-description.

Canonical input hashes use UTF-8 JSON with sorted keys and separators `,` and
`:`, with no insignificant whitespace. All hash values are lowercase SHA-256.
`contractSha256` hashes canonical `{scriptSha256, specSha256}`, binding this
script's raw bytes and this specification's raw bytes. Extraction input hashes
canonical `{sourceSha256, ledgerSha256, contractSha256}`. Audit input hashes
canonical `{sourceSha256, translationSha256, structureSha256, ledgerSha256,
contractSha256}`. Source, translation and ledger are immutable artifact files;
the binder never alters the existing translation candidate.

## Private manifest and commands

Manifest root is exactly `{version:1, kind:"private-hadith-structure-companion",
humanReview:"unreviewed", contractSha256, artifacts}`. Artifacts has exactly
source, translation, structure, ledger, extractionReceipt, auditReceipt,
extractionHost, auditHost, audit, render. Each is `{path, sha256}` using a locator
relative to repository `.runtime/` and a raw-byte digest. Resolved paths must
remain inside private `.runtime/`, including symlink resolution. All output is
write-once. The bound translation must be a parsed agent_complete, unreviewed
candidate whose sourceSha256 matches the raw source file and whose ordered
unit IDs, exact Arabic and nonempty English match the source inventory. Changed text, graph, ledger, receipts, rendering or contract requires
a new immutable attempt/manifest. Existing candidates and receipts remain intact.
The rendering is plain UTF-8 text generated only from structured source records;
it displays segments, ordered narrators, exact phrases, modes, gaps and notes.

```console
python scripts/hadith_structure.py validate --source .runtime/authority.json --structure .runtime/structure.json --ledger .runtime/ledger.json
python scripts/hadith_structure.py input-hashes --source .runtime/authority.json --ledger .runtime/ledger.json --translation .runtime/submission.json --structure .runtime/structure.json
python scripts/hadith_structure.py render --source .runtime/authority.json --structure .runtime/structure.json --ledger .runtime/ledger.json --output .runtime/structure.txt
python scripts/hadith_structure.py bind --source .runtime/authority.json --translation .runtime/submission.json --structure .runtime/structure.json --ledger .runtime/ledger.json --extraction-receipt .runtime/extraction-receipt.json --audit-receipt .runtime/audit-receipt.json --extraction-host .runtime/extraction-host.json --audit-host .runtime/audit-host.json --audit .runtime/audit.json --render .runtime/structure.txt --output .runtime/companion-manifest.json
python scripts/hadith_structure.py validate-manifest --manifest .runtime/companion-manifest.json
```

Python API: `validate(source_dict, structure_dict, ledger_dict)`,
`render(source_dict, structure_dict)`, `contract_hash()`,
`extraction_input_hash(source_path, ledger_path)`,
`audit_input_hash(source_path, translation_path, structure_path, ledger_path)`,
`build_manifest(paths_dict)`, `validate_manifest(manifest_dict)`. The paths dict
uses exactly the artifact names above. `build_manifest` validates all links,
audit coverage and exact rendering before returning a manifest; `write_new`
enforces containment and exclusive creation. See `tests/test_hadith_structure.py`
for a synthetic fixture with the exact extraction shape and graph examples.
The application runner must require this companion for adopted hadith scopes;
the generic closed translation and metadata contracts remain unchanged.
