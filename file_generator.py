"""
file_generator.py
Document Generation Engine for Nova Voice AI Assistant
Supports: PDF (ReportLab), PPTX (python-pptx), DOCX (python-docx), XLSX (openpyxl/pandas), CSV
"""

import os
import re
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("file_generator")

BASE_DIR = Path(__file__).resolve().parent

# On Vercel serverless, /tmp is the only writeable directory
if os.environ.get("VERCEL"):
    DOWNLOADS_DIR = Path("/tmp/downloads")
else:
    DOWNLOADS_DIR = BASE_DIR / "downloads"

DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)


def format_file_size(size_bytes: int) -> str:
    """Formats file size in human readable string (e.g. 42 KB, 1.2 MB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def clean_filename(title: str, ext: str) -> str:
    """Creates a sanitized unique filename with timestamp."""
    sanitized = re.sub(r"[^\w\s-]", "", title).strip()
    sanitized = re.sub(r"[-\s]+", "_", sanitized)
    if not sanitized:
        sanitized = "Generated_Document"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{sanitized[:40]}_{timestamp}.{ext.lstrip('.')}"


# -----------------------------------------------------------------------------
# 1. PDF Generation (ReportLab)
# -----------------------------------------------------------------------------
def create_pdf(title: str, sections: List[Dict[str, Any]], tables: Optional[List[List[Any]]] = None) -> Path:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    filename = clean_filename(title or "Executive_Report", "pdf")
    filepath = DOWNLOADS_DIR / filename

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    # Custom Palette
    c_primary = colors.HexColor("#4C1D95")    # Deep Violet
    c_secondary = colors.HexColor("#7C3AED")  # Accent Purple
    c_dark = colors.HexColor("#0F172A")       # Slate Dark
    c_text = colors.HexColor("#334155")       # Text Slate

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=c_primary,
        spaceAfter=6
    )

    meta_style = ParagraphStyle(
        "DocMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=14
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=c_secondary,
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=c_text,
        spaceAfter=8
    )

    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    story = []

    # Title & Metadata
    story.append(Paragraph(title, title_style))
    meta_text = f"Prepared by Nova Voice AI Assistant &bull; Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    story.append(Paragraph(meta_text, meta_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_secondary, spaceAfter=14))

    # Sections
    for sec in sections:
        sec_heading = sec.get("heading", "")
        if sec_heading:
            story.append(Paragraph(sec_heading, h1_style))

        sec_body = sec.get("body", "")
        if sec_body:
            paragraphs = sec_body.split("\n")
            for p in paragraphs:
                p = p.strip()
                if not p:
                    continue
                if p.startswith(("- ", "* ", "• ")):
                    clean_b = p.lstrip("-*• ").strip()
                    story.append(Paragraph(f"&bull; {clean_b}", bullet_style))
                else:
                    story.append(Paragraph(p, body_style))

        # Check for section-specific table or bullet list
        bullets = sec.get("bullets", [])
        for b in bullets:
            story.append(Paragraph(f"&bull; {b}", bullet_style))

        story.append(Spacer(1, 8))

    # Optional Table
    if tables and len(tables) > 1:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Structured Summary Data", h1_style))
        story.append(Spacer(1, 4))

        # Convert table cells to Paragraphs for word wrapping
        table_data = []
        for row in tables:
            formatted_row = [
                Paragraph(str(cell), ParagraphStyle("Cell", parent=body_style, fontSize=9, leading=12))
                for cell in row
            ]
            table_data.append(formatted_row)

        t = Table(table_data, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), c_primary),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F8FAFC"), colors.HexColor("#EDE9FE")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))

    # Footer note
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=6))
    story.append(Paragraph("Confidential & Proprietary &bull; Generated automatically via Voice Command", meta_style))

    doc.build(story)
    return filepath


# -----------------------------------------------------------------------------
# 2. PowerPoint Generation (python-pptx)
# -----------------------------------------------------------------------------
def create_pptx(title: str, slides_data: List[Dict[str, Any]]) -> Path:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.enum.shapes import MSO_SHAPE

    filename = clean_filename(title or "Presentation", "pptx")
    filepath = DOWNLOADS_DIR / filename

    prs = Presentation()
    # 16:9 Widescreen layout
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]

    # Theme Colors
    bg_color = RGBColor(11, 15, 25)       # Obsidian #0B0F19
    c_white = RGBColor(241, 245, 249)     # White #F1F5F9
    c_accent = RGBColor(168, 85, 247)     # Purple #A855F7
    c_cyan = RGBColor(6, 182, 212)        # Cyan #06B6D4
    c_slate = RGBColor(148, 163, 184)     # Slate #94A3B8

    # ----------------- Slide 1: Title Slide -----------------
    slide1 = prs.slides.add_slide(blank_layout)
    bg1 = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = bg_color
    bg1.line.fill.background()

    # Title Box
    title_box = slide1.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(11.0), Inches(2.2))
    tf1 = title_box.text_frame
    tf1.word_wrap = True

    p_title = tf1.paragraphs[0]
    p_title.text = title
    p_title.font.name = "Arial"
    p_title.font.size = Pt(44)
    p_title.font.bold = True
    p_title.font.color.rgb = c_white
    p_title.alignment = PP_ALIGN.LEFT

    p_sub = tf1.add_paragraph()
    p_sub.text = f"Strategic Briefing &bull; Generated by Nova Voice AI\n{datetime.now().strftime('%B %d, %Y')}"
    p_sub.font.name = "Arial"
    p_sub.font.size = Pt(18)
    p_sub.font.color.rgb = c_accent
    p_sub.space_before = Pt(16)

    # Decorative bottom accent bar
    bar = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.2), Inches(4.8), Inches(3.0), Inches(0.08))
    bar.fill.solid()
    bar.fill.fore_color.rgb = c_cyan
    bar.line.fill.background()

    # ----------------- Content Slides -----------------
    for slide_info in slides_data:
        slide = prs.slides.add_slide(blank_layout)
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = bg_color
        bg.line.fill.background()

        # Slide Title
        stitle_box = slide.shapes.add_textbox(Inches(1.0), Inches(0.8), Inches(11.3), Inches(1.0))
        stf = stitle_box.text_frame
        stf.word_wrap = True
        sp = stf.paragraphs[0]
        sp.text = slide_info.get("title", "Key Takeaway")
        sp.font.name = "Arial"
        sp.font.size = Pt(28)
        sp.font.bold = True
        sp.font.color.rgb = c_white

        # Subtle separator
        sbar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.0), Inches(1.65), Inches(11.3), Inches(0.03))
        sbar.fill.solid()
        sbar.fill.fore_color.rgb = c_accent
        sbar.line.fill.background()

        # Content Box
        content_box = slide.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.3), Inches(4.8))
        ctf = content_box.text_frame
        ctf.word_wrap = True

        bullets = slide_info.get("bullets", [])
        if not bullets and "body" in slide_info:
            bullets = [b.strip("-*• ") for b in slide_info["body"].split("\n") if b.strip()]

        for i, b_text in enumerate(bullets[:6]):
            bp = ctf.add_paragraph() if i > 0 else ctf.paragraphs[0]
            bp.text = f"• {b_text}"
            bp.font.name = "Arial"
            bp.font.size = Pt(18)
            bp.font.color.rgb = c_slate
            bp.space_after = Pt(14)
            bp.line_spacing = 1.25

    prs.save(str(filepath))
    return filepath


# -----------------------------------------------------------------------------
# 3. Word Document Generation (python-docx)
# -----------------------------------------------------------------------------
def create_docx(title: str, sections: List[Dict[str, Any]], tables: Optional[List[List[Any]]] = None) -> Path:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT

    filename = clean_filename(title or "Document", "docx")
    filepath = DOWNLOADS_DIR / filename

    doc = Document()

    # Document Title
    p_title = doc.add_paragraph()
    run_title = p_title.add_run(title)
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(24)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(76, 29, 149)
    p_title.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # Metadata
    p_meta = doc.add_paragraph()
    run_meta = p_meta.add_run(f"Generated by Nova Voice AI Assistant • {datetime.now().strftime('%B %d, %Y')}")
    run_meta.font.name = "Calibri"
    run_meta.font.size = Pt(9.5)
    run_meta.font.color.rgb = RGBColor(100, 116, 139)
    p_meta.paragraph_format.space_after = Pt(16)

    # Content Sections
    for sec in sections:
        heading_text = sec.get("heading", "")
        if heading_text:
            h = doc.add_heading(level=1)
            hrun = h.add_run(heading_text)
            hrun.font.name = "Calibri"
            hrun.font.size = Pt(14)
            hrun.font.bold = True
            hrun.font.color.rgb = RGBColor(124, 58, 237)
            h.paragraph_format.space_before = Pt(12)
            h.paragraph_format.space_after = Pt(4)

        body_text = sec.get("body", "")
        if body_text:
            for line in body_text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith(("- ", "* ", "• ")):
                    clean_line = line.lstrip("-*• ").strip()
                    doc.add_paragraph(clean_line, style="List Bullet")
                else:
                    p = doc.add_paragraph(line)
                    p.paragraph_format.space_after = Pt(6)

        for b in sec.get("bullets", []):
            doc.add_paragraph(b, style="List Bullet")

    # Optional Table
    if tables and len(tables) > 1:
        doc.add_heading("Data Summary", level=1)
        row_count = len(tables)
        col_count = len(tables[0])
        table = doc.add_table(rows=row_count, cols=col_count)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Light Shading Accent 1"

        for r_idx, row in enumerate(tables):
            for c_idx, cell in enumerate(row):
                cell_p = table.cell(r_idx, c_idx).paragraphs[0]
                cell_p.text = str(cell)
                if r_idx == 0:
                    for run in cell_p.runs:
                        run.font.bold = True

    doc.save(str(filepath))
    return filepath


# -----------------------------------------------------------------------------
# 4. Excel Spreadsheet Generation (openpyxl / pandas)
# -----------------------------------------------------------------------------
def create_xlsx(title: str, headers: List[str], rows: List[List[Any]]) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    filename = clean_filename(title or "Spreadsheet", "xlsx")
    filepath = DOWNLOADS_DIR / filename

    wb = Workbook()
    ws = wb.active
    ws.title = (title[:25] or "Sheet1")
    ws.views.sheetView[0].showGridLines = True

    # Palette
    fill_title = PatternFill(start_color="3B0764", end_color="3B0764", fill_type="solid")
    fill_header = PatternFill(start_color="6D28D9", end_color="6D28D9", fill_type="solid")
    fill_alt = PatternFill(start_color="F5F3FF", end_color="F5F3FF", fill_type="solid")
    font_title = Font(name="Calibri", size=15, bold=True, color="FFFFFF")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_data = Font(name="Calibri", size=10, color="0F172A")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )

    num_cols = max(len(headers), 1)

    # 1. Title Banner (Row 1)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
    cell_top = ws.cell(row=1, column=1, value=title)
    cell_top.font = font_title
    cell_top.fill = fill_title
    cell_top.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    # 2. Header Row (Row 2)
    ws.row_dimensions[2].height = 24
    for c_idx, h in enumerate(headers, start=1):
        c = ws.cell(row=2, column=c_idx, value=str(h).strip())
        c.font = font_header
        c.fill = fill_header
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = thin_border

    # 3. Data Rows
    for r_idx, row in enumerate(rows, start=3):
        ws.row_dimensions[r_idx].height = 20
        is_even = (r_idx % 2 == 0)
        for c_idx, val in enumerate(row, start=1):
            c = ws.cell(row=r_idx, column=c_idx, value=val)
            c.font = font_data
            c.border = thin_border
            if is_even:
                c.fill = fill_alt
            # Auto format numbers
            if isinstance(val, (int, float)):
                c.alignment = Alignment(horizontal="right")
                if isinstance(val, float):
                    c.number_format = "#,##0.00"
                else:
                    c.number_format = "#,##0"
            else:
                c.alignment = Alignment(horizontal="left")

    # Auto-fit Column Widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    wb.save(str(filepath))
    return filepath


# -----------------------------------------------------------------------------
# 5. CSV Generation
# -----------------------------------------------------------------------------
def create_csv(title: str, headers: List[str], rows: List[List[Any]]) -> Path:
    filename = clean_filename(title or "Data_Export", "csv")
    filepath = DOWNLOADS_DIR / filename

    with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)

    return filepath


# -----------------------------------------------------------------------------
# Master Document Synthesis Orchestrator
# -----------------------------------------------------------------------------
def detect_document_intent(user_prompt: str) -> Optional[str]:
    """
    Detects if the user wants to generate a document and returns the format
    ('pdf', 'pptx', 'docx', 'xlsx', 'csv') or None.
    """
    p = user_prompt.lower()

    # Trigger verbs / intent signals
    triggers = [
        "create", "generate", "make", "build", "write", "download",
        "export", "draft", "prepare", "بناؤ", "تیار کرو", "ڈاؤنلوڈ"
    ]
    has_trigger = any(t in p for t in triggers)

    # Explicit format check
    if re.search(r"\b(pdf|پی ڈی ایف)\b", p):
        return "pdf"
    if re.search(r"\b(ppt|pptx|powerpoint|presentation|slides|سلائیڈز|پریزنٹیشن)\b", p):
        return "pptx"
    if re.search(r"\b(doc|docx|word document|word file|ورڈ|دستاویز)\b", p):
        return "docx"
    if re.search(r"\b(excel|xlsx|xls|spreadsheet|sheet|ایکسل|شیٹ)\b", p):
        return "xlsx"
    if re.search(r"\b(csv|سی ایس وی)\b", p):
        return "csv"

    # If trigger is strong but format not named explicitly, default to PDF
    if has_trigger and any(w in p for w in ["report", "proposal", "summary", "document", "رپورٹ"]):
        return "pdf"

    return None


def synthesize_document(doc_type: str, topic: str, content_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Coordinates document generation based on doc_type and parsed content.
    Returns metadata dict with file_url, file_name, file_type, file_size.
    """
    if not content_data:
        content_data = {}

    title = content_data.get("title") or topic or "Nova_AI_Report"
    sections = content_data.get("sections", [])
    tables = content_data.get("table", [])
    headers = content_data.get("headers", ["Item", "Category", "Metric", "Notes"])
    rows = content_data.get("rows", [
        ["Phase 1", "Planning", 100, "Initial deployment"],
        ["Phase 2", "Execution", 250, "Core milestones complete"],
        ["Phase 3", "Review", 380, "Final performance validated"]
    ])

    # Ensure sections has at least default content if empty
    if not sections:
        sections = [
            {
                "heading": "Executive Summary",
                "body": f"This document presents an automated analysis and structured breakdown for: {topic}. Prepared through the Nova Voice AI system."
            },
            {
                "heading": "Key Strategic Findings",
                "bullets": [
                    "High efficiency and streamlined architecture deployed successfully.",
                    "Measurable impact across core operational parameters.",
                    "Full compatibility maintained with enterprise integration standards."
                ]
            },
            {
                "heading": "Recommended Next Steps",
                "body": "Continue system monitoring and execute milestone deliverables as mapped in the project roadmap."
            }
        ]

    # Generate according to doc_type
    doc_type = doc_type.lower()
    filepath: Path

    if doc_type == "pdf":
        filepath = create_pdf(title, sections, tables)
    elif doc_type in ["pptx", "ppt"]:
        # Map sections to slide deck
        slides_data = []
        for s in sections:
            slides_data.append({
                "title": s.get("heading", "Insight"),
                "bullets": s.get("bullets", [s.get("body", "")])
            })
        filepath = create_pptx(title, slides_data)
        doc_type = "pptx"
    elif doc_type in ["docx", "doc"]:
        filepath = create_docx(title, sections, tables)
        doc_type = "docx"
    elif doc_type in ["xlsx", "excel"]:
        filepath = create_xlsx(title, headers, rows)
        doc_type = "xlsx"
    elif doc_type == "csv":
        filepath = create_csv(title, headers, rows)
        doc_type = "csv"
    else:
        filepath = create_pdf(title, sections, tables)
        doc_type = "pdf"

    file_size_bytes = filepath.stat().st_size if filepath.exists() else 0

    return {
        "file_url": f"/downloads/{filepath.name}",
        "file_name": filepath.name,
        "file_type": doc_type,
        "file_size": format_file_size(file_size_bytes),
        "file_path": str(filepath)
    }

