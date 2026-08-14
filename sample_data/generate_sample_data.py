"""
sample_data/generate_sample_data.py
------------------------------------
Generates 6 realistic pharmaceutical customer complaint files under sample_data/:
1. complaint_01_discoloration.eml        (Email - Complete)
2. complaint_02_chipped_tablets.txt       (Email Text - Missing Lot/Batch #)
3. complaint_03_packaging_defect.pdf     (PDF - Complete)
4. complaint_04_particulate_matter.pdf   (PDF - Missing Complainant Info)
5. complaint_05_dosage_mixup.txt          (Phone Intake Transcript - Complete)
6. complaint_06_counterfeit_packaging.txt (Phone Intake Transcript - Complete)
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

OUT_DIR = Path(__file__).parent.resolve()
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. complaint_01_discoloration.eml
# ---------------------------------------------------------------------------
eml_content = """From: Sarah Jenkins <s.jenkins84@example-mail.com>
To: quality-complaints@pharma-corp-global.com
Date: Mon, 12 May 2025 09:14:22 -0400
Subject: Complaint: Discolored tablets in Clarivin 10mg bottle (Batch B2024-089A)
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

Dear Customer Quality Team,

I am writing to report a serious issue with my recent prescription refill of Clarivin 10mg Tablets (Loratadine).

I picked up a 30-tablet bottle from CVS Pharmacy #4821 on May 10th. Upon opening the sealed foil safety seal yesterday morning, I noticed that several tablets towards the top of the bottle were discolored. Instead of being uniform bright white, at least 6 tablets have yellowish-brown spots and streaks across the surface.

Product Details:
- Product Name: Clarivin 10mg Tablets (30 count bottle)
- Batch / Lot Number: B2024-089A
- Expiration Date: 11/2026
- NDC Number: 55432-890-30

Complainant Details:
- Name: Sarah Jenkins
- Phone: (555) 234-8901
- Email: s.jenkins84@example-mail.com
- Address: 742 Evergreen Terrace, Springfield, OR 97477

I have not taken any of the discolored tablets. I have preserved the bottle and remaining tablets in their original packaging in case your QA lab needs them sent in for chemical analysis.

Please advise on replacement procedures and whether this batch is subject to a safety advisory.

Sincerely,
Sarah Jenkins
"""

(OUT_DIR / "complaint_01_discoloration.eml").write_text(eml_content, encoding="utf-8")

# ---------------------------------------------------------------------------
# 2. complaint_02_chipped_tablets.txt (INCOMPLETE: Missing Batch/Lot Number)
# ---------------------------------------------------------------------------
txt_chipped = """EMAIL INTAKE RECORD — PHARMAVIGILANCE
================================================================================
RECEIVED: 2025-05-14 14:22 EST
RECIPIENT: complaint-intake@pharma-corp-global.com
HEADER SENDER: Dr. Robert Vance, MD <rvance@vanceinternalmed.org>

SUBJECT: Quality Defect Report — Severely Chipped Cardexin 25mg ER Tablets

To Whom It May Concern,

I am a board-certified internist writing on behalf of one of my chronic hypertension patients who presented today with physical tablet defects in their prescription of Cardexin 25mg Extended Release (Metoprolol Succinate ER).

The patient opened a new 90-count bottle and discovered that approximately 15 to 20 tablets were severely chipped, crumbled, or split into fragments at the bottom of the container. Given that these are extended-release formulation tablets, administration of broken fragments poses a significant risk of dose-dumping and acute hypotension.

PRODUCT IDENTIFICATION:
- Product Name: Cardexin 25mg Extended Release Tablets
- Quantity: 90-count HDPE Bottle
- Lot / Batch Number: UNKNOWN (Patient transferred tablets to a daily pill organizer and discarded the original prescription bottle and box before noticing the chips. No batch number available on pharmacy receipt.)
- Expiration Date: Unspecified on receipt

