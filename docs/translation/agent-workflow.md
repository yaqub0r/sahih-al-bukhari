# Agent entry point

This template now provides a generic executable translation coordinator. It does
not invoke a model, select rights on your behalf, or publish a book automatically.
After the adoption steps below, an agent can own a locked book scope through
translation and candidate submission without needing Elixr, a database, or an API
service. Python 3.11+, Git, and authenticated GitHub CLI are required.

## Adopt once per book

1. Follow `../adopt-this-template.md`. Read `quality-workflow.md` and
   `stage-contracts.md`. Create the book's issue and policies before importing.
2. Qualify the Arabic edition/authority and permitted witnesses for the intended
   commercial or noncommercial use. Register exact rights evidence, attribution,
   identities, hashes and allowed uses. Preserve immutable originals privately.
3. Supply a book-specific importer or frozen structured authority using the
   documented unit format. Validate alignment and exclusion coverage; independently
   review source order, chapter/chain boundaries, continuation context and formula
   spans. Do not copy Al-Isabah's OpenITI parser or biography-title rules to hadith.
4. Copy `profiles/translation-profile.example.json` to a versioned book profile.
   Replace **all** synthetic identities, hashes, methods and decisions. Supply
   approved exact coordinator/worker methods. Use the included Codex metadata
   adapter, or qualify a different host exporter. Register known
   name identities in a versioned, hash-bound project ledger before preparing
   production scopes; a newly discovered identity requires a reviewed revision. Bind local policies,
   executable, importer, and book-specific decisions by raw SHA-256. No policy
   dependency may live only in another repository.
5. Choose comparison enabled with an authorized English witness, or disabled with
   a reason. English-reference lack/omissions never exempt Arabic material.
6. Agree the publication schema and gates separately. The template remains
   synthetic-only, and its metadata projection is not a book-content schema.

## Execute a scope

Commands below assume repository root. Replace placeholders; do not run these
against this template's synthetic repository identity. Source and witness files,
all intermediate outputs, normalized host captures and receipts remain in
ignored `.runtime/` or approved private evidence storage.

```console
python scripts/translation_workflow.py doctor --profile profiles/book.v1.json
python -m unittest discover -s tests -v
python scripts/translation_workflow.py hydrate --profile profiles/book.v1.json --url https://provider.example/approved-authority.json --run .runtime/translation/acquisition
python scripts/translation_workflow.py status --profile profiles/book.v1.json
python scripts/translation_workflow.py claim --profile profiles/book.v1.json --source .runtime/translation/acquisition/source.json --units chapter-001 chain-001 report-001 --assignee YOUR_GITHUB_LOGIN
python scripts/translation_workflow.py prepare --profile profiles/book.v1.json --source .runtime/translation/acquisition/source.json --units chapter-001 chain-001 report-001 --issue ISSUE_NUMBER --coordinator-session ACTUAL_HOST_SESSION_ID --run .runtime/translation/issue-N-attempt-1
```

`hydrate` fetches HTTPS only and rejects a mismatched byte length/hash without
writing source bytes. Alternatively provide an already qualified local authority.
`claim` writes a GitHub assignment issue and rechecks overlap; `prepare` and
`submit` recheck the live ledger. GitHub issues are coordination, not an atomic
lock: if a concurrent claim overlaps, stop both affected executions and reconcile
ownership before semantic work. Do not ignore a failed post-claim overlap check.

For each next stage (`blind`, `critique`, optionally `comparison`, `witness`,
`adjudication`, `names`, `audit`):

```console
python scripts/translation_workflow.py stage-input --profile profiles/book.v1.json --run .runtime/translation/issue-N-attempt-1 --stage blind
```

Launch a fresh worker with explicit approved model/reasoning settings. Give only
the relevant Arabic/policy/stage input, never reference English to the blind
translator or Arabic critic. Read stage contracts for output shapes. The
coordinator captures actual host settings and hashes; the worker cannot attest
its own effective execution settings. Do not expose whole prior chats or mixed
book histories. Semantic decisions belong to independently launched agents;
deterministic commands do not need an LLM.

After the worker completes, save the actual explicit launch settings in private
JSON records: worker `{provider, model, reasoning, forkTurns: "none"}` and
coordinator `{provider, model, reasoning}`. These are launch receipts, never
values inferred from the worker's response. Capture the selected host-written
session and turn metadata before `record`:

```console
python scripts/translation_workflow.py capture-host --profile profiles/book.v1.json --run .runtime/translation/issue-N-attempt-1 --stage blind --output .runtime/blind-output.json --host .runtime/blind-host.json --session-log SELECTED_WORKER_LOG --session ACTUAL_WORKER_SESSION_ID --turn ACTUAL_WORKER_TURN_ID --coordinator-log SELECTED_COORDINATOR_LOG --coordinator-turn ACTUAL_COORDINATOR_TURN_ID --launch .runtime/worker-launch.json --coordinator-launch .runtime/coordinator-launch.json
```

Then record the captured stage:

```console
python scripts/translation_workflow.py record --profile profiles/book.v1.json --run .runtime/translation/issue-N-attempt-1 --stage blind --output .runtime/blind-output.json --host .runtime/blind-host.json
```

The adapter reads only explicitly selected JSONL logs. It retains selected
metadata and hashes without private text or log paths. Missing/unsupported host
metadata holds execution; never synthesize effective observations.

For both comparison `stage-input` and `record`, add
`--witness-file .runtime/qualified-english.txt`. The file is checked against the
registered witness. It is only added to stage input after Arabic critique.
Do not commit or expose it in a public report. Other witness consultation stays
selective and registered; preserve exact retrieval/passage evidence privately.

```console
python scripts/translation_workflow.py validate --profile profiles/book.v1.json --run .runtime/translation/issue-N-attempt-1
python scripts/translation_workflow.py render --profile profiles/book.v1.json --run .runtime/translation/issue-N-attempt-1
python scripts/translation_workflow.py submit --profile profiles/book.v1.json --run .runtime/translation/issue-N-attempt-1
```

`render` creates a private bilingual HTML artifact, English before Arabic on both
wide and narrow layouts. When previewing it, serve it through an approved local
HTTP server; do not open a `file://` URL. `submit` verifies the exact presentation
and writes `.runtime/.../submission.json`; it makes no GitHub publication call.
Review the eligible allowlisted candidate through the adopted book's proposal,
promotion and release mechanism. Keep private receipts available by hash.

Each receipt and rendering is write-once. On a substantive correction create a
new attempt directory, preserve the old attempt and issue history, and rerun
affected stages with fresh capture. Do not repeatedly retry a source or rights
failure; fix the input/permission issue and its reviewed profile first. A live
checkpoint should record issue, run directory, source/profile pins, completed
stages, held findings and exact next action; store private locations privately.

## Verify the foundation

```console
python scripts/validate_repository.py
python -m unittest discover -s tests -v
```

The synthetic end-to-end tests exercise both comparison paths through rendering
and submission, plus negative provenance, rights, coverage and boundary cases.
They call no model and create no GitHub issue or release. These tests establish
coordinator behavior, not translation quality or production-host qualification.
