# Translation quality workflow

This local policy governs adopted book projects. Read this file, the adopted
book profile, `agent-workflow.md`, and `stage-contracts.md` before translation.
Policy, executable validation, source identity, and exact stage methods are
integrity-bound by the profile. A downstream application is a consumer, never
the authority for a book's translation or rights decisions.

## Source and scope

Before durable translation, establish the exact edition, complete authority,
provenance, permission evidence, attribution, intended use, and artifact hash.
Public readability is not permission. For a commercial destination, source
translation/publication and witness processing must explicitly cover that use.
Do not inherit another book's permissions. A rights flag records a reviewed
decision; neither the validator nor an agent can grant rights.

The input is a frozen UTF-8 JSON authority with `units` and `exclusions`.
Each unit has a stable `id`, `kind`, precise `location`, exact `arabic`,
`contextIds`, and `formulaSpans`. Supported kinds are heading, chain, report,
comment, poetry, and entry. Numbering is display/location metadata, never identity.
Retain repeated reports and chains as distinct units. Inventory every substantive
heading, note, chapter introduction, chain, and report; explicitly record excluded
modern editorial matter and furniture. Do not translate unapproved annotations.

For an imported transcription, retain the original immutable artifact and an
append-only alignment/repair ledger in approved private storage. Record the
edition, original and normalized hashes, source locations, transformation and
exclusion rules, and every repair with before/after evidence. The adopted profile
must bind that alignment policy and any parser. Never silently rewrite source
bytes. If the approved structured transcription is itself the authority, disclose
that limitation and lack of same-edition facsimile verification. The generic
coordinator does not certify an importer's scholarly alignment.

Every formula occurrence is inventoried by Python Unicode code-point offsets
`start` inclusive and `end` exclusive, plus its referent. Preserve its exact Arabic
written form in English at the corresponding occurrence. Do not translate,
transliterate, omit, add, or substitute it. Independent critique and final audit
must check missing inventory entries, referent, grammatical agreement, and
unattested additions; literal span validation alone cannot establish these facts.

Claims must include governing context units. The starter intentionally requires
a context-closed scope rather than guessing inherited chapter or entry context.
A future book-specific slice adapter must supply validated bilingual continued
context before permitting smaller slices. Do not treat this restriction as
permission to omit a heading.

## Autonomous stages

1. Freeze the public-eligible Arabic authority and claim a nonoverlapping scope.
2. Translate directly from Arabic in a fresh context without English witnesses.
3. Independently critique Arabic fidelity, completeness, attribution, names,
   negation, numbers, structure, uncertainty, normalization, and formulas.
4. When enabled, independently compare meaning against a qualified English
   witness. Freeze the draft and Arabic critique first. Cover every Arabic span,
   including material absent from the reference. Use clause-sized spans, not
   wording similarity or automatic sentence matching. Record reference locations,
   substantive differences, and explicit reference omissions. Agreement is not
   proof; neither witness fluency nor majority vote overrides Arabic authority.
5. Resolve material findings using the smallest useful set of registered
   witnesses. Record unavailable retrieval as unavailable, never no-match.
   Witnesses may inform an Arabic-grounded decision; do not copy or closely
   paraphrase restricted expression. Access/processing permission is separate
   from permission to redistribute. A missing permitted English witness disables
   only comparison, with a recorded reason; it does not waive Arabic critique.
6. Adjudicate every finding against Arabic, preserving the draft and critique.
   Record bounded corrections and reasons. Do not silently normalize uncertainty.
7. Reconcile durable name IDs and exact bilingual mention spans against the final
   structured English. Identity merge/split decisions require an append-only
   project ledger; identical spelling alone does not establish identity. Version 1
   requires one English realization per identity. Version 2 preserves approved
   variants through exact registered Arabic-to-English occurrence mappings;
   unregistered variants require a reviewed ledger/profile revision.
8. Independently audit final source alignment, fidelity, formula semantics,
   names, and public-output eligibility. Preserve genuinely human-only findings
   with independently written public summaries; exhaust agent-actionable defects.
9. Validate exact coverage, stage order, approved method capture, current hashes,
   finding accounting, and formula/name spans. Generate a bilingual presentation
   from structured English and bind its hash to the submission.

The CLI enforces structural evidence, not semantic truth. Full Arabic audit,
formula inventory completeness, clause granularity, rights review, and independent
expression remain explicit semantic responsibilities. No metric or passing
schema grants scholarly approval. Restricted evidence stays private; public
outputs contain only eligible source, independently authored English, names,
safe provenance, and independently written uncertainty summaries.

## Completion, correction, and publication

`agent_complete` requires every locked unit, every applicable stage, zero
remaining agent units, current deterministic checks, and the generated review
presentation. A genuine human-only uncertainty may remain explicitly disclosed.
Known public-eligibility defects hold submission. Human review remains
`unreviewed` on machine submissions; ongoing review is append-only metadata and
does not itself gate public-working eligibility or canonical promotion.

Publication, canonical promotion, and human review are separate state axes.
`submit` writes private candidate files; it does not authorize publication,
create a GitHub PR, advance a release pointer, or promote content. Apply the
adopted project's rights/public-boundary review and release contracts afterward.
Corrections produce new immutable revisions and superseding releases. Never
rewrite an earlier stage receipt or released object. Start a new run directory
for a correction; retain prior runs and their source/policy/method pins.
