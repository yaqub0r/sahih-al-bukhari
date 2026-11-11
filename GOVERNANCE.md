# Governance

## Decision ownership

Maintainers of an adopted repository own project configuration, classifications, rights/source entries, review policy, corrections, promotion policy, and releases. Consumer teams own their application behavior, but cannot redefine producer truth.

Authority is role-based and project-configured. Changes to the identity registry or release policy require the same pull-request and validation path as contract changes.

## Change classes

- Contract and public-boundary changes require schema, validator, fixture, test, and consumer-contract updates together.
- Scholarly review updates per-record metadata/confidence and may be included in any later release; it does not create a separate release class.
- Corrections append a supersession link and replacement revision.
- Public release and optional canonical promotion are separate decisions.
- Emergency rollback changes only the active pointer, preserves immutable releases, and follows the rollback guidance.

## Compatibility

Reject unknown contract majors. Within a major, maintainers must avoid silently changing field meaning. If consumers cannot safely read the new shape, create a new major and API path. Deprecation should identify the last supported release and migration window.

## Maintainer workflow

Use focused issues and pull requests, resolve conversations, and require `contracts-and-policy`. A solo maintainer may require zero external approvals while still requiring a pull request, an up-to-date check, and no administrative bypass. Record any narrow bootstrap exception in the implementing issue or PR.
