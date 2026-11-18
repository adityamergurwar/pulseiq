from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "DataAnalytics_Aditya_Mergurwar_Phase2_Report.pdf"
REPO = "https://github.com/adityamergurwar/pulseiq"
TAG_URL = f"{REPO}/tree/phase-2"
APP_URL = "https://pulseiq-workforce.streamlit.app"
VALIDATION_URL = f"{REPO}/blob/phase-2/docs/phase2_validation.md"

INK = colors.HexColor("#18212F")
TEAL = colors.HexColor("#0F766E")
PALE = colors.HexColor("#E7F4F2")
MUTED = colors.HexColor("#526174")
GRID = colors.HexColor("#D7DEE7")
WHITE = colors.white

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
    fontSize=24, leading=28, textColor=INK, alignment=TA_LEFT, spaceAfter=4,
))
styles.add(ParagraphStyle(
    name="Eyebrow", parent=styles["Normal"], fontName="Helvetica-Bold",
    fontSize=8, leading=10, textColor=TEAL, spaceAfter=5,
))
styles.add(ParagraphStyle(
    name="Meta", parent=styles["Normal"], fontName="Helvetica",
    fontSize=9, leading=12, textColor=MUTED,
))
styles.add(ParagraphStyle(
    name="SectionTitle", parent=styles["Heading2"], fontName="Helvetica-Bold",
    fontSize=12.5, leading=14, textColor=INK, spaceBefore=5, spaceAfter=3,
))
styles.add(ParagraphStyle(
    name="BodySmall", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8.2, leading=10, textColor=INK, spaceAfter=2,
))
styles.add(ParagraphStyle(
    name="TableHead", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=8.2, leading=10, textColor=WHITE,
))
styles.add(ParagraphStyle(
    name="TableCell", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8.2, leading=10.5, textColor=INK,
))
styles.add(ParagraphStyle(
    name="TableStrong", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=8.2, leading=10.5, textColor=INK,
))
styles.add(ParagraphStyle(
    name="StatValue", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=15, leading=18, textColor=TEAL, alignment=TA_CENTER,
))
styles.add(ParagraphStyle(
    name="StatLabel", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=7.5, leading=9, textColor=MUTED, alignment=TA_CENTER,
))
styles.add(ParagraphStyle(
    name="CardLabel", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=7.2, leading=8.5, textColor=TEAL, alignment=TA_LEFT,
))
styles.add(ParagraphStyle(
    name="CardValue", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=13, leading=15, textColor=INK, alignment=TA_LEFT,
))
styles.add(ParagraphStyle(
    name="CardNote", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=7.2, leading=9, textColor=MUTED, alignment=TA_LEFT,
))
styles.add(ParagraphStyle(
    name="FlowHead", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=8, leading=9.5, textColor=INK,
))
styles.add(ParagraphStyle(
    name="FlowNote", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=7.2, leading=9, textColor=MUTED,
))
styles.add(ParagraphStyle(
    name="ImageCaption", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8, leading=10, textColor=MUTED, alignment=TA_CENTER,
))


def para(text, style="TableCell"):
    return Paragraph(text, styles[style])


def link(label, url):
    return f'<link href="{url}" color="#0F766E"><u>{label}</u></link>'


