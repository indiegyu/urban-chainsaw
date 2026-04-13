"""
AI Side Hustle Starter Kit — PDF Generator
==========================================
Converts products/ai-side-hustle-starter-kit.md to a PDF ebook
using the fpdf2 library.

Usage:
    pip install fpdf2
    python scripts/gen_ebook_pdf.py
"""

from pathlib import Path
from fpdf import FPDF
import re


INPUT_MD  = Path(__file__).parent.parent / "products" / "ai-side-hustle-starter-kit.md"
OUTPUT_PDF = Path(__file__).parent.parent / "products" / "ai-side-hustle-starter-kit.pdf"


class EbookPDF(FPDF):
    def header(self):
        # Only show on non-cover pages
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 8, "AI Side Hustle Starter Kit 2026", align="L")
            self.ln(2)

    def footer(self):
        if self.page_no() > 1:
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 8, f"Page {self.page_no() - 1}", align="C")


def sanitize(text: str) -> str:
    """Replace non-latin-1 characters with safe ASCII equivalents."""
    replacements = {
        '\u2014': '--',   # em dash
        '\u2013': '-',    # en dash
        '\u2019': "'",    # right single quotation
        '\u2018': "'",    # left single quotation
        '\u201c': '"',    # left double quotation
        '\u201d': '"',    # right double quotation
        '\u2026': '...',  # ellipsis
        '\u2022': '*',    # bullet
        '\u00a0': ' ',    # non-breaking space
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    # Final fallback: encode to latin-1, replacing errors
    return text.encode('latin-1', errors='replace').decode('latin-1')


def strip_markdown_inline(text: str) -> str:
    """Remove inline markdown formatting (bold, italic, links, code)."""
    # Remove links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove bold **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    # Remove italic *text* or _text_
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    # Remove inline code `text`
    text = re.sub(r'`([^`]+)`', r'\1', text)
    return sanitize(text)


def render_cover(pdf: FPDF):
    pdf.add_page()
    # Dark background
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 297, "F")

    # Accent strip
    pdf.set_fill_color(99, 102, 241)
    pdf.rect(0, 115, 210, 6, "F")

    # Main title
    pdf.set_y(60)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(255, 255, 255)
    pdf.multi_cell(0, 12, "AI Side Hustle\nStarter Kit", align="C")

    # Year / subtitle
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(165, 180, 252)
    pdf.cell(0, 10, "2026 Edition", align="C")
    pdf.ln(30)

    # Description
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(148, 163, 184)
    pdf.multi_cell(0, 7,
        "The Complete Guide to Building AI-Powered Side Income",
        align="C")

    # Author / publisher
    pdf.set_y(240)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 8, "Published 2026 · AI Income Daily", align="C")


