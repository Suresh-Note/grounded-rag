from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger("aegis.report")

PAGE_MARGIN = 36
CONTENT_WIDTH = 540  # 612 - 36 - 36 (Full width printable grid)

# --- Executive Color Palette ---
DARK_NAVY = colors.HexColor("#0B132B")
SLATE_HEADER = colors.HexColor("#1C2541")
ACCENT_INDIGO = colors.HexColor("#4361EE")
ACCENT_BLUE = colors.HexColor("#3A86FF")
TEXT_CHARCOAL = colors.HexColor("#2B2D42")
MUTED_SLATE = colors.HexColor("#8D99AE")
BG_CARD = colors.HexColor("#F8FAFC")
BORDER_CARD = colors.HexColor("#E2E8F0")

STATUS_RED_BG = colors.HexColor("#FFE5E5")
STATUS_RED_TEXT = colors.HexColor("#D90429")

STATUS_GREEN_BG = colors.HexColor("#E8F5E9")
STATUS_GREEN_TEXT = colors.HexColor("#2E7D32")

STATUS_AMBER_BG = colors.HexColor("#FEF3C7")
STATUS_AMBER_TEXT = colors.HexColor("#92400E")


def sanitize_for_reportlab(text: str) -> str:
    if not text:
        return ""
    text = str(text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*([\s\S]*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*([\s\S]*?)\*", r"<i>\1</i>", text)
    return text


def _build_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["DocTitle"] = ParagraphStyle(
        "DocTitle", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=20, leading=24, textColor=DARK_NAVY, spaceAfter=2
    )
    styles["DocSubtitle"] = ParagraphStyle(
        "DocSubtitle", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=8.5, leading=12, textColor=ACCENT_INDIGO
    )
    styles["MetaLabel"] = ParagraphStyle(
        "MetaLabel", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=7.5, leading=10, textColor=MUTED_SLATE, alignment=TA_RIGHT
    )
    styles["MetaValue"] = ParagraphStyle(
        "MetaValue", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=8.5, leading=11, textColor=DARK_NAVY, alignment=TA_RIGHT
    )
    styles["SectionHeader"] = ParagraphStyle(
        "SectionHeader", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=12, leading=16, textColor=DARK_NAVY, spaceBefore=10, spaceAfter=4
    )
    styles["CardTitle"] = ParagraphStyle(
        "CardTitle", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=10, leading=14, textColor=DARK_NAVY
    )
    styles["CardBody"] = ParagraphStyle(
        "CardBody", parent=base["Normal"], fontName="Helvetica",
        fontSize=9, leading=14, textColor=TEXT_CHARCOAL
    )
    styles["CardCitation"] = ParagraphStyle(
        "CardCitation", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=8, leading=11, textColor=ACCENT_INDIGO
    )
    styles["CardQuote"] = ParagraphStyle(
        "CardQuote", parent=base["Normal"], fontName="Helvetica-Oblique",
        fontSize=8.5, leading=12, textColor=TEXT_CHARCOAL, leftIndent=8
    )
    styles["BadgeRed"] = ParagraphStyle(
        "BadgeRed", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=8, leading=10, textColor=STATUS_RED_TEXT, alignment=TA_CENTER
    )
    styles["BadgeGreen"] = ParagraphStyle(
        "BadgeGreen", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=8, leading=10, textColor=STATUS_GREEN_TEXT, alignment=TA_CENTER
    )
    styles["BadgeAmber"] = ParagraphStyle(
        "BadgeAmber", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=8, leading=10, textColor=STATUS_AMBER_TEXT, alignment=TA_CENTER
    )
    styles["TelemetryHeader"] = ParagraphStyle(
        "TelemetryHeader", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=9, leading=12, textColor=DARK_NAVY
    )
    styles["TelemetryBody"] = ParagraphStyle(
        "TelemetryBody", parent=base["Normal"], fontName="Helvetica",
        fontSize=8.5, leading=13, textColor=TEXT_CHARCOAL
    )
    return styles


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(BORDER_CARD)
    canvas.setLineWidth(0.5)
    canvas.line(PAGE_MARGIN, 30, CONTENT_WIDTH + PAGE_MARGIN, 30)

    footer_text = f"AEGIS ENTERPRISE AGENTIC RAG AUDIT ENGINE  |  CONFIDENTIAL & PROPRIETARY  |  PAGE {doc.page}"
    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(MUTED_SLATE)
    canvas.drawString(PAGE_MARGIN, 18, footer_text)
    canvas.drawRightString(CONTENT_WIDTH + PAGE_MARGIN, 18, f"Cryptographic Verification: #{doc.report_signature[:12]}")
    canvas.restoreState()


def _header_grid(report_data: dict, styles) -> Table:
    generated_at = report_data.get("generated_at") or datetime.now().strftime("%B %d, %Y")
    request_id = report_data.get("request_id", "N/A")

    left_cell = [
        Paragraph("GROUNDEDRAG", styles["DocTitle"]),
        Paragraph("AUTOMATED REGULATORY COMPLIANCE &amp; EVIDENCE AUDIT LEDGER", styles["DocSubtitle"]),
    ]

    meta_rows = [
        [Paragraph("AUDIT DATE", styles["MetaLabel"]), Paragraph(str(generated_at), styles["MetaValue"])],
        [Paragraph("JOB HASH", styles["MetaLabel"]), Paragraph(str(request_id)[:14] + "...", styles["MetaValue"])],
        [Paragraph("ENGINE VER", styles["MetaLabel"]), Paragraph("v2.4-Agentic", styles["MetaValue"])],
    ]
    meta_table = Table(meta_rows, colWidths=[70, 130])
    meta_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    header = Table([[left_cell, meta_table]], colWidths=[340, 200])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return header


def _executive_summary_card(report_data: dict, styles) -> Table:
    risk_score = int(report_data.get("risk_score", 0))
    jurisdiction = report_data.get("audited_jurisdiction", "European Union (GDPR)")
    status = report_data.get("status", "COMPLETED_WITH_RISKS").replace("_", " ")

    score_color = STATUS_RED_TEXT if risk_score >= 60 else STATUS_GREEN_TEXT

    content = [
        Paragraph(f"<b>RISK ASSESSMENT SCORE:</b> <font color='{score_color.hexval()}'><b>{risk_score} / 100</b></font>  &bull;  <b>VERDICT:</b> {status}", styles["CardTitle"]),
        Spacer(1, 3),
        Paragraph(f"<b>Target Jurisdiction:</b> {jurisdiction}  |  <b>Audit Architecture:</b> Multi-Agent LangGraph + Qdrant Vector RAG + Llama 3.2 3B Guardrail", styles["CardBody"]),
    ]

    card = Table([[content]], colWidths=[CONTENT_WIDTH])
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (-1, -1), 1, ACCENT_INDIGO),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return card


def _deduplicate_findings(findings: list) -> list:
    # Keyed on (document, page, quote-prefix) rather than the LLM's paraphrased
    # `analysis` text, which differs on every call even for identical evidence —
    # see the matching key in src/agents/nodes/finalize.py. This is a render-time
    # safety net; findings should already be reconciled by the time they reach here.
    seen = set()
    unique = []
    for f in findings:
        loc = f.get("evidence_location") or {}
        doc = str(loc.get("document_name", "")).strip().lower()
        page = str(loc.get("page_number", "")).strip()
        quote_key = re.sub(r"[^a-z0-9]", "", str(f.get("evidence_quote", "")).lower())[:40]
        param = re.sub(r"[^a-z0-9]", "", str(f.get("parameter", "")).lower())[:40]
        key = f"{doc}|{page}|{quote_key or param}"
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def _build_finding_card(finding: dict, index: int, styles) -> Table:
    status_str = str(finding.get("finding_status", "NON_COMPLIANT")).upper()
    is_unresolved = bool(finding.get("unresolved_after_retries")) or "UNVERIFIED" in status_str
    is_non_compliant = any(kw in status_str for kw in ["FAIL", "NON_COMPLIANT", "FLAGGED"])

    if is_unresolved:
        badge_style, badge_bg, badge_text = styles["BadgeAmber"], STATUS_AMBER_BG, "UNVERIFIED"
    elif is_non_compliant:
        badge_style, badge_bg, badge_text = styles["BadgeRed"], STATUS_RED_BG, "NON_COMPLIANT"
    else:
        badge_style, badge_bg, badge_text = styles["BadgeGreen"], STATUS_GREEN_BG, "COMPLIANT"

    # Pill badge cell
    badge_table = Table([[Paragraph(f"<b>{badge_text}</b>", badge_style)]], colWidths=[110])
    badge_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), badge_bg),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    param_text = sanitize_for_reportlab(finding.get("parameter", "Unknown Compliance Rule"))
    header_table = Table([[Paragraph(f"<b>FINDING #{index + 1}: {param_text}</b>", styles["CardTitle"]), badge_table]], colWidths=[410, 110])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    analysis_text = sanitize_for_reportlab(finding.get("analysis", ""))

    quote_text = sanitize_for_reportlab(finding.get("evidence_quote", ""))

    # Extract clean citation string
    loc = finding.get("evidence_location", {})
    doc_name = loc.get("document_name", "Uploaded Contract Document") if isinstance(loc, dict) else "Uploaded Contract Document"
    pg_num = loc.get("page_number", 1) if isinstance(loc, dict) else 1
    verification_label = "NOT VERIFIED - EXCEEDED RETRY BUDGET" if is_unresolved else "Vector Sub-task Slice Verified"
    citation_text = f"EVIDENCE GROUNDING SOURCE: {doc_name}  &bull;  Page {pg_num}  &bull;  {verification_label}"
    if finding.get("reconciled_conflict"):
        citation_text += "  &bull;  <font color='" + STATUS_AMBER_TEXT.hexval() + "'>Conflicting sub-task verdicts on this clause were reconciled conservatively</font>"

    card_content = [
        header_table,
        Spacer(1, 4),
        Paragraph(analysis_text, styles["CardBody"]),
    ]
    if quote_text:
        card_content += [
            Spacer(1, 4),
            Paragraph(f"&ldquo;{quote_text}&rdquo;", styles["CardQuote"]),
        ]
    card_content += [
        Spacer(1, 4),
        Paragraph(citation_text, styles["CardCitation"]),
    ]

    card = Table([[card_content]], colWidths=[CONTENT_WIDTH])
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_CARD),
        ("LINEBEFORE", (0, 0), (-1, -1), 3.5, STATUS_AMBER_TEXT if is_unresolved else (STATUS_RED_TEXT if is_non_compliant else STATUS_GREEN_TEXT)),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return card


