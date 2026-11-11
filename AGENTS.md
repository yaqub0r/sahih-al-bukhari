# Repository guidance

## Purpose and ownership

Maintain a reusable, content-free foundation for canonical scholarly book repositories. An adopted repository owns its own source/rights register, records, review metadata, corrections, immutable releases, and consumer projections. Downstream applications consume verified releases; they do not become governance authorities.

## Public/private and data safety

Keep this template synthetic-only. Never add real book text, translation, OCR, source images, review evidence, prompts, model traces, credentials, database exports, or private filesystem paths. Public artifacts must satisfy `policy/public-payload-policy.json`; private working data belongs in adopter-defined excluded storage, never under a public release directory. Treat classification and rights status as explicit registered decisions, not filename conventions.

## Maintainer and release rules

Use project-configured identity IDs for producer, reviewer, and promoter roles; do not accept free-form identity claims as authority. Human review changes per-record state and confidence, not release class. Keep public release state separate from optional canonical-promotion state. Releases are immutable closures of hashes; correct them by supersession. Move a consumer pointer backward only through a recorded rollback, and never rewrite a released object.

Do not publish this template's fixtures. Adopters must deliberately choose compatible code and content licenses; this template intentionally supplies no software license.

## Verification and collaboration

Run `python scripts/validate_repository.py` and `python -m unittest discover -s tests -v` before proposing a change. Deliver changes through a focused issue and pull request with the `contracts-and-policy` check. Preserve strict schemas, supported-major rejection, recursive prohibited-payload checks, and read-only consumer isolation.

Use one Codex-managed worktree per active issue. Do not nest worktrees, delete the active worktree manually, or mix unrelated changes. Fast-forward the canonical checkout after merge.

## Realtime pronunciation

When unfamiliar non-English names appear in an adopted repository, verify their original-language spelling and pronounce meaningful distinctions carefully. Add a compact glossary here only for names the repository actually uses repeatedly; do not invent one for this content-free template.

## Translation workflow maintenance

Before changing translation behavior, read `docs/translation/quality-workflow.md`,
`docs/translation/agent-workflow.md`, and `docs/translation/stage-contracts.md`.
Preserve local integrity binding, exact source and method capture, fresh worker
contexts, occurrence-level Arabic formula preservation, public-output eligibility,
and agent completion separate from ongoing human review. English comparison is
optional, post-blind/post-Arabic-critique, independently performed, and authorized
for the witness's exact use. Resolve differences against Arabic. Keep all live
attempts and restricted evidence in ignored private runtime storage. Never
substitute template synthetic methods or captures for production evidence.

Changes remain issue-first and synthetic-only. Do not weaken the existing v1
metadata deny policy to make translation submissions fit; book-content publication
requires an explicit adopter schema and compatibility decision.
