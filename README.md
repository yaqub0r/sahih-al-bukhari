# Scholarly Book Repository Template

Private, synthetic-only foundation for repositories that are the canonical authority for one scholarly book project.

This repository defines governance, strict storage-neutral contracts, release validation, a read-only consumer boundary, and a book-neutral agent translation coordinator adapted from Al-Isabah. It contains no book text, translation, OCR, review evidence, model traces, credentials, database data, or real release. Adopters copy the structure, make project-specific policy decisions, and own the resulting scholarly record.

## Core model

- The book repository owns its sources register, rights decisions, scholarly records, per-record review state, corrections, supersession history, and immutable releases.
- Producer, reviewer, and promoter identities come from project configuration. A payload may refer to those identifiers; it cannot invent authority through free-form names.
- A public release is a closed, hashed set of projections. Human review updates record metadata and confidence, but does not create another release class or prevent a policy-authorized public working release.
- Public release and canonical promotion are separate state axes. Projects that do not use a promotion step record `not-used`.
- Consumers pin a release identity and contract major, retrieve read-only projections, and never connect to the producer's database or private workspace.

See [Architecture](docs/architecture.md) and [Governance](GOVERNANCE.md) for the full ownership and state model.

## Translate a book

Start at [Agent translation workflow](docs/translation/agent-workflow.md).
After qualifying a book's source, rights, structure and exact execution methods,
an agent follows:

```text
doctor -> hydrate -> claim -> prepare -> blind translation -> Arabic critique
  -> optional English meaning comparison -> selective witness resolution
  -> adjudication -> names -> independent final audit -> validate -> render -> submit
```

English witnesses are optional and independently qualified for processing. They
are withheld until the blind draft and Arabic critique are frozen. Comparison
accounts for source material the reference omits; Arabic remains authoritative.
Machine completion and ongoing human review remain separate.

The coordinator uses only Python's standard library and never calls a model.
It validates ordered, hash-bound stage receipts and creates a private candidate.
Book-specific importers, alternative-host exporters, source permissions, and text publication
schemas require explicit adoption. See [lineage and adaptation](docs/translation/al-isabah-lineage.md).
The example profile deliberately fails closed until configured.

## Validate

The validator and test suite use only the Python standard library:

```console
python scripts/validate_repository.py
python -m unittest discover -s tests -v
```

GitHub Actions runs the same commands as the `contracts-and-policy` check on pull requests and `main`.

## Adopt the template

Start with [Adopt this template](docs/adopt-this-template.md). In particular, replace synthetic configuration, decide public/private boundaries and promotion policy, choose compatible code and content licenses, configure maintainers, and keep all real or restricted material outside public release paths until policy permits it.

No license is granted by this template repository. Adopters must deliberately select and document licenses appropriate to their code, source material, metadata, and scholarly content.

## Repository map

- `contracts/v1/`: versioned JSON Schemas and the read-only OpenAPI contract
- `examples/synthetic/`: content-free fixtures used by validation
- `policy/`: recursive public-payload deny policy
- `scripts/`: dependency-free release validator and translation coordinator
- `profiles/`: fail-closed translation profile starter
- `docs/translation/`: local quality policy, executable runbook, stage contracts and lineage
- `tests/`: policy, contract, closure, rollback, and compatibility tests
- `docs/`: adoption, release, review, incident, rollback, and rights/source templates

This repository is a template, not a release channel. Do not create a tag or release from its synthetic fixtures.