def _build_telemetry_section(report_data: dict, styles) -> Table:
    findings = report_data.get("raw_findings_array", [])
    total = len(findings)
    unresolved = sum(1 for f in findings if f.get("unresolved_after_retries"))
    grounding_rate = ((total - unresolved) / total * 100.0) if total else 100.0

    retry_line = (
        f"<b>3. Deterministic Guardrail Execution:</b> {unresolved} of {total} finding(s) remained unresolved "
        "after exhausting the retry budget and are flagged UNVERIFIED for manual review."
        if unresolved
        else "<b>3. Deterministic Guardrail Execution:</b> All task slices passed evidence verification within the configured retry budget."
    )

    content = [
        Paragraph("<b>AGENTIC SHIELD &amp; GROUNDING TELEMETRY LOGS</b>", styles["TelemetryHeader"]),
        Spacer(1, 4),
        Paragraph("<b>1. Multi-Agent State Graph:</b> Node 1 (Planning) -> Node 2 (Hybrid Qdrant Retrieval) -> Node 3 (Schema Auditor) -> Node 4 (Critic Guardrail) -> Node 5 (Master Finalizer Matrix)", styles["TelemetryBody"]),
        Paragraph(f"<b>2. Evidence Grounding Pass:</b> {grounding_rate:.1f}% of extracted quotes verified against vector context using fuzzy sequence matching.", styles["TelemetryBody"]),
        Paragraph(retry_line, styles["TelemetryBody"]),
    ]

    card = Table([[content]], colWidths=[CONTENT_WIDTH])
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CARD),
        ("LINEBEFORE", (0, 0), (-1, -1), 3, ACCENT_INDIGO),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return card


