"""
Ignisia PDF Report Generator
=============================
Produces a government-grade bridge inspection report using ReportLab.
"""

from __future__ import annotations
import io
import os
import math
from datetime import datetime
from typing import List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Image as RLImage,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Circle
from reportlab.graphics import renderPDF
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.pdfgen import canvas as pdfcanvas

from app.models.schemas import InspectionInput, RiskOutput, RiskCategory, ActionCode

# ── Paths ──────────────────────────────────────────────────────────────────
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reports")
DATA_DIR    = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")

# ── Brand colours ──────────────────────────────────────────────────────────
IGNISIA_BLUE   = colors.HexColor("#1A237E")
IGNISIA_ACCENT = colors.HexColor("#00BCD4")
IGNISIA_DARK   = colors.HexColor("#0D1117")
DANGER_RED     = colors.HexColor("#D32F2F")
WARNING_ORANGE = colors.HexColor("#F57C00")
SUCCESS_GREEN  = colors.HexColor("#388E3C")
MODERATE_YELLOW= colors.HexColor("#FBC02D")
LIGHT_GREY     = colors.HexColor("#F5F5F5")
MID_GREY       = colors.HexColor("#9E9E9E")
WHITE          = colors.white
BLACK          = colors.black

PAGE_W, PAGE_H = A4


def _risk_color(category: RiskCategory) -> colors.Color:
    return {
        RiskCategory.critical: DANGER_RED,
        RiskCategory.high:     WARNING_ORANGE,
        RiskCategory.moderate: MODERATE_YELLOW,
        RiskCategory.low:      SUCCESS_GREEN,
    }.get(category, MID_GREY)


def _action_color(code: ActionCode) -> colors.Color:
    return {
        ActionCode.close_immediately: DANGER_RED,
        ActionCode.emergency:         WARNING_ORANGE,
        ActionCode.repair_required:   MODERATE_YELLOW,
        ActionCode.monitor:           IGNISIA_ACCENT,
        ActionCode.routine:           SUCCESS_GREEN,
    }.get(code, MID_GREY)


# ── Styles ─────────────────────────────────────────────────────────────────

def _build_styles():
    base = getSampleStyleSheet()
    styles = {}

    def S(name, **kw):
        styles[name] = ParagraphStyle(name, **kw)

    S("CoverTitle",  fontName="Helvetica-Bold", fontSize=26, textColor=WHITE,
      alignment=TA_CENTER, spaceAfter=6)
    S("CoverSub",    fontName="Helvetica",      fontSize=13, textColor=IGNISIA_ACCENT,
      alignment=TA_CENTER, spaceAfter=4)
    S("CoverMeta",   fontName="Helvetica",      fontSize=10, textColor=WHITE,
      alignment=TA_CENTER, spaceAfter=2)

    S("SectionHead", fontName="Helvetica-Bold", fontSize=13, textColor=IGNISIA_BLUE,
      spaceBefore=14, spaceAfter=6, borderPad=4)
    S("SubHead",     fontName="Helvetica-Bold", fontSize=10, textColor=IGNISIA_DARK,
      spaceBefore=8, spaceAfter=4)
    S("Body",        fontName="Helvetica",      fontSize=9,  textColor=BLACK,
      spaceAfter=4, leading=14)
    S("BodyJust",    fontName="Helvetica",      fontSize=9,  textColor=BLACK,
      spaceAfter=4, leading=14, alignment=TA_JUSTIFY)
    S("SmallGrey",   fontName="Helvetica",      fontSize=7.5, textColor=MID_GREY,
      spaceAfter=2)
    S("Bold",        fontName="Helvetica-Bold", fontSize=9,  textColor=BLACK)
    S("BigStat",     fontName="Helvetica-Bold", fontSize=28, textColor=IGNISIA_BLUE,
      alignment=TA_CENTER)
    S("StatLabel",   fontName="Helvetica",      fontSize=8,  textColor=MID_GREY,
      alignment=TA_CENTER)
    S("RecommendationBox", fontName="Helvetica-Bold", fontSize=11, textColor=WHITE,
      alignment=TA_CENTER, backColor=IGNISIA_BLUE, borderPad=8)
    S("Footer",      fontName="Helvetica",      fontSize=7,  textColor=MID_GREY,
      alignment=TA_CENTER)
    return styles