def page_chrome(canvas, doc):
    canvas.saveState()
    page_w, _ = landscape(A4)
    canvas.setStrokeColor(GRID)
    canvas.setLineWidth(0.5)
    canvas.line(17 * mm, 13 * mm, page_w - 17 * mm, 13 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(17 * mm, 8.5 * mm, "PulseIQ Phase 2 Foundation")
    canvas.drawRightString(page_w - 17 * mm, 8.5 * mm, f"Page {doc.page} of 3")
    canvas.restoreState()


def section(title):
    return Paragraph(title, styles["SectionTitle"])


def make_task_table():
    evidence_rows = [
        ("6 - Attendance and leave", "Sep rate 95.2%; working-day denominator and holiday context (p. 3)"),
        ("7 - Attrition", "Sep: 3 observed exits / 0.70%; predicted risk shown separately (p. 3)"),
        ("8 - Team productivity", "SP-38: 332 points; 89.7% on-time; 79.1% completion (p. 3)"),
        ("9 - Payroll cost", "18/18 payroll reference months reconcile; invalid rows quarantined (p. 3)"),
        ("10 - Budget and KPI", "D01 +INR 214,404; company total -INR 664,616 (p. 3)"),
    ]
    rows = [[para("Task", "TableHead"), para("Status", "TableHead"), para("Evidence", "TableHead")]]
    for task, evidence in evidence_rows:
        rows.append([
            para(task, "TableStrong"),
            para("DONE", "TableStrong"),
            para(evidence),
        ])
    table = Table(rows, colWidths=[153, 52, 540.4], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("BACKGROUND", (0, 1), (-1, -1), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F5F8FA")]),
        ("GRID", (0, 0), (-1, -1), 0.45, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (1, 1), (1, -1), TEAL),
    ]))
    return table


