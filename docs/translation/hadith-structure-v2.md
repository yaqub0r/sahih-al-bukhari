# Ordered isnad companion, version 2: reciprocal source communications

Version 1 remains immutable. All of its source binding, closed shapes, literal
spans, narrator identity, path ordering, report coverage, uncertainty, audit and
actual execution-capture requirements apply here except the explicitly changed
global cycle rule. This contract has its own script/specification hash, which
also binds the unchanged v1 contract. It does not certify historical contact.

A v2 structure has `version: 2`. Each unit may add the
`reciprocalCommunications` array; omission means no reciprocal declaration.
Inherited v1 units must retain omission exactly rather than adding an empty field. Each declaration is
exactly `{id, edgeIds, note}`. `edgeIds` contains exactly two distinct opposing
edges between the same two source-bound physical narrator occurrences. Both
edges must be explicit with distinct nonoverlapping predicates in printed source
order; the note explains the actual telling and response. A declaration is not
permission to infer an unprinted receipt, identity or historical interaction.

Each reciprocal edge belongs exclusively to its own two-node embedded path.
Primary, parallel, heading and commentary chains cannot use those edges. Every
path still forbids repeated nodes; self-links, gaps asserted explicit, dangling
links and orphan graph items remain prohibited. Two different printed mentions
of the same narrator remain separate occurrence nodes. Do not duplicate one
physical occurrence to evade a cycle, or use an earlier mention as a false
receiver for a later dialogue.

Validate strongly connected components of the **full graph**. Any cyclic
component must contain exactly the two physical narrators in one declaration,
with precisely its two declared internal edges. Larger cycles, extra internal
edges, undeclared cycles and duplicate declarations fail. Do not merely delete
the declared edges before checking for cycles: that could conceal a longer loop.
Independent source-based review must verify both predicates, their direction,
physical actor referents, semantic role and source order. Reciprocal textual
communications are separate ordered receipts, not a cyclic historical isnad.

The audit JSON, exact ten artifact names, actual fresh worker/capture rules and
source/English binding stay as in v1. The private manifest uses `version: 2` and
`kind: private-hadith-structure-companion-v2`; input/receipt hashes bind this new
contract. Final extraction requires the reviewed v2 contract before finalization.
Core translation profiles and previously saved submissions are not rewritten.
The renderer explicitly lists reciprocal declarations alongside their paths.

Collection/public integration must dispatch on explicit manifest/graph identity,
retain every new declaration, and validate with this contract. The original
release's records and v1 path remain unchanged. A new public field must be
optional for legacy records but closed and fully checked when present. This
specification alone does not enable publication or alter release approval.
