# Translation stage contracts, version 1

The executable contract is `scripts/translation_workflow.py`; objects reject
unknown and missing fields. All spans use Python Unicode code-point offsets,
zero-based start inclusive, end exclusive. IDs are stable lowercase identifiers.
The synthetic end-to-end fixtures in `tests/test_translation_workflow.py` show
complete objects for every stage; they contain no real scholarly text.

## Profile

`version: 1`, `workId`, `repository: owner/name`,
`intendedUse: commercial|noncommercial`, `source`, `witnesses`,
`englishComparison`, `methods`, `policyFiles`, `limitations`, `nameLedger`, `coordinatorMethod`.

Each source/witness record requires `id`, `edition`, `sha256` (raw file bytes),
`bytes`, `rightsBasis` (reviewed decision reference/basis), `attribution`, and
boolean `publicationAllowed`, `translationAllowed`, `processingAllowed`,
`commercialAllowed`. The source must permit processing, translation, and
publication. Each witness must permit the processing scope; commercial projects
require commercial authorization. Witness publication may remain false.

`englishComparison` requires boolean `enabled`, registered `witnessId` (null
when disabled), and a nonempty `reason`. Each active stage has exactly one
approved method with `id`, exact `provider`, `model`, and `reasoning`.
`coordinatorMethod` separately approves the exact coordinator configuration.
`policyFiles` maps repository-relative paths to raw SHA-256 hashes. Bind at least
the three local translation documents, this executable, the adopted book profile
policy, alignment policy/parser, and any formula/name policy. Refresh bindings
only through the adopted repository's reviewed issue/PR process. Never overwrite
an old profile used by completed runs; use versioned profile filenames.

## Project name ledger

`nameLedger` binds a repository-relative `path` and raw-file `sha256`.
The ledger has `version: 1`, `identities`, and append-only `decisions`.
Each identity is `{id, english, arabicForms}`. Each decision is
`{id, kind, fromIds, toIds, basis}`, where kind is merge, split, or correction.
Keep historical IDs and decisions when revising; do not silently repurpose an ID.
Before preparing a production scope, register its known name identities through
a reviewed versioned ledger. A newly discovered identity or correction holds name
reconciliation until a reviewed new ledger/profile/run revision exists. Every
mention must match both an attested Arabic form and the canonical English.
This deliberately prevents disjoint runs from assigning incompatible meanings
to the same durable ID. The starter ledger is empty and synthetic-only.

## Source authority

`{units: [...], exclusions: [...]}`. Each unit requires `id`, `kind`, `location`,
`arabic`, `contextIds` (IDs from the authority), and `formulaSpans` (ordered,
nonoverlapping `{start, end, referent}`). Each exclusion is `{location, reason}`.
`prepare` preserves source order and requires all context IDs in the scope.

## Stage outputs

- `blind`: `{units}`. Each translated unit is `{id, english, formulaTargets}`;
  targets are ordered `{start, end}` spans paired with source formula occurrences.
- `critique`: `{checkedUnitIds, checks, findings}`. Check IDs are the exact
  ordered `CHECKS` tuple in the executable. A finding is
  `{id, unitId, category, detail, start, end}` against an Arabic span.
- `comparison`: `{coverage, findings}`. Each coverage row is
  `{unitId, start, end, referenceLocation, status, findingIds}`. Rows for each unit
  partition every source character in source order. Status is `equivalent`,
  `difference`, or `reference-omits`; the latter has a null reference location.
  Differences/omissions need findings, using the critique finding shape.
  Comparison finding IDs must be distinct from critique IDs.
- `witness`: `{decisions, notRequiredReason}`. Decisions address all critique and
  comparison findings in that order: `{findingId, status, basis, witnessIds, evidence}`.
  Status is `resolved`, `unresolved`, or `unavailable`. Basis records Arabic
  evidence, query/retrieval and exact witness passage locations/hashes in private
  storage when consulted. Each consulted witness has one evidence entry
  `{witnessId, status, query, location, sha256}` in witness-ID order. Retrieval
  status is retrieved, unavailable, or no_match. Retrieved passages require
  exact location and SHA-256; other states require null location/hash.
  `notRequiredReason` explains an empty finding set.
- `adjudication`: `{units, decisions}`. Units use the blind shape. Every finding
  receives `{findingId, disposition, basis}` with disposition `corrected`,
  `retained`, or `unresolved`. Explain the Arabic basis, not merely reference
  agreement. Do not invent a finding resolution because a witness is unavailable.
- `names`: `{checkedUnitIds, names}`. Each mention is
  `{nameId, unitId, start, end, targetStart, targetEnd, english}`. Source spans
  identify observed Arabic names; target spans must equal `english`. Stable
  name IDs must use one consistent English realization within this run.
- `audit`: `{checkedUnitIds, checks, publicEligible, unresolved}`. Use the exact
  ordered `AUDIT_CHECKS` tuple. `publicEligible` must be true to submit.
  Every unresolved adjudication finding receives
  `{findingId, unitId, publicSummary, humanOnly: true}`. The independently written
  summary must disclose the substantive uncertainty without restricted wording.

## Trusted-host capture

Every stage requires a selected **host-written** capture object with
`provider`, `model`, `reasoning`, `sessionId`, `context: fresh`, `stage`, `runId`,
`inputSha256`, `outputSha256`, `launch: {provider, model, reasoning, forkTurns: none}`,
`turnId`, `adapter: codex-jsonl-v1`, `coordinator: {sessionId, turnId, provider, model, reasoning}`,
and `coordinatorLaunch: {provider, model, reasoning}`.
Launch overrides, observed settings, and the profile must agree exactly.
All semantic sessions are distinct from one another and the coordinator session
recorded at preparation. Capture output hashes after completion;
never populate observed values from intended settings or worker labels.

`stage-input` prints the exact run/input identity. Output hashes use canonical
JSON: UTF-8, sorted keys, no insignificant whitespace, Unicode preserved.
`digest()` implements this representation. The coordinator binds the selected
host capture into an append-only receipt with hashes and the approved method ID.

This is unsigned operational evidence under a trusted host and coordinator.
The `capture-host` command adapts explicitly selected Codex `session_meta` /
`turn_context` JSONL records, including validated direct-worker parent aliases.
It checks first-turn/non-forked worker context and rejects inconsistent settings
within the selected turn. It emits only selected metadata and bindings; no raw
log, prompt, response or private locator is retained. It verifies explicit
coordinator/worker launch records against observed settings and their approved
methods. It does not attest host honesty. Other host formats require a reviewed,
integrity-bound adapter before production. Missing effective metadata holds production; do not
generate a fictional capture or use synthetic methods for real translation.

## Submission boundary

The submission allowlist contains source/final English, exact unit identity and
locations, formula targets, names, public uncertainty summaries, hashes, counts,
limitations, and unreviewed state. It omits critique prose, restricted reference
text, witness findings, raw host records and private locations. The final audit
must also check those permitted fields for inappropriate expression; field
allowlisting cannot prove that English is independently authored.

The existing `contracts/v1` metadata release remains unchanged and still rejects
text fields. Translation candidates remain in ignored runtime storage. An
adopter must explicitly introduce its book-content distribution schema and
compatibility decision before publishing text; do not insert the submission
into the existing metadata projection or loosen its recursive deny policy.
