from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.services.certificate_service import (
    CertificateServiceError,
    generate_certificate,
)
from agent.services.certificate_verifier import (
    verify_certificate,
)


class CertificateTests(unittest.TestCase):
    def setUp(self) -> None:
        """Create isolated certificate and key folders for every test."""

        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )

        self.test_root = Path(
            self.temporary_directory.name
        )

        self.keys_directory = (
            self.test_root / "keys"
        )

        self.certificates_directory = (
            self.test_root / "certificates"
        )

        self.keys_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.certificates_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.private_key_path = (
            self.keys_directory
            / "private_key.pem"
        )

        self.public_key_path = (
            self.keys_directory
            / "public_key.pem"
        )

        self.path_patches = [
            patch(
                (
                    "agent.services.signature_service."
                    "PRIVATE_KEY_PATH"
                ),
                self.private_key_path,
            ),
            patch(
                (
                    "agent.services.signature_service."
                    "PUBLIC_KEY_PATH"
                ),
                self.public_key_path,
            ),
            patch(
                (
                    "agent.services.certificate_service."
                    "CERTIFICATES_DIR"
                ),
                self.certificates_directory,
            ),
        ]

        for path_patch in self.path_patches:
            path_patch.start()

    def tearDown(self) -> None:
        """Stop patches and remove temporary files."""

        for path_patch in reversed(
            self.path_patches
        ):
            path_patch.stop()

        self.temporary_directory.cleanup()

    def create_test_certificate(self) -> dict:
        """Generate one isolated signed certificate."""

        return generate_certificate(
            device_name="Automated Test Disk",
            serial_number="AUTO-TEST-0001",
            total_bytes=10 * 1024 * 1024,
            wipe_method=(
                "Single-pass zero overwrite"
            ),
            verification_status="PASSED",
        )

    def test_valid_certificate(self) -> None:
        """A newly signed certificate must be valid."""

        generated = self.create_test_certificate()

        json_path = Path(
            generated["json_path"]
        )

        pdf_path = Path(
            generated["pdf_path"]
        )

        qr_path = Path(
            generated["qr_path"]
        )

        self.assertTrue(
            json_path.exists()
        )

        self.assertTrue(
            pdf_path.exists()
        )

        self.assertTrue(
            qr_path.exists()
        )

        verification = verify_certificate(
            json_path
        )

        self.assertEqual(
            verification["status"],
            "VALID",
        )

        self.assertTrue(
            verification["hash_valid"]
        )

        self.assertTrue(
            verification["signature_valid"]
        )

        self.assertTrue(
            verification["algorithm_valid"]
        )

        self.assertTrue(
            verification["fingerprint_valid"]
        )

        self.assertEqual(
            verification["failed_checks"],
            [],
        )

    def test_modified_certificate_is_tampered(
        self,
    ) -> None:
        """Changing certificate data must break its hash and signature."""

        generated = self.create_test_certificate()

        json_path = Path(
            generated["json_path"]
        )

        certificate_document = json.loads(
            json_path.read_text(
                encoding="utf-8"
            )
        )

        certificate_document[
            "payload"
        ][
            "device_name"
        ] = "Modified Test Disk"

        tampered_path = (
            self.certificates_directory
            / "tampered_certificate.json"
        )

        tampered_path.write_text(
            json.dumps(
                certificate_document,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        verification = verify_certificate(
            tampered_path
        )

        self.assertEqual(
            verification["status"],
            "TAMPERED",
        )

        self.assertFalse(
            verification["hash_valid"]
        )

        self.assertFalse(
            verification["signature_valid"]
        )

        self.assertTrue(
            verification["fingerprint_valid"]
        )

        self.assertIn(
            "Certificate hash mismatch.",
            verification["failed_checks"],
        )

        self.assertIn(
            "Digital signature is invalid.",
            verification["failed_checks"],
        )

    def test_failed_verification_cannot_generate_certificate(
        self,
    ) -> None:
        """Certificate generation must reject failed wipe verification."""

        with self.assertRaises(
            CertificateServiceError
        ):
            generate_certificate(
                device_name="Automated Test Disk",
                serial_number="AUTO-TEST-0001",
                total_bytes=10 * 1024 * 1024,
                wipe_method=(
                    "Single-pass zero overwrite"
                ),
                verification_status="FAILED",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)