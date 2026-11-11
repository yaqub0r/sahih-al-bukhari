# Contributing

1. Open or select one focused issue and work on a feature branch.
2. Keep fixtures synthetic. Do not paste real source material, book content, evidence, credentials, private paths, or model traces into issues, commits, tests, or pull requests.
3. Update schema, validator, synthetic fixture, test, and consumer documentation together when changing a contract.
4. Run `python scripts/validate_repository.py` and `python -m unittest discover -s tests -v`.
5. Open a pull request using the repository template. Resolve conversations and wait for `contracts-and-policy` before a normal merge.

Closed schemas are intentional: new fields require an explicit compatibility decision. Review metadata must describe record state without embedding review evidence or source/body text in public projections.

No contribution is licensed merely by being submitted here because this template intentionally has no license. Repository owners must establish contribution and licensing terms before accepting external work.
