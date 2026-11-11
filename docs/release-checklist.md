# Release checklist

## Scope and authority

- [ ] Release identity and sequence are new and immutable.
- [ ] Producer ID resolves to the configured producer role.
- [ ] Public-release state and optional canonical-promotion state are set independently.
- [ ] Every included source/record has an explicit classification and current rights entry.

## Package verification

- [ ] Run the repository validator and complete tests from a clean checkout.
- [ ] Confirm every closure artifact exists and matches its canonical SHA-256 and byte length.
- [ ] Confirm projection, closure, pointer, and requested consumer pin use the same release identity.
- [ ] Confirm the contract major is supported and compatibility bounds are intentional.
- [ ] Confirm recursive prohibited-payload validation passes.
- [ ] Confirm unreviewed/incomplete records are accurately labeled and allowed by project release policy.

## Operations

- [ ] Record the previous release and tested rollback target.
- [ ] Confirm consumers can pin the new release and retain the prior release during rollout.
- [ ] Obtain any separately required canonical-promotion decision.
- [ ] Keep immutable artifacts; never repair them in place.
- [ ] Record release outcome and incidents without embedding private evidence in public metadata.
