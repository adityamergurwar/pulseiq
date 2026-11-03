"""Build the three-page Phase 3 handoff PDF from verified project evidence."""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "DataAnalytics_Aditya_Mergurwar_Phase3_Report.pdf"
REPO = "https://github.com/adityamergurwar/pulseiq"
TAG_URL = f"{REPO}/tree/phase-3"
APP = "https://pulseiq-workforce.streamlit.app"
VALIDATION = f"{REPO}/blob/phase-3/docs/phase3_validation.md"

INK = colors.HexColor("#172334")
TEAL = colors.HexColor("#0F766E")
PALE = colors.HexColor("#E8F4F2")
MUTED = colors.HexColor("#526174")
GRID = colors.HexColor("#D5DEE7")
WHITE = colors.white

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="Eyebrow3", parent=styles["Normal"], fontName="Helvetica-Bold",
    fontSize=8, leading=10, textColor=TEAL, spaceAfter=3,
))
styles.add(ParagraphStyle(
    name="Title3", parent=styles["Title"], fontName="Helvetica-Bold",
    fontSize=22, leading=25, textColor=INK, alignment=TA_LEFT, spaceAfter=3,
))
styles.add(ParagraphStyle(
    name="Meta3", parent=styles["Normal"], fontName="Helvetica",
    fontSize=8.4, leading=11, textColor=MUTED,
))
styles.add(ParagraphStyle(
    name="Section3", parent=styles["Heading2"], fontName="Helvetica-Bold",
    fontSize=11.5, leading=13, textColor=INK, spaceBefore=5, spaceAfter=3,
))
styles.add(ParagraphStyle(
    name="Body3", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8.1, leading=10.2, textColor=INK, spaceAfter=2,
))
styles.add(ParagraphStyle(
    name="BodySmall3", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=7.2, leading=8.8, textColor=INK, spaceAfter=1,
))
styles.add(ParagraphStyle(
    name="HeadCell3", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=7.4, leading=8.8, textColor=WHITE,
))
styles.add(ParagraphStyle(
    name="Cell3", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=7.2, leading=8.8, textColor=INK,
))
styles.add(ParagraphStyle(
    name="CellStrong3", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=7.2, leading=8.8, textColor=INK,
))
styles.add(ParagraphStyle(
    name="StatValue3", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=13.5, leading=15, textColor=TEAL, alignment=TA_CENTER,
))
styles.add(ParagraphStyle(
    name="StatLabel3", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=6.9, leading=8.2, textColor=MUTED, alignment=TA_CENTER,
))
styles.add(ParagraphStyle(
    name="CardHead3", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=7.4, leading=8.7, textColor=TEAL,
))
styles.add(ParagraphStyle(
    name="CardBody3", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=7.2, leading=9, textColor=INK,
))
styles.add(ParagraphStyle(
    name="CardBodySmall3", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=6.8, leading=8.2, textColor=INK,
))
styles.add(ParagraphStyle(
    name="LinkCenter3", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=7.5, leading=9, textColor=TEAL, alignment=TA_CENTER,
))


def p(text: str, style: str = "Cell3") -> Paragraph:
    return Paragraph(text, styles[style])


def link(label: str, url: str) -> str:
    return f'<link href="{escape(url, {"\"": "&quot;"})}" color="#0F766E"><u>{escape(label)}</u></link>'


