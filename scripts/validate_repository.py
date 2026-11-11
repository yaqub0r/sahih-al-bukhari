#!/usr/bin/env python3
"""Dependency-free validation for the synthetic scholarly-book template."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

SCHEMA_VERSION = "1.0.0"
CONTRACT_MAJOR = 1
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
EXPECTED_RELEASE_ARTIFACTS = {
    "source-provenance.json",
    "record-review-state.json",
    "correction-supersession.json",
    "consumer-projection.json",
}


class ContractError(ValueError):
    """Raised when a contract, policy, or release invariant is violated."""


def fail(path: str, message: str) -> None:
    raise ContractError(f"{path}: {message}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_free_canonical_json_bytes(value: Any) -> bytes:
    """Return the platform-neutral representation used by release hashes."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_digest(value: Any) -> tuple[str, int]:
    encoded = write_free_canonical_json_bytes(value)
    return hashlib.sha256(encoded).hexdigest(), len(encoded)


def expect_object(
    value: Any,
    path: str,
    required: Iterable[str],
    optional: Iterable[str] = (),
) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(path, "must be an object")
    required_set = set(required)
    allowed = required_set | set(optional)
    missing = sorted(required_set - set(value))
    extra = sorted(set(value) - allowed)
    if missing:
        fail(path, f"missing required field(s): {', '.join(missing)}")
    if extra:
        fail(path, f"unknown field(s): {', '.join(extra)}")
    return value


def expect_list(value: Any, path: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list):
        fail(path, "must be an array")
    if len(value) < minimum:
        fail(path, f"must contain at least {minimum} item(s)")
    return value


def expect_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        fail(path, "must be a boolean")
    return value


