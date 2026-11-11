# Rollback guidance

Rollback changes the active pointer; it never mutates or deletes an immutable release.

For a normal advance, `activeReleaseId` and `latestReleaseId` both identify the new closure, `reasonCode` is `normal-advance`, and `rollbackFromReleaseId` is null. For a rollback, `latestReleaseId` stays on the problematic newest closure, `activeReleaseId` must equal that closure's declared `previousReleaseId`, and `rollbackFromReleaseId` identifies the newest closure.

Before changing the pointer, verify the target closure and hashes, consumer compatibility, configured promoter identity, and incident authority. Afterward, verify consumers resolve the intended pin. Remediation should produce a later corrected release; do not silently move the latest identity or patch an old package.
