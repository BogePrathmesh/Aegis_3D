import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.pdfgen import canvas as pdfcanvas

# Colors matching the brand guidelines
PRIMARY_COLOR = colors.HexColor("#1A237E")  # Deep Navy
ACCENT_COLOR = colors.HexColor("#00BCD4")   # Cyan
DARK_COLOR = colors.HexColor("#212121")     # Dark grey/black
LIGHT_GREY = colors.HexColor("#F5F5F5")     # Light grey background
BORDER_GREY = colors.HexColor("#E0E0E0")    # Border grey
LINE_GREY = colors.HexColor("#BDBDBD")

class NumberedCanvas(pdfcanvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_decorations(num_pages)
            pdfcanvas.Canvas.showPage(self)
        pdfcanvas.Canvas.save(self)

    def _draw_page_decorations(self, total_pages):
        self.saveState()
        w, h = A4
        
        # Header (Skip cover page 1)
        if self._pageNumber > 1:
            self.setFillColor(PRIMARY_COLOR)
            self.rect(0, h - 28, w, 28, fill=True, stroke=False)
            self.setFillColor(colors.white)
            self.setFont("Helvetica-Bold", 8)
            self.drawString(1.5 * cm, h - 18, "AEGIS UNIFIED PLATFORM — TECHNICAL DOCUMENTATION")
            self.setFont("Helvetica", 7)
            self.drawRightString(w - 1.5 * cm, h - 18, "Architecture & Implementation Reference")
        
        # Footer
        self.setFillColor(LIGHT_GREY)
        self.rect(0, 0, w, 22, fill=True, stroke=False)
        self.setFillColor(colors.HexColor("#757575"))
        self.setFont("Helvetica", 7)
        self.drawString(1.5 * cm, 7, "Confidential — Internal Engineering Documentation")
        self.drawRightString(w - 1.5 * cm, 7, f"Page {self._pageNumber} of {total_pages}")
        
        self.restoreState()

def parse_markdown_to_story(md_path, styles):
    story = []
    
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    in_code_block = False
    code_content = []
    in_table = False
    table_headers = []
    table_rows = []
    
    # Simple regex to replace markdown formatting with HTML tags supported by ReportLab Paragraphs
    def clean_text(text):
        # Escape HTML entities first, except we want to keep our tags
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Restore bold
        text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
        
        # Restore code tags
        text = re.sub(r"`(.*?)`", r'<font name="Courier" color="#C2185B"><b>\1</b></font>', text)
        
        # Restore simple links
        text = re.sub(r"\[(.*?)\]\((.*?)\)", r'<font color="#00BCD4"><u>\1</u></font>', text)
        
        # Re-allow basic text styling tags that ReportLab parses
        text = text.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
        text = text.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
        text = text.replace("&lt;u&gt;", "<u>").replace("&lt;/u&gt;", "</u>")
        text = text.replace('&lt;font name="Courier" color="#C2185B"&gt;&lt;b&gt;', '<font name="Courier" color="#C2185B"><b>')
        text = text.replace('&lt;/b&gt;&lt;/font&gt;', '</b></font>')
        text = text.replace('&lt;font color="#00BCD4"&gt;&lt;u&gt;', '<font color="#00BCD4"><u>')
        text = text.replace('&lt;/u&gt;&lt;/font&gt;', '</u></font>')
        text = text.replace("&lt;br/&gt;", "<br/>")
        
        return text.strip()

    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 1. Code block handling
        if line.startswith("```"):
            if in_code_block:
                # End of code block
                in_code_block = False
                code_text = "<br/>".join(code_content)
                story.append(Paragraph(code_text, styles["CodeBlock"]))
                story.append(Spacer(1, 8))
                code_content = []
            else:
                in_code_block = True
            i += 1
            continue
            
        if in_code_block:
            # Escape HTML characters within code blocks so they don't break paragraph parser
            escaped_code = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "").replace(" ", "&nbsp;")
            code_content.append(f'<font name="Courier" size="8" color="#37474F">{escaped_code}</font>')
            i += 1
            continue

        # 2. Table handling
        if line.strip().startswith("|") and not in_code_block:
            if not in_table:
                in_table = True
                table_headers = [clean_text(cell) for cell in line.split("|")[1:-1]]
                # Skip separator line
                i += 2
                continue
            else:
                row_cells = [clean_text(cell) for cell in line.split("|")[1:-1]]
                table_rows.append(row_cells)
                i += 1
                continue
        elif in_table:
            # End of table
            in_table = False
            
            # Construct Table
            all_table_data = []
            # Headers
            header_row = [Paragraph(f"<b>{h}</b>", styles["TableHeaderText"]) for h in table_headers]
            all_table_data.append(header_row)
            
            for row in table_rows:
                all_table_data.append([Paragraph(cell, styles["TableBodyText"]) for cell in row])
                
            # Estimate column widths
            num_cols = len(table_headers)
            col_width = (A4[0] - 3.0 * cm) / max(1, num_cols)
            
            t = Table(all_table_data, colWidths=[col_width] * num_cols)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
                ('GRID', (0,0), (-1,-1), 0.5, LINE_GREY),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT_GREY]),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 10))
            table_rows = []
            table_headers = []
            continue

        # 3. Headings
        stripped_line = line.strip()
        if stripped_line.startswith("# ") and not in_code_block:
            title_text = clean_text(stripped_line[2:])
            # Cover title page if it's the first header
            if len(story) == 0:
                story.append(Spacer(1, 5 * cm))
                story.append(Paragraph(title_text, styles["CoverTitle"]))
                story.append(Spacer(1, 0.5 * cm))
                story.append(HRFlowable(width="70%", thickness=2, color=ACCENT_COLOR, spaceAfter=20))
                story.append(Paragraph("System Architecture, Models & Operational Reference Guide", styles["CoverSub"]))
                story.append(Spacer(1, 8 * cm))
                story.append(Paragraph("<b>Version:</b> 3.0.0 (Production Grade)<br/><b>Generated:</b> June 2026", styles["CoverMeta"]))
                story.append(PageBreak())
            else:
                story.append(Paragraph(title_text, styles["H1"]))
                story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY_COLOR, spaceAfter=8))
            i += 1
            continue
            
        if stripped_line.startswith("## ") and not in_code_block:
            story.append(Spacer(1, 12))
            story.append(Paragraph(clean_text(stripped_line[3:]), styles["H2"]))
            i += 1
            continue
            
        if stripped_line.startswith("### ") and not in_code_block:
            story.append(Spacer(1, 8))
            story.append(Paragraph(clean_text(stripped_line[4:]), styles["H3"]))
            i += 1
            continue

        # 4. Bullet lists
        if (stripped_line.startswith("- ") or stripped_line.startswith("* ")) and not in_code_block:
            item_text = clean_text(stripped_line[2:])
            story.append(Paragraph(f"•&nbsp;&nbsp;{item_text}", styles["BulletItem"]))
            i += 1
            continue
            
        # 5. Numbered lists
        match = re.match(r"^(\d+)\.\s+(.*)", stripped_line)
        if match and not in_code_block:
            num = match.group(1)
            item_text = clean_text(match.group(2))
            story.append(Paragraph(f"{num}.&nbsp;&nbsp;{item_text}", styles["BulletItem"]))
            i += 1
            continue
            
        # 6. Block quotes
        if stripped_line.startswith("> ") and not in_code_block:
            quote_text = clean_text(stripped_line[2:])
            story.append(Paragraph(quote_text, styles["BlockQuote"]))
            i += 1
            continue

        # 7. Blank lines
        if stripped_line == "":
            i += 1
            continue

        # 8. Regular text paragraphs
        story.append(Paragraph(clean_text(stripped_line), styles["Body"]))
        story.append(Spacer(1, 6))
        i += 1
        
    return story

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    md_path = os.path.join(base_dir, "TECHNICAL_DOCUMENTATION.md")
    pdf_path = os.path.join(base_dir, "TECHNICAL_DOCUMENTATION.pdf")
    
    if not os.path.exists(md_path):
        print(f"Error: Could not find documentation at {md_path}")
        return
        
    # Styles Setup
    styles = {}
    base_styles = getSampleStyleSheet()
    
    styles["CoverTitle"] = ParagraphStyle(
        "CoverTitle",
        fontName="Helvetica-Bold",
        fontSize=28,
        textColor=PRIMARY_COLOR,
        alignment=TA_CENTER,
        leading=34,
        spaceAfter=15
    )
    styles["CoverSub"] = ParagraphStyle(
        "CoverSub",
        fontName="Helvetica",
        fontSize=12,
        textColor=colors.HexColor("#555555"),
        alignment=TA_CENTER,
        leading=16
    )
    styles["CoverMeta"] = ParagraphStyle(
        "CoverMeta",
        fontName="Helvetica",
        fontSize=9,
        textColor=colors.HexColor("#777777"),
        alignment=TA_CENTER,
        leading=14
    )
    
    styles["H1"] = ParagraphStyle(
        "Heading1",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=PRIMARY_COLOR,
        spaceBefore=18,
        spaceAfter=8,
        keepWithNext=True
    )
    styles["H2"] = ParagraphStyle(
        "Heading2",
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=PRIMARY_COLOR,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    styles["H3"] = ParagraphStyle(
        "Heading3",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=DARK_COLOR,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    styles["Body"] = ParagraphStyle(
        "BodyText",
        fontName="Helvetica",
        fontSize=9,
        textColor=DARK_COLOR,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=8
    )
    styles["BulletItem"] = ParagraphStyle(
        "BulletItem",
        fontName="Helvetica",
        fontSize=9,
        textColor=DARK_COLOR,
        leading=14,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )
    styles["BlockQuote"] = ParagraphStyle(
        "BlockQuote",
        fontName="Helvetica-Oblique",
        fontSize=9,
        textColor=colors.HexColor("#424242"),
        backColor=LIGHT_GREY,
        borderPadding=8,
        leftIndent=15,
        rightIndent=15,
        leading=13,
        spaceAfter=8
    )
    styles["CodeBlock"] = ParagraphStyle(
        "CodeBlock",
        fontName="Courier",
        fontSize=8,
        textColor=colors.HexColor("#263238"),
        backColor=colors.HexColor("#ECEFF1"),
        borderPadding=10,
        leading=12,
        spaceAfter=8
    )
    styles["TableHeaderText"] = ParagraphStyle(
        "TableHeaderText",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        textColor=colors.white,
        leading=10,
        alignment=TA_LEFT
    )
    styles["TableBodyText"] = ParagraphStyle(
        "TableBodyText",
        fontName="Helvetica",
        fontSize=7.5,
        textColor=DARK_COLOR,
        leading=9,
        alignment=TA_LEFT
    )
    
    # Doc Template
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm
    )
    
    print("Parsing Markdown...")
    story = parse_markdown_to_story(md_path, styles)
    
    print("Building PDF...")
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF built successfully at: {pdf_path}")

if __name__ == "__main__":
    main()
