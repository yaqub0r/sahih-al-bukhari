# First working-release decision: owner-approved

Decision ID: `bukhari-working-release-1-owner-approved`.
Scope: `bukhari-opening-faith-working-1`, the opening and Book of Faith,
110 retained units and numbered reports 1–58, with all 49 disclosures.

The owner explicitly instructed: “Use CC BY 4.0 for our English translation and
structure. I accept the disclosed source risks. Go ahead and publish the first
working release, clearly marked human-unreviewed.” This authorizes the scoped
allowlisted proposal, content-license grant, normal merge, exact-commit archive,
maintainer release approval and manual publication. It does not authorize release
of private drafts, execution captures, raw findings, receipts, witnesses or later
unreviewed source scopes.

## Content and rights

The original English and project-authored structure/notes are offered under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); see
[LICENSE-CONTENT.md](../../LICENSE-CONTENT.md). The grant applies to original
project contributions, with source attribution and exclusions preserved.

The Arabic distribution subject is the reviewed underlying classical text from
the pinned OpenITI JK000110 transcript. Modern introductions, footnotes, editorial
discussion, indices and corpus annotations are excluded. No modern English
translation or restricted witness is distributed. The owner explicitly accepts
the disclosed residual risks concerning possible modern editorial expression and
database rights for this external distribution. OpenITI's corpus CC BY-NC-SA 4.0
notice remains disclosed; no commercial permission from OpenITI, third-party
rights waiver or legal clearance is asserted.

The original private-processing/source-admission documents and earlier candidate
are retained as historical evidence. This decision adds scoped external-release
authority; it does not rewrite their bound bytes or expand source eligibility to
the whole collection. Every record and every ordered Arabic transmission path is
unchanged from the independently reviewed candidate. Only public-facing release,
rights and authorization metadata changes.

## Review and release controls

All 110 records remain human `unreviewed` and machine `agent_complete`.
Working publication and human scholarly review are separate. Canonical promotion
is unused; the working release is an explicitly labeled GitHub prerelease.
There is no claim of historical chain continuity from graph order.

`bukhari-owner-reviewer` resolves to the configured owner role. The approval file
binds the exact proposal/schema digests and this decision; it records actual
owner authorization, not a new scholarly review or cryptographic signature.
The final archive is independently checked after normal merge and rebuilt twice
against the exact final main commit before dispatch.

Release immutability is enabled before creation. The `public-release` environment
permits only the main branch and requires the owner maintainer (yaqub0r) to approve.
As a single-maintainer repository, self-review is allowed; the same authenticated
owner can dispatch and approve under the explicit instruction above. Use the
normal environment-approval endpoint, never an administrator bypass. Existing
branch controls are unchanged; successful contracts-and-policy is required by
the release publisher even where main lacks branch protection. Every future
release requires its own explicit reviewed approval and archive binding.

## Credential-boundary correction before first publication

The first dispatch passed all hosted tests but stopped before tag creation:
GitHub's Actions token cannot read the administration-only immutability API.
The corrected workflow is protected read-only validation; final publication is
performed in the owner-owned checkout with the authenticated owner CLI after a
successful matching run and its normal environment approval. The finalizer binds
the exact inputs/checksum through GitHub run logs, repeats archive checks, and
checks immutability live before any tag/release mutation. No broad administrator
credential is added to CI and no gate is bypassed. The failed dispatch is retained
as failure evidence and cannot qualify the finalizer.