# ── Risk gauge (SVG-like via ReportLab Drawing) ───────────────────────────

def _risk_gauge(score: float, category: RiskCategory) -> Drawing:
    """Semi-circular gauge showing insurance risk score."""
    d = Drawing(180, 100)
    col = _risk_color(category)

    # Background arc segments (low → critical)
    segment_colors = [SUCCESS_GREEN, MODERATE_YELLOW, WARNING_ORANGE, DANGER_RED]
    for i, sc in enumerate(segment_colors):
        rect = Rect(5 + i * 42, 55, 38, 12, fillColor=sc, strokeColor=None)
        d.add(rect)

    # Score text
    d.add(String(90, 20, f"{score:.0f}", textAnchor="middle",
                 fontSize=32, fontName="Helvetica-Bold",
                 fillColor=col))
    d.add(String(90, 8,  "/100", textAnchor="middle",
                 fontSize=10, fontName="Helvetica",
                 fillColor=MID_GREY))
    d.add(String(90, 72, category.value.upper(), textAnchor="middle",
                 fontSize=9, fontName="Helvetica-Bold",
                 fillColor=col))
    # Indicator dot
    frac  = score / 100.0
    dot_x = 5 + frac * 168
    d.add(Circle(dot_x, 61, 7, fillColor=col, strokeColor=WHITE, strokeWidth=2))
    return d


def _bar_chart_breakdown(breakdown_data: dict) -> Drawing:
    """Small bar chart of score component breakdown."""
    labels = list(breakdown_data.keys())
    values = list(breakdown_data.values())

    d   = Drawing(420, 120)
    bc  = VerticalBarChart()
    bc.x, bc.y, bc.width, bc.height = 50, 10, 360, 95
    bc.data = [values]
    bc.bars[0].fillColor = IGNISIA_ACCENT
    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontSize  = 7
    bc.categoryAxis.labels.angle     = 0
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = max(values) * 1.2 if values else 10
    bc.valueAxis.labels.fontSize = 7
    d.add(bc)
    return d


# ── Page callbacks (header/footer on every page) ──────────────────────────

