## Why

<!-- Link the focused issue and explain the intended outcome. -->

Closes #

## Change

<!-- Summarize contracts, policy, implementation, or documentation changed. -->

## Boundary and compatibility

- [ ] Fixtures and examples are synthetic-only.
- [ ] No book/source/translation text, OCR, evidence, model trace, prompt, credential, private path, or database data is included.
- [ ] Public/private and producer/consumer ownership remain explicit.
- [ ] Contract-major and consumer compatibility impact is documented.
- [ ] No release, tag, deployment, or database change is part of this PR.

## Verification

- [ ] `python scripts/validate_repository.py`
- [ ] `python -m unittest discover -s tests -v`
- [ ] `contracts-and-policy` is green and conversations are resolved.

## Rollback

<!-- State how to revert this repository change. Released artifacts remain immutable. -->
