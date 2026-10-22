"""Create the Phase 1 evidence report from verified project results and a live-app screenshot."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "DataAnalytics_Aditya_Mergurwar_Phase1_Report.pdf"
SCREENSHOT = ROOT / "output" / "evidence" / "PulseIQ_Live_Dashboard_2026-10-22.png"
INK = colors.HexColor("#14213d")
TEAL = colors.HexColor("#117c78")
PALE = colors.HexColor("#e8f3f1")
MUTED = colors.HexColor("#526179")
LINE = colors.HexColor("#d4dde7")


def make_table(data, widths, header=True, font_size=8.5):
    wrapped = []
    for ri, row in enumerate(data):
        wrapped.append([Paragraph(str(cell), styles["TableHeader" if header and ri == 0 else "TableCell"]) for cell in row])
    table = Table(wrapped, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
    ]
    if header:
        commands += [("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
    if len(data) > (1 if header else 0):
        commands.append(("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, PALE]))
    table.setStyle(TableStyle(commands))
    return table


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleCustom", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=INK, alignment=TA_LEFT, spaceAfter=5))
styles.add(ParagraphStyle(name="Deck", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=12, textColor=MUTED, spaceAfter=5))
styles.add(ParagraphStyle(name="SectionCustom", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=TEAL, spaceBefore=8, spaceAfter=4))
styles.add(ParagraphStyle(name="BodyCustom", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.7, leading=12, textColor=INK, spaceAfter=4))
styles.add(ParagraphStyle(name="TableHeader", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white))
styles.add(ParagraphStyle(name="TableCell", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.8, leading=10, textColor=INK))
styles.add(ParagraphStyle(name="Note", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.6, leading=10, textColor=MUTED))
styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9, leading=13, textColor=INK, backColor=PALE, borderColor=TEAL, borderWidth=0.6, borderPadding=7, spaceBefore=4, spaceAfter=6))


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=15 * mm, bottomMargin=17 * mm, title="PulseIQ Phase 1 Report", author="Aditya Mergurwar")
    story = [
        Paragraph("PulseIQ | Phase 1 Report", styles["TitleCustom"]),
        Paragraph("Aura Workforce by Growmar - Data Analytics Track - Foundation", styles["Deck"]),
    ]
    meta = [
        ["Author", "Aditya Mergurwar", "Data cutoff", "30 Sep 2026"],
        ["Repository", "Private GitHub: main published", "Phase tag", "phase-1 at 965d9f6"],
        ["Live dashboard", "pulseiq-workforce.streamlit.app", "Production login", "Pending hosted secrets"],
    ]
    story.append(make_table(meta, [22 * mm, 67 * mm, 23 * mm, 50 * mm], header=False, font_size=7.6))
    story += [Spacer(1, 5), Paragraph("Phase 1 built a validated local warehouse, a 28-metric governed layer, and the first workforce dashboard. The private GitHub repository and phase tag are published, and the dashboard is deployed. Production login, phone/viewer verification and programme submission still need the account and owner actions listed on page 2.", styles["Callout"])]
    story.append(Paragraph("Five task outcomes", styles["SectionCustom"]))
    tasks = [
        ["Task", "Result", "Evidence"],
        ["1. ETL and contracts", "Complete locally", "29 CSV feeds; row counts reconcile; 297 dictionary checks across 23 operational tables; quarantines have reasons."],
        ["2. Star schema", "Complete locally", "0 declared orphans; employee history joins by employee_key; diagram and join map are documented."],
        ["3. Data quality", "Complete locally", "14 checks run on every load and each has an injection test; all 11 planted issue categories were detected."],
        ["4. Governed metrics", "Complete locally", "28 views return rows; catalog carries formula, source, owner and minimum group size; hand checks match."],
        ["5. Workforce dashboard", "Complete locally", "Month and department filters, five CEO questions, workforce cards, trend and mix charts with numeric insights."],
    ]
    story.append(make_table(tasks, [31 * mm, 30 * mm, 101 * mm], font_size=7.8))
    story.append(Paragraph("Validation evidence", styles["SectionCustom"]))
    checks = [
        ["Check", "Result"],
        ["Automated tests", "13 passed, including dashboard query, monthly Excel export, host-secret configuration, salary-role access, department-scope and seeded-issue disposition regressions."],
        ["Rerun safety", "Two full ETL refreshes produced identical row counts and business snapshots, with 31 invalid rows quarantined and explained."],
        ["Metric layer", "28 of 28 governed metric views return rows; M28 error is null because actuals and forecasts do not overlap."],
        ["Payroll reconciliation", "18 of 18 reference months match; maximum clean payroll-to-ledger difference INR 0.00000004 (tolerance INR 0.01)."],
        ["Department comparison", "180 privacy-safe rows match; 18 one-person D00 rows are withheld; task differences match quarantined rows."],
    ]
    story.append(make_table(checks, [37 * mm, 125 * mm], font_size=7.8))
    story.append(Paragraph("Raw DQ findings intentionally remain visible. The data-quality page reports REVIEW REQUIRED until an owner reviews the seeded findings; the clean-layer checks and calculations are reported separately.", styles["Note"]))
    story.append(PageBreak())

    story.append(Paragraph("Metric checks and decisions", styles["TitleCustom"]))
    story.append(Paragraph("Five independent calculations", styles["SectionCustom"]))
    hand = [
        ["Metric", "Independent calculation", "Governed view", "Result"],
        ["M01 headcount, D01", "167", "167", "Pass"],
        ["M07 gross pay, D01", "INR 20,720,901.38", "INR 20,720,901.38", "Pass"],
        ["M13 attendance rate, D01", "96.1784%", "96.1784%", "Pass"],
        ["M17 ledger net profit", "INR 14,985,979.13", "INR 14,985,979.13", "Pass"],
        ["M20 event-based DSO", "47.9977 days", "47.9977 days", "Pass"],
    ]
    story.append(make_table(hand, [39 * mm, 45 * mm, 45 * mm, 22 * mm], font_size=7.7))
    story.append(Paragraph("Questions answered by the first dashboard", styles["SectionCustom"]))
    questions = [
        "How many people are in the workforce now, and how has headcount changed over time?",
        "Which departments account for the largest share of headcount?",
        "How many people joined and left in the selected month?",
        "Which location tier contains the most employees?",
        "Which work mode is most common?",
    ]
    for question in questions:
        story.append(Paragraph("- " + question, styles["BodyCustom"]))
    story.append(Paragraph("Learning summary - owner review", styles["SectionCustom"]))
    story.append(Paragraph("The implementation shows how preserving source rows and quarantining invalid rows keeps counts explainable. Employee history must join by the version key for a time-correct department result. A governed metric view keeps dashboards and the API on one formula. A group can be analytically valid and still be unsafe to display. Confirm this summary reflects your own experience before submission.", styles["BodyCustom"]))
    story.append(Paragraph("Problems and fixes", styles["SectionCustom"]))
    story.append(Paragraph("The workforce page raised a DuckDB invalid-input error because the prior-month query had three placeholders but received two values. The department filter is now bound twice and the selected period once, with a regression test for company and department scopes. Seeded payroll, attendance, task, invoice, leave, expense, attrition-risk and SCD issues remain in raw evidence and are documented with their clean-layer handling.", styles["BodyCustom"]))
    story.append(Paragraph("Next phase and submission", styles["SectionCustom"]))
    story.append(Paragraph("The private GitHub main branch is published with the latest deployment readiness update; the phase-1 tag remains pinned to release commit 965d9f6. A monthly warehouse/report workflow is configured; its first hosted run and a changing source feed remain unconfirmed. Still required for formal submission: save production login secrets and verify role access, review the seeded raw-data findings, add fobesitech as a collaborator, test the live link on a phone and with another viewer, record the five-minute demo, confirm the personal learning reflection and upload the required files.", styles["BodyCustom"]))
    story.append(Paragraph("Source: supplied fictional PulseIQ data, validation vault and project playbook. Detailed results are in docs/validation_results.md and docs/task_acceptance_matrix.md.", styles["Note"]))
    if SCREENSHOT.exists():
        story.append(PageBreak())
        story.append(Paragraph("Live dashboard evidence", styles["TitleCustom"]))
        story.append(Paragraph("Owner-supplied browser screenshot of the deployed app at pulseiq-workforce.streamlit.app. This proves the dashboard rendered at the public URL; the visible demo persona selector also shows that production login still needs to be enabled.", styles["Deck"]))
        story.append(Spacer(1, 5))
        story.append(Image(str(SCREENSHOT), width=174 * mm, height=98 * mm, kind="bound"))
        story.append(Spacer(1, 5))
        story.append(Paragraph("The screenshot uses fictional Zenith Nova training data. Do not use this demo persona as production authentication.", styles["Note"]))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, 12 * mm, A4[0] - 18 * mm, 12 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 8 * mm, "PulseIQ - Fictional Zenith Nova training data")
        canvas.drawRightString(A4[0] - 18 * mm, 8 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return OUTPUT


if __name__ == "__main__":
    print(build())
