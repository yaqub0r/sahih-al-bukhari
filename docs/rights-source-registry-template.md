# Rights and source registry template

Maintain this register in structured project data. This table is a planning aid; do not paste source text, scans, credentials, private paths, or confidential legal advice into it.

| Field | Required decision |
| --- | --- |
| Source ID | Stable project identifier |
| Source type | Project-defined controlled value |
| Public locator | Safe persistent/public identifier, or `withheld` |
| Fingerprint | Algorithm and digest of the governed source object, stored outside public payloads when restricted |
| Classification | Public, restricted, or private according to project policy |
| Rights entry ID | Stable link to the rights decision record |
| Rights status | Unknown, under review, approved scope, restricted, or expired |
| Permitted scopes | Metadata, quotation, derived facts, full text, images, or other project-defined scope |
| Decision authority | Configured identity/role, not a free-form claim |
| Effective/expiry dates | When applicable |
| Review trigger | New edition, correction, license change, expiry, or incident |

Public provenance should expose only the fields and scopes approved for release. Detailed evidence stays in access-controlled project records and is referenced by an opaque decision ID if policy permits.
