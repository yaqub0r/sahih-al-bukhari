# Book distribution and release workflow

This is an opt-in book-content contract alongside the unchanged v1 metadata
contracts. It adapts Al-Isabah's deterministic compiler, exact closure,
commit-addressed transport and manual publication model. It does not inherit
Al-Isabah's source permissions, CC BY-NC-SA license or content schema.

## Prepare, review, publish

Preparation is local and makes no network requests. `release_distribution.py`
validates an explicitly projected proposal against a closed adopter record schema
and an adopter semantic adapter. It emits exactly five files: `manifest.json`,
`records.jsonl`, `record-schema.json`, `reader.html`, `release-closure.json`.
The manifest binds source authority, rights decision, exact ordered scope,
repository/commit, contract ID, proposal digest, per-record review state and all
non-manifest outputs. The closure binds their raw UTF-8 hashes and byte lengths,
including the manifest. The ZIP has sorted members, fixed timestamps, fixed file
modes and no compression; its external `.sha256` binds exact archive bytes.
No file contains an unpredictable generation timestamp.

```console
python scripts/release_distribution.py build --proposal PRIVATE_PROPOSAL.json --directory NEW_PRIVATE_OUTPUT --archive NEW_PRIVATE_ARCHIVE.zip --commit REVIEWED_40_CHARACTER_COMMIT
python scripts/release_distribution.py validate --directory PRIVATE_OUTPUT
```

The build CLI requires new outputs inside ignored `.runtime/`.
Keep real candidate text and review files in ignored private storage until an
explicit public-boundary and publication decision. Even a GitHub draft release
or a public PR containing the text would cross that boundary. Do not create one
just to obtain a review. Serve the generated `reader.html` through a loopback
HTTP server for local review; do not use a `file://` application preview.

A pending rights decision is permitted for a visibly held candidate. It produces
`publicationEligible: false`; preparation cannot authorize publication. A record
may be human-unreviewed and still eventually eligible under adopter policy.
Human scholarly review, machine completion, publication authorization and
canonical promotion remain separate. This first contract uses
`canonicalPromotion: unused` and `releaseClass: public-working`.

## Adopt once

1. Supply `release/distribution.config.json`: book/repository/contract identity,
   record schema, semantic adapter, publicationEnabled, exampleOnly, approverIds.
   Keep publishing disabled until the explicit adoption decision. The template's
   synthetic configuration has both publication disabled and exampleOnly true;
   template fixtures must never be published.
2. Implement a closed record schema and `validate_records(records, proposal)`.
   Every record has `sourceUnitId`, increasing `sourceOrdinal`, `arabic`,
   `english`, `humanReview`, `machineState`; additional fields must be explicitly
   modeled. Never key on printed numbering. The dependency-free validator
   implements only the documented subset used by included schemas: local $defs
   refs, closed objects, required/properties, arrays/items/minItems, string
   minLength/pattern, integer minimum, boolean/null, const/enum and standalone
   anyOf. Unsupported keywords fail, rather than silently being ignored. The whole
   schema is linted before records, including unused definitions and absent
   optional properties; recursive schema references are unsupported.
3. Derive proposals from validated evidence with a dedicated allowlisting
   projection. The generic compiler cannot discover semantic omissions or prove
   private audit authenticity. Require the adopted adapter's admission checks,
   independently review the projection, and test negative boundary cases.
4. Resolve content rights and attribution separately from software licensing.
   `rights.originalContentLicense` applies only to original project contributions;
   `arabicBasis`, attribution, excluded material and residualRisk explain source
   treatment. A boolean status is a recorded decision, never a grant of rights.
5. Configure the `public-release` GitHub environment with required maintainer
   reviewers and main-only deployment restrictions. Enable repository release
   immutability. The workflow checks the GitHub immutable-releases API and fails
   on missing permission, unknown state, or disabled immutability. It does not
   change repository settings or protections. Configure the required
   `contracts-and-policy` check; branch protection remains an adopter decision.

## Approval and future dispatch

Only after explicit publication authorization, make the reviewed allowlisted
proposal available at `release/proposals/<release-id>.json` in a deliberate
public-content change. Add `release/approvals/<release-id>.json`, exactly:

```json
{"version":1,"releaseId":"RELEASE_ID","proposalSha256":"CANONICAL_PROPOSAL_SHA256","schemaSha256":"CANONICAL_SCHEMA_SHA256","approvedBy":"CONFIGURED_APPROVER_ID","decisionId":"REVIEWED_DECISION_ID","authorized":true}
```

Approval references a configured identity and is meaningful only as part of the
reviewed repository history; it is not a cryptographic signature. No script may
invent owner approval. The schema and proposal digests use canonical JSON
(sorted keys, compact separators, UTF-8, no non-finite numbers). Archive hashes
use raw bytes. The approver IDs must be adopted from the project's identity
registry; do not invent identities in a payload.

Merge the content/approval/configuration change normally. Prepare and review the
archive again using that exact final main commit; the different commit changes
its manifest and checksum. Dispatch `publish-public-distribution.yml` manually
with full repository_commit, proposal_path and exact archive_sha256. There is no
push or PR trigger and no automatic dispatch on merge. The publisher checks
current main, clean checkout, tracked proposal/approval, successful
contracts-and-policy, configured repository, non-synthetic enabled configuration,
rights decision, exact approval bindings and archive checksum. It builds twice
and compares bytes before creating any tag/release. An existing tag/release or
uncertain API result fails closed. No direct private runtime folder is uploaded.

The release tag is `public-working-<full-commit>` and the assets are
`<book-id>-public-distribution-<full-commit>.zip` plus its `.sha256`. The exact-commit tag is created atomically through GitHub (an intervening tag
creation fails rather than being reused). Assets are
attached to a draft before final publication so GitHub immutability can protect
them. Publication verifies `immutable: true`. This workflow must not be
manually dispatched merely to test adoption.

## Consumer verification and recovery

Consumers pin releaseId, contractId, repositoryCommit and archive digest, reject
unsupported contract majors, verify every closure member/hash/length and ordered
record identity, then validate schema and scholarly structure. The shipped
`validate` command performs exact reconstruction against the locally pinned
contract/adapter and rejects missing/extra artifacts or drift, including reader
parity. It is not an untrusted ZIP extractor. Extract only the five fixed regular
filenames into a new directory with your own safe ZIP tooling; reject duplicate,
absolute, traversing or symlink members before extraction.

Keep predecessors and record `previousReleaseId` for supersession. A correction,
review-state update or license decision creates a new proposal/closure and
commit-addressed release. Never overwrite a published asset or tag. Consumers
roll back by pinning the prior verified immutable release, not by replacing it.
If any remote step fails after tag creation, preserve the tag/draft, local
artifacts and workflow receipt, inspect GitHub's actual state and resume only
with an explicit reconciled decision; do not automatically delete or retry.

References: [Al-Isabah distribution design](https://github.com/yaqub0r/al-isabah/blob/main/docs/architecture/public-distribution.md),
[Al-Isabah publishing workflow](https://github.com/yaqub0r/al-isabah/blob/main/.github/workflows/publish-public-distribution.yml),
[GitHub immutable-releases API](https://docs.github.com/en/rest/repos/repos#check-if-immutable-releases-are-enabled-for-a-repository).
