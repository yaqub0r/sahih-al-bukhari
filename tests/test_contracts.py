from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.validate_repository import (
    ContractError,
    canonical_digest,
    validate_bundle,
    validate_contract_schemas,
    validate_openapi,
)

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_SYNTHETIC = ROOT / "examples" / "synthetic"


class RepositoryContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self._temporary.name) / "synthetic"
        shutil.copytree(ORIGINAL_SYNTHETIC, self.workspace)
        self.project = self.workspace / "project-config.json"
        self.release = self.workspace / "public-release"
        self.contracts = ROOT / "contracts" / "v1"
        self.policy = ROOT / "policy" / "public-payload-policy.json"

    def tearDown(self) -> None:
        self._temporary.cleanup()

    @staticmethod
    def read(path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def write(path: Path, value) -> None:
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def validate(self):
        return validate_bundle(
            self.project,
            self.release,
            self.contracts,
            self.policy,
        )

    def refresh_artifact(self, name: str) -> None:
        closure_path = self.release / "release-closure.json"
        closure = self.read(closure_path)
        artifact_value = self.read(self.release / name)
        digest, length = canonical_digest(artifact_value)
        artifact = next(
            item for item in closure["artifacts"] if item["path"] == name
        )
        artifact["sha256"] = digest
        artifact["canonicalBytes"] = length
        self.write(closure_path, closure)

    def test_valid_release_closure_includes_working_review_state(self) -> None:
        result = self.validate()
        self.assertEqual("syn-release-0002", result["release_id"])
        self.assertEqual(4, result["artifact_count"])
        self.assertEqual(2, result["record_count"])
        self.assertEqual(
            1,
            result["unreviewed_count"],
            "unreviewed metadata must remain visible without creating a release class",
        )
        closure = self.read(self.release / "release-closure.json")
        self.assertEqual("published", closure["states"]["publicRelease"])
        self.assertEqual("candidate", closure["states"]["canonicalPromotion"])

    def test_changed_artifact_hash_is_rejected(self) -> None:
        projection_path = self.release / "consumer-projection.json"
        projection = self.read(projection_path)
        projection["records"].reverse()
        self.write(projection_path, projection)
        with self.assertRaisesRegex(ContractError, "hash mismatch"):
            self.validate()

    def test_missing_artifact_is_rejected(self) -> None:
        (self.release / "source-provenance.json").unlink()
        with self.assertRaisesRegex(ContractError, "missing required public file"):
            self.validate()

    def test_missing_hash_is_rejected(self) -> None:
        closure_path = self.release / "release-closure.json"
        closure = self.read(closure_path)
        del closure["artifacts"][0]["sha256"]
        self.write(closure_path, closure)
        with self.assertRaisesRegex(ContractError, "missing required field.*sha256"):
            self.validate()

    def test_recursive_prohibited_keys_are_rejected(self) -> None:
        prohibited = [
            "body",
            "sourceText",
            "translationText",
            "ocr",
            "evidence",
            "modelTrace",
            "prompt",
            "credentials",
        ]
        original = self.read(
            ORIGINAL_SYNTHETIC / "public-release" / "consumer-projection.json"
        )
        for key in prohibited:
            with self.subTest(key=key):
                projection = json.loads(json.dumps(original))
                projection["records"][0]["nestedEnvelope"] = {
                    "deeper": {key: "synthetic-forbidden-value"}
                }
                self.write(self.release / "consumer-projection.json", projection)
                with self.assertRaisesRegex(ContractError, "prohibited public payload key"):
                    self.validate()

    def test_private_path_is_rejected_recursively(self) -> None:
        source_path = self.release / "source-provenance.json"
        source = self.read(source_path)
        source["entries"][0]["locator"]["value"] = r"C:\restricted\source.json"
        self.write(source_path, source)
        with self.assertRaisesRegex(ContractError, "windows-absolute-path"):
            self.validate()

    def test_unknown_major_schema_is_rejected(self) -> None:
        source_path = self.release / "source-provenance.json"
        source = self.read(source_path)
        source["schemaVersion"] = "2.0.0"
        self.write(source_path, source)
        with self.assertRaisesRegex(ContractError, "unsupported schema version"):
            self.validate()

    def test_unknown_projection_field_is_rejected(self) -> None:
        projection_path = self.release / "consumer-projection.json"
        projection = self.read(projection_path)
        projection["records"][0]["unexpectedMetadata"] = "synthetic"
        self.write(projection_path, projection)
        with self.assertRaisesRegex(ContractError, "unknown field"):
            self.validate()

    def test_non_public_classification_is_rejected(self) -> None:
        projection_path = self.release / "consumer-projection.json"
        projection = self.read(projection_path)
        projection["records"][0]["classification"] = "synthetic-private"
        self.write(projection_path, projection)
        with self.assertRaisesRegex(ContractError, "configured public classification"):
            self.validate()

    def test_release_authority_must_be_a_configured_producer(self) -> None:
        closure_path = self.release / "release-closure.json"
        closure = self.read(closure_path)
        closure["producerId"] = "unconfigured-producer"
        self.write(closure_path, closure)
        with self.assertRaisesRegex(ContractError, "not configured with the 'producer' role"):
            self.validate()

    def test_correction_must_match_replacement_and_superseded_revision(self) -> None:
        correction_path = self.release / "correction-supersession.json"
        correction = self.read(correction_path)
        correction["corrections"][0]["replacementRevision"] = 3
        self.write(correction_path, correction)
        self.refresh_artifact("correction-supersession.json")
        with self.assertRaisesRegex(ContractError, "replacementRevision"):
            self.validate()

    def test_recorded_rollback_pointer_to_declared_predecessor_is_valid(self) -> None:
        pointer_path = self.release / "release-pointer.json"
        pointer = self.read(pointer_path)
        pointer.update(
            {
                "activeReleaseId": "syn-release-0001",
                "latestReleaseId": "syn-release-0002",
                "reasonCode": "rollback",
                "rollbackFromReleaseId": "syn-release-0002",
            }
        )
        self.write(pointer_path, pointer)
        result = self.validate()
        self.assertEqual("syn-release-0002", result["release_id"])

    def test_rollback_pointer_to_undeclared_release_is_rejected(self) -> None:
        pointer_path = self.release / "release-pointer.json"
        pointer = self.read(pointer_path)
        pointer.update(
            {
                "activeReleaseId": "syn-release-0999",
                "latestReleaseId": "syn-release-0002",
                "reasonCode": "rollback",
                "rollbackFromReleaseId": "syn-release-0002",
            }
        )
        self.write(pointer_path, pointer)
        with self.assertRaisesRegex(ContractError, "rollback target"):
            self.validate()

    def test_consumer_projection_requires_release_identity(self) -> None:
        projection_path = self.release / "consumer-projection.json"
        projection = self.read(projection_path)
        del projection["releaseId"]
        self.write(projection_path, projection)
        with self.assertRaisesRegex(ContractError, "missing required field.*releaseId"):
            self.validate()

    def test_consumer_release_pin_must_match_closure(self) -> None:
        projection_path = self.release / "consumer-projection.json"
        projection = self.read(projection_path)
        projection["releaseId"] = "syn-release-0999"
        self.write(projection_path, projection)
        self.refresh_artifact("consumer-projection.json")
        with self.assertRaisesRegex(ContractError, "must match release-closure.releaseId"):
            self.validate()

    def test_schema_objects_are_closed_and_api_is_read_only(self) -> None:
        validate_contract_schemas(self.contracts)
        validate_openapi(self.contracts / "openapi.yaml")


if __name__ == "__main__":
    unittest.main()
