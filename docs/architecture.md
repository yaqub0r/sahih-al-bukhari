# Architecture and ownership

## Authority boundary

An adopted book repository is the canonical authority for that project's scholarly data. It owns source provenance, rights/classification decisions, record revisions, review state, corrections and supersession, release closure, and consumer projections. A consumer may cache or index a verified projection, but must preserve its release identity and cannot change the canonical record.

Storage is deliberately unspecified. Files, object storage, or a database may back authoring, but only versioned contracts and immutable release artifacts cross the consumer boundary. Consumers never receive direct database credentials or table access.

## Configured authority

`project-config.schema.json` defines an identity registry. Producer, reviewer, and promoter are role assignments to stable project IDs. Payloads refer to those IDs, and validation resolves them against configuration. A display name or other free-form string is not evidence of authority.

- **Producer** assembles and signs off on a release closure.
- **Reviewer** changes per-record review/completeness metadata or records a correction.
- **Promoter** moves a project-controlled pointer or optional canonical-promotion state.

One identity may hold multiple roles when a solo project chooses that governance model, but the role assignment remains explicit and reviewable.

## Information classification

Every source-register entry and public record projection has an explicit classification. Template fixtures permit only synthetic public metadata. An adopter must define its own classes and rights mapping before importing real material.

The public boundary is allowlisted: only fields modeled by closed schemas may be released. The repository validator also recursively denies body/source/translation text, evidence, OCR, prompts, model traces, credentials, secrets, and private/local paths. A nested object cannot evade that policy.

## Record lifecycle

Review state, completeness, and confidence attach to a particular record revision. They can change through a new canonical revision without inventing a new release class. A policy may therefore publish a working projection containing an explicitly `unreviewed` record.

Corrections are append-only links from a prior revision to a replacement revision. Supersession identifies what the correction replaces; it does not mutate or erase the historical release. Consumer projections carry revision and correction references so consumers can explain lineage.

## Release lifecycle

A release closure identifies one immutable release and enumerates every public JSON artifact by canonical SHA-256 and canonical byte length. Validation rejects a missing artifact, missing hash, changed hash, unsafe path, unsupported schema major, or mismatched release identity.

Two state axes are explicit:

1. `publicRelease`: whether the closed public package is published or withdrawn.
2. `canonicalPromotion`: whether that release is not used for promotion, a candidate, promoted, or reverted.

Publishing does not imply full human review or canonical promotion. Projects without a promotion concept use `not-used`. Projects with it configure promoters and advance that state separately.

## Rollback and compatibility

Released objects remain immutable. The mutable release pointer may advance to the latest release or point back to the closure's declared previous release with reason `rollback`; it records who changed it and which release was rolled back. Recovery publishes a new corrected release rather than rewriting either historical closure.

Consumers pin both `releaseId` and `contractMajor`. A response whose projection release identity differs from the requested pin is invalid. Major contract changes require a new API path and schema directory; compatible additive work belongs in the existing major only when closed schemas and consumers can accept it deliberately.
