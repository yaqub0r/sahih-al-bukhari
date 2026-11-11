# Version 1 contracts

These JSON Schemas describe the storage-neutral exchange boundary. All objects are closed with `additionalProperties: false`; unknown data must be rejected rather than silently forwarded. The executable validator currently supports schema version `1.0.0` and contract major `1` only.

| Contract | Purpose |
| --- | --- |
| `project-config.schema.json` | Project-owned identities, classes, and release policy |
| `source-provenance.schema.json` | Public source identifiers, fingerprints, classification, and rights-register link/state |
| `record-review-state.schema.json` | Per-revision completeness, review status, confidence, and configured reviewer identity |
| `correction-supersession.schema.json` | Append-only correction and supersession links |
| `release-closure.schema.json` | Immutable release identity, independent publication/promotion state, compatibility, and artifact hashes |
| `release-pointer.schema.json` | Auditable normal advance or rollback pointer |
| `consumer-projection.schema.json` | Read-only, release-pinned consumer records with no body text |
| `openapi.yaml` | Minimal read-only HTTP retrieval boundary |

An incompatible shape or meaning requires `contracts/v2/` and `/v2/` API paths. A new review status or optional field is not automatically compatible merely because it appears additive: closed consumers must opt into it.

Schema conformance alone is insufficient. `scripts/validate_repository.py` also resolves configured roles, checks cross-file identities and correction links, verifies canonical artifact hashes, validates rollback semantics, and recursively applies the public-payload policy.
