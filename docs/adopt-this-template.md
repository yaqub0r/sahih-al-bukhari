# Adopt this template

Complete this checklist before importing real material or publishing a release.

## Repository identity and ownership

- [ ] Rename the project and replace all `replace-me`/synthetic identifiers.
- [ ] Configure stable producer, reviewer, and promoter identities and least-privilege access.
- [ ] Decide whether canonical promotion is unused or separately governed.
- [ ] Name maintainers and a private security contact.

## Policy

- [ ] Define public, restricted, and private classes.
- [ ] Establish a source/rights review process and fill the registry without embedding source text.
- [ ] Decide when public working releases are allowed; do not confuse release eligibility with full human review.
- [ ] Define correction, withdrawal, supersession, retention, and incident procedures.
- [ ] Choose compatible code and content licenses deliberately. Do not assume one license covers both.

## Engineering

- [ ] Keep authoring/private storage outside public release paths and direct consumer access.
- [ ] Adapt project configuration and synthetic fixtures, then keep a synthetic test corpus.
- [ ] Preserve closed schemas and add a new major for incompatible consumer changes.
- [ ] Configure `contracts-and-policy` as an up-to-date required check on the default branch.
- [ ] Require pull requests, conversation resolution, administrators, and block force pushes/deletion without a bypass.
- [ ] Exercise release validation, consumer pinning, correction, incident, and rollback procedures.
- [ ] Document backup/restore and verify rollback without rewriting an immutable release.

## Translation adoption

- [ ] Follow [Agent translation workflow](translation/agent-workflow.md) and bind all required local policies.
- [ ] Qualify exact source and witness uses, including commercial use when intended.
- [ ] Supply and review the book's unit importer, alignment/repair ledger, chapter/chain scope and formula inventory.
- [ ] Configure exact approved methods and qualify the actual host metadata exporter; synthetic settings are never production approvals.
- [ ] Enable English comparison only with a qualified witness, or record why it is disabled.
- [ ] Keep original source, private evidence, captures and append-only attempts out of public payloads.
- [ ] Verify both the generic suite and adopter-specific import/host/distribution tests before a real run.
- [ ] Introduce an explicit book-text distribution schema before publishing text; existing v1 metadata contracts stay closed.

## First publication

- [ ] Complete `docs/release-checklist.md` with project-specific evidence.
- [ ] Verify no fixture or placeholder is presented as scholarly fact.
- [ ] Verify every artifact hash from a clean checkout.
- [ ] Publish through the adopted project's reviewed release mechanism—not from this template repository.
