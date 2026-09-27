#!/usr/bin/env python
"""Builds the document fixtures the upload tests use.

Run from `apps/api`:  uv run python tests/fixtures/make_fixtures.py

Generated rather than committed as binaries so the content is reviewable in the
diff and obviously invented. Nobody's real resume belongs in a test fixture.
"""

from pathlib import Path

HERE = Path(__file__).parent

RESUME_TEXT = [
    "Example Person",
    "Software Engineer",
    "",
    "Software Engineer, Example Corp",
    "April 2021 to March 2024",
    "Built and maintained internal services used across the company.",
    "",
    "Junior Developer, Sample Industries",
    "June 2018 to March 2021",
    "Worked on the billing system and its reporting tools.",
    "",
    "Skills: Ruby, PostgreSQL, TypeScript",
    "Languages: English (native), Japanese (business)",
]

JAPANESE_RESUME = [
    "職務経歴書",
    "",
    "職務要約",
    "サンプル株式会社にて、社内システムの開発と保守を担当しました。",
    "",
    "職務経歴",
    "エンジニア、サンプル株式会社",
    "令和3年4月から令和6年3月まで",
    "社内向けサービスの開発および保守を担当。",
    "",
    "スキル：Ruby、PostgreSQL、TypeScript",
]


def write_pdf(path: Path, lines: list[str]) -> None:
    import io

    from pypdf import PdfWriter
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4)
    y = 780
    for line in lines:
        page.drawString(60, y, line)
        y -= 18
    page.save()

    writer = PdfWriter(clone_from=io.BytesIO(buffer.getvalue()))
    with path.open("wb") as handle:
        writer.write(handle)


def write_docx(path: Path, lines: list[str]) -> None:
    import docx

    document = docx.Document()
    for line in lines:
        document.add_paragraph(line)
    document.save(path)


def write_scanned_pdf(path: Path) -> None:
    """A PDF with no text layer, as a scan or photograph produces."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    page = canvas.Canvas(str(path), pagesize=A4)
    # Shapes only. No drawString, so nothing is extractable.
    page.rect(60, 600, 480, 160, fill=0)
    page.line(60, 560, 540, 560)
    page.save()


if __name__ == "__main__":
    write_pdf(HERE / "example-resume.pdf", RESUME_TEXT)
    write_docx(HERE / "example-resume.docx", RESUME_TEXT)
    write_docx(HERE / "example-resume-ja.docx", JAPANESE_RESUME)
    write_scanned_pdf(HERE / "scanned-no-text.pdf")
    print("fixtures written to", HERE)