def footer(canvas, doc):
    canvas.saveState()
    width, _ = landscape(A4)
    canvas.setStrokeColor(GRID)
    canvas.setLineWidth(0.45)
    canvas.line(15 * mm, 11 * mm, width - 15 * mm, 11 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(15 * mm, 6.5 * mm, "PulseIQ Phase 3  ·  Data Analytics Track")
    canvas.drawRightString(width - 15 * mm, 6.5 * mm, f"{doc.page} / 3")
    canvas.restoreState()


def section(title: str):
    return Paragraph(escape(title), styles["Section3"])


def task_table():
    task_items = [
        ("11 · P&L and expenses", "PnL_and_Expenses", "06_PnL_and_Expenses.py"),
        ("12 · Receivables and cash", "Receivables_and_Cash", "07_Receivables_and_Cash.py"),
        ("13 · Department impact", "Department_Impact", "08_Department_Impact.py"),
        ("14 · AI signals", "Forecasts_and_Anomalies", "09_Forecasts_and_Anomalies.py"),
        ("15 · Executive scorecard", "Executive_Scorecard", "10_Executive_Scorecard.py"),
    ]
    rows = [[p("Task", "HeadCell3"), p("Status", "HeadCell3"), p("Evidence links", "HeadCell3")]]
    for label, route, source in task_items:
        dashboard_url = f"{APP}/{route}"
        code_url = f"{REPO}/blob/phase-3/pages/{source}"
        rows.append([
            p(escape(label), "CellStrong3"),
            p("DONE", "CellStrong3"),
            p(f"{link('Live page', dashboard_url)}  ·  {link('Source', code_url)}", "Cell3"),
        ])
    table = Table(rows, colWidths=[145, 52, 549], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F4F7FA")]),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (1, 1), (1, -1), TEAL),
    ]))
    return table