def expect_integer(value: Any, path: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        fail(path, "must be an integer")
    if value < minimum:
        fail(path, f"must be at least {minimum}")
    return value


def expect_string(value: Any, path: str, *, minimum: int = 1) -> str:
    if not isinstance(value, str) or len(value) < minimum:
        fail(path, f"must be a string of length at least {minimum}")
    return value


def expect_enum(value: Any, path: str, allowed: Iterable[Any]) -> Any:
    choices = tuple(allowed)
    if value not in choices:
        fail(path, f"must be one of {choices}")
    return value


def expect_id(value: Any, path: str) -> str:
    value = expect_string(value, path)
    if not ID_RE.fullmatch(value):
        fail(path, "must be a stable lowercase project identifier")
    return value


def expect_nullable_id(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return expect_id(value, path)


def expect_schema_version(value: Any, path: str) -> None:
    version = expect_string(value, path)
    try:
        major = int(version.split(".", 1)[0])
    except ValueError:
        fail(path, "must be semantic version text")
    if major != CONTRACT_MAJOR or version != SCHEMA_VERSION:
        fail(path, f"unsupported schema version {version!r}; supported: {SCHEMA_VERSION}")


def expect_datetime(value: Any, path: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    value = expect_string(value, path)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        fail(path, "must be an ISO 8601 date-time")
    if parsed.tzinfo is None:
        fail(path, "must include a timezone")
    return value


def expect_unique_strings(values: Any, path: str, *, minimum: int = 0) -> list[str]:
    items = expect_list(values, path, minimum=minimum)
    result = [expect_string(item, f"{path}[{index}]") for index, item in enumerate(items)]
    if len(set(result)) != len(result):
        fail(path, "must not contain duplicates")
    return result


def require_role(
    identities: dict[str, set[str]], identity_id: str | None, role: str, path: str
) -> None:
    if identity_id is None or role not in identities.get(identity_id, set()):
        fail(path, f"{identity_id!r} is not configured with the {role!r} role")


def validate_project_config(value: Any, path: str = "project-config") -> dict[str, Any]:
    value = expect_object(
        value,
        path,
        [
            "schemaVersion",
            "projectId",
            "identityRegistry",
            "classificationPolicy",
            "releasePolicy",
        ],
    )
    expect_schema_version(value["schemaVersion"], f"{path}.schemaVersion")
    expect_id(value["projectId"], f"{path}.projectId")

    identities: dict[str, set[str]] = {}
    for index, entry in enumerate(
        expect_list(value["identityRegistry"], f"{path}.identityRegistry", minimum=1)
    ):
        entry_path = f"{path}.identityRegistry[{index}]"
        entry = expect_object(entry, entry_path, ["id", "roles"])
        identity_id = expect_id(entry["id"], f"{entry_path}.id")
        roles = expect_unique_strings(entry["roles"], f"{entry_path}.roles", minimum=1)
        for role in roles:
            expect_enum(role, f"{entry_path}.roles", ["producer", "reviewer", "promoter"])
        if identity_id in identities:
            fail(entry_path, f"duplicate identity {identity_id!r}")
        identities[identity_id] = set(roles)

    for role in ("producer", "reviewer", "promoter"):
        if not any(role in roles for roles in identities.values()):
            fail(f"{path}.identityRegistry", f"must configure at least one {role}")

    classes = expect_object(
        value["classificationPolicy"],
        f"{path}.classificationPolicy",
        ["publicValues", "nonPublicValues"],
    )
    public_values = expect_unique_strings(
        classes["publicValues"], f"{path}.classificationPolicy.publicValues", minimum=1
    )
    non_public_values = expect_unique_strings(
        classes["nonPublicValues"],
        f"{path}.classificationPolicy.nonPublicValues",
        minimum=1,
    )
    overlap = sorted(set(public_values) & set(non_public_values))
    if overlap:
        fail(f"{path}.classificationPolicy", f"classifications overlap: {overlap}")

    release_policy = expect_object(
        value["releasePolicy"],
        f"{path}.releasePolicy",
        [
            "allowPublicWorkingRelease",
            "requireHumanReviewForRelease",
            "canonicalPromotionMode",
        ],
    )
    expect_bool(
        release_policy["allowPublicWorkingRelease"],
        f"{path}.releasePolicy.allowPublicWorkingRelease",
    )
    expect_bool(
        release_policy["requireHumanReviewForRelease"],
        f"{path}.releasePolicy.requireHumanReviewForRelease",
    )
    expect_enum(
        release_policy["canonicalPromotionMode"],
        f"{path}.releasePolicy.canonicalPromotionMode",
        ["unused", "optional", "required"],
    )
    return {
        "identities": identities,
        "public_values": set(public_values),
        "release_policy": release_policy,
    }


def validate_policy(value: Any, path: str = "public-payload-policy") -> dict[str, Any]:
    value = expect_object(
        value,
        path,
        [
            "schemaVersion",
            "scope",
            "keyNormalization",
            "prohibitedKeys",
            "prohibitedValuePatterns",
        ],
    )
    expect_schema_version(value["schemaVersion"], f"{path}.schemaVersion")
    expect_enum(value["scope"], f"{path}.scope", ["public-json-payloads"])
    expect_enum(
        value["keyNormalization"],
        f"{path}.keyNormalization",
        ["lowercase-and-remove-nonalphanumeric"],
    )
    keys = expect_unique_strings(
        value["prohibitedKeys"], f"{path}.prohibitedKeys", minimum=1
    )
    normalized_keys = set()
    for index, key in enumerate(keys):
        normalized = re.sub(r"[^a-z0-9]", "", key.lower())
        if normalized != key:
            fail(f"{path}.prohibitedKeys[{index}]", "must already be normalized")
        normalized_keys.add(normalized)

    patterns: list[tuple[str, re.Pattern[str]]] = []
    for index, item in enumerate(
        expect_list(
            value["prohibitedValuePatterns"],
            f"{path}.prohibitedValuePatterns",
            minimum=1,
        )
    ):
        item_path = f"{path}.prohibitedValuePatterns[{index}]"
        item = expect_object(item, item_path, ["id", "regex"])
        pattern_id = expect_id(item["id"], f"{item_path}.id")
        pattern_text = expect_string(item["regex"], f"{item_path}.regex")
        try:
            compiled = re.compile(pattern_text, re.IGNORECASE)
        except re.error as error:
            fail(f"{item_path}.regex", f"invalid regular expression: {error}")
        patterns.append((pattern_id, compiled))
    return {"keys": normalized_keys, "patterns": patterns}


def scan_public_payload(value: Any, policy: dict[str, Any], path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if normalized in policy["keys"]:
                fail(f"{path}.{key}", "prohibited public payload key")
            scan_public_payload(child, policy, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_public_payload(child, policy, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern_id, pattern in policy["patterns"]:
            if pattern.search(value):
                fail(path, f"prohibited public payload value ({pattern_id})")


def validate_source_register(
    value: Any, project: dict[str, Any], path: str
) -> dict[str, dict[str, Any]]:
    value = expect_object(value, path, ["schemaVersion", "entries"])
    expect_schema_version(value["schemaVersion"], f"{path}.schemaVersion")
    sources: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(expect_list(value["entries"], f"{path}.entries", minimum=1)):
        item_path = f"{path}.entries[{index}]"
        entry = expect_object(
            entry,
            item_path,
            [
                "sourceId",
                "classification",
                "sourceType",
                "locator",
                "fingerprint",
                "rights",
            ],
        )
        source_id = expect_id(entry["sourceId"], f"{item_path}.sourceId")
        if source_id in sources:
            fail(item_path, f"duplicate source {source_id!r}")
        classification = expect_string(
            entry["classification"], f"{item_path}.classification"
        )
        if classification not in project["public_values"]:
            fail(
                f"{item_path}.classification",
                "public register entry must use a configured public classification",
            )
        expect_string(entry["sourceType"], f"{item_path}.sourceType")

        locator = expect_object(
            entry["locator"], f"{item_path}.locator", ["scheme", "value"]
        )
        expect_enum(
            locator["scheme"], f"{item_path}.locator.scheme", ["uri", "opaque", "withheld"]
        )
        expect_string(locator["value"], f"{item_path}.locator.value")

        fingerprint = expect_object(
            entry["fingerprint"],
            f"{item_path}.fingerprint",
            ["algorithm", "value"],
        )
        expect_enum(
            fingerprint["algorithm"], f"{item_path}.fingerprint.algorithm", ["sha256"]
        )
        digest = expect_string(
            fingerprint["value"], f"{item_path}.fingerprint.value"
        )
        if not SHA256_RE.fullmatch(digest):
            fail(f"{item_path}.fingerprint.value", "must be a lowercase SHA-256")

        rights = expect_object(
            entry["rights"],
            f"{item_path}.rights",
            ["registryEntryId", "status", "permittedScopes", "decidedBy", "decidedAt"],
        )
        expect_id(
            rights["registryEntryId"], f"{item_path}.rights.registryEntryId"
        )
        status = expect_enum(
            rights["status"],
            f"{item_path}.rights.status",
            ["unknown", "under-review", "approved", "restricted", "expired"],
        )
        scopes = expect_unique_strings(
            rights["permittedScopes"], f"{item_path}.rights.permittedScopes"
        )
        for scope in scopes:
            expect_enum(
                scope,
                f"{item_path}.rights.permittedScopes",
                ["metadata", "derived-facts", "quotation", "full-text", "images"],
            )
        decided_by = expect_nullable_id(
            rights["decidedBy"], f"{item_path}.rights.decidedBy"
        )
        decided_at = expect_datetime(
            rights["decidedAt"], f"{item_path}.rights.decidedAt", nullable=True
        )
        if status == "approved":
            if not scopes:
                fail(f"{item_path}.rights.permittedScopes", "approved rights need a scope")
            require_role(
                project["identities"],
                decided_by,
                "reviewer",
                f"{item_path}.rights.decidedBy",
            )
            if decided_at is None:
                fail(f"{item_path}.rights.decidedAt", "approved rights need a decision time")
        sources[source_id] = entry
    return sources


def validate_review_states(
    value: Any, project: dict[str, Any], path: str
) -> dict[tuple[str, int], dict[str, Any]]:
    value = expect_object(value, path, ["schemaVersion", "records"])
    expect_schema_version(value["schemaVersion"], f"{path}.schemaVersion")
    records: dict[tuple[str, int], dict[str, Any]] = {}
    for index, entry in enumerate(expect_list(value["records"], f"{path}.records", minimum=1)):
        item_path = f"{path}.records[{index}]"
        entry = expect_object(
            entry, item_path, ["recordId", "revision", "completeness", "review"]
        )
        record_id = expect_id(entry["recordId"], f"{item_path}.recordId")
        revision = expect_integer(entry["revision"], f"{item_path}.revision", minimum=1)
        key = (record_id, revision)
        if key in records:
            fail(item_path, f"duplicate review state for {key}")

        completeness = expect_object(
            entry["completeness"],
            f"{item_path}.completeness",
            ["sourceLinkage", "metadata", "correctionState"],
        )
        expect_enum(
            completeness["sourceLinkage"],
            f"{item_path}.completeness.sourceLinkage",
            ["complete", "partial", "unknown"],
        )
        expect_enum(
            completeness["metadata"],
            f"{item_path}.completeness.metadata",
            ["complete", "partial", "unknown"],
        )
        expect_enum(
            completeness["correctionState"],
            f"{item_path}.completeness.correctionState",
            ["current", "corrected", "superseded"],
        )

        review = expect_object(
            entry["review"],
            f"{item_path}.review",
            ["status", "confidence", "reviewerId", "reviewedAt"],
        )
        status = expect_enum(
            review["status"],
            f"{item_path}.review.status",
            ["unreviewed", "in-review", "human-reviewed", "corrected"],
        )
        expect_enum(
            review["confidence"],
            f"{item_path}.review.confidence",
            ["unknown", "low", "medium", "high"],
        )
        reviewer_id = expect_nullable_id(
            review["reviewerId"], f"{item_path}.review.reviewerId"
        )
        reviewed_at = expect_datetime(
            review["reviewedAt"], f"{item_path}.review.reviewedAt", nullable=True
        )
        if status in {"human-reviewed", "corrected"}:
            require_role(
                project["identities"],
                reviewer_id,
                "reviewer",
                f"{item_path}.review.reviewerId",
            )
            if reviewed_at is None:
                fail(f"{item_path}.review.reviewedAt", "reviewed state needs a time")
        elif status == "unreviewed" and (reviewer_id is not None or reviewed_at is not None):
            fail(f"{item_path}.review", "unreviewed state cannot claim a reviewer or time")
        records[key] = entry
    return records


def validate_corrections(
    value: Any, project: dict[str, Any], path: str
) -> dict[str, dict[str, Any]]:
    value = expect_object(value, path, ["schemaVersion", "corrections"])
    expect_schema_version(value["schemaVersion"], f"{path}.schemaVersion")
    corrections: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(expect_list(value["corrections"], f"{path}.corrections")):
        item_path = f"{path}.corrections[{index}]"
        entry = expect_object(
            entry,
            item_path,
            [
                "correctionId",
                "subjectRecordId",
                "priorRevision",
                "replacementRevision",
                "status",
                "reasonCode",
                "correctedBy",
                "correctedAt",
                "supersedes",
            ],
        )
        correction_id = expect_id(entry["correctionId"], f"{item_path}.correctionId")
        if correction_id in corrections:
            fail(item_path, f"duplicate correction {correction_id!r}")
        expect_id(entry["subjectRecordId"], f"{item_path}.subjectRecordId")
        prior = expect_integer(
            entry["priorRevision"], f"{item_path}.priorRevision", minimum=1
        )
        replacement = expect_integer(
            entry["replacementRevision"],
            f"{item_path}.replacementRevision",
            minimum=2,
        )
        if replacement <= prior:
            fail(item_path, "replacementRevision must be greater than priorRevision")
        expect_enum(entry["status"], f"{item_path}.status", ["recorded"])
        expect_enum(
            entry["reasonCode"],
            f"{item_path}.reasonCode",
            ["factual", "provenance", "classification", "rights", "metadata", "withdrawal"],
        )
        corrected_by = expect_id(entry["correctedBy"], f"{item_path}.correctedBy")
        require_role(
            project["identities"], corrected_by, "reviewer", f"{item_path}.correctedBy"
        )
        expect_datetime(entry["correctedAt"], f"{item_path}.correctedAt")

        supersedes = expect_object(
            entry["supersedes"],
            f"{item_path}.supersedes",
            ["releaseId", "recordRevision"],
        )
        expect_id(supersedes["releaseId"], f"{item_path}.supersedes.releaseId")
        old_revision = expect_integer(
            supersedes["recordRevision"],
            f"{item_path}.supersedes.recordRevision",
            minimum=1,
        )
        if old_revision != prior:
            fail(
                f"{item_path}.supersedes.recordRevision",
                "must equal priorRevision",
            )
        corrections[correction_id] = entry
    return corrections


def validate_projection(
    value: Any, project: dict[str, Any], path: str
) -> dict[str, Any]:
    value = expect_object(
        value,
        path,
        [
            "schemaVersion",
            "projectionId",
            "releaseId",
            "releaseSequence",
            "contractMajor",
            "generatedAt",
            "records",
        ],
    )
    expect_schema_version(value["schemaVersion"], f"{path}.schemaVersion")
    expect_id(value["projectionId"], f"{path}.projectionId")
    expect_id(value["releaseId"], f"{path}.releaseId")
    expect_integer(value["releaseSequence"], f"{path}.releaseSequence", minimum=1)
    expect_enum(value["contractMajor"], f"{path}.contractMajor", [CONTRACT_MAJOR])
    expect_datetime(value["generatedAt"], f"{path}.generatedAt")

    records: dict[tuple[str, int], dict[str, Any]] = {}
    for index, entry in enumerate(expect_list(value["records"], f"{path}.records", minimum=1)):
        item_path = f"{path}.records[{index}]"
        entry = expect_object(
            entry,
            item_path,
            [
                "recordId",
                "revision",
                "classification",
                "sourceIds",
                "reviewStateRef",
                "correctionRef",
                "supersedesRevision",
            ],
        )
        record_id = expect_id(entry["recordId"], f"{item_path}.recordId")
        revision = expect_integer(entry["revision"], f"{item_path}.revision", minimum=1)
        key = (record_id, revision)
        if key in records:
            fail(item_path, f"duplicate projected record {key}")
        classification = expect_string(
            entry["classification"], f"{item_path}.classification"
        )
        if classification not in project["public_values"]:
            fail(
                f"{item_path}.classification",
                "projection must use a configured public classification",
            )
        source_ids = expect_unique_strings(
            entry["sourceIds"], f"{item_path}.sourceIds", minimum=1
        )
        for source_id in source_ids:
            expect_id(source_id, f"{item_path}.sourceIds")
        expect_id(entry["reviewStateRef"], f"{item_path}.reviewStateRef")
        expect_nullable_id(entry["correctionRef"], f"{item_path}.correctionRef")
        supersedes_revision = entry["supersedesRevision"]
        if supersedes_revision is not None:
            expect_integer(
                supersedes_revision, f"{item_path}.supersedesRevision", minimum=1
            )
            if supersedes_revision >= revision:
                fail(
                    f"{item_path}.supersedesRevision",
                    "must identify an earlier revision",
                )
        records[key] = entry
    return {"value": value, "records": records}


def safe_release_path(value: Any, path: str) -> str:
    value = expect_string(value, path)
    if "\\" in value:
        fail(path, "must use a relative POSIX path")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or ".." in parsed.parts or "." in parsed.parts:
        fail(path, "must stay within the release directory")
    if parsed.name != value:
        fail(path, "nested release artifacts are not supported by version 1")
    return value


def validate_release_closure(
    value: Any,
    project: dict[str, Any],
    release_dir: Path,
    parsed_public_files: dict[str, Any],
    review_records: dict[tuple[str, int], dict[str, Any]],
    path: str,
) -> dict[str, Any]:
    value = expect_object(
        value,
        path,
        [
            "schemaVersion",
            "releaseId",
            "releaseSequence",
            "previousReleaseId",
            "createdAt",
            "producerId",
            "states",
            "consumerCompatibility",
            "artifacts",
        ],
    )
    expect_schema_version(value["schemaVersion"], f"{path}.schemaVersion")
    release_id = expect_id(value["releaseId"], f"{path}.releaseId")
    sequence = expect_integer(value["releaseSequence"], f"{path}.releaseSequence", minimum=1)
    previous_release_id = expect_nullable_id(
        value["previousReleaseId"], f"{path}.previousReleaseId"
    )
    if sequence == 1 and previous_release_id is not None:
        fail(f"{path}.previousReleaseId", "first release cannot have a predecessor")
    if sequence > 1 and previous_release_id is None:
        fail(f"{path}.previousReleaseId", "later release must identify its predecessor")
    expect_datetime(value["createdAt"], f"{path}.createdAt")
    producer_id = expect_id(value["producerId"], f"{path}.producerId")
    require_role(project["identities"], producer_id, "producer", f"{path}.producerId")

    states = expect_object(
        value["states"],
        f"{path}.states",
        ["publicRelease", "canonicalPromotion", "promotedBy", "promotedAt"],
    )
    public_state = expect_enum(
        states["publicRelease"],
        f"{path}.states.publicRelease",
        ["published", "withdrawn"],
    )
    promotion_state = expect_enum(
        states["canonicalPromotion"],
        f"{path}.states.canonicalPromotion",
        ["not-used", "candidate", "promoted", "reverted"],
    )
    promoted_by = expect_nullable_id(
        states["promotedBy"], f"{path}.states.promotedBy"
    )
    promoted_at = expect_datetime(
        states["promotedAt"], f"{path}.states.promotedAt", nullable=True
    )
    if promotion_state in {"promoted", "reverted"}:
        require_role(
            project["identities"],
            promoted_by,
            "promoter",
            f"{path}.states.promotedBy",
        )
        if promoted_at is None:
            fail(f"{path}.states.promotedAt", "promotion decision needs a time")
    elif promoted_by is not None or promoted_at is not None:
        fail(
            f"{path}.states",
            "non-final promotion state cannot claim a promoter or promotion time",
        )
    promotion_mode = project["release_policy"]["canonicalPromotionMode"]
    if promotion_mode == "unused" and promotion_state != "not-used":
        fail(f"{path}.states.canonicalPromotion", "project configured promotion as unused")
    if promotion_mode == "required" and public_state == "published" and promotion_state != "promoted":
        fail(f"{path}.states.canonicalPromotion", "project requires promotion before publication")

    compatibility = expect_object(
        value["consumerCompatibility"],
        f"{path}.consumerCompatibility",
        ["contractMajor", "minimumConsumerMajor", "maximumConsumerMajor"],
    )
    expect_enum(
        compatibility["contractMajor"],
        f"{path}.consumerCompatibility.contractMajor",
        [CONTRACT_MAJOR],
    )
    minimum = expect_integer(
        compatibility["minimumConsumerMajor"],
        f"{path}.consumerCompatibility.minimumConsumerMajor",
        minimum=1,
    )
    maximum = expect_integer(
        compatibility["maximumConsumerMajor"],
        f"{path}.consumerCompatibility.maximumConsumerMajor",
        minimum=1,
    )
    if not (minimum <= CONTRACT_MAJOR <= maximum):
        fail(f"{path}.consumerCompatibility", "does not include contract major 1")

    artifact_paths: set[str] = set()
    for index, artifact in enumerate(
        expect_list(value["artifacts"], f"{path}.artifacts", minimum=1)
    ):
        item_path = f"{path}.artifacts[{index}]"
        artifact = expect_object(
            artifact,
            item_path,
            ["path", "mediaType", "schemaVersion", "sha256", "canonicalBytes"],
        )
        relative_path = safe_release_path(artifact["path"], f"{item_path}.path")
        if relative_path in artifact_paths:
            fail(item_path, f"duplicate artifact {relative_path!r}")
        artifact_paths.add(relative_path)
        expect_enum(
            artifact["mediaType"], f"{item_path}.mediaType", ["application/json"]
        )
        expect_schema_version(artifact["schemaVersion"], f"{item_path}.schemaVersion")
        expected_digest = expect_string(artifact["sha256"], f"{item_path}.sha256")
        if not SHA256_RE.fullmatch(expected_digest):
            fail(f"{item_path}.sha256", "must be a lowercase SHA-256")
        expected_bytes = expect_integer(
            artifact["canonicalBytes"], f"{item_path}.canonicalBytes", minimum=2
        )
        artifact_path = release_dir / relative_path
        if not artifact_path.is_file():
            fail(f"{item_path}.path", f"artifact is missing: {relative_path}")
        artifact_value = parsed_public_files.get(relative_path)
        if artifact_value is None:
            artifact_value = load_json(artifact_path)
        expect_schema_version(
            artifact_value.get("schemaVersion") if isinstance(artifact_value, dict) else None,
            f"{relative_path}.schemaVersion",
        )
        actual_digest, actual_bytes = canonical_digest(artifact_value)
        if actual_digest != expected_digest:
            fail(
                f"{item_path}.sha256",
                f"hash mismatch for {relative_path}: expected {expected_digest}, got {actual_digest}",
            )
        if actual_bytes != expected_bytes:
            fail(
                f"{item_path}.canonicalBytes",
                f"length mismatch for {relative_path}: expected {expected_bytes}, got {actual_bytes}",
            )
    if artifact_paths != EXPECTED_RELEASE_ARTIFACTS:
        fail(
            f"{path}.artifacts",
            f"release closure must contain exactly {sorted(EXPECTED_RELEASE_ARTIFACTS)}",
        )

    if public_state == "published":
        review_policy = project["release_policy"]
        if review_policy["requireHumanReviewForRelease"]:
            incomplete = [
                key
                for key, item in review_records.items()
                if item["review"]["status"] not in {"human-reviewed", "corrected"}
            ]
            if incomplete:
                fail(
                    f"{path}.states.publicRelease",
                    f"project policy requires human review; incomplete records: {incomplete}",
                )
        elif not review_policy["allowPublicWorkingRelease"]:
            incomplete = [
                key
                for key, item in review_records.items()
                if item["review"]["status"] not in {"human-reviewed", "corrected"}
            ]
            if incomplete:
                fail(
                    f"{path}.states.publicRelease",
                    "project disallows a public working release with incomplete review",
                )
    return {
        "value": value,
        "release_id": release_id,
        "sequence": sequence,
        "previous_release_id": previous_release_id,
    }


def validate_release_pointer(
    value: Any,
    project: dict[str, Any],
    closure: dict[str, Any],
    path: str,
) -> None:
    value = expect_object(
        value,
        path,
        [
            "schemaVersion",
            "pointerId",
            "activeReleaseId",
            "latestReleaseId",
            "reasonCode",
            "rollbackFromReleaseId",
            "updatedAt",
            "updatedBy",
        ],
    )
    expect_schema_version(value["schemaVersion"], f"{path}.schemaVersion")
    expect_id(value["pointerId"], f"{path}.pointerId")
    active = expect_id(value["activeReleaseId"], f"{path}.activeReleaseId")
    latest = expect_id(value["latestReleaseId"], f"{path}.latestReleaseId")
    reason = expect_enum(
        value["reasonCode"], f"{path}.reasonCode", ["normal-advance", "rollback"]
    )
    rollback_from = expect_nullable_id(
        value["rollbackFromReleaseId"], f"{path}.rollbackFromReleaseId"
    )
    expect_datetime(value["updatedAt"], f"{path}.updatedAt")
    updated_by = expect_id(value["updatedBy"], f"{path}.updatedBy")
    require_role(project["identities"], updated_by, "promoter", f"{path}.updatedBy")

    if latest != closure["release_id"]:
        fail(f"{path}.latestReleaseId", "must identify the validated latest closure")
    if reason == "normal-advance":
        if active != latest or rollback_from is not None:
            fail(path, "normal advance requires active=latest and no rollbackFromReleaseId")
    else:
        if closure["previous_release_id"] is None:
            fail(path, "cannot roll back a first release")
        if active != closure["previous_release_id"]:
            fail(f"{path}.activeReleaseId", "rollback target must be closure.previousReleaseId")
        if rollback_from != latest:
            fail(f"{path}.rollbackFromReleaseId", "must identify latestReleaseId")


def validate_cross_links(
    sources: dict[str, dict[str, Any]],
    reviews: dict[tuple[str, int], dict[str, Any]],
    corrections: dict[str, dict[str, Any]],
    projection: dict[str, Any],
    closure: dict[str, Any],
) -> None:
    projection_value = projection["value"]
    if projection_value["releaseId"] != closure["release_id"]:
        fail("consumer-projection.releaseId", "must match release-closure.releaseId")
    if projection_value["releaseSequence"] != closure["sequence"]:
        fail("consumer-projection.releaseSequence", "must match release closure")
    if projection_value["contractMajor"] != closure["value"]["consumerCompatibility"]["contractMajor"]:
        fail("consumer-projection.contractMajor", "must match release compatibility")

    projected_keys = set(projection["records"])
    if set(reviews) != projected_keys:
        fail("record-review-state.records", "must cover exactly the projected record revisions")

    for key, entry in projection["records"].items():
        record_id, revision = key
        expected_review_ref = f"{record_id}.r{revision}"
        if entry["reviewStateRef"] != expected_review_ref:
            fail(
                f"consumer-projection.records[{record_id}].reviewStateRef",
                f"must equal {expected_review_ref!r}",
            )
        unknown_sources = sorted(set(entry["sourceIds"]) - set(sources))
        if unknown_sources:
            fail(
                f"consumer-projection.records[{record_id}].sourceIds",
                f"unknown source IDs: {unknown_sources}",
            )
        correction_ref = entry["correctionRef"]
        if correction_ref is None:
            if entry["supersedesRevision"] is not None:
                fail(
                    f"consumer-projection.records[{record_id}]",
                    "supersedesRevision requires correctionRef",
                )
            continue
        correction = corrections.get(correction_ref)
        if correction is None:
            fail(
                f"consumer-projection.records[{record_id}].correctionRef",
                f"unknown correction {correction_ref!r}",
            )
        if correction["subjectRecordId"] != record_id:
            fail(
                f"consumer-projection.records[{record_id}].correctionRef",
                "correction subject does not match record",
            )
        if correction["replacementRevision"] != revision:
            fail(
                f"consumer-projection.records[{record_id}].revision",
                "must equal correction replacementRevision",
            )
        if correction["priorRevision"] != entry["supersedesRevision"]:
            fail(
                f"consumer-projection.records[{record_id}].supersedesRevision",
                "must equal correction priorRevision",
            )

    referenced_corrections = {
        entry["correctionRef"]
        for entry in projection["records"].values()
        if entry["correctionRef"] is not None
    }
    if referenced_corrections != set(corrections):
        fail("correction-supersession.corrections", "must be referenced exactly once by projections")


def validate_contract_schemas(contracts_dir: Path) -> None:
    schema_paths = sorted(contracts_dir.glob("*.schema.json"))
    if not schema_paths:
        fail(str(contracts_dir), "no JSON Schemas found")

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and node.get("additionalProperties") is not False:
                fail(path, "every object schema must set additionalProperties to false")
            for key, child in node.items():
                walk(child, f"{path}.{key}")
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{path}[{index}]")

    for schema_path in schema_paths:
        schema = load_json(schema_path)
        expect_object(
            schema,
            str(schema_path),
            ["$schema", "$id", "title", "type", "additionalProperties", "required", "properties"],
            ["$defs"],
        )
        expect_enum(
            schema["$schema"],
            f"{schema_path}.$schema",
            ["https://json-schema.org/draft/2020-12/schema"],
        )
        expect_enum(schema["type"], f"{schema_path}.type", ["object"])
        if schema["additionalProperties"] is not False:
            fail(str(schema_path), "root schema must be closed")
        walk(schema, str(schema_path))


def validate_openapi(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    required_fragments = [
        "openapi: 3.1.0",
        "/v1/releases/{releaseId}/projection:",
        "/v1/release-pointer:",
        "X-Contract-Major",
        "$ref: './consumer-projection.schema.json'",
        "$ref: './release-pointer.schema.json'",
    ]
    for fragment in required_fragments:
        if fragment not in text:
            fail(str(path), f"missing required read-only API element: {fragment}")
    if re.search(r"(?m)^\s{4}(post|put|patch|delete):", text):
        fail(str(path), "consumer API must remain read-only")


def validate_bundle(
    project_path: Path,
    release_dir: Path,
    contracts_dir: Path,
    policy_path: Path,
) -> dict[str, Any]:
    project_value = load_json(project_path)
    project = validate_project_config(project_value, project_path.name)
    policy = validate_policy(load_json(policy_path), policy_path.name)

    parsed_public_files: dict[str, Any] = {}
    for public_path in sorted(release_dir.glob("*.json")):
        parsed = load_json(public_path)
        scan_public_payload(parsed, policy, public_path.name)
        parsed_public_files[public_path.name] = parsed

    required_files = EXPECTED_RELEASE_ARTIFACTS | {
        "release-closure.json",
        "release-pointer.json",
    }
    missing = sorted(required_files - set(parsed_public_files))
    if missing:
        fail(str(release_dir), f"missing required public file(s): {', '.join(missing)}")

    sources = validate_source_register(
        parsed_public_files["source-provenance.json"],
        project,
        "source-provenance",
    )
    reviews = validate_review_states(
        parsed_public_files["record-review-state.json"],
        project,
        "record-review-state",
    )
    corrections = validate_corrections(
        parsed_public_files["correction-supersession.json"],
        project,
        "correction-supersession",
    )
    projection = validate_projection(
        parsed_public_files["consumer-projection.json"],
        project,
        "consumer-projection",
    )
    closure = validate_release_closure(
        parsed_public_files["release-closure.json"],
        project,
        release_dir,
        parsed_public_files,
        reviews,
        "release-closure",
    )
    validate_cross_links(sources, reviews, corrections, projection, closure)
    validate_release_pointer(
        parsed_public_files["release-pointer.json"],
        project,
        closure,
        "release-pointer",
    )
    validate_contract_schemas(contracts_dir)
    validate_openapi(contracts_dir / "openapi.yaml")
    return {
        "release_id": closure["release_id"],
        "artifact_count": len(closure["value"]["artifacts"]),
        "record_count": len(projection["records"]),
        "unreviewed_count": sum(
            item["review"]["status"] == "unreviewed" for item in reviews.values()
        ),
    }


def validate_repository(root: Path) -> dict[str, Any]:
    validate_project_config(
        load_json(root / "project.config.example.json"),
        "project.config.example.json",
    )
    return validate_bundle(
        root / "examples" / "synthetic" / "project-config.json",
        root / "examples" / "synthetic" / "public-release",
        root / "contracts" / "v1",
        root / "policy" / "public-payload-policy.json",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the script's parent repository)",
    )
    args = parser.parse_args()
    try:
        result = validate_repository(args.root.resolve())
    except (ContractError, OSError, json.JSONDecodeError) as error:
        print(f"validation failed: {error}", file=sys.stderr)
        return 1
    print(
        "validated "
        f"{result['release_id']}: "
        f"{result['artifact_count']} artifacts, "
        f"{result['record_count']} records, "
        f"{result['unreviewed_count']} explicitly unreviewed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
