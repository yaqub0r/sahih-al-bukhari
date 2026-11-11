# Sahih al-Bukhari

A complete-work project for an independently authored English translation of
صحيح البخاري. The Arabic working base is the pinned, cleaned OpenITI JK000110
transcription. This is a text-only edition: it is not verified against scans.

## Current status

Template adoption and source audit are in progress under issue #1. No translation
release or human scholarly approval is claimed. Synthetic fixtures are tests,
never book content. Private translation candidates and review evidence remain in
ignored runtime storage. Public Git contains tooling, policies and safe metadata.

## Translation policy

See [Bukhari adoption](docs/translation/bukhari-adoption.md),
[source decision](docs/translation/bukhari-source-decision.md), and the
[agent workflow](docs/translation/agent-workflow.md). Preserve every substantive
heading, chain, report and repetition. Translate directly from Arabic, then use
fresh independent critique, adjudication, name reconciliation and final audit.
English witnesses are disabled unless separately qualified.

Commercial use is the owner's intended use, with explicitly accepted residual
rights uncertainty; it is not a representation that OpenITI granted commercial
permission. The source decision distinguishes medieval text from modern editorial
contributions and corpus/database rights. No license to third parties for new
project content or code is granted yet. Public text distribution requires its own
reviewed schema and release decision; v1 metadata contracts remain unchanged.

## Local verification

Python 3.11+ and the standard library suffice:

```console
python scripts/validate_repository.py
python -m unittest discover -s tests -v
```

The original template is [book-repository-template](https://github.com/yaqub0r/book-repository-template).