def summary_cards():
    cards = [
        ("ATTENDANCE", "95.2%", "September rate"),
        ("ATTRITION", "3 exits / 0.70%", "September observed"),
        ("TEAM DELIVERY", "89.7% on time", "SP-38 across teams"),
        ("EMPLOYER COST", "INR 55.52m", "September payroll"),
    ]
    cells = []
    for label, value, note in cards:
        card = Table([
            [para(label, "CardLabel")],
            [para(value, "CardValue")],
            [para(note, "CardNote")],
        ], colWidths=[174])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PALE),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B7D9D5")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        cells.append(card)
    table = Table([cells], colWidths=[186.35] * 4, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def data_flow_table():
    steps = [
        ("1. SOURCE DATA", "29 supplied HR, task and finance tables"),
        ("2. ETL + QUALITY", "Validated, corrected or quarantined with audit reasons"),
        ("3. GOVERNED METRICS", "28 DuckDB views feed reusable measures"),
        ("4. DASHBOARDS", "Five role-aware Streamlit pages with filters"),
    ]
    rows = [[para(head, "FlowHead") for head, _ in steps],
            [para(note, "FlowNote") for _, note in steps]]
    table = Table(rows, colWidths=[186.35] * 4, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F8FA")),
        ("BOX", (0, 0), (-1, -1), 0.45, GRID),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def challenge_table():
    lines = [
        "Raw row FA-00018 for Sep 2026 records employee EMP-0002 in D08: 21 scheduled days, 21 present, 0 half-unpaid days.",
        "ETL checks the row, joins employee and date keys, and loads accepted rows into clean.fact_attendance_monthly.",
        "M13 sums present_days + 0.5 x half_days_unpaid (8,672.5) and divides by scheduled_days (9,111) across 444 rows.",
        "Hand check: 8,672.5 / 9,111 x 100 = 95.1871%; the metric view returns 0.951871, displayed as 95.2%.",
        "The Attendance page selects M13 for ALL and plots it by month; September 2026 is the 95.2% chart point.",
    ]
    rows = [[para(str(i), "TableStrong"), para(text, "BodySmall")] for i, text in enumerate(lines, 1)]
    table = Table(rows, colWidths=[20, 725.4], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), PALE),
        ("TEXTCOLOR", (0, 0), (0, -1), TEAL),
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def stat_table():
    stats = [
        ("18 / 18", "automated tests passed"),
        ("28 / 28", "metric views populated"),
        ("18 / 18", "payroll reference months match"),
        ("0", "declared warehouse orphans"),
    ]
    table = Table([
        [para(value, "StatValue") for value, _ in stats],
        [para(label, "StatLabel") for _, label in stats],
    ], colWidths=[186.35] * 4, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B7D9D5")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B7D9D5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def screenshot_tile(filename, caption, max_width, max_height):
    path = ROOT / "output" / "evidence" / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing screenshot evidence: {path}")
    image = Image(str(path), width=max_width, height=max_height, kind="proportional", hAlign="CENTER")
    return [image, Paragraph(caption, styles["ImageCaption"])]


def screenshot_gallery():
    small_w, small_h = 235, 132
    top = Table([[
        screenshot_tile("PulseIQ_Phase2_Attendance_2026-10-31.png", "Attendance rate and holiday markers", small_w, small_h),
        screenshot_tile("PulseIQ_Phase2_Attrition_2026-10-31.png", "Observed exits and monthly attrition", small_w, small_h),
        screenshot_tile("PulseIQ_Phase2_Team_2026-10-31.png", "Team sprint measures and rules", small_w, small_h),
    ]], colWidths=[248.5, 248.5, 248.5], hAlign="LEFT")
    top.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    bottom = Table([[
        screenshot_tile("PulseIQ_Phase2_Attendance_Findings_2026-10-31.png", "Three unusual months and calendar context", small_w, small_h),
        screenshot_tile("PulseIQ_Phase2_Payroll_2026-10-31.png", "September payroll totals and cost trend", small_w, small_h),
        screenshot_tile("PulseIQ_Phase2_Budget_2026-10-31.png", "Budget variance ranking and totals", small_w, small_h),
    ]], colWidths=[248.5, 248.5, 248.5], hAlign="LEFT")
    bottom.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return [top, Spacer(1, 3), bottom]


def build_report():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=landscape(A4),
        leftMargin=17 * mm, rightMargin=17 * mm,
        topMargin=12 * mm, bottomMargin=19 * mm,
        title="PulseIQ Phase 2: People and Teams",
        author="Aditya Mergurwar",
        subject="PulseIQ Phase 2 foundation and verification",
    )
    story = []

    # Page 1: report header, project summary and the five task/evidence rows.
    story.append(Paragraph("DATA ANALYTICS TRACK  /  PHASE 2", styles["Eyebrow"]))
    story.append(Paragraph("PulseIQ Phase 2: People and Teams", styles["ReportTitle"]))
    story.append(Paragraph("Aditya Mergurwar  |  Data Analytics Track  |  Phase 2  |  Snapshot through 30 Sep 2026", styles["Meta"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"GitHub repository: {link(REPO, REPO)}  |  Git tag: {link('phase-2', TAG_URL)}<br/>"
        f"Live dashboard: {link(APP_URL, APP_URL)}",
        styles["BodySmall"],
    ))
    story.append(Spacer(1, 2))
    story.append(section("Build summary"))
    story.append(Paragraph(
        "Phase 2 turns the supplied workforce, delivery and finance data into five decision-oriented dashboard pages. "
        "The build emphasizes consistent metric definitions, privacy-safe aggregates and checks that trace dashboard results "
        "back to the warehouse. The figures below describe the supplied snapshot, not a live HR system.",
        styles["BodySmall"],
    ))
    story.append(section("Data-to-dashboard path"))
    story.append(data_flow_table())
    story.append(section("September operating snapshot"))
    story.append(summary_cards())
    story.append(Spacer(1, 2))
    story.append(Paragraph(
        "Decision read: company payroll finished INR 664,616 (1.2%) below budget, while D01 alone exceeded its budget by "
        "INR 214,404. The department view therefore matters alongside the company total; the page ranks overspend and links "
        "it to a review of open roles and overtime.",
        styles["BodySmall"],
    ))
    story.append(section("Phase 2 task outcomes and evidence"))
    story.append(make_task_table())
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        f"Verification detail: {link('Phase 2 checks', VALIDATION_URL)}  |  "
        f"Live dashboard: {link('Budget vs Actual', f'{APP_URL}/Budget_vs_Actual')}",
        styles["BodySmall"],
    ))

    story.append(PageBreak())

    # Page 2: test proof, five-line data trace, reflection and next-phase plan.
    story.append(Paragraph("VERIFICATION", styles["Eyebrow"]))
    story.append(Paragraph("Proof, learning and next steps", styles["ReportTitle"]))
    story.append(stat_table())
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "The acceptance checker covered 29 source tables with zero unexplained row-count differences and zero declared "
        "relationship orphans. Independent calculations matched the attendance denominator, two team/sprint examples and "
        "three department budget variances. Across 18 reference months, the maximum clean payroll-to-ledger difference was "
        "INR 0.00000004, within the INR 0.01 tolerance. These checks support the clean warehouse outputs; they do not mean "
        "every supplied raw row was valid.",
        styles["BodySmall"],
    ))
    story.append(section("Mini challenge: trace September attendance in five lines"))
    story.append(challenge_table())
    story.append(section("Reconciliation and variance, in plain language"))
    explain = Table([[
        para("Reconciliation", "TableStrong"),
        para("Compare two independent totals for the same money, like checking a bill against a bank record. All 18 reference months match; the largest gap is less than one cent.", "BodySmall"),
        para("Variance", "TableStrong"),
        para("Actual payroll cost minus budget. A positive result means overspend; a negative result means spending below budget.", "BodySmall"),
    ]], colWidths=[85, 285, 70, 305.4], hAlign="LEFT")
    explain.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), PALE),
        ("BACKGROUND", (2, 0), (2, 0), PALE),
        ("BOX", (0, 0), (-1, -1), 0.45, GRID),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(explain)
    story.append(section("What the build taught"))
    for text in [
        "Use scheduled working days as the attendance denominator; holidays and leave add context but do not prove a cause.",
        "Keep observed exits separate from predicted risk, and suppress small groups before showing sensitive breakdowns.",
        "Pair sprint velocity with cycle time, on-time delivery, completion, blocked work and reopens before interpreting delivery.",
        "Reconcile totals and define the variance sign so readers can distinguish a company underspend from a local overspend.",
    ]:
        story.append(Paragraph(f"- {text}", styles["BodySmall"]))
    story.append(section("Problems and fixes"))
    story.append(Paragraph(
        "The supplied raw data includes seeded exceptions. Four invalid payroll rows with duplicate keys or unmatched "
        "employee references are quarantined with reasons; the raw inputs remain intact. Attendance calendar markers are "
        "described as context, not as proof of cause. Hosted DuckDB binding/schema errors were corrected, and pandas 3 "
        "styling was updated from Styler.applymap to Styler.map.",
        styles["BodySmall"],
    ))
    story.append(section("Plan for Phase 3"))
    story.append(Paragraph(
        "1. Load the next source period and repeat row, relationship, metric and reconciliation checks. "
        "2. Review the D01 budget driver and agree owners and thresholds for follow-up with Finance. "
        "3. Extend governed reporting to revenue, cash and AI signals; publish forecast accuracy only after actuals overlap "
        "the forecast horizon.",
        styles["BodySmall"],
    ))

    story.append(PageBreak())

    # Page 3: screenshots supplied from the running dashboard.
    story.append(Paragraph("DASHBOARD EVIDENCE", styles["Eyebrow"]))
    story.append(Paragraph("Dashboard screenshots", styles["ReportTitle"]))
    story.append(Paragraph(
        "Screenshots from the live Phase 2 pages, including budget variance ranking and totals.",
        styles["BodySmall"],
    ))
    story.append(Spacer(1, 4))
    story.extend(screenshot_gallery())
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Attendance: {link('open page', f'{APP_URL}/Attendance_and_Leave')}  |  "
        f"Attrition: {link('open page', f'{APP_URL}/Attrition')}  |  "
        f"Team productivity: {link('open page', f'{APP_URL}/Team_Productivity')}  |  "
        f"Payroll: {link('open page', f'{APP_URL}/Payroll_and_Cost')}  |  "
        f"Budget/KPI: {link('open page', f'{APP_URL}/Budget_vs_Actual')}",
        ParagraphStyle("LinkLine", parent=styles["BodySmall"], alignment=TA_CENTER),
    ))

    doc.build(story, onFirstPage=page_chrome, onLaterPages=page_chrome)
    return OUTPUT


if __name__ == "__main__":
    print(build_report())
