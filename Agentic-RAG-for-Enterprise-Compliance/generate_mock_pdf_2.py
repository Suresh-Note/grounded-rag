import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY


def build_employee_data_agreement_pdf(filename="sample_employee_data_agreement.pdf"):
    """
    A second synthetic ground-truth document, deliberately structured and worded
    differently from generate_mock_pdf.py's MSA (different section numbering style,
    different subject matter) so the eval suite isn't just re-testing one document's
    specific phrasing. Plants two distinct, unambiguous violations:
      1. Section 2.2 — employee biometric data shared with third parties without consent.
      2. Section 7.1 — no defined data breach notification timeline (violates the
         GDPR Article 33 72-hour requirement).
    """
    print(f"Building employee data agreement PDF: {filename}...")

    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=24, leading=28, spaceAfter=20
    )
    h1_style = ParagraphStyle(
        'SecHeader', parent=styles['Heading2'], fontSize=14, leading=18, spaceBefore=15, spaceAfter=10
    )
    body_style = ParagraphStyle(
        'ContractBody', parent=styles['Normal'], alignment=TA_JUSTIFY, fontSize=10, leading=15, spaceAfter=8
    )

    story = []

    # --- PAGE 1: TITLE & PREAMBLE ---
    story.append(Paragraph("EMPLOYEE DATA PROCESSING & MONITORING AGREEMENT", title_style))
    story.append(Spacer(1, 40))
    story.append(Paragraph(
        "This Employee Data Processing & Monitoring Agreement ('Agreement') is executed as of January 1, 2026, "
        "between Northwind HR Systems ('Employer') and Vendor Beta Workforce Analytics ('Processor'). This "
        "document governs the collection, processing, and monitoring of employee data across Employer's "
        "workforce management platform.", body_style
    ))
    story.append(PageBreak())

    # --- PAGE 2: MONITORING SCOPE ---
    story.append(Paragraph("SECTION 1: MONITORING SCOPE AND PURPOSE", h1_style))
    story.append(Paragraph(
        "Section 1.1: Purpose Limitation. Processor shall deploy workplace monitoring devices, including badge "
        "access logs and workstation activity trackers, solely for the purposes of security, productivity "
        "measurement, and regulatory compliance auditing.", body_style
    ))
    story.append(Paragraph(
        "Section 1.2: Retention of Monitoring Logs. Workstation activity logs will be retained for a period of "
        "thirty (30) days before automatic deletion, consistent with standard data minimization principles.", body_style
    ))
    story.append(PageBreak())

    # --- PAGE 3: INTENTIONAL ERROR #1 (BIOMETRIC DATA SHARING WITHOUT CONSENT) ---
    story.append(Paragraph("SECTION 2: EMPLOYEE BIOMETRIC DATA HANDLING", h1_style))
    story.append(Paragraph(
        "Section 2.1: Biometric Collection Scope. Employer collects fingerprint and facial recognition data "
        "from employees for the purpose of secure facility access control.", body_style
    ))
    story.append(Paragraph(
        "<b>Section 2.2: Third-Party Data Sharing.</b> Processor may share employee biometric identifiers, "
        "including fingerprint templates and facial recognition profiles, with third-party marketing affiliates "
        "and workforce analytics partners for commercial benchmarking purposes, without obtaining additional "
        "explicit consent from the affected employees.", body_style
    ))
    story.append(PageBreak())

    # --- PAGES 4-6: OPERATIONAL FILLER ---
    for page_num in range(4, 7):
        story.append(Paragraph(f"SECTION {page_num}: WORKFORCE PLATFORM OPERATIONS - PART {page_num - 2}", h1_style))
        story.append(Paragraph(
            f"This section establishes supplementary operational terms for the workforce management platform "
            f"applicable on page {page_num} of this agreement.", body_style
        ))
        for c in range(3):
            story.append(Paragraph(
                f"Section {page_num}.{c+1}: Platform uptime commitments, support ticket escalation paths, "
                f"scheduled maintenance windows, and standard service-level reporting cadences under this "
                f"workforce analytics engagement.", body_style
            ))
        story.append(PageBreak())

    # --- PAGE 7: INTENTIONAL ERROR #2 (NO BREACH NOTIFICATION TIMELINE) ---
    story.append(Paragraph("SECTION 7: SECURITY INCIDENT HANDLING", h1_style))
    story.append(Paragraph(
        "<b>Section 7.1: Data Breach Notification.</b> In the event of a security incident affecting employee "
        "personal data, Processor shall notify Employer at Processor's sole discretion, with no defined maximum "
        "notification timeframe, and Employer shall determine whether downstream notification to affected "
        "employees or regulatory authorities is warranted on a case-by-case basis.", body_style
    ))
    story.append(PageBreak())

    # --- PAGE 8: SIGNATURES ---
    story.append(Paragraph("SECTION 8: EXECUTION", h1_style))
    story.append(Paragraph(
        "IN WITNESS WHEREOF, the parties hereto have executed this Employee Data Processing & Monitoring "
        "Agreement as of the effective date written above.", body_style
    ))

    doc.build(story)
    print("Mock PDF generation successfully finalized!")


if __name__ == "__main__":
    build_employee_data_agreement_pdf()
