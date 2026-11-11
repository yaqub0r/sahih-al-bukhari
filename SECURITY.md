# Security policy

## Supported state

This private template has no published release or deployed service. Security fixes target the current `main` branch. Adopters must replace this statement with their supported-version policy before publishing.

## Report privately

Do not open a public issue for a credential, private source, rights-sensitive material, or exploitable vulnerability. Use the repository owner's private security-reporting channel. If private reporting is not configured, contact a maintainer out of band and disclose only the minimum needed to establish a secure channel.

## Immediate containment

If sensitive data enters Git, stop distribution, revoke exposed credentials, restrict repository access if needed, preserve an incident record, and assess history-removal requirements with maintainers. Deleting one file in a later commit is not sufficient containment. Follow `docs/incident-response.md`.

The validator is a release guard, not a secret scanner or rights determination. Maintain separate secret scanning, access control, backup, and legal/scholarly review appropriate to the adopted project.
