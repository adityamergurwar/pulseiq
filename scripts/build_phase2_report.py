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
    fontSize=13, leading=16, textColor=INK, spaceBefore=8, spaceAfter=5,
))
styles.add(ParagraphStyle(
    name="BodySmall", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8.5, leading=11, textColor=INK, spaceAfter=3,
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
        ("6 - Attendance and leave", "Attendance rate, holidays, leave type and unusual-month findings", "pages/01_Attendance_and_Leave.py"),
        ("7 - Attrition", "Observed exits, grouped risk, tenure and reasons", "pages/02_Attrition.py"),
        ("8 - Team productivity", "Team/sprint metrics, rules, health comparison and manual checks", "pages/03_Team_Productivity.py"),
        ("9 - Payroll cost", "Cost trend, privacy-safe groups, exclusions and reconciliation", "pages/04_Payroll_and_Cost.py"),
        ("10 - Budget and KPI", "Signed variance, traffic lights, targets and recommendations", "pages/05_Budget_vs_Actual.py"),
    ]
    rows = [[para("Task", "TableHead"), para("Status", "TableHead"), para("Evidence", "TableHead")]]
    for task, evidence, page in evidence_rows:
        url = f"{REPO}/blob/phase-2/{page}"
        rows.append([
            para(task, "TableStrong"),
            para("COMPLETE", "TableStrong"),
            para(f'{link(evidence, url)}<br/><font color="#526174">Validation detail: {link("Phase 2 checks", VALIDATION_URL)}</font>'),
        ])
    table = Table(rows, colWidths=[138, 72, 535.4], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("BACKGROUND", (0, 1), (-1, -1), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F5F8FA")]),
        ("GRID", (0, 0), (-1, -1), 0.45, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TEXTCOLOR", (1, 1), (1, -1), TEAL),
    ]))
    return table


def make_proof_table():
    rows = [
        [para("Area", "TableHead"), para("Verified result", "TableHead")],
        [para("Attendance", "TableStrong"), para(
            "Lowest company rates: May 2026 92.89% (1 holiday, 545 approved leave days); "
            "January 2026 93.29% (3 holidays, 573 leave days); April 2026 93.35% (2 holidays, 405 leave days). "
            "The page marks holiday context without claiming it caused the rate change."
        )],
        [para("Attrition", "TableStrong"), para(
            "September 2026: 3 observed exits (2 voluntary, 1 other); 0.70% monthly attrition. "
            "The baseline risk view is separate and grouped; small groups are suppressed."
        )],
        [para("Teams", "TableStrong"), para(
            "SP-01 manual checks match the metric views. T01: 162 points, 4.64-day cycle, 96.00% on-time, "
            "90.91% complete, 2 blocked, 4 reopened. T02: 210 points, 4.79-day cycle, 93.65% on-time, "
            "92.65% complete, 2 blocked, 4 reopened."
        )],
        [para("Payroll", "TableStrong"), para(
            "PQ-09: 18 of 18 reference months match; the largest clean payroll-to-ledger difference is "
            "INR 0.00000004 against an INR 0.01 tolerance. Four excluded rows are two duplicate run keys and "
            "two unmatched employee references; the app lists row and reason without personal identifiers or pay amounts."
        )],
        [para("Budget and KPI", "TableStrong"), para(
            "September 2026 independent variances: D01 +INR 214,404.24 (+1.03%, amber), D03 +INR 30,889.62 "
            "(+0.48%, amber), D02 -INR 42,581.21. D01 and D03 are the two largest overspends and each has a "
            "review-open-roles/overtime action. KPI status follows each target's direction."
        )],
    ]
    table = Table(rows, colWidths=[104, 641.4], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F5F8FA")]),
        ("GRID", (0, 0), (-1, -1), 0.45, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


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

    # Page 1: concise overview, links and task status/evidence.
    story.append(Paragraph("DATA ANALYTICS TRACK  /  PHASE 2", styles["Eyebrow"]))
    story.append(Paragraph("PulseIQ Phase 2: People and Teams", styles["ReportTitle"]))
    story.append(Paragraph("Aditya Mergurwar  |  Data Analytics Track  |  Phase 2", styles["Meta"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Repository: {link(TAG_URL, TAG_URL)}<br/>Git tag: {link('phase-2', TAG_URL)}<br/>"
        f"Live dashboard: {link(APP_URL, APP_URL)}",
        styles["BodySmall"],
    ))
    story.append(Spacer(1, 2))
    story.append(section("Build summary"))
    story.append(Paragraph(
        "Five connected dashboard modules extend the existing workforce analytics foundation: attendance and leave, "
        "attrition, team delivery, payroll cost, and budget/KPI monitoring. Governed DuckDB views supply consistent "
        "definitions to the Streamlit pages. The build adds calendar-aware attendance context, a clearly separated "
        "grouped risk signal, sprint-level delivery measures, privacy-safe payroll aggregates, and signed budget variance "
        "with specific follow-up actions.",
        styles["BodySmall"],
    ))
    story.append(section("Five task outcomes and evidence"))
    story.append(make_task_table())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"All five Phase 2 tasks have working local pages and validation evidence. The {link('validation note', VALIDATION_URL)} "
        "contains the hand-check values, reference reconciliation and test summary.",
        styles["BodySmall"],
    ))

    story.append(PageBreak())

    # Page 2: concrete proof, short learning notes, issues/fixes and next phase.
    story.append(Paragraph("VERIFICATION", styles["Eyebrow"]))
    story.append(Paragraph("Evidence and outcomes", styles["ReportTitle"]))
    stats = Table([
        [para("18", "StatValue"), para("18 / 18", "StatValue"), para("28 / 28", "StatValue"), para("0", "StatValue")],
        [para("automated tests passed", "StatLabel"), para("payroll reference months match", "StatLabel"),
         para("metric views populated", "StatLabel"), para("declared warehouse orphans", "StatLabel")],
    ], colWidths=[186.375] * 4, hAlign="LEFT")
    stats.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B7D9D5")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B7D9D5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(stats)
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        "The latest acceptance run covers 29 source tables with no unexplained row-count differences; all 28 governed "
        "metric views return results. Independent checks confirm the scheduled-day attendance denominator, two team/sprint "
        "calculations, three budget variances and the complete PQ-09 reference comparison.",
        styles["BodySmall"],
    ))
    story.append(section("Task-level proof"))
    story.append(make_proof_table())
    story.append(section("Learning notes"))
    for text in [
        "Calendar context should accompany attendance rates before a month is interpreted.",
        "Observed exits and predicted risk answer different questions and should remain separate.",
        "Velocity needs cycle time, on-time delivery, blocked work and reopen counts for a fair team view.",
        "Reconciliation proves cost totals; a written variance sign makes the action clear.",
    ]:
        story.append(Paragraph(f"- {text}", styles["BodySmall"]))
    story.append(section("Issues, fixes and next phase"))
    story.append(Paragraph(
        "Four invalid payroll rows were traced to duplicate run keys or unmatched employee references; clean reporting "
        "excludes them with row-level reasons while preserving the raw source. Attendance dips now include leave and holiday "
        "context, and the team page balances velocity with delivery-quality measures. Next, extend the governed model to "
        "revenue, cash and AI signals, and connect refreshes to new source data.",
        styles["BodySmall"],
    ))

    story.append(PageBreak())

    # Page 3: screenshot evidence from the running dashboard.
    story.append(Paragraph("DASHBOARD EVIDENCE", styles["Eyebrow"]))
    story.append(Paragraph("Attendance and leave", styles["ReportTitle"]))
    story.append(Paragraph(
        "Live page evidence showing monthly attendance, public-holiday markers, approved leave, late arrivals and overtime. "
        "Task-specific code and verification links are available in the Phase 2 table on page 1.",
        styles["BodySmall"],
    ))
    story.append(Spacer(1, 8))
    screenshot_path = ROOT / "output" / "evidence" / "PulseIQ_Attendance_Leave_2026-09.png"
    if not screenshot_path.exists():
        raise FileNotFoundError(f"Missing screenshot evidence: {screenshot_path}")
    screenshot = Image(str(screenshot_path), width=734, height=360, kind="proportional", hAlign="CENTER")
    evidence = Table([[screenshot]], colWidths=[745.5], hAlign="CENTER")
    evidence.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, GRID),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#101318")),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(evidence)
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"Dashboard: {link(APP_URL, APP_URL)}  |  Repository and Phase 2 release: {link(TAG_URL, TAG_URL)}",
        ParagraphStyle("LinkLine", parent=styles["BodySmall"], alignment=TA_CENTER),
    ))

    doc.build(story, onFirstPage=page_chrome, onLaterPages=page_chrome)
    return OUTPUT


if __name__ == "__main__":
    print(build_report())
