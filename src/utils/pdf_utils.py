from io import BytesIO
from pathlib import Path
from markdown_pdf import MarkdownPdf, Section


def md_to_pdf_bytes(markdown_path: Path | str) -> bytes:
    """
    Convert a Markdown file to PDF bytes using the markdown-pdf library.

    - toc_level=2 to include H1/H2 in bookmarks
    - optimize=True for smaller PDFs
    - No header/footer or special fonts by request
    """
    markdown_path = Path(markdown_path)
    if not markdown_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {markdown_path}")

    text = markdown_path.read_text(encoding="utf-8", errors="ignore")

    pdf = MarkdownPdf(toc_level=3)
    # Basic table borders for readability; keep styling minimal
    user_css = "table, th, td {border: 1px solid #aaa; border-collapse: collapse;} th, td {padding: 4px;}"
    pdf.add_section(Section(text), user_css=user_css)

    out = BytesIO()
    pdf.save_bytes(out)
    return out.getvalue()