def build_cards():
    items = [
        ("Ledger", "Detail-account P&amp;L, expense categories, top vendors and tie-out."),
        ("Cash", "Open AR, ageing, days to pay, overdue clients and cash movement."),
        ("Department", "Aggregate-first join with payroll, overtime, leave and attrition."),
        ("AI", "Risk-ranked anomaly types and an 80% forecast band with limits."),
        ("Scorecard", "Eight governed KPIs with target, trend, status and page links."),
    ]
    cells = []
    for title, body in items:
        card = Table([[p(escape(title), "CardHead3")], [p(body, "CardBodySmall3")]], colWidths=[140])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PALE),
            ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8DAD5")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        cells.append(card)
    table = Table([cells], colWidths=[151.37] * 5, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def stat_cards():
    items = [
        ("26 / 26", "unit tests passed"),
        ("12 / 12", "Phase 3 checks passed"),
        ("18 / 18", "P&L months tie to key"),
        ("INR 0.00", "receivable bucket gap"),
        ("28 / 28", "client averages included"),
        ("180 / 180", "privacy-safe PQ-13 rows"),
        ("8 / 8", "scorecard metrics return"),
        ("0 / 66", "forecast/actual overlap"),
    ]
    cells = []
    for value, label in items:
        card = Table([[p(value, "StatValue3")], [p(escape(label), "StatLabel3")]], colWidths=[177])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PALE),
            ("BOX", (0, 0), (-1, -1), 0.45, colors.HexColor("#B8DAD5")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        cells.append(card)
    table = Table([cells[:4], cells[4:]], colWidths=[188.5] * 4, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return table


def challenge_cards():
    cards = [
        ("P&L · Sep 2026", "Revenue INR 80.27m<br/>Net profit INR 14.99m<br/>Operating margin 18.67%"),
        ("Receivables · 30 Sep", "Open AR INR 139.39m<br/>Past due INR 27.11m<br/>Age buckets reconcile exactly."),
        ("Cash · Sep ledger", "Cash in INR 84.67m<br/>Cash out INR 68.68m<br/>Net movement +INR 15.98m."),
        ("Department impact · Sep", "Employer payroll INR 55.52m<br/>Overtime pay INR 0.193m<br/>No bank opening balance supplied."),
    ]
    row = []
    for title, body in cards:
        card = Table([[p(escape(title), "CardHead3")], [p(body, "CardBody3")]], colWidths=[177])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F7FA")),
            ("BOX", (0, 0), (-1, -1), 0.45, GRID),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        row.append(card)
    table = Table([row], colWidths=[188.5] * 4, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def margin_table():
    rows = [
        [p("Possible driver", "HeadCell3"), p("April evidence", "HeadCell3"), p("Evidence needed to confirm", "HeadCell3")],
        [p("Expense growth outpaced revenue", "CellStrong3"),
         p("Revenue rose 11.4%; ledger expenses rose 20.7%; margin fell 6.95 percentage points.", "Cell3"),
         p("Separate recurring from one-off postings; inspect invoice timing and expense-account detail.", "Cell3")],
        [p("Revenue mix shifted", "CellStrong3"),
         p("Consulting rose INR 7.48m and support rose INR 6.43m; software services fell INR 3.41m.", "Cell3"),
         p("Compare price, volume and direct contribution margin by service, client or contract.", "Cell3")],
        [p("People cost or staffing mix changed", "CellStrong3"),
         p("Employer payroll rose 26.6% to INR 62.17m, while overtime pay fell to INR 0.166m.", "Cell3"),
         p("Reconcile payroll postings to the ledger; compare headcount, salary mix, vacancies and utilization.", "Cell3")],
    ]
    table = Table(rows, colWidths=[150, 284, 312], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F4F7FA")]),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def build_report() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=landscape(A4),
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=11 * mm, bottomMargin=16 * mm,
        title="PulseIQ Phase 3: Money and Insight",
        author="Aditya Mergurwar",
        subject="Data Analytics Track, Phase 3 build and validation",
    )
    story = []

    # Page 1 — handoff summary and one evidence link for each task.
    story.extend([
        Paragraph("DATA ANALYTICS TRACK  /  PHASE 3", styles["Eyebrow3"]),
        Paragraph("PulseIQ Phase 3: Money and Insight", styles["Title3"]),
        Paragraph("Aditya Mergurwar  ·  Data Analytics Track  ·  Snapshot through 30 September 2026", styles["Meta3"]),
        Spacer(1, 3),
        Paragraph(
            f"GitHub repository: {link(REPO, REPO)}  ·  Git tag: {link('phase-3', TAG_URL)}<br/>"
            f"Live dashboard: {link(APP, APP)}  ·  Validation: {link('Phase 3 checks', VALIDATION)}",
            styles["Body3"],
        ),
        section("What is in the build"),
        Paragraph(
            "Five Phase 3 pages connect ledger performance, customer cash collection, department effects, model signals and executive KPIs. "
            "The build uses governed metric views, preserves traceability to supplied source records, and surfaces the limits of the training snapshot.",
            styles["Body3"],
        ),
        Spacer(1, 2),
        build_cards(),
        section("Task status and evidence"),
        task_table(),
        Spacer(1, 4),
        Paragraph(
            "The dashboard links open the Phase 3 page for each task; the source links open the matching implementation at the phase tag.",
            styles["BodySmall3"],
        ),
    ])

    story.append(PageBreak())

    # Page 2 — repeatable checks and the five-minute management challenge.
    story.extend([
        Paragraph("VERIFICATION  /  OPERATING READOUT", styles["Eyebrow3"]),
        Paragraph("Proof and mini challenge", styles["Title3"]),
        stat_cards(),
        section("What the checks establish"),
        Paragraph(
            "The P&amp;L ties month by month to the official PQ-09 ledger key and balances revenue plus other income less expenses to net profit. "
            "Open invoice balances use SENT, OVERDUE and PARTIALLY_PAID; the requested ageing buckets plus not-due sum to the same open-AR total. "
            "All 28 clients with paid invoice history are included in payment-speed averages. The privacy-safe department comparison matches 180 of 180 eligible reference rows; non-task fields match, while task differences trace to quarantined source rows.",
            styles["Body3"],
        ),
        section("Mini challenge · Five-minute answer: Does September profit mean cash is available?"),
        challenge_cards(),
        Spacer(1, 4),
        Paragraph(
            "Read across the P&amp;L, Receivables and Cash, and Department Impact pages. Positive September profit and positive ledger cash movement are encouraging, "
            "but INR 27.11m is past due and INR 139.39m remains open. Payroll is a recurring obligation. A 75-day payer is a risk only if that exceeds contracted terms or balances are overdue; Finance should confirm terms, disputes, concentration and promised receipts. The ledger cash trend cannot prove bank liquidity because no opening bank balance or forward obligations were supplied.",
            styles["Body3"],
        ),
        Paragraph(
            "Hand checks: INR 80,268,200 revenue + INR 333,495 other income − INR 65,615,715.87 expenses = INR 14,985,979.13 net profit. "
            "Receivable bucket total − open AR = INR 0.00. Finance follow-up: confirm bank position, due terms, disputed invoices, expected receipt dates and upcoming payroll/payables.",
            styles["BodySmall3"],
        ),
    ])

    story.append(PageBreak())

    # Page 3 — evidence-led interpretation, learning, fixes and Phase 4 plan.
    story.extend([
        Paragraph("ANALYSIS  /  NEXT PHASE", styles["Eyebrow3"]),
        Paragraph("Margin case, learning and next steps", styles["Title3"]),
        Paragraph(
            "April 2026 is the clearest supplied example of revenue growing while margin falls: revenue increased from INR 74.88m to INR 83.45m (+11.4%), "
            "expenses increased from INR 59.64m to INR 72.00m (+20.7%), and operating margin moved from 20.67% to 13.72% (-6.95 percentage points).",
            styles["Body3"],
        ),
        margin_table(),
        Spacer(1, 3),
        Paragraph(
            "April expense-register context: Office Rent was INR 2.81m; Insurance was INR 2.50m; Skyline Realty Holdings was the largest vendor at INR 2.40m. "
            "The submitted-expense register includes GST and is a separate source from the ledger P&amp;L, so these amounts are investigative context rather than a P&amp;L tie-out.",
            styles["BodySmall3"],
        ),
        section("What the build made clear"),
        Paragraph(
            "• Aggregate sources to the same department and month before joining to prevent duplicated measures.",
            styles["BodySmall3"],
        ),
        Paragraph(
            "• Reconciliation compares independent totals for the same period and definition; the bucket check is a practical example.",
            styles["BodySmall3"],
        ),
        Paragraph(
            "• A positive variance means actual exceeds budget; a negative variance means actual is below budget.",
            styles["BodySmall3"],
        ),
        Paragraph(
            "• Forecast error requires overlapping actuals; a confidence band is not an accuracy score.",
            styles["BodySmall3"],
        ),
        section("Problems and fixes"),
        Paragraph(
            "The workbook README contains data-volume headlines but no P&amp;L amounts; a clean-ledger snapshot was added to the project README and independently checked against PQ-09. "
            "The client collection view initially limited averages to clients with five paid invoices; that cutoff was removed so all clients with paid history are covered. "
            "Twenty invalid task rows are quarantined, producing task-field differences in 19 department-month groups; payroll, attendance, headcount and attrition reference fields match.",
            styles["Body3"],
        ),
        section("Plan for Phase 4"),
        Paragraph(
            "1. Load a new source period and rerun the contract, quarantine and reconciliation checks. &nbsp; "
            "2. Package and monitor repeatable monthly PDF/Excel refreshes and the hosted dashboard. &nbsp; "
            "3. Review authentication, metric ownership and the API with users before enabling broader self-service.",
            styles["Body3"],
        ),
        Paragraph(
            f"Data boundary: the supplied actuals end 30 September 2026, while 66 forecast rows begin in October; forecast accuracy is not estimable yet. "
            f"Source-level seeded findings remain visible in the quality review. {link('Validation detail', VALIDATION)}  ·  {link('Open dashboard', APP)}",
            styles["BodySmall3"],
        ),
    ])

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return OUTPUT


if __name__ == "__main__":
    print(build_report())
