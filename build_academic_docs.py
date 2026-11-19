import os
import re
import sys
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Preformatted
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('Cambria', r'C:\Windows\Fonts\cambria.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('Cambria-Bold', r'C:\Windows\Fonts\cambriab.ttf'))
pdfmetrics.registerFont(TTFont('Cambria-Italic', r'C:\Windows\Fonts\cambriai.ttf'))
pdfmetrics.registerFont(TTFont('Cambria-BoldItalic', r'C:\Windows\Fonts\cambriaz.ttf'))

DOCS_DIR = r'E:\Janmitra\JanMitra_Assist_Final_Submission\Documentation'

def clean_md_text(text):
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = text.replace('**', '').replace('__', '').replace('*', '').replace('`', '')
    return text.strip()

def markdown_to_docx(md_path, docx_path, title):
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    styles = doc.styles
    normal_style = styles['Normal']
    normal_style.font.name = 'Cambria'
    normal_style.font.size = Pt(10)
    normal_style.font.color.rgb = RGBColor(30, 41, 59)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run(title)
    run_title.font.name = 'Cambria'
    run_title.font.size = Pt(16)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(15, 23, 42)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Master of Computer Applications (MCA) Major Project\nJanMitra Assist System Documentation")
    r_sub.font.name = 'Cambria'
    r_sub.font.size = Pt(10)
    r_sub.font.italic = True
    r_sub.font.color.rgb = RGBColor(71, 85, 105)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_code_block = False
    code_block_lines = []
    in_table = False
    table_rows = []

    for line in lines:
        line_strip = line.strip()

        if line_strip.startswith('```'):
            if in_code_block:
                if code_block_lines:
                    text_block = "\n".join(code_block_lines)
                    p_code = doc.add_paragraph()
                    p_code.paragraph_format.space_before = Pt(4)
                    p_code.paragraph_format.space_after = Pt(6)
                    r_code = p_code.add_run(text_block)
                    r_code.font.name = 'Consolas'
                    r_code.font.size = Pt(7.5)
                    r_code.font.color.rgb = RGBColor(30, 41, 59)
                code_block_lines = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_block_lines.append(line.rstrip())
            continue

        if line_strip.startswith('|') and line_strip.endswith('|'):
            if '---' in line_strip:
                continue
            cols = [clean_md_text(c) for c in line_strip.split('|')[1:-1]]
            table_rows.append(cols)
            in_table = True
            continue
        else:
            if in_table and table_rows:
                col_count = max(len(r) for r in table_rows)
                t = doc.add_table(rows=len(table_rows), cols=col_count)
                t.style = 'Table Grid'
                for r_idx, row_data in enumerate(table_rows):
                    for c_idx, cell_data in enumerate(row_data):
                        if c_idx < col_count:
                            cell = t.cell(r_idx, c_idx)
                            cell.text = cell_data
                            p = cell.paragraphs[0]
                            p.paragraph_format.space_before = Pt(2)
                            p.paragraph_format.space_after = Pt(2)
                            for r in p.runs:
                                r.font.name = 'Cambria'
                                r.font.size = Pt(9)
                                if r_idx == 0:
                                    r.font.bold = True
                doc.add_paragraph()
                table_rows = []
                in_table = False

        if not line_strip:
            continue

        if line_strip.startswith('# ') or line_strip.startswith('## '):
            h_text = clean_md_text(line_strip.lstrip('#').strip())
            h = doc.add_paragraph()
            h.paragraph_format.space_before = Pt(14)
            h.paragraph_format.space_after = Pt(4)
            h.paragraph_format.keep_with_next = True
            r = h.add_run(h_text)
            r.font.name = 'Cambria'
            r.font.size = Pt(12)
            r.font.bold = True
            r.font.color.rgb = RGBColor(30, 58, 138)
        elif line_strip.startswith('### ') or line_strip.startswith('#### '):
            h_text = clean_md_text(line_strip.lstrip('#').strip())
            h = doc.add_paragraph()
            h.paragraph_format.space_before = Pt(8)
            h.paragraph_format.space_after = Pt(2)
            h.paragraph_format.keep_with_next = True
            r = h.add_run(h_text)
            r.font.name = 'Cambria'
            r.font.size = Pt(10)
            r.font.bold = True
            r.font.color.rgb = RGBColor(51, 65, 85)
        elif line_strip.startswith('- ') or line_strip.startswith('* ') or re.match(r'^\d+\.\s', line_strip):
            p = doc.add_paragraph(style='List Bullet' if not re.match(r'^\d+\.\s', line_strip) else 'List Number')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            content = re.sub(r'^[-*]\s+|\d+\.\s+', '', line_strip)
            r = p.add_run(clean_md_text(content))
            r.font.name = 'Cambria'
            r.font.size = Pt(10)
        else:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.15
            r = p.add_run(clean_md_text(line_strip))
            r.font.name = 'Cambria'
            r.font.size = Pt(10)

    doc.save(docx_path)
    print(f"[DOCX] Generated: {docx_path} ({os.path.getsize(docx_path):,} bytes)")

def markdown_to_pdf(md_path, pdf_path, title):
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    style_title = ParagraphStyle(
        'DocTitle',
        fontName='Cambria-Bold',
        fontSize=16,
        leading=20,
        alignment=1,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=6
    )
    style_subtitle = ParagraphStyle(
        'DocSubtitle',
        fontName='Cambria-Italic',
        fontSize=10,
        leading=13,
        alignment=1,
        textColor=colors.HexColor('#475569'),
        spaceAfter=12
    )
    style_h1 = ParagraphStyle(
        'DocH1',
        fontName='Cambria-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=12,
        spaceAfter=4,
        keepWithNext=True
    )
    style_h2 = ParagraphStyle(
        'DocH2',
        fontName='Cambria-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#334155'),
        spaceBefore=8,
        spaceAfter=2,
        keepWithNext=True
    )
    style_body = ParagraphStyle(
        'DocBody',
        fontName='Cambria',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=2,
        spaceAfter=3
    )
    style_bullet = ParagraphStyle(
        'DocBullet',
        fontName='Cambria',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#1e293b'),
        leftIndent=15,
        spaceBefore=1,
        spaceAfter=1
    )
    style_table_header = ParagraphStyle(
        'DocTH',
        fontName='Cambria-Bold',
        fontSize=8.5,
        leading=10,
        textColor=colors.white
    )
    style_table_cell = ParagraphStyle(
        'DocTD',
        fontName='Cambria',
        fontSize=8.5,
        leading=10.5,
        textColor=colors.HexColor('#1e293b')
    )
    style_code = ParagraphStyle(
        'DocCode',
        fontName='Courier',
        fontSize=6.5,
        leading=8,
        textColor=colors.HexColor('#0f172a'),
        backColor=colors.HexColor('#f1f5f9'),
        borderPadding=3,
        spaceBefore=2,
        spaceAfter=2
    )

    story = [
        Paragraph(title, style_title),
        Paragraph("Master of Computer Applications (MCA) Major Project | JanMitra Assist", style_subtitle),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceAfter=10)
    ]

    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_code_block = False
    code_block_lines = []
    in_table = False
    table_rows = []

    for line in lines:
        line_strip = line.strip()

        if line_strip.startswith('```'):
            if in_code_block:
                if code_block_lines:
                    # Split code block into chunks of 25 lines so it can break cleanly across pages
                    chunk_size = 25
                    for i in range(0, len(code_block_lines), chunk_size):
                        chunk = "\n".join(code_block_lines[i:i+chunk_size])
                        story.append(Preformatted(chunk, style_code))
                        story.append(Spacer(1, 2))
                code_block_lines = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_block_lines.append(line.rstrip())
            continue

        if line_strip.startswith('|') and line_strip.endswith('|'):
            if '---' in line_strip:
                continue
            cols = [clean_md_text(c) for c in line_strip.split('|')[1:-1]]
            table_rows.append(cols)
            in_table = True
            continue
        else:
            if in_table and table_rows:
                col_count = max(len(r) for r in table_rows)
                flowable_table_data = []
                for r_idx, row in enumerate(table_rows):
                    row_cells = []
                    for c_idx, cell_str in enumerate(row):
                        st = style_table_header if r_idx == 0 else style_table_cell
                        cell_str_clean = cell_str[:100] + '...' if len(cell_str) > 100 else cell_str
                        row_cells.append(Paragraph(cell_str_clean, st))
                    while len(row_cells) < col_count:
                        row_cells.append(Paragraph("", style_table_cell))
                    flowable_table_data.append(row_cells)

                available_width = 532
                col_w = available_width / col_count
                t = Table(flowable_table_data, colWidths=[col_w]*col_count)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                    ('TOPPADDING', (0,0), (-1,-1), 3),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
                ]))
                story.append(Spacer(1, 4))
                story.append(t)
                story.append(Spacer(1, 6))
                table_rows = []
                in_table = False

        if not line_strip:
            continue

        if line_strip.startswith('# ') or line_strip.startswith('## '):
            h_text = clean_md_text(line_strip.lstrip('#').strip())
            story.append(Paragraph(h_text, style_h1))
        elif line_strip.startswith('### ') or line_strip.startswith('#### '):
            h_text = clean_md_text(line_strip.lstrip('#').strip())
            story.append(Paragraph(h_text, style_h2))
        elif line_strip.startswith('- ') or line_strip.startswith('* ') or re.match(r'^\d+\.\s', line_strip):
            content = re.sub(r'^[-*]\s+|\d+\.\s+', '', line_strip)
            story.append(Paragraph(f"• {clean_md_text(content)}", style_bullet))
        else:
            story.append(Paragraph(clean_md_text(line_strip), style_body))

    doc.build(story)
    print(f"[PDF] Generated: {pdf_path} ({os.path.getsize(pdf_path):,} bytes)")

