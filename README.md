# Sahih al-Bukhari

A complete-work project for an independently authored English translation of
صحيح البخاري. The Arabic working base is the pinned, cleaned OpenITI JK000110
transcription. This is a text-only edition: it is not verified against scans.

## Current status

The first public-working release covers the opening and Book of Faith: 110
retained units and numbered reports 1–58, including ordered Arabic isnads,
branches, missing links and all uncertainty disclosures. Every record remains
**human-unreviewed**. This is a partial-work release, not completion of the
collection or human scholarly approval. See [Releases](https://github.com/yaqub0r/sahih-al-bukhari/releases)
and the [first-release decision](docs/decisions/bukhari-working-release-1.md).
Private drafts, execution captures and review evidence remain excluded.

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
contributions and corpus/database rights. Our original English and project-authored structure/notes are licensed under
[CC BY 4.0](LICENSE-CONTENT.md), permitting commercial reuse under its terms.
This does not relicense third-party source contributions or repository software.
The scoped distribution decision preserves accepted source risks and attribution;
v1 metadata contracts remain unchanged.

## Local verification

Python 3.11+ and the standard library suffice:

```console
python scripts/validate_repository.py
python -m unittest discover -s tests -v
```

The original template is [book-repository-template](https://github.com/yaqub0r/book-repository-template).


Hadith records also require a [source-bound ordered isnad companion](docs/translation/hadith-structure.md).
It separates narration paths from matn while retaining exact Arabic transmission
wording, branches, missing links and uncertainty. Translation-only completion is
insufficient for an adopted hadith scope. Existing v1 metadata contracts are unchanged.

## Prepare a book distribution

See [the reusable release workflow](docs/distribution-workflow.md) for deterministic private preparation, review, explicit licensing and separately authorized manual publication. Publishing is disabled by default; existing v1 metadata contracts remain unchanged.

Bukhari: [first-release candidate and ordered isnad contract](docs/bukhari-release-candidate.md).