def render_toc(pdf: FPDF, toc_lines: list):
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(15, 23, 42)
    pdf.ln(4)
    pdf.cell(0, 12, "Table of Contents", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(99, 102, 241)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(51, 65, 85)
    for line in toc_lines:
        text = strip_markdown_inline(line.lstrip("1234567890. "))
        pdf.cell(0, 9, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)


def write_paragraph(pdf: FPDF, text: str):
    """Write a body paragraph, handling inline bold manually."""
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    # Split on bold markers
    segments = re.split(r'(\*\*[^*]+\*\*)', text)
    x_start = pdf.get_x()
    line_height = 6

    for seg in segments:
        bold_match = re.match(r'\*\*(.+?)\*\*', seg)
        if bold_match:
            pdf.set_font("Helvetica", "B", 10)
            content = bold_match.group(1)
        else:
            pdf.set_font("Helvetica", "", 10)
            content = seg

        # Strip remaining inline markdown
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
        content = re.sub(r'`([^`]+)`', r'\1', content)
        content = re.sub(r'_(.+?)_', r'\1', content)

        if content:
            pdf.write(line_height, sanitize(content))

    pdf.ln(line_height + 2)


def main():
    if not INPUT_MD.exists():
        print(f"ERROR: Input file not found: {INPUT_MD}")
        return False

    content = INPUT_MD.read_text(encoding="utf-8")
    lines = content.splitlines()

    pdf = EbookPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(20, 20, 20)

    # --- Cover ---
    render_cover(pdf)

    # --- Parse and collect TOC lines ---
    toc_lines = []
    for line in lines:
        if re.match(r'^\d+\.', line.strip()):
            toc_lines.append(line.strip())

    render_toc(pdf, toc_lines)

    # --- Body content ---
    pdf.add_page()
    in_table = False
    table_rows = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip the very first H1 / subtitle block (already on cover)
        if line.startswith("# ") and i == 0:
            i += 1
            continue
        if line.startswith("**The Complete Guide"):
            i += 1
            continue
        if line.startswith("*Published"):
            i += 1
            continue
        if line.strip() == "---":
            # Horizontal rule
            pdf.set_draw_color(226, 232, 240)
            pdf.set_line_width(0.3)
            pdf.line(20, pdf.get_y() + 3, 190, pdf.get_y() + 3)
            pdf.ln(6)
            i += 1
            continue

        # Table of contents block — skip (already rendered)
        if line.startswith("## Table of Contents"):
            while i < len(lines) and not lines[i].strip() == "---":
                i += 1
            i += 1
            continue

        # Table rows
        if line.strip().startswith("|"):
            if not in_table:
                in_table = True
                table_rows = []
            # Skip separator rows
            if re.match(r'^\|[\s\-\|]+\|', line.strip()):
                i += 1
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            table_rows.append(cells)
            i += 1
            # Check if next line is still a table row
            if i >= len(lines) or not lines[i].strip().startswith("|"):
                # Render table
                in_table = False
                col_w = [55, 55, 25, 40]
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_fill_color(241, 245, 249)
                pdf.set_text_color(15, 23, 42)
                for j, row in enumerate(table_rows):
                    font_style = "B" if j == 0 else ""
                    pdf.set_font("Helvetica", font_style, 8)
                    fill = j == 0
                    for k, cell in enumerate(row[:4]):
                        w = col_w[k] if k < len(col_w) else 30
                        txt = strip_markdown_inline(cell)
                        pdf.cell(w, 6, txt[:40], border=1, fill=fill)
                    pdf.ln()
                pdf.ln(4)
                table_rows = []
            continue

        # Heading levels
        if line.startswith("## "):
            pdf.add_page()
            text = strip_markdown_inline(line[3:])
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(30, 58, 95)
            pdf.multi_cell(0, 10, text)
            pdf.set_draw_color(99, 102, 241)
            pdf.set_line_width(0.6)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(6)
            i += 1
            continue

        if line.startswith("### "):
            text = strip_markdown_inline(line[4:])
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(15, 23, 42)
            pdf.multi_cell(0, 8, text)
            pdf.ln(2)
            i += 1
            continue

        # Bullet / list items
        if re.match(r'^[-*] ', line) or re.match(r'^\d+\. ', line) or re.match(r'^- \[', line):
            # Checkbox items
            if re.match(r'^- \[', line):
                marker = "[ ]" if "[ ]" in line else "[x]"
                text = re.sub(r'^- \[.\] ', '', line)
            elif re.match(r'^[-*] ', line):
                marker = "-"
                text = line[2:]
            else:
                m = re.match(r'^(\d+)\. (.*)', line)
                marker = f"{m.group(1)}."
                text = m.group(2)

            text = strip_markdown_inline(text)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(51, 65, 85)
            # Indent
            pdf.set_x(25)
            pdf.cell(8, 6, marker)
            pdf.set_x(33)
            pdf.multi_cell(157, 6, text)
            i += 1
            continue

        # Blockquote (prompt examples)
        if line.startswith("> "):
            text = strip_markdown_inline(line[2:])
            pdf.set_fill_color(240, 244, 255)
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(79, 70, 229)
            pdf.set_x(22)
            pdf.multi_cell(166, 6, text, fill=True)
            pdf.ln(2)
            i += 1
            continue

        # Empty lines
        if line.strip() == "":
            pdf.ln(3)
            i += 1
            continue

        # Regular paragraph text
        text = line.strip()
        if text:
            write_paragraph(pdf, text)
        i += 1

    # Save PDF
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT_PDF))
    size_kb = OUTPUT_PDF.stat().st_size / 1024
    print(f"PDF generated: {OUTPUT_PDF}")
    print(f"File size: {size_kb:.1f} KB")
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
