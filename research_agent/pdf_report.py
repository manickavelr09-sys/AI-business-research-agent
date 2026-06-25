from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def build_research_pdf(report: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title="Business Research Report",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="FieldLabel",
            parent=styles["Normal"],
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#5c6b7a"),
            spaceAfter=1,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FieldValue",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=10.5,
            textColor=colors.HexColor("#1f2933"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["Normal"],
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#5c6b7a"),
        )
    )

    story: list[Any] = []
    summary = report.get("search_summary", {})
    story.append(Paragraph("Business Research Report", styles["Title"]))
    story.append(Paragraph(_safe(summary.get("query", "")), styles["Heading2"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(_summary_table(summary, report.get("data_quality_summary", {}), styles))
    story.append(Spacer(1, 0.2 * inch))
    research_summary = report.get("research_summary", {})
    if research_summary:
        story.extend(_research_summary_section(research_summary, styles))
        story.append(Spacer(1, 0.15 * inch))

    results = report.get("business_results", [])
    if not results:
        story.append(Paragraph("No businesses were returned for this report.", styles["Normal"]))
    for index, business in enumerate(results, start=1):
        if index > 1:
            story.append(Spacer(1, 0.12 * inch))
        story.extend(_business_section(index, business, styles))
        if index % 3 == 0 and index != len(results):
            story.append(PageBreak())

    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _summary_table(summary: dict[str, Any], quality: dict[str, Any], styles) -> Table:
    rows = [
        ["Businesses Found", _safe(summary.get("businesses_found", "")), "Verified", _safe(summary.get("businesses_verified", ""))],
        [
            "Duplicates Removed",
            _safe(summary.get("duplicate_records_removed", "")),
            "Sources Searched",
            _safe(summary.get("sources_searched", "")),
        ],
        ["Duration", _safe(summary.get("research_duration", "")), "Website Coverage", _safe(quality.get("records_with_website", ""))],
        ["Phone Coverage", _safe(quality.get("records_with_phone_number", "")), "Service Coverage", _safe(quality.get("records_with_services", ""))],
        ["Address Coverage", _safe(quality.get("records_with_address", "")), "License Coverage", _safe(quality.get("records_with_license_information", ""))],
    ]
    table = Table([[Paragraph(str(cell), styles["FieldValue"]) for cell in row] for row in rows], colWidths=[1.35 * inch, 1.55 * inch, 1.35 * inch, 1.55 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f7f9")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d6dde6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _research_summary_section(summary: dict[str, Any], styles) -> list[Any]:
    lines: list[Any] = [Paragraph("Research Summary", styles["Heading2"])]
    if summary.get("summary"):
        lines.append(Paragraph(_safe(summary["summary"]), styles["Normal"]))
    details = [
        ["RAG Evidence Chunks", _safe(summary.get("retrieved_evidence_chunks", "")), "LLM Used", "Yes" if summary.get("llm_used") else "No"],
        ["Source Strategy", _safe(", ".join(summary.get("source_strategy", [])[:8])), "Query", _safe(summary.get("query_understood_as", ""))],
    ]
    table = Table([[Paragraph(str(cell), styles["FieldValue"]) for cell in row] for row in details], colWidths=[1.35 * inch, 1.55 * inch, 1.35 * inch, 1.55 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f7f9")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d6dde6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    lines.append(Spacer(1, 0.08 * inch))
    lines.append(table)
    if summary.get("limitations"):
        lines.append(Spacer(1, 0.06 * inch))
        lines.append(Paragraph(f"Limitations: {_safe('; '.join(summary['limitations'][:4]))}", styles["Small"]))
    return lines


def _business_section(index: int, business: dict[str, Any], styles) -> list[Any]:
    verification = business.get("verification", {})
    conflicts = business.get("conflicts", {})
    name = business.get("business_name") or _verified_value(verification, "business_name") or "Unnamed business"
    section: list[Any] = [
        Paragraph(f"{index}. {_safe(name)}", styles["Heading3"]),
        _business_table(business, verification, conflicts, styles),
    ]
    sources = _source_lines(business.get("source_urls", {}))
    if sources:
        section.append(Spacer(1, 0.05 * inch))
        section.append(Paragraph(f"Sources: {_safe(sources)}", styles["Small"]))
    return section


def _business_table(
    business: dict[str, Any],
    verification: dict[str, Any],
    conflicts: dict[str, Any],
    styles,
) -> Table:
    field_pairs = [
        ("Address", "address"),
        ("Phone", "phone"),
        ("Email", "email"),
        ("Website", "website"),
        ("Hours", "working_hours"),
        ("Rating", "rating"),
        ("Reviews", "review_count"),
        ("License", "license_information"),
        ("Services", "services"),
        ("Specialties", "specialties"),
        ("Certifications", "certifications"),
        ("Awards", "awards"),
    ]
    rows = []
    for label, key in field_pairs:
        value = _verified_value(verification, key)
        if value in ("", None, []):
            value = business.get(key, "")
        if value in ("", None, []):
            continue
        level = verification.get(key, {}).get("verified_level", "unverified") if isinstance(verification.get(key), dict) else "unverified"
        conflict_note = " - conflict flagged" if key in conflicts else ""
        rows.append(
            [
                Paragraph(f"{label}<br/><font color='#5c6b7a'>{level}{conflict_note}</font>", styles["FieldLabel"]),
                Paragraph(_safe(_display(value)), styles["FieldValue"]),
            ]
        )
    if not rows:
        rows = [[Paragraph("Record", styles["FieldLabel"]), Paragraph("No structured fields extracted.", styles["FieldValue"])]]
    table = Table(rows, colWidths=[1.45 * inch, 5.0 * inch])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d6dde6")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f4f7f9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _source_lines(source_urls: dict[str, list[str]]) -> str:
    lines = []
    for field_name, urls in sorted(source_urls.items()):
        if urls:
            lines.append(f"{field_name}: {', '.join(urls[:3])}")
    return " | ".join(lines[:8])


def _verified_value(verification: dict[str, Any], field_name: str) -> Any:
    value = verification.get(field_name)
    if isinstance(value, dict):
        return value.get("value")
    return None


def _display(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item)
    return str(value)


def _safe(value: Any) -> str:
    text = _display(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\x00", "")
    )


def _footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#5c6b7a"))
    canvas.drawRightString(7.95 * inch, 0.32 * inch, f"Page {document.page}")
    canvas.drawString(0.55 * inch, 0.32 * inch, "Generated by AI Business Research Agent")
    canvas.restoreState()
