import os
import ssl
import smtplib
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage

# Attempt to load .env from backend/.env or workspace root
try:
    from dotenv import load_dotenv
    _backend_dir = Path(__file__).resolve().parent.parent.parent
    for _candidate in [_backend_dir / ".env", _backend_dir.parent / ".env", Path.cwd() / ".env"]:
        if _candidate.exists():
            load_dotenv(dotenv_path=_candidate, override=False)
except ImportError:
    pass

MAX_ATTACHMENT_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB limit per attachment
CONFIGURED_RECIPIENT = os.getenv("REPORT_RECIPIENT", "aimhighpa@gmail.com").strip() or "aimhighpa@gmail.com"
STANDARD_DISCLAIMER = (
    "DISCLAIMER: This inspection report contains AI-generated preliminary screening findings and damage "
    "heuristic evaluations. These findings do NOT constitute an official structural safety certification, "
    "certified non-destructive test (NDT) validation, or professional engineering sign-off. Comprehensive on-site "
    "engineering validation by a licensed civil or structural engineer is required before undertaking load modifications, "
    "traffic closures, or repair contracts."
)


class EmailConfigError(Exception):
    """Raised when Gmail SMTP environment variables are missing or invalid."""
    pass


class EmailSendError(Exception):
    """Raised when email transmission fails."""
    pass


def get_email_config() -> Dict[str, str]:
    """
    Retrieve and validate Gmail SMTP credentials from environment variables.
    Strictly forbids exposing credentials to frontend or logs.
    """
    gmail_address = os.getenv("GMAIL_ADDRESS", "").strip()
    gmail_password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    recipient = os.getenv("REPORT_RECIPIENT", "aimhighpa@gmail.com").strip() or "aimhighpa@gmail.com"

    # Automatically clean spaces if user copied 4-group app password 'abcd efgh ijkl mnop'
    cleaned_password = re.sub(r"\s+", "", gmail_password)

    if not gmail_address or not cleaned_password:
        raise EmailConfigError(
            "Gmail SMTP is not configured on the server. Please set GMAIL_ADDRESS and "
            "GMAIL_APP_PASSWORD in backend/.env with a valid Google App Password."
        )

    return {
        "address": gmail_address,
        "password": cleaned_password,
        "recipient": recipient,
    }


def format_gps_info(latitude: Optional[float], longitude: Optional[float], gps_status: Optional[str]) -> Dict[str, str]:
    """
    Format GPS coordinates and clearly identify the data source.
    """
    if latitude is None or longitude is None:
        return {
            "coordinates": "Not Available (No GPS metadata detected)",
            "source": "None / Geotag Missing",
            "has_gps": False
        }

    status_str = (gps_status or "").lower()
    if status_str == "real":
        source_label = "Image EXIF Metadata (Embedded by Camera / Drone GPS)"
    elif status_str == "device":
        source_label = "Device GPS Sensor"
    elif status_str == "manual":
        source_label = "Manual Field Input"
    elif status_str == "fallback":
        source_label = "Fallback Reference Coordinates (EXIF GPS unavailable in source image)"
    else:
        source_label = f"Reported ({gps_status})" if gps_status else "Unspecified"

    return {
        "coordinates": f"{latitude:.6f}°, {longitude:.6f}°",
        "source": source_label,
        "has_gps": True
    }


def generate_inspection_pdf(data: Dict[str, Any]) -> Optional[str]:
    """
    Attempt to build an inspection PDF using the existing ReportGenerator service.
    Returns path to generated PDF or None if unavailable.
    """
    try:
        from app.services.report_generator import ReportGenerator

        report_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "reports"))
        os.makedirs(report_dir, exist_ok=True)
        gen = ReportGenerator(output_dir=report_dir)

        # Prepare payload matching StructureData schema expected by ReportGenerator
        structure_name = data.get("structure_name") or data.get("filename") or "Infrastructure Asset"
        lat = data.get("latitude")
        lng = data.get("longitude")
        loc = f"GPS: {lat:.4f}, {lng:.4f}" if lat is not None and lng is not None else "Site scan"

        severity = float(data.get("severity_index") or 0.0)
        risk_level = str(data.get("risk_level") or "Safe").upper()

        cracks = data.get("cracks") or []
        defects = []
        for i, c in enumerate(cracks):
            c_type = c.get("type", "Crack") if isinstance(c, dict) else getattr(c, "type", "Crack")
            c_area = float(c.get("area_pct", 0) if isinstance(c, dict) else getattr(c, "area_pct", 0))
            c_width = float(c.get("width_px", 0) if isinstance(c, dict) else getattr(c, "width_px", 0))
            defects.append({
                "id": f"D{i+1}",
                "type": c_type.capitalize(),
                "severity": min(5, max(1, int(severity / 20) or 1)),
                "depth": round(c_width * 0.1, 1),
                "length": round(c_area * 50, 1),
                "growth": 15,
            })

        pdf_payload = {
            "structure_name": structure_name[:32],
            "location": loc,
            "risk_score": int(severity),
            "risk_level": risk_level,
            "failure_probability": round(min(1.0, severity / 100.0), 2),
            "insurance_score": int(severity * 1.15),
            "defects": defects,
        }

        pdf_path = gen.generate_report(pdf_payload)
        if pdf_path and os.path.exists(pdf_path):
            return pdf_path
    except Exception as e:
        # Graceful fallback: report generation is non-blocking
        print(f"[email_service] Note: PDF generation skipped ({e})")
    return None