class _HeaderFooterCanvas(pdfcanvas.Canvas):
    def __init__(self, *args, report_meta=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self._report_meta = report_meta or {}

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_header_footer(num_pages)
            pdfcanvas.Canvas.showPage(self)
        pdfcanvas.Canvas.save(self)

    def _draw_header_footer(self, page_count):
        page = self._pageNumber
        w, h = A4

        # Header bar (skip cover page 1)
        if page > 1:
            self.setFillColor(IGNISIA_BLUE)
            self.rect(0, h - 28, w, 28, fill=True, stroke=False)
            self.setFillColor(WHITE)
            self.setFont("Helvetica-Bold", 8)
            self.drawString(cm, h - 18, "IGNISIA AI INSPECTION SYSTEM")
            meta = self._report_meta
            self.setFont("Helvetica", 7)
            self.drawRightString(w - cm, h - 18,
                f"{meta.get('structure_name','—')}  |  Report: {meta.get('report_id','—')}")

        # Footer
        self.setFillColor(LIGHT_GREY)
        self.rect(0, 0, w, 22, fill=True, stroke=False)
        self.setFillColor(MID_GREY)
        self.setFont("Helvetica", 6.5)
        self.drawString(cm, 7, "Generated by Ignisia AI Inspection System — Confidential Infrastructure Report")
        self.drawRightString(w - cm, 7, f"Page {page} of {page_count}")


# ── PDF builder ────────────────────────────────────────────────────────────

def generate_report(inspection: InspectionInput, risk: RiskOutput, report_id: str) -> str:
    """
    Build a full PDF inspection report. Returns file path.
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)
    out_path = os.path.join(REPORTS_DIR, f"{report_id}.pdf")

    meta = {
        "structure_name": inspection.structure.structure_name,
        "report_id":      report_id,
    }

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.0 * cm,
    )

    styles = _build_styles()
    story  = []

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 1 — COVER
    # ══════════════════════════════════════════════════════════════════════
    _add_cover(story, styles, inspection, risk, report_id)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 2 — EXECUTIVE SUMMARY
    # ══════════════════════════════════════════════════════════════════════
    _add_executive_summary(story, styles, inspection, risk)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 3 — INSURANCE RISK ANALYSIS
    # ══════════════════════════════════════════════════════════════════════
    _add_insurance_section(story, styles, risk)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 4 — DEFECT TABLE
    # ══════════════════════════════════════════════════════════════════════
    _add_defect_table(story, styles, risk)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 5 — DEFECT IMAGES (one block per defect)
    # ══════════════════════════════════════════════════════════════════════
    _add_defect_images(story, styles, risk, inspection)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 6 — HISTORICAL COMPARISON
    # ══════════════════════════════════════════════════════════════════════
    _add_historical_section(story, styles, inspection, risk)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 7 — FINAL RECOMMENDATION
    # ══════════════════════════════════════════════════════════════════════
    _add_recommendation(story, styles, inspection, risk, report_id)

    # Build
    def _make_canvas(filename, **kwargs):
        return _HeaderFooterCanvas(filename, report_meta=meta, **kwargs)

    doc.build(story, canvasmaker=_make_canvas)
    return out_path


# ── Section builders ──────────────────────────────────────────────────────

def _add_cover(story, styles, inspection: InspectionInput, risk: RiskOutput, report_id: str):
    """Full dark cover page."""
    s = inspection.structure

    # Dark cover rectangle (drawn via a table background)
    cover_data = [[""]]
    cover_table = Table(cover_data, colWidths=[PAGE_W - 4 * cm], rowHeights=[PAGE_H * 0.9])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), IGNISIA_BLUE),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [IGNISIA_BLUE]),
    ]))
    story.append(cover_table)

    # We use a separate "overlay" approach — title in a table cell
    rc = risk.risk_category
    rc_color = _risk_color(rc)
    rc_name  = rc.value.upper()

    cover_content = [
        Spacer(1, 2.5 * cm),
        Paragraph("IGNISIA AI INSPECTION SYSTEM", ParagraphStyle("ct1",
            fontName="Helvetica-Bold", fontSize=10, textColor=IGNISIA_ACCENT,
            alignment=TA_CENTER, spaceAfter=4)),
        Paragraph("Infrastructure Risk Assessment Report", ParagraphStyle("ct2",
            fontName="Helvetica-Bold", fontSize=22, textColor=WHITE,
            alignment=TA_CENTER, spaceAfter=20)),
        HRFlowable(width="80%", thickness=1, color=IGNISIA_ACCENT, spaceAfter=16),
        Paragraph(s.structure_name.upper(), ParagraphStyle("ct3",
            fontName="Helvetica-Bold", fontSize=18, textColor=WHITE,
            alignment=TA_CENTER, spaceAfter=12)),
        Paragraph(f"{s.structure_type.value.replace('_',' ').title()}  ·  {s.location}",
            ParagraphStyle("ct4", fontName="Helvetica", fontSize=11, textColor=IGNISIA_ACCENT,
            alignment=TA_CENTER, spaceAfter=30)),
        # Risk badge table
        _cover_badge(rc_name, rc_color, risk.insurance_risk_score),
        Spacer(1, 1.5 * cm),
        _cover_meta_table(inspection, report_id, styles),
    ]

    story.extend(cover_content)


def _cover_badge(label: str, col: colors.Color, score: float):
    badge_data = [[f"RISK STATUS: {label}  |  SCORE: {score:.0f}/100"]]
    t = Table(badge_data, colWidths=[12 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), col),
        ("TEXTCOLOR",   (0, 0), (-1, -1), WHITE),
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 13),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [col]),
    ]))
    return Table([[t]], colWidths=[PAGE_W - 4 * cm],
                 style=[("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0)])


def _cover_meta_table(inspection: InspectionInput, report_id: str, styles):
    s   = inspection.structure
    now = datetime.now().strftime("%d %B %Y, %H:%M")
    rows = [
        ["Report ID:",        report_id,              "Inspection Date:",    inspection.inspection_date],
        ["Structure ID:",     s.structure_id,          "Year Built:",         str(s.year_built)],
        ["Jurisdiction:",     s.jurisdiction,          "Traffic Level:",      s.traffic_level.value.title()],
        ["Reviewed By:",      inspection.reviewed_by,  "Generated On:",       now],
    ]
    t = Table(rows, colWidths=[3.5 * cm, 5.5 * cm, 3.5 * cm, 5.5 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("TEXTCOLOR",   (0, 0), (-1, -1), WHITE),
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",    (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR",   (0, 0), (0, -1), IGNISIA_ACCENT),
        ("TEXTCOLOR",   (2, 0), (2, -1), IGNISIA_ACCENT),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _add_executive_summary(story, styles, inspection: InspectionInput, risk: RiskOutput):
    s = inspection.structure
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("1. Executive Summary", styles["SectionHead"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=IGNISIA_BLUE, spaceAfter=10))

    # KPI cards row
    high_sev = max(d.severity_score for d in inspection.defects)
    kpi_data = [
        [_kpi_cell(str(len(inspection.defects)), "Total Defects", styles),
         _kpi_cell(str(high_sev) + "/5",         "Max Severity",  styles),
         _kpi_cell(f"{risk.insurance_risk_score:.0f}", "Risk Score", styles),
         _kpi_cell(f"{risk.failure_probability:.0f}%", "Fail Prob.", styles)],
    ]
    kpi_table = Table(kpi_data, colWidths=[4.2 * cm] * 4)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_GREY),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [LIGHT_GREY]),
        ("BOX",           (0, 0), (-1, -1), 0.5, MID_GREY),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.4 * cm))

    # Summary paragraph
    story.append(Paragraph("Inspection Overview", styles["SubHead"]))
    story.append(Paragraph(
        f"This report documents the AI-assisted drone inspection of <b>{s.structure_name}</b>, "
        f"a {s.structure_type.value.replace('_',' ')} located at <b>{s.location}, {s.state}</b>, "
        f"constructed in {s.year_built} (age: {s.age_years} years). "
        f"The inspection identified <b>{len(inspection.defects)} defect(s)</b> with a "
        f"maximum severity of <b>{high_sev}/5</b>.",
        styles["BodyJust"],
    ))

    # Risk reasons
    story.append(Paragraph("Key Risk Factors", styles["SubHead"]))
    for r in risk.risk_reasons:
        story.append(Paragraph(f"• {r}", styles["Body"]))

    # Action box
    story.append(Spacer(1, 0.3 * cm))
    action = risk.recommended_action
    action_col = _action_color(action.code)
    action_data = [[
        Paragraph(f"Recommended Action: {action.label}", ParagraphStyle("ab",
            fontName="Helvetica-Bold", fontSize=11, textColor=WHITE, alignment=TA_CENTER)),
        Paragraph(action.detail, ParagraphStyle("ad", fontName="Helvetica", fontSize=9,
            textColor=WHITE, alignment=TA_CENTER)),
    ]]
    at = Table(action_data, colWidths=[7 * cm, 10 * cm])
    at.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), action_col),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [action_col]),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(at)

    if action.urgency_days > 0:
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(
            f"⏱ Required action within <b>{action.urgency_days} day(s)</b>.",
            styles["Body"],
        ))


def _kpi_cell(value: str, label: str, styles) -> Table:
    t = Table([
        [Paragraph(value, styles["BigStat"])],
        [Paragraph(label, styles["StatLabel"])],
    ], colWidths=[4.0 * cm])
    t.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _add_insurance_section(story, styles, risk: RiskOutput):
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("2. Insurance Risk Analysis", styles["SectionHead"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=IGNISIA_BLUE, spaceAfter=10))

    # Gauge + raw stats side by side
    gauge = _risk_gauge(risk.insurance_risk_score, risk.risk_category)
    gauge_col = [gauge, Spacer(1, 4)]

    stats_rows = [
        ["Insurance Risk Score", f"{risk.insurance_risk_score:.1f} / 100"],
        ["Risk Category",        risk.risk_category.value],
        ["Failure Probability",  f"{risk.failure_probability:.1f}%"],
        ["Claim Probability",    f"{risk.claim_probability:.1f}%"],
        ["Premium Multiplier",   f"{risk.premium_multiplier:.2f}×"],
        ["Priority Rank",        f"#{risk.repair_priority_rank}"],
    ]
    stats_table = Table(stats_rows, colWidths=[5.5 * cm, 4.5 * cm])
    stats_table.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",    (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",   (0, 0), (0, -1), IGNISIA_BLUE),
        ("GRID",        (0, 0), (-1, -1), 0.3, MID_GREY),
        ("BACKGROUND",  (0, 0), (-1, 0), LIGHT_GREY),
        ("ROWBACKGROUNDS",(0, 0),(-1,-1),[WHITE, LIGHT_GREY]),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))

    row_data = [[Table([[gauge]], colWidths=[5.5 * cm]), stats_table]]
    side_table = Table(row_data, colWidths=[6 * cm, 12 * cm])
    side_table.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(side_table)
    story.append(Spacer(1, 0.4 * cm))

    # Score breakdown bar chart
    story.append(Paragraph("Score Component Breakdown", styles["SubHead"]))
    bd = risk.score_breakdown
    breakdown_vals = {
        "Severity": bd.severity,
        "Depth":    bd.depth,
        "Growth":   bd.growth,
        "Count":    bd.count,
        "Age":      bd.age,
        "Traffic":  bd.traffic,
    }
    chart = _bar_chart_breakdown(breakdown_vals)
    story.append(chart)
    story.append(Spacer(1, 0.2 * cm))

    # Multipliers note
    story.append(Paragraph(
        f"Infrastructure multiplier: <b>{bd.infra_multiplier:.2f}×</b> | "
        f"Temporal multiplier: <b>{bd.temporal_multiplier:.2f}×</b> | "
        f"Sub-total before multipliers: <b>{bd.subtotal:.1f} pts</b>",
        styles["SmallGrey"],
    ))

    # Risk reasons
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Risk Narrative", styles["SubHead"]))
    for r in risk.risk_reasons:
        story.append(Paragraph(f"▶  {r}", styles["Body"]))


def _add_defect_table(story, styles, risk: RiskOutput):
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("3. Defect Inventory", styles["SectionHead"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=IGNISIA_BLUE, spaceAfter=10))

    headers = ["ID", "Type", "Severity", "Depth (mm)", "Area (cm²)",
               "Length (mm)", "Growth%", "Zone", "Risk", "Action"]
    table_data = [headers]

    for d in risk.defects:
        rc_col = _risk_color(d.risk_category)
        row = [
            Paragraph(d.defect_id[:10], ParagraphStyle("tc", fontName="Helvetica-Bold", fontSize=7)),
            Paragraph(d.defect_type.title(), ParagraphStyle("tc", fontName="Helvetica", fontSize=7)),
            Paragraph(str(d.severity_score), ParagraphStyle("tc", fontName="Helvetica-Bold",
                fontSize=8, alignment=TA_CENTER)),
            f"{d.depth_mm:.1f}",
            f"{d.area_cm2:.1f}" if d.area_cm2 else "—",
            f"{d.length_mm:.0f}" if d.length_mm else "—",
            f"{d.growth_pct:.0f}%" if d.growth_pct else "—",
            Paragraph(d.zone[:20], ParagraphStyle("tc", fontName="Helvetica", fontSize=7)),
            Paragraph(d.risk_category.value, ParagraphStyle("trc",
                fontName="Helvetica-Bold", fontSize=7, textColor=WHITE,
                backColor=rc_col, alignment=TA_CENTER)),
            Paragraph(d.suggested_action.replace("_", " "), ParagraphStyle("ta",
                fontName="Helvetica", fontSize=6.5)),
        ]
        table_data.append(row)

    col_w = [1.5, 2.0, 1.4, 1.7, 1.6, 1.8, 1.4, 2.6, 1.8, 2.6]
    col_w_cm = [w * cm for w in col_w]

    t = Table(table_data, colWidths=col_w_cm, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  IGNISIA_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  7.5),
        ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("GRID",          (0, 0), (-1, -1), 0.3, MID_GREY),
        ("FONTSIZE",      (0, 1), (-1, -1), 7.5),
        ("ALIGN",         (2, 1), (2, -1),  "CENTER"),
        ("ALIGN",         (3, 1), (5, -1),  "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)


def _add_defect_images(story, styles, risk: RiskOutput, inspection: InspectionInput):
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("4. Defect Image Evidence", styles["SectionHead"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=IGNISIA_BLUE, spaceAfter=10))

    images_dir = os.path.join(DATA_DIR, "images")
    masks_dir  = os.path.join(DATA_DIR, "masks")

    for d in risk.defects:
        story.append(KeepTogether(_defect_image_block(d, styles, images_dir, masks_dir)))
        story.append(Spacer(1, 0.5 * cm))


def _defect_image_block(defect, styles, images_dir: str, masks_dir: str) -> list:
    block = []
    block.append(Paragraph(
        f"Defect: <b>{defect.defect_id}</b>  ·  {defect.defect_type.title()}  ·  "
        f"Severity {defect.severity_score}/5  ·  Zone: {defect.zone}",
        styles["SubHead"],
    ))

    imgs = []
    for label, fname in [
        ("Original", defect.original_image),
        ("Annotated", defect.annotated_image),
        ("Mask", defect.mask_image),
    ]:
        if fname:
            full = os.path.join(images_dir, fname) if label != "Mask" else os.path.join(masks_dir, fname)
            if os.path.exists(full):
                try:
                    img = RLImage(full, width=4 * cm, height=3 * cm)
                    imgs.append([Paragraph(label, styles["SmallGrey"]), img])
                except Exception:
                    pass

    if imgs:
        img_row = [[item[1] for item in imgs]]
        lbl_row = [[item[0] for item in imgs]]
        ncols = len(imgs)
        tbl = Table(lbl_row + img_row, colWidths=[5.5 * cm] * ncols)
        tbl.setStyle(TableStyle([
            ("ALIGN",  (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        block.append(tbl)
    else:
        block.append(Paragraph(
            "ℹ Image files not available in data directory.",
            styles["SmallGrey"],
        ))

    block.append(Paragraph(
        f"Depth: <b>{defect.depth_mm:.1f} mm</b> | "
        f"Risk Score: <b>{defect.defect_risk_score:.1f}</b> | "
        f"Action: <b>{defect.suggested_action}</b>",
        styles["Body"],
    ))
    return block


def _add_historical_section(story, styles, inspection: InspectionInput, risk: RiskOutput):
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("5. Historical Trend Analysis", styles["SectionHead"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=IGNISIA_BLUE, spaceAfter=10))

    has_growth = [d for d in inspection.defects if d.growth_pct is not None]

    if inspection.previous_inspection_date:
        story.append(Paragraph(
            f"Previous Inspection: <b>{inspection.previous_inspection_date}</b>  |  "
            f"Previous Risk Score: <b>{inspection.previous_risk_score or '—'}</b>  |  "
            f"Current Risk Score: <b>{risk.insurance_risk_score:.1f}</b>",
            styles["Body"],
        ))
    else:
        story.append(Paragraph("No previous inspection data available for comparison.", styles["Body"]))

    if has_growth:
        headers = ["Defect ID", "Zone", "Prev. Size (est.)", "Current Size", "Growth %", "Trend"]
        rows = [headers]
        for d in has_growth:
            growth = d.growth_pct or 0
            trend  = "▲ WORSENING" if growth > 20 else ("→ STABLE" if growth <= 5 else "↗ GROWING")
            trend_col = DANGER_RED if growth > 20 else (SUCCESS_GREEN if growth <= 5 else WARNING_ORANGE)
            rows.append([
                d.defect_id,
                d.zone,
                f"{d.depth_mm / (1 + growth/100):.1f} mm (est.)",
                f"{d.depth_mm:.1f} mm",
                f"{growth:.0f}%",
                Paragraph(trend, ParagraphStyle("tr", fontName="Helvetica-Bold",
                    fontSize=7.5, textColor=trend_col)),
            ])

        t = Table(rows, colWidths=[2.5*cm, 3.5*cm, 3.5*cm, 3.0*cm, 2.0*cm, 3.0*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), IGNISIA_BLUE),
            ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 7.5),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
            ("GRID",          (0, 0), (-1, -1), 0.3, MID_GREY),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4 * cm))

        # Simple line chart for growth
        story.append(_growth_bar_chart(has_growth))
    else:
        story.append(Paragraph("No growth data available for individual defects.", styles["SmallGrey"]))


def _growth_bar_chart(defects_with_growth) -> Drawing:
    d    = Drawing(400, 130)
    bc   = VerticalBarChart()
    bc.x, bc.y, bc.width, bc.height = 50, 20, 330, 95
    bc.data = [[d.growth_pct for d in defects_with_growth]]
    bc.bars[0].fillColor = IGNISIA_ACCENT
    bc.categoryAxis.categoryNames = [d.defect_id[:8] for d in defects_with_growth]
    bc.categoryAxis.labels.fontSize = 7
    bc.valueAxis.labels.fontSize    = 7
    bc.valueAxis.valueMin           = 0

    # Colour bars red if growth > 25%
    for i, defect in enumerate(defects_with_growth):
        if (defect.growth_pct or 0) > 25:
            bc.bars[(0, i)].fillColor = DANGER_RED

    d.add(bc)
    d.add(String(200, 118, "Crack Growth % by Defect", textAnchor="middle",
                 fontSize=8, fontName="Helvetica-Bold", fillColor=IGNISIA_BLUE))
    return d


def _add_recommendation(story, styles, inspection: InspectionInput, risk: RiskOutput, report_id: str):
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("6. Final Engineering Recommendation", styles["SectionHead"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=IGNISIA_BLUE, spaceAfter=10))

    action = risk.recommended_action
    ac     = _action_color(action.code)
    s      = inspection.structure

    # Big recommendation box
    rec_text = (
        f"<b>{action.label}</b><br/>"
        f"{action.detail}<br/><br/>"
        f"Based on an Insurance Risk Score of <b>{risk.insurance_risk_score:.1f}/100</b> and "
        f"a Failure Probability of <b>{risk.failure_probability:.1f}%</b>, "
        f"this {s.structure_type.value.replace('_', ' ')} is classified as "
        f"<b>{risk.risk_category.value.upper()} RISK</b>."
    )
    if action.urgency_days > 0:
        rec_text += f"<br/><br/>⚠ Required action within <b>{action.urgency_days} day(s)</b>."
    else:
        rec_text += "<br/><br/>🚨 <b>STRUCTURE CLOSED TO TRAFFIC — IMMEDIATE ACTION REQUIRED</b>"

    rec_data = [[Paragraph(rec_text, ParagraphStyle("rb",
        fontName="Helvetica", fontSize=10, textColor=WHITE,
        alignment=TA_JUSTIFY, leading=16))]]
    rec_table = Table(rec_data, colWidths=[PAGE_W - 4 * cm])
    rec_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), ac),
        ("TOPPADDING",    (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
    ]))
    story.append(rec_table)
    story.append(Spacer(1, 0.6 * cm))

    # Prioritization note
    story.append(Paragraph("Budget Prioritization", styles["SubHead"]))
    story.append(Paragraph(
        f"This structure holds <b>Priority Rank #{risk.repair_priority_rank}</b> in the regional "
        f"infrastructure repair queue. A premium multiplier of <b>{risk.premium_multiplier:.2f}×</b> "
        "is recommended for insurance underwriting purposes.",
        styles["BodyJust"],
    ))

    # Signature block
    story.append(Spacer(1, 1.5 * cm))
    sig_rows = [
        ["Engineer Signature:", "_" * 35, "Date:", "_" * 20],
        ["Print Name:",         "_" * 35, "License No.:", "_" * 20],
    ]
    sig_table = Table(sig_rows, colWidths=[3 * cm, 6.5 * cm, 2.5 * cm, 5 * cm])
    sig_table.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTNAME",    (1, 0), (1, -1), "Helvetica"),
        ("FONTNAME",    (3, 0), (3, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("TEXTCOLOR",   (0, 0), (0, -1), IGNISIA_BLUE),
        ("TEXTCOLOR",   (2, 0), (2, -1), IGNISIA_BLUE),
        ("TOPPADDING",  (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0),(-1, -1), 8),
    ]))
    story.append(sig_table)

    # Footer disclaimer
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f"Report ID: {report_id}  ·  "
        f"Generated: {datetime.now().strftime('%d %B %Y %H:%M UTC')}  ·  "
        "Powered by Ignisia AI Inspection System  ·  "
        "This report is for professional use only. Field verification required.",
        styles["Footer"],
    ))
