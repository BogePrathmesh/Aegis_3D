import os
import io
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.email_service import (
    get_email_config,
    format_gps_info,
    build_email_body,
    send_inspection_report_email,
    EmailConfigError,
    EmailSendError,
    CONFIGURED_RECIPIENT,
    STANDARD_DISCLAIMER,
)

client = TestClient(app)


# ─── 1. Configuration & Credential Security ──────────────────────────────────

def test_config_raises_when_unconfigured(monkeypatch):
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    with pytest.raises(EmailConfigError) as exc_info:
        get_email_config()
    assert "Gmail SMTP is not configured" in str(exc_info.value)


def test_config_cleans_password_and_locks_recipient(monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "  testsender@gmail.com  ")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "abcd efgh ijkl mnop")
    monkeypatch.delenv("REPORT_RECIPIENT", raising=False)

    cfg = get_email_config()
    assert cfg["address"] == "testsender@gmail.com"
    assert cfg["password"] == "abcdefghijklmnop"  # stripped spaces
    assert cfg["recipient"] == "aimhighpa@gmail.com"


# ─── 2. GPS Geolocation Source Formatting ────────────────────────────────────

def test_gps_formatting_real_exif():
    info = format_gps_info(18.52043, 73.85674, "real")
    assert info["has_gps"] is True
    assert "18.520430°, 73.856740°" in info["coordinates"]
    assert "EXIF Metadata" in info["source"]


def test_gps_formatting_fallback():
    info = format_gps_info(19.0760, 72.8777, "fallback")
    assert info["has_gps"] is True
    assert "Fallback Reference Coordinates" in info["source"]


def test_gps_formatting_missing():
    info = format_gps_info(None, None, None)
    assert info["has_gps"] is False
    assert "Not Available" in info["coordinates"]


# ─── 3. Email Body Generation & Disclaimer ───────────────────────────────────

def test_email_body_includes_required_fields_and_disclaimer():
    report_data = {
        "filename": "bridge_pier_04.jpg",
        "structure_type": "bridge",
        "material_type": "concrete",
        "material_source": "AI prediction",
        "health_score": 78.5,
        "severity_index": 21.5,
        "risk_level": "Low",
        "crack_count": 2,
        "total_crack_area_pct": 0.182,
        "max_crack_width": 12.4,
        "calibration_status": "Uncalibrated — pixels only",
        "cracks": [
            {"id": 1, "type": "hairline", "confidence": 0.89, "width_px": 6.2, "area_pct": 0.05},
            {"id": 2, "type": "longitudinal", "confidence": 0.94, "width_px": 12.4, "area_pct": 0.132},
        ],
        "recommendations": ["DECISION-SUPPORT EVALUATION", "Routine visual monitoring advised."],
    }
    gps_info = format_gps_info(18.5204, 73.8567, "real")
    plain, html = build_email_body(report_data, "2026-10-21 14:00:00 UTC", gps_info)

    # Subject & Filename
    assert "bridge_pier_04.jpg" in plain
    assert "bridge_pier_04.jpg" in html

    # Model outputs
    assert "78.5" in plain
    assert "21.5" in plain
    assert "Low" in plain
    assert "12.4 px" in plain
    assert "0.182%" in plain
    assert "hairline" in plain
    assert "longitudinal" in plain

    # Geolocation
    assert "18.520400°, 73.856700°" in plain
    assert "EXIF Metadata" in plain

    # Regulatory disclaimer
    assert STANDARD_DISCLAIMER in plain
    assert "DISCLAIMER" in html
    assert "NOT constitute an official structural safety certification" in html


def test_email_body_graceful_with_sparse_data():
    sparse_data = {"filename": "unknown.jpg"}
    gps_info = format_gps_info(None, None, None)
    plain, html = build_email_body(sparse_data, "2026-10-21 14:00:00 UTC", gps_info)

    assert "unknown.jpg" in plain
    assert "Not Available" in plain
    assert STANDARD_DISCLAIMER in plain


# ─── 4. Attachment Restrictions & Validations ────────────────────────────────

def test_attachment_size_limit_rejection(monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "abcdefghijklmnop")

    oversized_bytes = b"0" * (16 * 1024 * 1024)  # 16 MB > 15 MB limit
    with pytest.raises(EmailSendError) as exc_info:
        send_inspection_report_email(
            report_data={"filename": "large.jpg"},
            image_bytes=oversized_bytes,
            attach_pdf=False
        )
    assert "exceeds allowable limit" in str(exc_info.value)


# ─── 5. Mock SMTP Transmission ──────────────────────────────────────────────

@patch("smtplib.SMTP")
def test_send_inspection_report_email_success(mock_smtp, monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "sender@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "1234567890abcdef")
    monkeypatch.setenv("REPORT_RECIPIENT", "aimhighpa@gmail.com")

    # Mock server instance
    instance = MagicMock()
    mock_smtp.return_value.__enter__.return_value = instance

    sample_img = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb"
    res = send_inspection_report_email(
        report_data={
            "filename": "pier_test.jpg",
            "health_score": 85.0,
            "severity_index": 15.0,
            "risk_level": "Low",
        },
        image_bytes=sample_img,
        image_filename="pier_test.jpg",
        attach_pdf=False,
    )

    assert res["status"] == "success"
    assert res["recipient"] == "aimhighpa@gmail.com"
    assert "pier_test.jpg" in res["attachments"]

    # Verify SMTP calls
    instance.starttls.assert_called_once()
    instance.login.assert_called_once_with("sender@gmail.com", "1234567890abcdef")
    instance.send_message.assert_called_once()
    sent_msg = instance.send_message.call_args[0][0]
    assert sent_msg["Subject"] == "AEGIS-3D | New Infrastructure Inspection Report"
    assert sent_msg["To"] == "aimhighpa@gmail.com"


# ─── 6. API Route Integration Tests ──────────────────────────────────────────

def test_api_email_config_unconfigured(monkeypatch):
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)

    resp = client.get("/api/analysis/email-config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is False
    assert data["recipient"] == "aimhighpa@gmail.com"


def test_api_email_report_unconfigured_error(monkeypatch):
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)

    resp = client.post(
        "/api/analysis/email-report/json",
        json={"report_data": {"filename": "test.jpg"}}
    )
    assert resp.status_code == 500
    assert "Gmail SMTP is not configured" in resp.json()["detail"]


@patch("smtplib.SMTP")
def test_api_email_report_multipart_success(mock_smtp, monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "sender@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "1234567890abcdef")

    instance = MagicMock()
    mock_smtp.return_value.__enter__.return_value = instance

    payload_json = '{"filename": "test_drone.jpg", "health_score": 90, "severity_index": 10, "risk_level": "Safe"}'
    fake_img = io.BytesIO(b"fake-image-bytes")

    resp = client.post(
        "/api/analysis/email-report",
        data={"report_data": payload_json, "attach_pdf": "false"},
        files={"file": ("test_drone.jpg", fake_img, "image/jpeg")}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["recipient"] == "aimhighpa@gmail.com"
