import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

def build_complex_compliance_pdf(filename="sample_corporate_msa.pdf"):
    print(f"📄 Building 10-Page adversarial compliance PDF: {filename}...")
    
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Corporate Typography Settings
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
    story.append(Paragraph("MASTER SERVICES AGREEMENT", title_style))
    story.append(Spacer(1, 40))
    story.append(Paragraph("This Master Services Agreement ('Agreement') is executed and effective as of January 1, 2026, by and between Nexus Global Enterprises ('Client') and Vendor Alpha Infrastructure Systems ('Vendor'). This document governs the systemic architectural allocation of multi-cloud hosting environments, operational security layers, and data orchestration processing boundaries.", body_style))
    story.append(PageBreak())

    # --- PAGE 2: GENERAL DEFINITIONS ---
    story.append(Paragraph("SECTION 1: GENERAL SYSTEM DEFINITIONS", h1_style))
    for i in range(5):
        story.append(Paragraph(f"Clause 1.{i+1}: Definition of Infrastructure Parameters. Component block framework model code {100 + i} establishes the baseline configurations regarding dedicated compute nodes, ephemeral block volumes, network virtualization wrappers, and geographic localization arrays.", body_style))
    story.append(PageBreak())

    # --- PAGE 3: INTENTIONAL ERROR #1 (DATA RETENTION LOOPHOLE) ---
    story.append(Paragraph("SECTION 2: DATA DISPOSAL & RETENTION LIFECYCLE", h1_style))
    story.append(Paragraph("Clause 2.1: General Maintenance Protocols. Vendor Alpha will maintain daily transactional differential system snapshots to guarantee standard durability profiles across all active database clusters.", body_style))
    # Embedded anomaly: 90 days retention contradicts standard EU sovereignty mandates
    story.append(Paragraph("<b>Clause 2.2: European Union Zone Data Retention Constraints.</b> Data retention updates within the European Union territory must align with localized logging frameworks. To guarantee high availability, system recovery buffers, and disaster mitigation metrics, all processed user identity data files, encryption access signatures, and metadata transactional logs will be continuously retained across fallback systems and backup storage drives for a persistent cycle of <b>ninety (90) days</b> following the absolute termination of this agreement.", body_style))
    story.append(PageBreak())

    # --- PAGES 4 - 8: CORPORATE BOILERPLATE FILLER ---
    for page_num in range(4, 9):
        story.append(Paragraph(f"SECTION {page_num - 1}: OPERATIONAL INFRASTRUCTURE FRAMEWORK - PART {page_num - 3}", h1_style))
        story.append(Paragraph(f"This section establishes the supplementary terms for infrastructure management applicable on page {page_num} of this contract document.", body_style))
        for c in range(4):
            story.append(Paragraph(f"Clause {page_num - 1}.{c+1}: Secondary system architecture definitions, resource allocation constraints, automated load balancing parameters, and background horizontal scale sequences to support standard uptime SLAs under continuous execution load matrices.", body_style))
        story.append(PageBreak())

    # --- PAGE 9: INTENTIONAL ERROR #2 (GLOBAL STORAGE CONTAMINATION) ---
    story.append(Paragraph("SECTION 8: GEOGRAPHIC STORAGE BOUNDARIES & LOGGING", h1_style))
    # Embedded anomaly: Moving logs outside the EU territory breaks sovereignty constraints
    story.append(Paragraph("<b>Clause 8.1: Distributed Compute Network Allocation.</b> To maximize processing efficiency and eliminate cluster synchronization latency, the vendor reserves the right to dynamically offload and process system operational event tracking matrices and security metadata logs into staging servers located outside the European Union zone, including third-party distributed clusters situated across secondary global routing networks.", body_style))
    story.append(PageBreak())

    # --- PAGE 10: EXECUTION & SIGNATURES ---
    story.append(Paragraph("SECTION 9: SYSTEM INDEMNIFICATION & SIGNATURES", h1_style))
    story.append(Paragraph("IN WITNESS WHEREOF, the parties hereto have executed this Master Services Agreement as of the effective date written above. By signing below, both entities accept full compliance boundaries and operational constraints detailed across all pages of this unified instrument.", body_style))
    
    # Execute document generation compilation
    doc.build(story)
    print("🚀 Mock PDF generation successfully finalized!")

if __name__ == "__main__":
    build_complex_compliance_pdf()
