# Bukhari first public-working release candidate

The approved task is preparation for review only. Do not publish, dispatch the
publishing workflow, create tags/releases/drafts, upload assets or put real book
text in a public branch. Publishing remains disabled in the distribution config;
no release approval exists. Existing v1 metadata deny rules are unchanged.

## Contract and coverage

The first candidate comprises every retained opening and Book of Faith unit:
110 units, numbered reports 1–58, including headings, authorial comments and
supplementary/embedded transmissions. It is a partial work, not the complete
collection. All records are `agent_complete` and human `unreviewed`.

`contracts/distribution-v1/hadith-record.schema.json` is a separate closed public
content schema. Each sourceUnitId is stable; sourceOrdinal preserves authority
order. printedHadithNumber is display metadata only and need not be unique in
future scopes. Each record includes exact Arabic and its UTF-8 SHA-256,
independently authored English, explicit segmentation, and an isnad object.

Segments include exact source substrings. Narrator/gap/compiler occurrence nodes
retain their ordered path references, approved identity IDs or null, status,
source-unit Unicode spans and exact Arabic mention. Edges retain full literal
transmission wording, or null when unprinted, plus explicit/implicit/suspended/
uncertain mode. Parallel, embedded and heading paths share nodes/edges as needed.
Report envelopes bind all paths. Gaps never assert missing identities or counts;
quoted matn participants are not inferred as narrators. Structure notes and
independently written human-only uncertainty summaries remain visible. Unicode
spans address the released record's Arabic, not private file/line coordinates.
No graph order is a historical authentication judgment.

The public adapter revalidates exact literal/span agreement, source hashes,
segmentation, DAG/path/report integrity, gaps/uncertainty propagation and required
report disclosures. It derives a minimal mention ledger solely to check released
structure; it does not re-adjudicate identity. The reviewed `release/bukhari-source-admission.json` pins the full authority,
number inventory, upstream artifact/revision and both approved companion
manifest hashes; stale inputs, wrong upstream hashes and duplicate unit keys
fail before any proposal is emitted. The preparation adapter first
validates both independently audited companion manifests, authentic receipts and
frozen source/translation/ledger bindings, then explicitly projects fields. Raw
findings, stage receipts/hashes, execution captures, prompts, private paths and
source-file coordinates are excluded. Existing immutable private files are not
modified. All fourteen English uncertainties and all human-only structural
findings are retained; no automatic claim of human review is made.

## Prepare privately

Run from the canonical checkout, with an approved frozen full authority,
number inventory and opening/Faith companion manifests:

```console
python scripts/prepare_bukhari_release.py --authority PRIVATE_AUTHORITY.json --inventory PRIVATE_INVENTORY.json --opening-manifest PRIVATE_OPENING_MANIFEST.json --faith-manifest PRIVATE_FAITH_MANIFEST.json --output NEW_PRIVATE_PROPOSAL.json
python scripts/release_distribution.py build --proposal NEW_PRIVATE_PROPOSAL.json --directory NEW_PRIVATE_BUNDLE --archive NEW_PRIVATE_ARCHIVE.zip --commit REVIEWED_MAIN_COMMIT
python scripts/release_distribution.py validate --directory NEW_PRIVATE_BUNDLE
```

The proposal output and its private admission receipt are write-once and stay
under ignored runtime storage. The receipt records input hashes and is never
included in the release archive. Build again under a different new output name
and compare ZIP bytes to establish reproducibility. Inspect the generated reader
and machine-readable records. See [the reusable workflow](distribution-workflow.md)
for final-main rebinding, owner review and future publication gates.

## Licensing decision held for review

The candidate deliberately records `rights.status: pending` and
`originalContentLicense: null`, yielding `publicationEligible: false`.
Commercial use remains the owner's objective. A proposed option is CC BY 4.0 for
original English and project-authored structure/notes; no such grant is made now.
Arabic source treatment needs an explicit external-distribution rationale and
accepted residual risks. OpenITI's CC BY-NC-SA corpus license is disclosed, not
represented as commercial permission or silently replaced by a permissive grant.
The existing source decision authorizes private processing/admission only.
Preparation neither settles third-party rights nor grants software licensing.

Review should decide the original-content license and source treatment, then
approve the exact final archive and public-content boundary. Those are genuine
publication decisions. Human scholarly review can remain ongoing if an adopted
working-release policy explicitly permits it. No public release is authorized
by merely merging this tooling.
