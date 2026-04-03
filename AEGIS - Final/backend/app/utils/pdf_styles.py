from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.colors import HexColor, black, white

def get_report_styles():
    styles = getSampleStyleSheet()
    
    # Custom Colors
    PRIMARY_COLOR = HexColor("#1E3A8A") # Dark Blue
    SECONDARY_COLOR = HexColor("#3B82F6") # Blue
    DANGER_COLOR = HexColor("#EF4444") # Red
    WARNING_COLOR = HexColor("#F59E0B") # Orange
    SUCCESS_COLOR = HexColor("#10B981") # Green
    DARK_GRAY = HexColor("#374151")
    LIGHT_GRAY = HexColor("#F3F4F6")

    # Title Style
    styles.add(ParagraphStyle(
        name='ReportTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=PRIMARY_COLOR,
        alignment=TA_CENTER,
        spaceAfter=30
    ))

    # Section Heading Style
    styles.add(ParagraphStyle(
        name='SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=SECONDARY_COLOR,
        spaceBefore=20,
        spaceAfter=15,
        borderPadding=5,
        backColor=LIGHT_GRAY
    ))

    # Sub-heading Style
    styles.add(ParagraphStyle(
        name='SubHeading',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=DARK_GRAY,
        spaceBefore=15,
        spaceAfter=10
    ))

    # Normal Text Style
    styles.add(ParagraphStyle(
        name='NormalText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        textColor=black,
        spaceBefore=6,
        spaceAfter=6,
        leading=14
    ))

    # Bold Text Style
    styles.add(ParagraphStyle(
        name='BoldText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=black,
        spaceBefore=6,
        spaceAfter=6,
        leading=14
    ))

    # Alert Text (Red)
    styles.add(ParagraphStyle(
        name='AlertText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=DANGER_COLOR,
        spaceBefore=6,
        spaceAfter=6
    ))

    # Center Text
    styles.add(ParagraphStyle(
        name='CenterText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        alignment=TA_CENTER,
        spaceBefore=6,
        spaceAfter=6
    ))

    return styles, PRIMARY_COLOR, DANGER_COLOR, WARNING_COLOR, SUCCESS_COLOR, LIGHT_GRAY