targets = [
    {
        'md': os.path.join(DOCS_DIR, 'Project_Report.md'),
        'title': 'JanMitra Assist — Comprehensive MCA Major Project Report',
        'docx': os.path.join(DOCS_DIR, 'Project_Report.docx'),
        'pdf': os.path.join(DOCS_DIR, 'Project_Report.pdf')
    },
    {
        'md': os.path.join(DOCS_DIR, 'SRS.md'),
        'title': 'JanMitra Assist — Software Requirements Specification (SRS)',
        'docx': os.path.join(DOCS_DIR, 'SRS.docx'),
        'pdf': os.path.join(DOCS_DIR, 'SRS.pdf')
    },
    {
        'md': os.path.join(DOCS_DIR, 'Citizen_User_Manual.md'),
        'title': 'JanMitra Assist — Citizen User Manual',
        'docx': os.path.join(DOCS_DIR, 'Citizen_User_Manual.docx'),
        'pdf': os.path.join(DOCS_DIR, 'Citizen_User_Manual.pdf')
    },
    {
        'md': os.path.join(DOCS_DIR, 'Admin_User_Manual.md'),
        'title': 'JanMitra Assist — Admin Governance User Manual',
        'docx': os.path.join(DOCS_DIR, 'Admin_User_Manual.docx'),
        'pdf': os.path.join(DOCS_DIR, 'Admin_User_Manual.pdf')
    },
    {
        'md': os.path.join(DOCS_DIR, 'API_Documentation', 'JanMitra_API_Specification.md'),
        'title': 'JanMitra Assist — RESTful API Specification (OpenAPI 3.0)',
        'docx': os.path.join(DOCS_DIR, 'API_Documentation', 'JanMitra_API_Specification.docx'),
        'pdf': os.path.join(DOCS_DIR, 'API_Documentation', 'JanMitra_API_Specification.pdf')
    },
    {
        'md': os.path.join(DOCS_DIR, 'Architecture_Diagrams', 'System_Diagrams.md'),
        'title': 'JanMitra Assist — System Architecture & UML Specifications',
        'docx': os.path.join(DOCS_DIR, 'Architecture_Diagrams', 'System_Diagrams.docx'),
        'pdf': os.path.join(DOCS_DIR, 'Architecture_Diagrams', 'System_Diagrams.pdf')
    }
]

for t in targets:
    if os.path.exists(t['md']):
        print(f"Processing {t['md']}...")
        markdown_to_docx(t['md'], t['docx'], t['title'])
        markdown_to_pdf(t['md'], t['pdf'], t['title'])

print("All academic documents re-generated successfully with rendered diagram blocks!")
