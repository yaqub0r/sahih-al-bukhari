# Add-only metadata and contextual isnad supplements

The unpublished prefix adopts contract `sahih-al-bukhari-prefix-distribution-2`
through the existing `release/distribution-prefix-v1.config.json` locator. This is
an unpublished contract upgrade, not a change to any published release. Record
schema 3 clones schema 2 and adds one optional closed root `contextualIsnad`.
The original v1/v2 record schemas, local H1/H2 engines, profiles, collection
producer, prior proposals, prefix source policy and predecessor digests remain
unchanged. Publication stays disabled and registration remains independent.

The contextual layer represents textual continuation, not historical contact,
a new hearing event, or reconciliation of narrator identities. It preserves two
complete ordered antecedent prefixes, including their compiler root and every
node/edge, and connects their distinct named terminal occurrences to the
separate printed narrator occurrence in the current record. Current dual and
attribution cues have exact Unicode spans and literal text. Devotional hearing
inside prayer content cannot be used as a continuation cue. References resolve
only to earlier records in the same released prefix and bind both Arabic hashes.
The known continuation in this prefix requires this layer and its qualified
antecedent; publishing a base-only record cannot evade that requirement.

The reader displays both full chains with Arabic narrator mentions and literal
transmission wording, the current source occurrence, contextual wording, limits,
and a link to the antecedent. The ordinary closed machine structure remains
visible. All values are HTML escaped. Reader parity uses the existing exact
reconstruction check; the archive still has exactly five deterministic members.
Records with no extension retain the previous reader rendering and data fields.

## Private API

`scripts/hadith_supplements_v1.py` provides structural and digest validation.
None of these functions authenticates a semantic worker or authorizes publication.
All input paths and authentic captures stay in ignored private runtime storage.
Raw pins use exact file bytes; proof digests use canonical JSON.

`validate_source_supplement(supplement, source_path, ledger_path,
base_inventory_path, local_graph_path)` returns the validated object unchanged.
Its closed top level contains `version: 1`, `sourceSha256`, `ledgerSha256`,
`baseInventorySha256`, `localGraphSha256`, `addedNameOccurrences`, and
`contextualIsnads`. Added occurrence rows contain only `unitId`, `start`, `end`,
`arabic`, and `nameId`. They must be new source occurrences of an existing ledger
identity/form. The original inventory is never rewritten. Context rows contain
only `unitId` and `contextualIsnad`.

The closed context object contains `version: 1`,
`kind: dual-source-continuation`, `currentArabicSha256`, `antecedentUnitId`,
`antecedentArabicSha256`, `currentSourceNodeId`, `cues`, `branches`, and a nonempty
`uncertainty` disclosure. There are exactly two cues, in order: `dual-speakers`
and `attribution`. Each contains `role`, `start`, `end`, and `arabic`. There are
exactly two distinct branches. A branch contains `id`, `antecedentNodeIds`,
`antecedentEdgeIds`, `currentSourceNodeId`, and
`relation: contextual-ascription`. Ordered edge endpoints must match adjacent
nodes; every edge must belong to a released path. Known names cannot be replaced
with gaps. Both branches point to the same distinct current source occurrence.

`validate_names_supplement(supplement, source_supplement, source_path,
translation_path, ledger_path)` takes the source supplement **path** as its second
argument and returns the validated names object unchanged. Its closed top level
contains `version: 1`, `sourceSupplementSha256`, `sourceSha256`,
`translationSha256`, `ledgerSha256`, and `addedNameAlignments`. Each alignment has
`unitId`, `start`, `end`, `arabic`, `nameId`, `englishStart`, `englishEnd`, `english`,
and `rendering`. The last two must match the exact immutable English span and the
registered rendering for that Arabic form. Alignments must cover exactly the
added source occurrences without duplicates. This never edits English prose.

`compile_supplement(source_supplement_path, names_supplement_path, source_path,
translation_path, ledger_path, base_inventory_path, local_graph_path,
source_proof, names_proof)` requires the caller to have independently qualified
both authentic semantic proof objects first. It revalidates both artifacts and
returns a closed object containing `version: 1`, `sourceSupplementSha256`,
`namesSupplementSha256`, `sourceProofSha256`, `namesProofSha256`, and `units`.
Only affected units occur. Each row retains `unitId`, full
`addedNameOccurrences`, full `addedNameAlignments`, and `contextualIsnad` only
when present. Unaffected units receive no new or empty metadata fields.

`project_contextual_isnads(records, compiled)` copies records and allowlists only
the typed context field. It never projects private proof objects, name alignment
metadata, file locators or capture references. It cannot overwrite an existing
context layer. `validate_contextual_isnads(records)` performs cross-record
validation after unchanged base-v2 admission.

## Producer admission

The trusted owning private wrapper must run authentic B6
`validate_book_supplement` **before** collection or production, then call
`prefix_release_v2.prepare(authority_path, inventory_path, cohorts_path,
output_path, qualified_book_supplement)`. The gate result contains `book`,
`compiled`, `semanticActors`, `sourceProof`, and `namesProof`. The producer checks
proof digest consistency, retains ordinary cohort admission, projects context,
and validates the complete proposal. Generic producer CLI invocation fails
closed. Arbitrary callbacks, module paths, verdict-only files, and a plain
syntactic supplement PASS are not semantic admission.

The owning wrapper must bind/revalidate its admitted inputs and the exact output;
this public module cannot establish that an arbitrary caller really ran B6.
Private admission sidecars record compiled/proof digests. A registration candidate
is preparation evidence, not registry promotion or publishing approval. Normal
independent projection review, exact proposal registration, protected workflow,
review bindings and immutable release controls still govern delivery.