COMPLAINANT CONTACT:
- Reporter: Dr. Robert Vance, MD
- Clinic: Vance Internal Medicine Associates
- Phone: (555) 891-3400
- Email: rvance@vanceinternalmed.org
- Patient Reference: Patient Initials J.D. (DOB 1958-03-12)

REQUESTED ACTION:
Please confirm if other complaints of friability or physical tablet fragmentation have been reported for recent Cardexin production lots. I have advised the patient to hold the medication and issued a replacement prescription.

Regards,
Dr. Robert Vance, MD
"""

(OUT_DIR / "complaint_02_chipped_tablets.txt").write_text(txt_chipped, encoding="utf-8")

# ---------------------------------------------------------------------------
# 3. complaint_03_packaging_defect.pdf (PDF - Complete)
# ---------------------------------------------------------------------------
def build_pdf_03():
    pdf_path = OUT_DIR / "complaint_03_packaging_defect.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#1e293b'), spaceAfter=8)
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor('#64748b'), spaceAfter=14)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, leading=15, textColor=colors.HexColor('#334155'), spaceAfter=10)
    label_style = ParagraphStyle('LabelStyle', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#475569'), fontName='Helvetica-Bold')
    val_style = ParagraphStyle('ValStyle', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#0f172a'))

    elements = []
    elements.append(Paragraph("ST. JUDE HOSPITAL PHARMACY — QUALITY DEFECT NOTICE", title_style))
    elements.append(Paragraph("FORMAL COMPLAINT SUBMISSION // MEDICAL DEVICE & PACKAGING DIVISION", sub_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=14))

    meta_data = [
        [Paragraph("Date of Report:", label_style), Paragraph("May 15, 2025", val_style), Paragraph("Complaint Ref:", label_style), Paragraph("SJH-QC-2025-0891", val_style)],
        [Paragraph("Facility Name:", label_style), Paragraph("St. Jude Regional Medical Center", val_style), Paragraph("Department:", label_style), Paragraph("Inpatient Pharmacy Services", val_style)],
        [Paragraph("Complainant:", label_style), Paragraph("Mark Thorne, PharmD (Lead QA Pharmacist)", val_style), Paragraph("Contact Email:", label_style), Paragraph("m.thorne@stjude-health.org", val_style)],
        [Paragraph("Direct Phone:", label_style), Paragraph("(555) 443-9000 ext. 4102", val_style), Paragraph("Address:", label_style), Paragraph("100 Hospital Plaza, Suite 3B, Chicago, IL", val_style)]
    ]

    t_meta = Table(meta_data, colWidths=[100, 160, 90, 154])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#f1f5f9')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("<b>PRODUCT & LOT DETAILS</b>", label_style))
    prod_data = [
        [Paragraph("Product Trade Name:", label_style), Paragraph("PulmoVent 100mcg Inhalation Aerosol (Albuterol Sulfate)", val_style)],
        [Paragraph("Lot / Batch Number:", label_style), Paragraph("<b>LOT-99321-X</b>", val_style)],
        [Paragraph("Manufacture Date:", label_style), Paragraph("01/2025", val_style)],
        [Paragraph("Expiration Date:", label_style), Paragraph("01/2027", val_style)],
        [Paragraph("Package Format:", label_style), Paragraph("200-Actuation Canister in Foil Pouch Blister Carton", val_style)],
    ]
    t_prod = Table(prod_data, colWidths=[140, 364])
    t_prod.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_prod)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("<b>DEFECT DESCRIPTION & FINDINGS</b>", label_style))
    desc_text = (
        "During routine cleanroom intake inspection of Shipment #PO-883910, hospital pharmacy technicians identified a critical "
        "packaging defect affecting 4 out of 25 shipping cartons (total of 48 individual units affected).<br/><br/>"
        "<b>Observed Defect:</b> The protective outer foil barrier pouches for the PulmoVent inhalers exhibit incomplete heat sealing along the "
        "longitudinal bottom margin. The heat-seal seam displays unbonded channel voids ranging from 3mm to 12mm in length, allowing ambient air "
        "and moisture exposure to the primary actuator and valve assembly.<br/><br/>"
        "<b>Risk Impact:</b> PulmoVent canisters require moisture barrier protection to prevent hygroscopic clumping of the micronized albuterol powder. "
        "Unsealed foil pouches compromise dose uniformity and valve delivery characteristics. All 48 compromised units have been quarantined in our pharmacy hold room.<br/><br/>"
        "<b>Corrective Action Requested:</b> Issue Return Material Authorization (RMA) for replacement of Lot LOT-99321-X and initiate packaging line seal integrity audit."
    )
    elements.append(Paragraph(desc_text, body_style))
    doc.build(elements)

build_pdf_03()

# ---------------------------------------------------------------------------
# 4. complaint_04_particulate_matter.pdf (PDF - INCOMPLETE: Missing Complainant Info)
# ---------------------------------------------------------------------------
def build_pdf_04():
    pdf_path = OUT_DIR / "complaint_04_particulate_matter.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#991b1b'), spaceAfter=6)
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#7f1d1d'), spaceAfter=14)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, leading=15, textColor=colors.HexColor('#1f2937'), spaceAfter=10)
    label_style = ParagraphStyle('LabelStyle', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#374151'), fontName='Helvetica-Bold')
    val_style = ParagraphStyle('ValStyle', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#111827'))

    elements = []
    elements.append(Paragraph("ANONYMOUS ANALYTICAL INCIDENT REPORT — CRITICAL PRODUCT QUALITY DEFECT", title_style))
    elements.append(Paragraph("SUBMITTED VIA PHARMA C&A SECURE UPLOAD PORTAL // CONFIDENTIAL EVALUATION", sub_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#dc2626'), spaceAfter=14))

    meta_data = [
        [Paragraph("Date Logged:", label_style), Paragraph("May 18, 2025", val_style), Paragraph("Incident Type:", label_style), Paragraph("Foreign Particulate Matter (Parenteral)", val_style)],
        [Paragraph("Reporter Name:", label_style), Paragraph("<b>[NOT PROVIDED / ANONYMOUS PORTAL SUBMISSION]</b>", val_style), Paragraph("Reporter Role:", label_style), Paragraph("Unspecified Hospital Quality Control Analyst", val_style)],
        [Paragraph("Contact Email:", label_style), Paragraph("<b>[NONE PROVIDED]</b>", val_style), Paragraph("Contact Phone:", label_style), Paragraph("<b>[NONE PROVIDED]</b>", val_style)],
    ]

    t_meta = Table(meta_data, colWidths=[100, 160, 90, 154])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fef2f2')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#fca5a5')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#fecaca')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("<b>PRODUCT IDENTIFICATION & SPECIFICATIONS</b>", label_style))
    prod_data = [
        [Paragraph("Product Name:", label_style), Paragraph("Metoprolol Tartrate Injection USP (5mg/5mL Sterile Vial)", val_style)],
        [Paragraph("Batch / Lot Number:", label_style), Paragraph("<b>B-API-88741</b>", val_style)],
        [Paragraph("ND C Number:", label_style), Paragraph("00781-3044-95", val_style)],
        [Paragraph("Expiration Date:", label_style), Paragraph("08/2026", val_style)],
    ]
    t_prod = Table(prod_data, colWidths=[140, 364])
    t_prod.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e5e7eb')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#f3f4f6')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_prod)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("<b>INCIDENT DETAILS & MICROSCOPY OBSERVATIONS</b>", label_style))
    desc_text = (
        "During pre-administration visual inspection under high-intensity polarized light in a IV compounding cleanroom, a 5mL glass vial of "
        "Metoprolol Tartrate Injection (Batch B-API-88741) was found to contain visible translucent floating fibers and dark specks.<br/><br/>"
        "<b>Microscopic Examination:</b> Microscopic examination at 40x magnification revealed two distinct contaminant populations:<br/>"
        "1. Translucent fibrous filaments approximately 1.2mm to 2.5mm in length (resembling elastomer rubber stopper shedding).<br/>"
        "2. Irregular black particulate specs (~150 to 300 microns) consistent with carbonized stainless steel or pump seal wear.<br/><br/>"
        "<b>Patient Exposure:</b> The vial was rejected prior to IV bag reconstitution. No patient was exposed to the contaminated batch.<br/><br/>"
        "<b>Note on Missing Contact Info:</b> The submitting technician opted not to provide personal contact details or hospital location on the web portal. "
        "Immediate QA investigation of Lot B-API-88741 retain samples is strongly recommended."
    )
    elements.append(Paragraph(desc_text, body_style))
    doc.build(elements)

build_pdf_04()

# ---------------------------------------------------------------------------
# 5. complaint_05_dosage_mixup.txt (Phone Intake Transcript - Complete)
# ---------------------------------------------------------------------------
txt_mixup = """CALL CENTER CALL TRANSCRIPT — PHARMA INTAKE HOTLINE
================================================================================
CALL ID: CALL-2025-0520-9941
DATE/TIME: May 20, 2025 | 11:04 AM EST
CALL TAKEN BY: Representative James Miller (Badge #JM-408)
CALL SOURCE: Toll-Free Healthcare Provider Line (1-800-555-QMS1)

CALL DETAILS / PARTICIPANTS:
--------------------------------------------------------------------------------
Caller Name: Elena Rostova, RPh (Pharmacy Manager)
Facility: MetroCare Outpatient Pharmacy
Phone Number: (555) 782-9110
Email: e.rostova@metrocare-pharmacy.org
Address: 450 Medical Center Blvd, Floor 1, Boston, MA 02115

COMPLAINT INFORMATION:
--------------------------------------------------------------------------------
Product Name: NeuroPam (Diazepam) Capsules
Reported Strength: 5mg Capsules
Batch / Lot Number: NP-77402-B
Expiration Date: 09/2026
Package Size: 100-count bottle

TRANSCRIPT / SUMMARY OF CALL:
--------------------------------------------------------------------------------
[11:04:12] REP MILLER: Thank you for calling Customer Quality Care. My name is James. How may I assist you today?

[11:04:25] PHARMACIST ROSTOVA: Hello James. I'm calling from MetroCare Pharmacy in Boston. We have a potential medication mix-up inside a bottle of NeuroPam 5mg capsules that we opened this morning during routine prescription dispensing.

[11:04:42] REP MILLER: I understand. Can you describe what was found in the bottle?

[11:04:48] PHARMACIST ROSTOVA: Yes. The bottle is labeled as NeuroPam 5mg Capsules (which are yellow, opaque, size 3 capsules). While pouring the capsules onto the counting tray, my technician noticed one single capsule that was distinctively blue and white, which matches the physical appearance of NeuroPam 10mg Capsules.

[11:05:15] REP MILLER: Thank you for catching that. Was the bottle safety seal intact prior to opening?

[11:05:22] PHARMACIST ROSTOVA: Yes, the heat-induction foil seal was 100% intact when the technician opened it. The bottle was from a sealed 12-pack case received from our wholesaler yesterday.

[11:05:40] REP MILLER: May I get the lot number and expiration date from the bottle label?

[11:05:45] PHARMACIST ROSTOVA: The lot number on the side of the bottle is NP-77402-B, and the expiration date is 09/2026.

[11:06:05] REP MILLER: Thank you, Elena. Have any patients received doses from this specific bottle?

[11:06:12] PHARMACIST ROSTOVA: No, thankfully we caught it during counting before any prescription was dispensed. We have segregated this bottle and checked the remaining 11 bottles in the case — no other visual anomalies were spotted, but we have placed the entire lot on quarantine hold.

[11:06:35] REP MILLER: Perfect. I am logging this as a Critical Level-1 Product Mix-up Incident. I will email you a prepaid shipping kit to send the bottle and the mismatched 10mg capsule to our central QA laboratory for laser printing and capsule shell verification.

SUMMARY OF ACTION:
- Case reference # CMP-2025-0520 created.
- Product: NeuroPam 5mg Capsules (Lot NP-77402-B).
- Defect: Single 10mg blue/white capsule found inside 5mg yellow bottle.
- Quarantine confirmed at dispensing facility.
================================================================================
"""

(OUT_DIR / "complaint_05_dosage_mixup.txt").write_text(txt_mixup, encoding="utf-8")

# ---------------------------------------------------------------------------
# 6. complaint_06_counterfeit_packaging.txt (Phone Intake Transcript - Complete)
# ---------------------------------------------------------------------------
txt_counterfeit = """CALL CENTER CALL TRANSCRIPT — PHARMA SECURITY & QUALITY HOTLINE
================================================================================
CALL ID: CALL-2025-0522-1042
DATE/TIME: May 22, 2025 | 03:45 PM EST
CALL TAKEN BY: Representative Maria Davis (Badge #MD-712)
CALL SOURCE: Direct Line — Medical Executive Office

CALL DETAILS / PARTICIPANTS:
--------------------------------------------------------------------------------
Caller Name: Dr. Aris Thorne, MD
Role: Director of Clinical Oncology Services
Facility: Tri-State Cancer Center
Phone Number: (555) 902-4411
Email: athorne@tristate-oncology.com
Address: 880 Bellevue Avenue, Suite 400, Seattle, WA 98801

COMPLAINT INFORMATION:
--------------------------------------------------------------------------------
Product Name: Oncolox (Paclitaxel) Injection 100mg/16.7mL
Batch / Lot Number: ONC-2025-001
Labeled Expiration: 03/2027
Wholesaler / Source: Secondary Distributor (Apex Pharma Logistics)

TRANSCRIPT / SUMMARY OF CALL:
--------------------------------------------------------------------------------
[15:45:05] REP DAVIS: Quality & Product Integrity Hotline, Maria speaking. How can I help you?

[15:45:18] DR. THORNE: Good afternoon. I need to report a suspected counterfeit packaging issue regarding a recent delivery of Oncolox 100mg IV infusion vials.

[15:45:32] REP DAVIS: I take these reports very seriously, Doctor. Please tell me what raised suspicion about the product.

[15:45:41] DR. THORNE: We received 10 cartons of Oncolox today from a secondary supplier because our primary distributor was backordered. When our oncology pharmacy team inspected the outer boxes, several discrepancies were immediately obvious compared to our standard inventory:
1. The security hologram sticker on the top flap lacks the multi-color refraction pattern of authentic Oncolox cartons. It looks like a flat metallic foil print.
2. The lot number printed on the carton side panel (ONC-2025-001) uses a different font typeface than usual, and the ink smudges easily when touched.
3. The QR verification code on the back of the box returns an error ("URL Not Found") when scanned with a mobile device.

[15:46:40] REP DAVIS: Thank you for these precise details, Dr. Thorne. Has any of this product been prepared or administered to any patient?

[15:46:48] DR. THORNE: Absolutely not. The pharmacy flagged it immediately upon receipt and locked the entire shipment in our secure vault.

[15:47:02] REP DAVIS: Excellent. Can you confirm the batch number and supplier name for my report?

[15:47:09] DR. THORNE: Lot number is ONC-2025-001. Distributor on the invoice is Apex Pharma Logistics, Invoice #AP-994812.

[15:47:28] REP DAVIS: Thank you. I am immediately escalating this to Global Brand Protection, Anti-Counterfeiting Taskforce, and Regulatory Affairs. Please do not return the shipment to Apex Logistics until our security team has inspected and secured high-resolution photographs and physical samples.

SUMMARY OF ACTION:
- Case reference # CMP-2025-0522 created.
- Product: Oncolox 100mg Injection (Lot ONC-2025-001).
- Category: Counterfeit / Falsified Product.
- Status: Escalated to Brand Security & Legal. Product quarantined.
================================================================================
"""

(OUT_DIR / "complaint_06_counterfeit_packaging.txt").write_text(txt_counterfeit, encoding="utf-8")

# ---------------------------------------------------------------------------
# 7. complaint_07_metformin_api.pdf (PDF - Metformin Hydrochloride API)
# ---------------------------------------------------------------------------
def build_pdf_07():
    pdf_path = OUT_DIR / "complaint_07_metformin_api.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#1e293b'), spaceAfter=8)
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor('#64748b'), spaceAfter=14)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, leading=15, textColor=colors.HexColor('#334155'), spaceAfter=10)
    label_style = ParagraphStyle('LabelStyle', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#475569'), fontName='Helvetica-Bold')
    val_style = ParagraphStyle('ValStyle', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#0f172a'))

    elements = []
    elements.append(Paragraph("APOLLO PHARMACEUTICAL MANUFACTURING — QUALITY COMPLAINT REPORT", title_style))
    elements.append(Paragraph("ACTIVE PHARMACEUTICAL INGREDIENT (API) INCOMING QUALITY DEFECT", sub_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#059669'), spaceAfter=14))

    meta_data = [
        [Paragraph("Date of Report:", label_style), Paragraph("July 12, 2026", val_style), Paragraph("Complaint Ref:", label_style), Paragraph("APO-API-2026-0712", val_style)],
        [Paragraph("Customer Name:", label_style), Paragraph("Apollo Pharmacy Laboratories", val_style), Paragraph("Department:", label_style), Paragraph("Raw Material QA / QC", val_style)],
        [Paragraph("Complainant Contact:", label_style), Paragraph("Dr. Rajiv Sharma (Head of QA) <r.sharma@apollopharma.example.com>", val_style), Paragraph("Phone:", label_style), Paragraph("+91 98765 43210", val_style)],
    ]

    t_meta = Table(meta_data, colWidths=[110, 160, 90, 144])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#bbf7d0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dcfce7')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("<b>API MATERIAL & LOT DETAILS</b>", label_style))
    prod_data = [
        [Paragraph("Product Name:", label_style), Paragraph("Metformin Hydrochloride API", val_style)],
        [Paragraph("Product Grade / Strength:", label_style), Paragraph("IP / BP (Pharma Grade)", val_style)],
        [Paragraph("Batch / Lot Number:", label_style), Paragraph("<b>MFH260712A</b>", val_style)],
        [Paragraph("Manufacturing Date:", label_style), Paragraph("2026-01-15", val_style)],
        [Paragraph("Expiry Date:", label_style), Paragraph("2029-01-14", val_style)],
        [Paragraph("Affected Quantity:", label_style), Paragraph("50 kg (2 HDPE drums)", val_style)],
    ]
    t_prod = Table(prod_data, colWidths=[140, 364])
    t_prod.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_prod)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("<b>COMPLAINT DESCRIPTION & DEFECT ANALYSIS</b>", label_style))
    desc_text = (
        "During incoming raw material receipt inspection of Metformin Hydrochloride API batch MFH260712A, quality control analysts "
        "observed abnormal off-white discoloration and clumping in two 25kg HDPE drums.<br/><br/>"
        "<b>Defect Details:</b> Standard specification requires a pure white crystalline powder. The material in drum #2 displays "
        "yellowish discoloration and moist agglomerates, failing assay purity and loss on drying (LOD) specification limits.<br/><br/>"
        "<b>Suggested Action:</b> Place batch MFH260712A on quarantine hold, perform vendor QA investigation, and issue replacement shipment."
    )
    elements.append(Paragraph(desc_text, body_style))
    doc.build(elements)

build_pdf_07()

print(f"Successfully generated sample complaint files in: {OUT_DIR}")