def build_email_body(data: Dict[str, Any], timestamp_str: str, gps_info: Dict[str, str]) -> tuple[str, str]:
    """
    Build both plain-text and responsive HTML email bodies containing all required metrics.
    Only includes fields when they are actually available.
    """
    filename = data.get("filename") or "inspection_scan.jpg"
    structure_type = str(data.get("structure_type") or "Infrastructure").capitalize()
    material_type = str(data.get("material_type") or "Unspecified").capitalize()
    material_source = data.get("material_source") or "Inspection system"

    health_score = data.get("health_score")
    severity_index = data.get("severity_index")
    risk_level = data.get("risk_level") or "Unspecified"
    crack_count = data.get("crack_count")
    total_area_pct = data.get("total_crack_area_pct")
    max_crack_width = data.get("max_crack_width")
    calibration_status = data.get("calibration_status") or "Uncalibrated — pixels only"
    cracks = data.get("cracks") or []
    recommendations = data.get("recommendations") or []

    # Risk badge color
    risk_upper = str(risk_level).upper()
    if risk_upper in ("CRITICAL", "EMERGENCY"):
        badge_bg, badge_fg = "#fee2e2", "#991b1b"
    elif risk_upper in ("HIGH", "REPAIR REQUIRED"):
        badge_bg, badge_fg = "#ffedd5", "#9a3412"
    elif risk_upper in ("MEDIUM", "MODERATE"):
        badge_bg, badge_fg = "#fef3c7", "#92400e"
    elif risk_upper in ("LOW", "ROUTINE"):
        badge_bg, badge_fg = "#e0f2fe", "#075985"
    else:
        badge_bg, badge_fg = "#dcfce7", "#166534"

    # --- Plain Text Version ---
    text_lines = [
        "=" * 60,
        "AEGIS-3D INFRASTRUCTURE INTELLIGENCE REPORT",
        "=" * 60,
        f"Analysis Timestamp: {timestamp_str}",
        f"Original Filename:  {filename}",
        f"Structure Type:     {structure_type}",
        f"Surface Material:   {material_type} ({material_source})",
        "",
        "GEOLOCATION:",
        f"  Coordinates:      {gps_info['coordinates']}",
        f"  Source:           {gps_info['source']}",
        "",
        "PRIMARY INTEGRITY & RISK METRICS:",
    ]

    if health_score is not None:
        text_lines.append(f"  Structural Integrity (SI):     {health_score} / 100")
    if severity_index is not None:
        text_lines.append(f"  Structural Severity Index (SSI): {severity_index} / 100")
    text_lines.append(f"  Inspection Risk Level:         {risk_level}")

    if crack_count is not None:
        text_lines.append(f"  Detected Crack Anomalies:      {crack_count}")
    if total_area_pct is not None:
        text_lines.append(f"  Total Crack Coverage:          {total_area_pct}%")
    if max_crack_width is not None:
        text_lines.append(f"  Max Fracture Caliper:          {max_crack_width} px ({calibration_status})")

    if cracks:
        text_lines.extend(["", "DETECTED FRACTURE DETAILS:"])
        for i, c in enumerate(cracks):
            c_type = c.get("type", "Crack") if isinstance(c, dict) else getattr(c, "type", "Crack")
            c_conf = c.get("confidence") if isinstance(c, dict) else getattr(c, "confidence", None)
            c_area = c.get("area_pct") if isinstance(c, dict) else getattr(c, "area_pct", None)
            c_width = c.get("width_px") if isinstance(c, dict) else getattr(c, "width_px", None)

            detail_parts = [f"#{i+1}: {c_type}"]
            if c_conf is not None:
                detail_parts.append(f"Confidence: {c_conf * 100:.1f}%" if c_conf <= 1.0 else f"Confidence: {c_conf:.1f}%")
            if c_width is not None:
                detail_parts.append(f"Width: {c_width} px")
            if c_area is not None:
                detail_parts.append(f"Area: {c_area}%")
            text_lines.append("  - " + " | ".join(detail_parts))

    if recommendations:
        text_lines.extend(["", "ENGINEERING DECISION-SUPPORT NOTES:"])
        for rec in recommendations:
            text_lines.append(f"  * {rec}")

    text_lines.extend([
        "",
        "-" * 60,
        STANDARD_DISCLAIMER,
        "-" * 60,
    ])
    plain_text = "\n".join(text_lines)

    # --- HTML Version ---
    cracks_html_rows = ""
    for i, c in enumerate(cracks):
        c_type = c.get("type", "Crack") if isinstance(c, dict) else getattr(c, "type", "Crack")
        c_conf = c.get("confidence") if isinstance(c, dict) else getattr(c, "confidence", None)
        c_area = c.get("area_pct") if isinstance(c, dict) else getattr(c, "area_pct", None)
        c_width = c.get("width_px") if isinstance(c, dict) else getattr(c, "width_px", None)
        conf_str = f"{c_conf * 100:.1f}%" if c_conf is not None and c_conf <= 1.0 else (f"{c_conf:.1f}%" if c_conf else "—")
        width_str = f"{c_width} px" if c_width is not None else "—"
        area_str = f"{c_area}%" if c_area is not None else "—"
        cracks_html_rows += f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 8px 12px; font-weight: 600; color: #1e293b;">#{i+1}</td>
            <td style="padding: 8px 12px; text-transform: capitalize; color: #334155;">{c_type}</td>
            <td style="padding: 8px 12px; font-family: monospace; color: #0284c7;">{conf_str}</td>
            <td style="padding: 8px 12px; font-family: monospace; color: #334155;">{width_str}</td>
            <td style="padding: 8px 12px; font-family: monospace; color: #334155;">{area_str}</td>
        </tr>
        """

    recs_html_items = ""
    for rec in recommendations:
        recs_html_items += f"<li style='margin-bottom: 6px; color: #334155; line-height: 1.45;'>{rec}</li>"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>AEGIS-3D Inspection Report</title>
</head>
<body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #0f172a;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
        <!-- Header Banner -->
        <tr>
            <td style="background: linear-gradient(135deg, #1e3a8a 0%, #0284c7 100%); padding: 28px 32px; color: #ffffff;">
                <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 2px; font-weight: 700; color: #bae6fd; margin-bottom: 6px;">AEGIS-3D Infrastructure Intelligence</div>
                <h1 style="margin: 0; font-size: 22px; font-weight: 800; color: #ffffff;">Infrastructure Inspection Report</h1>
                <div style="font-size: 13px; color: #e0f2fe; margin-top: 6px;">Automated preliminary engineering screening</div>
            </td>
        </tr>

        <!-- Overview Cards -->
        <tr>
            <td style="padding: 24px 32px 16px 32px;">
                <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px;">
                    <tr>
                        <td width="50%" style="vertical-align: top; padding-right: 12px;">
                            <div style="background: #f1f5f9; padding: 14px 16px; border-radius: 10px;">
                                <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #64748b; margin-bottom: 4px;">Asset & File</div>
                                <div style="font-size: 14px; font-weight: 700; color: #0f172a; word-break: break-all;">{filename}</div>
                                <div style="font-size: 12px; color: #475569; margin-top: 2px;">Type: <strong>{structure_type}</strong> | Mat: <strong>{material_type}</strong></div>
                            </div>
                        </td>
                        <td width="50%" style="vertical-align: top; padding-left: 12px;">
                            <div style="background: #f1f5f9; padding: 14px 16px; border-radius: 10px;">
                                <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #64748b; margin-bottom: 4px;">Analysis Timestamp</div>
                                <div style="font-size: 13px; font-family: monospace; font-weight: 600; color: #0f172a;">{timestamp_str}</div>
                                <div style="margin-top: 6px;">
                                    <span style="display: inline-block; padding: 3px 10px; border-radius: 9999px; font-size: 11px; font-weight: 800; text-transform: uppercase; background-color: {badge_bg}; color: {badge_fg};">
                                        {risk_level}
                                    </span>
                                </div>
                            </div>
                        </td>
                    </tr>
                </table>

                <!-- Geolocation Box -->
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px 16px; margin-bottom: 20px;">
                    <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #0284c7; margin-bottom: 4px;">📍 Geolocation & Origin</div>
                    <div style="font-size: 14px; font-weight: 700; font-family: monospace; color: #0f172a;">{gps_info['coordinates']}</div>
                    <div style="font-size: 12px; color: #64748b; margin-top: 3px;">Source: <strong style="color: #334155;">{gps_info['source']}</strong></div>
                </div>

                <!-- Primary Metrics Grid -->
                <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #475569; margin-bottom: 10px;">Key Screening Metrics</div>
                <table width="100%" cellpadding="0" cellspacing="0" style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; margin-bottom: 24px; text-align: center;">
                    <tr>
                        <td style="padding: 16px 10px; border-right: 1px solid #e2e8f0;">
                            <div style="font-size: 11px; color: #64748b; font-weight: 600;">INTEGRITY (SI)</div>
                            <div style="font-size: 26px; font-weight: 800; color: #1e3a8a; margin-top: 2px;">{health_score if health_score is not None else '—'}</div>
                            <div style="font-size: 10px; color: #94a3b8;">0–100 Scale</div>
                        </td>
                        <td style="padding: 16px 10px; border-right: 1px solid #e2e8f0;">
                            <div style="font-size: 11px; color: #64748b; font-weight: 600;">SEVERITY (SSI)</div>
                            <div style="font-size: 26px; font-weight: 800; color: {badge_fg}; margin-top: 2px;">{severity_index if severity_index is not None else '—'}</div>
                            <div style="font-size: 10px; color: #94a3b8;">Hazard Index</div>
                        </td>
                        <td style="padding: 16px 10px; border-right: 1px solid #e2e8f0;">
                            <div style="font-size: 11px; color: #64748b; font-weight: 600;">ANOMALIES</div>
                            <div style="font-size: 26px; font-weight: 800; color: #334155; margin-top: 2px;">{crack_count if crack_count is not None else '0'}</div>
                            <div style="font-size: 10px; color: #94a3b8;">Detected Regions</div>
                        </td>
                        <td style="padding: 16px 10px;">
                            <div style="font-size: 11px; color: #64748b; font-weight: 600;">COVERAGE</div>
                            <div style="font-size: 26px; font-weight: 800; color: #334155; margin-top: 2px;">{f"{total_area_pct}%" if total_area_pct is not None else '—'}</div>
                            <div style="font-size: 10px; color: #94a3b8;">Surface Area</div>
                        </td>
                    </tr>
                </table>

                {f'''
                <!-- Cracks Breakdown Table -->
                <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #475569; margin-bottom: 8px;">Detected Fracture Breakdown</div>
                <table width="100%" cellpadding="0" cellspacing="0" style="border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 24px; font-size: 12px; text-align: left; overflow: hidden;">
                    <thead style="background: #f1f5f9; color: #475569;">
                        <tr>
                            <th style="padding: 8px 12px;">ID</th>
                            <th style="padding: 8px 12px;">Type</th>
                            <th style="padding: 8px 12px;">Confidence</th>
                            <th style="padding: 8px 12px;">Width</th>
                            <th style="padding: 8px 12px;">Area %</th>
                        </tr>
                    </thead>
                    <tbody>
                        {cracks_html_rows}
                    </tbody>
                </table>
                ''' if cracks else ''}

                {f'''
                <!-- Engineering Notes -->
                <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #475569; margin-bottom: 8px;">Decision-Support Evaluation</div>
                <div style="background: #f8fafc; border-left: 4px solid #0284c7; padding: 12px 16px; border-radius: 0 8px 8px 0; margin-bottom: 24px;">
                    <ul style="margin: 0; padding-left: 18px; font-size: 13px;">
                        {recs_html_items}
                    </ul>
                </div>
                ''' if recommendations else ''}

                <!-- Disclaimer Notice -->
                <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px; padding: 14px 16px; margin-top: 10px;">
                    <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #b91c1c; margin-bottom: 4px;">Important Regulatory Notice</div>
                    <div style="font-size: 11px; color: #7f1d1d; line-height: 1.5;">{STANDARD_DISCLAIMER}</div>
                </div>
            </td>
        </tr>

        <!-- Footer -->
        <tr>
            <td style="background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 16px 32px; font-size: 11px; color: #94a3b8; text-align: center;">
                Generated by <strong>AEGIS-3D Unified Platform</strong> &bull; Recipient: <span style="font-family: monospace;">aimhighpa@gmail.com</span>
            </td>
        </tr>
    </table>
</body>
</html>"""

    return plain_text, html_content


