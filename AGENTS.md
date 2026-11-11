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
