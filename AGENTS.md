# Repository guidance

## Ownership and scope

This adopted repository owns the complete Sahih al-Bukhari English translation.
Read docs/translation/bukhari-adoption.md and bukhari-source-decision.md alongside
quality-workflow.md, agent-workflow.md and stage-contracts.md before source or
translation changes. User authorization: text-only audit and independent English
translation, intended commercial use, proportionate residual copyright risk
accepted. Continue routine steps autonomously. Do not require scans.

## Private/public boundary

Real Arabic authority, drafts, critique, host captures, name mentions, prompts,
receipts and candidates stay in ignored .runtime/ or approved private storage.
Public Git holds tooling, synthetic tests, policies and safe provenance. No real
text is to be placed in examples/synthetic or contracts/v1. Do not weaken the v1
metadata deny policy. A separate reviewed distribution contract is required before
publishing any book text. Never label risk acceptance as legal clearance.

## Delivery and verification

Work issue-first through focused PRs; run scripts/validate_repository.py and
python -m unittest discover -s tests -v. Require contracts-and-policy before normal
merge. Preserve exact source hashes, every substantive unit, repetitions, context,
formula occurrences, append-only attempts, independent fresh semantic workers and
host-written execution captures. Missing authentic metadata holds stage admission;
never synthesize it. Human review stays unreviewed on machine completion.

Use the user-selected canonical checkout. Do not create nested worktrees or
change execution environments for convenience. Semantic translation, critique,
adjudication, names and audit require separate fresh workers. Independently review
importer and adoption changes before admitting a production scope.

## Pronunciation

صحيح البخاري: Ṣaḥīḥ al-Bukhārī; distinguish ḥ from ordinary h, kh from k, and
retain long ī and ā. الإسناد: al-isnād, chain of transmission.

## Hadith-specific ordered isnad requirement

A hadith scope is not complete with prose translation alone. Follow
`docs/translation/hadith-structure.md`: retain the exact Arabic as authority and
provide an independently audited private companion with ordered narrator
occurrences, exact transmission phrases, isnad/matn/comment segmentation,
alternative/embedded paths, shared branches and explicit missing/implicit or
uncertain links. Never invent a narrator or infer historical continuity merely
from graph order. Keep ambiguous short names distinct until evidence supports
identity reconciliation. Quoted participants in the matn are not automatically
transmitters. Inventory transmissions in headings, comments and follow-ups too.

Existing translation candidates and prior profiles remain immutable. A legacy
opening candidate may receive a separately versioned source/hash-bound companion;
do not overwrite it to add fields to its closed schema. Every subsequent hadith
scope requires the validated companion manifest alongside the translation
submission before project-level completion. The generic translation CLI alone
does not certify this book-specific requirement. Fresh extraction and independent
Arabic structural audit need actual host captures; every uncertainty must remain
visible in the companion review. Structures/evidence remain private under the
same book-text boundary; public Git contains synthetic contracts/tooling only.

## Distribution preparation and publication

Read docs/distribution-workflow.md before preparing or changing release tooling. Keep unpublished real proposals and archives private; GitHub drafts and public PRs also cross the public boundary. Use closed adopter schemas and semantic admission, deterministic archive/closure validation, exact commit and review bindings. Never dispatch publishing, invent approval, enable publication or assert a license merely because a private candidate passes. Template fixtures remain synthetic-only and unpublishable.
Read docs/bukhari-release-candidate.md for hadith-specific projection and the pending first-release rights decision. Existing bound translation policies and private companions remain immutable.

## Owner-authorized first public working release

The owner selected CC BY 4.0 for original English and structure, accepted the
disclosed source risks, and authorized publication of the first working release
clearly human-unreviewed. Read docs/decisions/bukhari-working-release-1.md and
LICENSE-CONTENT.md. The reviewed release/proposals allowlist and its bound
approval may be public; raw private authorities, stage evidence and later scopes
remain private. This scoped authorization supersedes earlier preparation-only
holds for that proposal. It never converts machine completion to human review,
licenses third-party rights, or authorizes subsequent unapproved releases.