def send_inspection_report_email(
    report_data: Dict[str, Any],
    image_bytes: Optional[bytes] = None,
    image_filename: Optional[str] = None,
    attach_pdf: bool = True
) -> Dict[str, Any]:
    """
    Construct and dispatch the inspection report email to aimhighpa@gmail.com via Gmail SMTP.
    Validates attachment sizes, credentials, and attachments.
    """
    config = get_email_config()
    sender_address = config["address"]
    sender_password = config["password"]
    recipient = config["recipient"]

    # Validate image attachment size
    if image_bytes and len(image_bytes) > MAX_ATTACHMENT_SIZE_BYTES:
        raise EmailSendError(
            f"Image attachment size ({len(image_bytes) / (1024*1024):.1f} MB) exceeds allowable limit of 15 MB."
        )

    timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    gps_info = format_gps_info(
        report_data.get("latitude"),
        report_data.get("longitude"),
        report_data.get("gps_status")
    )

    plain_body, html_body = build_email_body(report_data, timestamp_str, gps_info)

    # Compose Root MIME Message
    msg = MIMEMultipart("mixed")
    msg["Subject"] = "AEGIS-3D | New Infrastructure Inspection Report"
    msg["From"] = f"AEGIS-3D Intelligence <{sender_address}>"
    msg["To"] = recipient

    # Alternative body container (plain text + HTML)
    alt_container = MIMEMultipart("alternative")
    alt_container.attach(MIMEText(plain_body, "plain", "utf-8"))
    alt_container.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt_container)

    attachments_included = []

    # 1. Attach Uploaded/Annotated Image if practical
    if image_bytes:
        img_name = image_filename or report_data.get("filename") or "inspection_scan.jpg"
        # Determine image subtype
        ext = os.path.splitext(img_name)[1].lower().strip(".")
        subtype = "png" if ext == "png" else ("webp" if ext == "webp" else "jpeg")

        try:
            img_part = MIMEImage(image_bytes, _subtype=subtype)
            img_part.add_header("Content-Disposition", "attachment", filename=os.path.basename(img_name))
            msg.attach(img_part)
            attachments_included.append(os.path.basename(img_name))
        except Exception as e:
            # Fallback as generic application octet-stream
            part = MIMEApplication(image_bytes, Name=os.path.basename(img_name))
            part.add_header("Content-Disposition", "attachment", filename=os.path.basename(img_name))
            msg.attach(part)
            attachments_included.append(os.path.basename(img_name))

    # 2. Attach Inspection PDF if requested / available
    pdf_path = None
    if attach_pdf:
        pdf_path = generate_inspection_pdf(report_data)
        if pdf_path and os.path.exists(pdf_path):
            try:
                pdf_size = os.path.getsize(pdf_path)
                if pdf_size <= MAX_ATTACHMENT_SIZE_BYTES:
                    with open(pdf_path, "rb") as pf:
                        pdf_bytes = pf.read()
                    pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
                    pdf_filename = f"AEGIS_Inspection_Report_{os.path.basename(pdf_path)}"
                    pdf_part.add_header("Content-Disposition", "attachment", filename=pdf_filename)
                    msg.attach(pdf_part)
                    attachments_included.append(pdf_filename)
            except Exception as e:
                print(f"[email_service] Warning: Failed to attach PDF ({e})")

    # 3. Transmit via SMTP
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=25) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(sender_address, sender_password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise EmailSendError(
            "Gmail SMTP authentication failed. Please check GMAIL_ADDRESS and ensure "
            "GMAIL_APP_PASSWORD is a valid 16-character Google App Password (not your account login password)."
        ) from e
    except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError) as e:
        raise EmailSendError(f"Failed to connect to Gmail SMTP server: {e}") from e
    except Exception as e:
        raise EmailSendError(f"Failed to transmit email: {e}") from e

    return {
        "status": "success",
        "message": f"Inspection report successfully emailed to {recipient}.",
        "recipient": recipient,
        "timestamp": timestamp_str,
        "attachments": attachments_included,
    }
