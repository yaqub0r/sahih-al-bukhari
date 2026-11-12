# Name alignment supplements version 2

This additive module preserves frozen English, canonical ledgers, profiles, and
all version 1 tooling. It only permits literal case differences and an explicitly
recorded shared possessive. It does not certify the semantic scope of a modifier;
a fresh independent names review must establish that scope before admission.

`scripts/hadith_supplements_v2.py` exports the same function signatures as v1:

- `validate_source_supplement(supplement, source_path, ledger_path,
  base_inventory_path, local_graph_path)` is the unchanged v1 function alias.
- `validate_names_supplement(supplement, source_supplement, source_path,
  translation_path, ledger_path)` takes the exact source-supplement **path** as
  its second argument and returns the validated names object unchanged.
- `compile_supplement(source_supplement_path, names_supplement_path, source_path,
  translation_path, ledger_path, base_inventory_path, local_graph_path,
  source_proof, names_proof)` revalidates v1 source and v2 names, returning the
  same closed compiled shape with `version: 2`. Raw supplement hashes and
  canonical proof hashes remain distinct. Authentic independent proof
  qualification is the admitting caller's mandatory prior responsibility.
- `project_contextual_isnads(records, compiled)` strictly accepts compiled version
  2, checking its closed shape, hashes and unit keys. It deep-copies a temporary
  **projection view** with version 1 solely to reuse the unchanged v1 field
  allowlist. This view is not semantic compilation, a v1 qualification, or a new
  admitted artifact. The real version 2 input, proof hashes and private metadata
  remain intact. Only typed context reaches public records; names, modifiers,
  proof objects and private paths are never projected.

Names top-level fields are unchanged except `version: 2`: `sourceSupplementSha256`,
`sourceSha256`, `translationSha256`, `ledgerSha256`, and `addedNameAlignments`.
Every row requires the v1 fields `unitId`, `start`, `end`, `arabic`, `nameId`,
`englishStart`, `englishEnd`, `english`, and `rendering`. `english` is the exact
literal immutable target span. `rendering` is the exact registered canonical
Arabic/rendering pair. Without a modifier their casefolded strings must match.
Thus synthetic literal `His guide` may align to canonical `His Guide`; lexical
rewrites, extra articles, whitespace changes, and dropped words remain invalid.

The only optional row field is closed `sharedModifier`, containing
`kind: shared-possessive`, `englishStart`, `englishEnd`, `english`, and nonempty
`reason`. It identifies an earlier nonoverlapping literal span in the same unit.
The literal is exactly one of His/My/your/our/their/her/its, with case variants.
Adjacent Unicode letters, combining marks, numbers or underscores are forbidden;
the modifier must be a whole word. Punctuation boundaries are allowed. These
lexical boundaries do not establish semantic coordination or shared scope.
The casefolded modifier plus one space plus the main literal must equal the
canonical rendering. Synthetic `His teacher and guide` can therefore identify
`His` and `guide` as two exact spans for canonical `His Guide`, subject to
independent semantic review. Shared articles and arbitrary dropped text are not
supported. The validator never edits or normalizes either stored literal.

Compilation preserves complete affected rows, including modifier spans/reasons,
in source order. Unaffected units receive no new or empty fields. Duplicate or
missing source/name alignments, unregistered forms/renderings, stale raw pins,
and invalid spans fail. No schema, producer, registry, approval, publication
setting, prose, or canonical ledger is changed by this module.

## Private producer compatibility

`prefix_release_v3.prepare(authority_path, inventory_path, cohorts_path,
output_path, qualified_book_supplement)` is the additive producer for actual
compiled version 2. The trusted owning wrapper must authenticate independent
book admission first. Producer 2 and all prior files remain unchanged. Producer
3 retains predecessor, source, cohort, rights, registration-candidate and closed
public-adapter validation. Its private admission sidecar has version 3 and binds
the **actual compiled version 2** canonical digest and actual proof hashes,
never the temporary projection view. Generic CLI invocation fails closed.
Record schema 3, public adapter 2, config and deterministic archive format do
not change. Compilation and projection do not enable publication.
