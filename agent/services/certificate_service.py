from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from agent.services.signature_service import (
    PUBLIC_KEY_PATH,
    generate_key_pair,
    sign_data,
)


CERTIFICATES_FOLDER = Path("certificates")


def convert_to_canonical_bytes(
    data: dict,
) -> bytes:
    """Convert certificate data into stable JSON bytes."""

    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def split_text(
    text: str,
    length: int = 48,
) -> list[str]:
    """Split long hash or signature text into smaller lines."""

    return [
        text[index : index + length]
        for index in range(0, len(text), length)
    ]


def generate_certificate(
    device_name: str = "Fake Test Disk",
    serial_number: str = "TEST-DISK-0001",
    total_bytes: int = 10 * 1024 * 1024,
    wipe_method: str = "Single-pass zero overwrite",
    verification_status: str = "PASSED",
) -> dict:
    """Generate a digitally signed PDF wipe certificate."""

    CERTIFICATES_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

    generate_key_pair()

    created_at = datetime.now(timezone.utc)

    unique_part = uuid.uuid4().hex[:6].upper()

    certificate_number = (
        f"DRK-"
        f"{created_at.strftime('%Y%m%d-%H%M%S')}-"
        f"{unique_part}"
    )

    signed_payload = {
        "certificate_number": certificate_number,
        "device_name": device_name,
        "serial_number": serial_number,
        "total_bytes": total_bytes,
        "wipe_method": wipe_method,
        "verification_status": verification_status,
        "created_at_utc": created_at.isoformat(),
    }

    payload_bytes = convert_to_canonical_bytes(
        signed_payload
    )

    certificate_hash = hashlib.sha256(
        payload_bytes
    ).hexdigest()

    digital_signature = sign_data(
        payload_bytes
    )

    certificate_record = {
        "payload": signed_payload,
        "security": {
            "hash_algorithm": "SHA-256",
            "certificate_hash": certificate_hash,
            "signature_algorithm": "Ed25519",
            "digital_signature": digital_signature,
            "public_key_path": str(PUBLIC_KEY_PATH),
        },
    }

    json_path = CERTIFICATES_FOLDER / (
        f"{certificate_number}.json"
    )

    json_path.write_text(
        json.dumps(
            certificate_record,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    qr_data = {
        "certificate_number": certificate_number,
        "verification_status": verification_status,
        "certificate_hash": certificate_hash,
        "signature_algorithm": "Ed25519",
        "digital_signature": digital_signature,
    }

    qr_content = json.dumps(
        qr_data,
        sort_keys=True,
        separators=(",", ":"),
    )

    qr_image = qrcode.make(qr_content)

    qr_path = CERTIFICATES_FOLDER / (
        f"{certificate_number}_qr.png"
    )

    qr_image.save(qr_path)

    pdf_path = CERTIFICATES_FOLDER / (
        f"{certificate_number}.pdf"
    )

    pdf = canvas.Canvas(
        str(pdf_path),
        pagesize=A4,
    )

    page_width, page_height = A4

    pdf.setTitle(
        f"DataRakshak Certificate {certificate_number}"
    )

    pdf.setAuthor("DataRakshak")
    pdf.setSubject(
        "Digitally Signed Secure Data Wipe Certificate"
    )

    pdf.setFont("Helvetica-Bold", 25)

    pdf.drawCentredString(
        page_width / 2,
        page_height - 28 * mm,
        "DataRakshak",
    )

    pdf.setFont("Helvetica-Bold", 16)

    pdf.drawCentredString(
        page_width / 2,
        page_height - 40 * mm,
        "Secure Data Wipe Certificate",
    )

    pdf.setFont("Helvetica", 10)

    pdf.drawCentredString(
        page_width / 2,
        page_height - 47 * mm,
        "Digitally signed using Ed25519",
    )

    pdf.line(
        25 * mm,
        page_height - 54 * mm,
        page_width - 25 * mm,
        page_height - 54 * mm,
    )

    details = [
        (
            "Certificate Number",
            certificate_number,
        ),
        (
            "Device Name",
            device_name,
        ),
        (
            "Serial Number",
            serial_number,
        ),
        (
            "Storage Size",
            f"{total_bytes} bytes",
        ),
        (
            "Wipe Method",
            wipe_method,
        ),
        (
            "Verification Status",
            verification_status,
        ),
        (
            "Created At",
            created_at.strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
        ),
        (
            "Signature Algorithm",
            "Ed25519",
        ),
        (
            "Hash Algorithm",
            "SHA-256",
        ),
    ]

    current_y = page_height - 68 * mm

    for label, value in details:
        pdf.setFont(
            "Helvetica-Bold",
            10,
        )

        pdf.drawString(
            27 * mm,
            current_y,
            f"{label}:",
        )

        pdf.setFont(
            "Helvetica",
            10,
        )

        pdf.drawString(
            72 * mm,
            current_y,
            str(value),
        )

        current_y -= 9 * mm

    current_y -= 2 * mm

    pdf.setFont(
        "Helvetica-Bold",
        10,
    )

    pdf.drawString(
        27 * mm,
        current_y,
        "Certificate SHA-256 Hash:",
    )

    current_y -= 7 * mm

    pdf.setFont(
        "Courier",
        8,
    )

    for hash_line in split_text(
        certificate_hash,
        length=40,
    ):
        pdf.drawString(
            27 * mm,
            current_y,
            hash_line,
        )

        current_y -= 5 * mm

    current_y -= 4 * mm

    pdf.setFont(
        "Helvetica-Bold",
        10,
    )

    pdf.drawString(
        27 * mm,
        current_y,
        "Ed25519 Digital Signature:",
    )

    current_y -= 7 * mm

    pdf.setFont(
        "Courier",
        7,
    )

    for signature_line in split_text(
        digital_signature,
        length=52,
    ):
        pdf.drawString(
            27 * mm,
            current_y,
            signature_line,
        )

        current_y -= 5 * mm

    pdf.drawImage(
        str(qr_path),
        page_width - 63 * mm,
        24 * mm,
        width=38 * mm,
        height=38 * mm,
        preserveAspectRatio=True,
        mask="auto",
    )

    pdf.setFont(
        "Helvetica-Bold",
        9,
    )

    pdf.drawString(
        27 * mm,
        35 * mm,
        "Digital Signature Status: SIGNED",
    )

    pdf.setFont(
        "Helvetica",
        8,
    )

    pdf.drawString(
        27 * mm,
        28 * mm,
        "Prototype certificate generated by DataRakshak.",
    )

    pdf.drawString(
        27 * mm,
        23 * mm,
        "Current version operates only on the fake test disk.",
    )

    pdf.save()

    return {
        "status": "created",
        "certificate_number": certificate_number,
        "certificate_hash": certificate_hash,
        "digital_signature": digital_signature,
        "signature_algorithm": "Ed25519",
        "pdf_path": str(pdf_path),
        "qr_path": str(qr_path),
        "json_path": str(json_path),
        "public_key_path": str(PUBLIC_KEY_PATH),
    }


if __name__ == "__main__":
    result = generate_certificate()

    print("Digitally signed certificate created successfully")
    print(
        "Certificate number:",
        result["certificate_number"],
    )
    print(
        "PDF path:",
        result["pdf_path"],
    )
    print(
        "JSON path:",
        result["json_path"],
    )
    print(
        "QR path:",
        result["qr_path"],
    )
    print(
        "SHA-256:",
        result["certificate_hash"],
    )
    print(
        "Signature algorithm:",
        result["signature_algorithm"],
    )
    print(
        "Digital signature:",
        result["digital_signature"],
    )