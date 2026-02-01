"""
PDF Markdown Renderer (ReportLab)
--------------------------------
Converts *lightweight markdown-ish* LLM output into ReportLab flowables.

Why:
- LLM sections sometimes include markdown headers like `# Introduction`, `## Subsection`.
- The PDF generator already adds section headings, so those become duplicated in the PDF.
- Raw `#` markers look unprofessional; we want clean headings and paragraphs.

Scope (intentionally small + robust):
- Headings: `#`, `##`, `###` → rendered as heading/subheading flowables
- Paragraphs: blank-line separated blocks → rendered as body paragraphs
- Code fences: ``` ... ``` → rendered as code blocks (via formatter callback)
- Bullet lines: `- item` / `* item` → rendered as bulleted paragraphs

This is *not* a full markdown implementation; it is a pragmatic renderer for
LLM-generated scientific prose in this application.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Sequence

from reportlab.platypus import Paragraph, Spacer


@dataclass(frozen=True)
class _Block:
    kind: str  # 'heading' | 'paragraph' | 'code' | 'bullet'
    level: int = 0
    text: str = ""


class PDFMarkdownRenderer:
    def __init__(
        self,
        *,
        styles,
        clean_text_for_pdf: Callable[[str], str],
        format_code_for_pdf: Callable[[str], str],
    ):
        self._styles = styles
        self._clean = clean_text_for_pdf
        self._format_code = format_code_for_pdf

    def render(
        self,
        markdown_text: str,
        *,
        skip_first_heading: Optional[str] = None,
        body_style_name: str = "ScientificBody",
        heading_style_name: str = "SubsectionHeading",
        subheading_style_name: str = "SubsectionHeading",
        spacer_after_paragraph: float = 6,
        spacer_after_heading: float = 4,
    ) -> List:
        """
        Convert markdown-ish text into a list of ReportLab flowables.

        Args:
            markdown_text: Text that may contain markdown headers/bullets/code fences.
            skip_first_heading: If the first heading matches this (case-insensitive),
                                it will be dropped (prevents duplicate section titles).
            body_style_name: Paragraph style name for body text.
            heading_style_name: Style for top-level headings inside a section.
            subheading_style_name: Style for deeper headings.
        """
        blocks = list(self._parse_blocks(markdown_text or "", skip_first_heading=skip_first_heading))
        flowables: List = []

        for block in blocks:
            if block.kind == "heading":
                style = self._styles[heading_style_name] if block.level <= 2 else self._styles[subheading_style_name]
                flowables.append(Paragraph(self._clean(block.text), style))
                flowables.append(Spacer(1, spacer_after_heading))
                continue

            if block.kind == "code":
                flowables.append(Paragraph(self._format_code(block.text), self._styles["CodeBlock"]))
                flowables.append(Spacer(1, spacer_after_paragraph))
                continue

            if block.kind == "bullet":
                # Keep bullets simple and robust (avoid Paragraph bulletText edge cases).
                bullet_text = f"• {block.text}"
                flowables.append(Paragraph(self._clean(bullet_text), self._styles[body_style_name]))
                flowables.append(Spacer(1, spacer_after_paragraph))
                continue

            if block.kind == "paragraph":
                flowables.append(Paragraph(self._clean(block.text), self._styles[body_style_name]))
                flowables.append(Spacer(1, spacer_after_paragraph))
                continue

        # Trim trailing spacer if present
        if flowables and isinstance(flowables[-1], Spacer):
            flowables.pop()

        return flowables

    # -------------------------
    # Parsing
    # -------------------------

    def _parse_blocks(self, text: str, *, skip_first_heading: Optional[str]) -> Iterable[_Block]:
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

        in_code = False
        code_lines: List[str] = []
        para_lines: List[str] = []

        first_heading_skipped = False
        skip_norm = (skip_first_heading or "").strip().lower()

        def flush_paragraph():
            nonlocal para_lines
            paragraph = " ".join(s.strip() for s in para_lines if s.strip()).strip()
            para_lines = []
            if paragraph:
                yield _Block(kind="paragraph", text=paragraph)

        def flush_code():
            nonlocal code_lines
            code = "\n".join(code_lines).rstrip("\n")
            code_lines = []
            if code.strip():
                yield _Block(kind="code", text=code)

        for raw in lines:
            line = raw.rstrip("\n")

            # Code fences
            if line.strip().startswith("```"):
                if in_code:
                    # closing fence
                    in_code = False
                    yield from flush_code()
                else:
                    # opening fence
                    yield from flush_paragraph()
                    in_code = True
                continue

            if in_code:
                code_lines.append(line)
                continue

            stripped = line.strip()
            if not stripped:
                yield from flush_paragraph()
                continue

            # Headings
            if stripped.startswith("#"):
                yield from flush_paragraph()
                level = len(stripped) - len(stripped.lstrip("#"))
                heading_text = stripped.lstrip("#").strip()
                # Handle pathological "### # Title" patterns (double-marked)
                while heading_text.startswith("#"):
                    heading_text = heading_text.lstrip("#").strip()

                # Skip redundant section title heading (usually first line)
                if skip_norm and not first_heading_skipped and heading_text.lower() == skip_norm:
                    first_heading_skipped = True
                    continue

                yield _Block(kind="heading", level=level, text=heading_text)
                continue

            # Bullet lines
            bullet_match = re.match(r"^[-*]\s+(.*)$", stripped)
            if bullet_match:
                yield from flush_paragraph()
                item = bullet_match.group(1).strip()
                if item:
                    yield _Block(kind="bullet", text=item)
                continue

            # Normal paragraph line
            para_lines.append(stripped)

        # Final flush
        yield from flush_paragraph()
        if in_code:
            yield from flush_code()