def build_compliance_pdf(report_data: dict, output_path: str) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=PAGE_MARGIN,
        leftMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=PAGE_MARGIN,
        title="GroundedRAG Compliance Audit",
    )
    styles = _build_styles()
    story = []

    payload_bytes = json.dumps(report_data, sort_keys=True).encode("utf-8")
    doc.report_signature = hashlib.sha256(payload_bytes).hexdigest()

    # --- Header ---
    story.append(_header_grid(report_data, styles))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_NAVY, spaceAfter=10))

    # --- Executive Summary ---
    story.append(_executive_summary_card(report_data, styles))
    story.append(Spacer(1, 10))

    # --- Section 1: Findings Matrix Cards ---
    story.append(Paragraph("1. CORE STATUTORY FINDINGS &amp; EVIDENCE MATRIX", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MUTED_SLATE, spaceBefore=1, spaceAfter=8))

    raw_findings = report_data.get("raw_findings_array", [])
    deduped = _deduplicate_findings(raw_findings)

    if deduped:
        for idx, finding in enumerate(deduped):
            story.append(_build_finding_card(finding, idx, styles))
            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("No regulatory non-compliance issues identified within the audited contract slice.", styles["CardBody"]))

    story.append(Spacer(1, 6))

    story.append(Paragraph("2. SYSTEM VERIFICATION &amp; TELEMETRY LOGS", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MUTED_SLATE, spaceBefore=1, spaceAfter=8))
    story.append(_build_telemetry_section(report_data, styles))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    logger.info("Compliance report PDF successfully serialized at %s", output_path)
    return os.path.abspath(output_path)
