from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from agent.paths import (
    CERTIFICATES_DIR,
    ensure_runtime_directories,
)
from agent.services.signature_service import (
    SIGNATURE_ALGORITHM,
    canonical_json_bytes,
    sign_payload,
)


class CertificateServiceError(Exception):
    """Raised when certificate generation fails."""


def current_timestamp() -> str:
    """Return the current UTC timestamp."""

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def create_certificate_number() -> str:
    """Create a unique DataRakshak certificate number."""

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%d-%H%M%S")

    unique_part = uuid.uuid4().hex[:6].upper()

    return (
        f"DRK-{timestamp}-{unique_part}"
    )


def calculate_payload_hash(
    payload: dict[str, Any],
) -> str:
    """Calculate the SHA-256 hash of the certificate payload."""

    return hashlib.sha256(
        canonical_json_bytes(payload)
    ).hexdigest()


def validate_certificate_inputs(
    device_name: str,
    serial_number: str,
    total_bytes: int,
    wipe_method: str,
    verification_status: str,
) -> None:
    """Validate certificate-generation inputs."""

    if not device_name.strip():
        raise CertificateServiceError(
            "Device name cannot be empty."
        )

    if not serial_number.strip():
        raise CertificateServiceError(
            "Serial number cannot be empty."
        )

    if total_bytes <= 0:
        raise CertificateServiceError(
            "Total bytes must be greater than zero."
        )

    if not wipe_method.strip():
        raise CertificateServiceError(
            "Wipe method cannot be empty."
        )

    if verification_status.strip().upper() != "PASSED":
        raise CertificateServiceError(
            "A certificate can be generated only "
            "after successful wipe verification."
        )


def format_bytes(
    size_bytes: int,
) -> str:
    """Convert bytes into a readable value."""

    units = [
        "bytes",
        "KB",
        "MB",
        "GB",
        "TB",
    ]

    size = float(size_bytes)
    unit_index = 0

    while (
        size >= 1024
        and unit_index < len(units) - 1
    ):
        size /= 1024
        unit_index += 1

    return (
        f"{size:.2f} {units[unit_index]} "
        f"({size_bytes} bytes)"
    )


def split_long_value(
    value: str,
    group_size: int = 32,
) -> str:
    """Insert spaces into long cryptographic values for PDF display."""

    return " ".join(
        value[index:index + group_size]
        for index in range(
            0,
            len(value),
            group_size,
        )
    )


def create_qr_code(
    certificate_number: str,
    certificate_hash: str,
    public_key_fingerprint: str,
    qr_path: Path,
) -> None:
    """Create a QR image containing certificate verification data."""

    qr_data = {
        "certificate_number": certificate_number,
        "certificate_hash": certificate_hash,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "public_key_fingerprint": (
            public_key_fingerprint
        ),
    }

    try:
        qr_image = qrcode.make(
            json.dumps(
                qr_data,
                sort_keys=True,
                separators=(",", ":"),
            )
        )

        qr_image.save(qr_path)

    except Exception as error:
        raise CertificateServiceError(
            f"Could not create the QR code: {error}"
        ) from error


