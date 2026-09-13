"""Render the 90-day memo Markdown into a compact, verified PDF."""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "memo_90_days.md"
OUTPUT = ROOT / "docs" / "memo_90_days.pdf"
NAVY = colors.HexColor("#01102B")
BLUE = colors.HexColor("#1C73E7")
SLATE = colors.HexColor("#41546A")
PALE = colors.HexColor("#E4EAF3")


def clean(text: str) -> str:
    text = text.replace("—", "-").replace("–", "-").replace("’", "'")
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    return text


class MemoDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=17 * mm,
            rightMargin=17 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
            title="My first 90 days as Lexroom's first Analytics Engineer",
            author="Candidate submission",
        )
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="main")
        self.addPageTemplates([PageTemplate(id="memo", frames=frame, onPage=self.decorate)])

    def decorate(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(PALE)
        canvas.line(doc.leftMargin, 12 * mm, A4[0] - doc.rightMargin, 12 * mm)
        canvas.setFillColor(SLATE)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(doc.leftMargin, 7.5 * mm, "Candidate case study | Unofficial")
        canvas.drawRightString(A4[0] - doc.rightMargin, 7.5 * mm, f"Page {doc.page}")
        canvas.restoreState()


def build_story() -> list:
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "Title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=21,
        leading=24, textColor=NAVY, alignment=TA_LEFT, spaceAfter=7 * mm,
    )
    heading = ParagraphStyle(
        "Heading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11.5,
        leading=13.5, textColor=BLUE, spaceBefore=3.5 * mm, spaceAfter=1.6 * mm,
        keepWithNext=True,
    )
    body = ParagraphStyle(
        "Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.7,
        leading=11.2, textColor=colors.HexColor("#1E293B"), spaceAfter=2.2 * mm,
    )
    story = []
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            story.append(Paragraph(clean(line[2:]), title))
        elif line.startswith("## "):
            if line.startswith("## Days 61-90"):
                story.append(PageBreak())
            story.append(Paragraph(clean(line[3:]), heading))
        else:
            story.append(Paragraph(clean(line), body))
    story.append(Spacer(1, 2 * mm))
    return story


if __name__ == "__main__":
    MemoDocTemplate(str(OUTPUT)).build(build_story())
    print(OUTPUT)