def create_pdf_certificate(
    payload: dict[str, Any],
    certificate_hash: str,
    signature_information: dict[str, str],
    pdf_path: Path,
    qr_path: Path,
) -> None:
    """Create the printable DataRakshak PDF certificate."""

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name="DataRakshakTitle",
        parent=styles["Title"],
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0F766E"),
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        name="DataRakshakSubtitle",
        parent=styles["Normal"],
        fontSize=12,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#334155"),
        spaceAfter=18,
    )

    section_style = ParagraphStyle(
        name="DataRakshakSection",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=10,
        spaceAfter=8,
    )

    normal_style = ParagraphStyle(
        name="DataRakshakNormal",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#111827"),
    )

    small_style = ParagraphStyle(
        name="DataRakshakSmall",
        parent=styles["Normal"],
        fontSize=7,
        leading=10,
        textColor=colors.HexColor("#334155"),
    )

    document = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=(
            "DataRakshak Secure Wipe Certificate"
        ),
        author="DataRakshak",
    )

    story: list[Any] = []

    story.append(
        Paragraph(
            "DataRakshak",
            title_style,
        )
    )

    story.append(
        Paragraph(
            "Secure Data Wiping and Verification Certificate",
            subtitle_style,
        )
    )

    story.append(
        Paragraph(
            "Certificate Details",
            section_style,
        )
    )

    details = [
        [
            "Certificate Number",
            payload["certificate_number"],
        ],
        [
            "Issued At",
            payload["issued_at"],
        ],
        [
            "Device Name",
            payload["device_name"],
        ],
        [
            "Serial Number",
            payload["serial_number"],
        ],
        [
            "Storage Size",
            format_bytes(
                int(payload["total_bytes"])
            ),
        ],
        [
            "Wipe Method",
            payload["wipe_method"],
        ],
        [
            "Verification Status",
            payload["verification_status"],
        ],
    ]

    formatted_details = [
        [
            Paragraph(
                f"<b>{label}</b>",
                normal_style,
            ),
            Paragraph(
                str(value),
                normal_style,
            ),
        ]
        for label, value in details
    ]

    details_table = Table(
        formatted_details,
        colWidths=[
            52 * mm,
            118 * mm,
        ],
        repeatRows=0,
    )

    details_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#E2E8F0"),
                ),
                (
                    "BACKGROUND",
                    (1, 0),
                    (1, -1),
                    colors.HexColor("#F8FAFC"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#94A3B8"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    story.append(details_table)
    story.append(Spacer(1, 10 * mm))

    story.append(
        Paragraph(
            "Cryptographic Verification",
            section_style,
        )
    )

    certificate_hash_display = split_long_value(
        certificate_hash
    )

    fingerprint_display = split_long_value(
        signature_information[
            "public_key_fingerprint"
        ]
    )

    crypto_details = [
        [
            "Hash Algorithm",
            "SHA-256",
        ],
        [
            "Certificate Hash",
            certificate_hash_display,
        ],
        [
            "Signature Algorithm",
            signature_information[
                "algorithm"
            ],
        ],
        [
            "Public-Key Fingerprint",
            fingerprint_display,
        ],
    ]

    formatted_crypto_details = [
        [
            Paragraph(
                f"<b>{label}</b>",
                small_style,
            ),
            Paragraph(
                str(value),
                small_style,
            ),
        ]
        for label, value in crypto_details
    ]

    crypto_table = Table(
        formatted_crypto_details,
        colWidths=[
            52 * mm,
            118 * mm,
        ],
    )

    crypto_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#CCFBF1"),
                ),
                (
                    "BACKGROUND",
                    (1, 0),
                    (1, -1),
                    colors.white,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#5EEAD4"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    story.append(crypto_table)
    story.append(Spacer(1, 8 * mm))

    qr_image = Image(
        str(qr_path),
        width=38 * mm,
        height=38 * mm,
    )

    qr_table = Table(
        [
            [
                qr_image,
                Paragraph(
                    (
                        "<b>Verification QR Code</b><br/><br/>"
                        "The QR code contains the certificate "
                        "number, SHA-256 hash, signature algorithm "
                        "and public-key fingerprint."
                    ),
                    normal_style,
                ),
            ]
        ],
        colWidths=[
            48 * mm,
            122 * mm,
        ],
    )

    qr_table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    colors.HexColor("#CBD5E1"),
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )

    story.append(qr_table)
    story.append(Spacer(1, 8 * mm))

    story.append(
        Paragraph(
            (
                "<b>Declaration:</b> The specified test storage "
                "target was overwritten using the recorded wipe "
                "method and the resulting content passed software "
                "verification. This document belongs to the "
                "DataRakshak prototype and is digitally signed "
                "using the local Ed25519 key."
            ),
            small_style,
        )
    )

    try:
        document.build(story)

    except Exception as error:
        raise CertificateServiceError(
            f"Could not create the PDF certificate: {error}"
        ) from error


def generate_certificate(
    device_name: str,
    serial_number: str,
    total_bytes: int,
    wipe_method: str,
    verification_status: str,
) -> dict[str, Any]:
    """Generate signed JSON, PDF and QR certificate files."""

    ensure_runtime_directories()

    validate_certificate_inputs(
        device_name=device_name,
        serial_number=serial_number,
        total_bytes=total_bytes,
        wipe_method=wipe_method,
        verification_status=verification_status,
    )

    certificate_number = (
        create_certificate_number()
    )

    payload: dict[str, Any] = {
        "certificate_number": certificate_number,
        "issued_at": current_timestamp(),
        "issuer": "DataRakshak",
        "device_name": device_name.strip(),
        "serial_number": serial_number.strip(),
        "total_bytes": total_bytes,
        "wipe_method": wipe_method.strip(),
        "verification_status": (
            verification_status.strip().upper()
        ),
    }

    certificate_hash = calculate_payload_hash(
        payload
    )

    signature_information = sign_payload(
        payload
    )

    certificate_document = {
        "schema_version": "1.0",
        "payload": payload,
        "certificate_hash": certificate_hash,
        "digital_signature": {
            "algorithm": signature_information[
                "algorithm"
            ],
            "signature": signature_information[
                "signature"
            ],
            "public_key_fingerprint": (
                signature_information[
                    "public_key_fingerprint"
                ]
            ),
        },
    }

    pdf_path = (
        CERTIFICATES_DIR
        / f"{certificate_number}.pdf"
    )

    json_path = (
        CERTIFICATES_DIR
        / f"{certificate_number}.json"
    )

    qr_path = (
        CERTIFICATES_DIR
        / f"{certificate_number}_qr.png"
    )

    try:
        json_path.write_text(
            json.dumps(
                certificate_document,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        create_qr_code(
            certificate_number=certificate_number,
            certificate_hash=certificate_hash,
            public_key_fingerprint=(
                signature_information[
                    "public_key_fingerprint"
                ]
            ),
            qr_path=qr_path,
        )

        create_pdf_certificate(
            payload=payload,
            certificate_hash=certificate_hash,
            signature_information=(
                signature_information
            ),
            pdf_path=pdf_path,
            qr_path=qr_path,
        )

    except CertificateServiceError:
        raise

    except OSError as error:
        raise CertificateServiceError(
            f"Could not save certificate files: {error}"
        ) from error

    return {
        "status": "created",
        "certificate_number": certificate_number,
        "certificate_hash": certificate_hash,
        "signature_algorithm": (
            signature_information["algorithm"]
        ),
        "public_key_fingerprint": (
            signature_information[
                "public_key_fingerprint"
            ]
        ),
        "pdf_path": str(pdf_path),
        "json_path": str(json_path),
        "qr_path": str(qr_path),
    }