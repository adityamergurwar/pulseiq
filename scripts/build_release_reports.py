"""Build the Phase 4 and consolidated PulseIQ release reports."""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf"
PHASE4 = OUT / "DataAnalytics_Aditya_Mergurwar_Phase4_Report.pdf"
CONSOLIDATED = OUT / "DataAnalytics_Aditya_Mergurwar_Consolidated_Report.pdf"
REPO = "https://github.com/adityamergurwar/pulseiq"
APP = "https://pulseiq-workforce.streamlit.app"
TAG = f"{REPO}/tree/phase-4"

INK = colors.HexColor("#152238")
TEAL = colors.HexColor("#0B7A75")
ORANGE = colors.HexColor("#D97706")
MUTED = colors.HexColor("#56657A")
GRID = colors.HexColor("#D5DEE8")
PALE = colors.HexColor("#EAF5F3")
SOFT = colors.HexColor("#F5F7FA")
WHITE = colors.white

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="EyebrowR", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=TEAL, spaceAfter=3))
styles.add(ParagraphStyle(name="TitleR", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=23, leading=26, textColor=INK, alignment=TA_LEFT, spaceAfter=4))
styles.add(ParagraphStyle(name="SubR", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=MUTED, spaceAfter=3))
styles.add(ParagraphStyle(name="SectionR", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=14, textColor=INK, spaceBefore=5, spaceAfter=4))
styles.add(ParagraphStyle(name="BodyR", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.2, leading=10.4, textColor=INK, spaceAfter=3))
styles.add(ParagraphStyle(name="SmallR", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.2, leading=8.8, textColor=INK, spaceAfter=2))
styles.add(ParagraphStyle(name="HeadR", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.4, leading=8.8, textColor=WHITE))
styles.add(ParagraphStyle(name="CellR", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.2, leading=8.7, textColor=INK))
styles.add(ParagraphStyle(name="CellBoldR", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.2, leading=8.7, textColor=INK))
styles.add(ParagraphStyle(name="StatR", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=15, leading=17, textColor=TEAL, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="StatLabelR", parent=styles["BodyText"], fontName="Helvetica", fontSize=6.7, leading=8, textColor=MUTED, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="CardHeadR", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=9.5, textColor=TEAL))
styles.add(ParagraphStyle(name="CardR", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.3, leading=9.2, textColor=INK))
styles.add(ParagraphStyle(name="CoverR", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=30, leading=33, textColor=INK, alignment=TA_LEFT, spaceAfter=8))
styles.add(ParagraphStyle(name="QuoteR", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=TEAL, alignment=TA_LEFT))


def p(text, style="BodyR"):
    return Paragraph(text, styles[style])


def link(label, url):
    return f'<link href="{escape(url)}" color="#0B7A75"><u>{escape(label)}</u></link>'


def footer(label, total):
    def draw(canvas, doc):
        canvas.saveState()
        width, _ = landscape(A4)
        canvas.setStrokeColor(GRID)
        canvas.line(15 * mm, 11 * mm, width - 15 * mm, 11 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(15 * mm, 6.5 * mm, label)
        canvas.drawRightString(width - 15 * mm, 6.5 * mm, f"{doc.page} / {total}")
        canvas.restoreState()
    return draw


def stat_row(items):
    cells = []
    for value, label in items:
        card = Table([[p(value, "StatR")], [p(label, "StatLabelR")]], colWidths=[135])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), .5, colors.HexColor("#B9DBD6")),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        cells.append(card)
    table = Table([cells], colWidths=[151] * len(cells), hAlign="LEFT")
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    return table


def info_cards(items, width=180):
    cells = []
    for title, body in items:
        card = Table([[p(title, "CardHeadR")], [p(body, "CardR")]], colWidths=[width])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SOFT), ("BOX", (0, 0), (-1, -1), .45, GRID),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        cells.append(card)
    col = 756 / len(cells)
    outer = Table([cells], colWidths=[col] * len(cells), hAlign="LEFT")
    outer.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    return outer


def picture(path, width=360, height=202, caption=None):
    img = Image(str(path), width=width, height=height, kind="proportional")
    rows = [[img]]
    if caption:
        rows.append([p(caption, "SmallR")])
    t = Table(rows, colWidths=[width + 12])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT), ("BOX", (0, 0), (-1, -1), .5, GRID),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"), ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def two_pictures(left_path, left_caption, right_path, right_caption):
    t = Table([[picture(left_path, 350, 197, left_caption), picture(right_path, 350, 197, right_caption)]], colWidths=[378, 378])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    return t


def phase4_task_table():
    rows = [[p("Task", "HeadR"), p("Status", "HeadR"), p("Build and evidence", "HeadR")]]
    values = [
        ("16 · Reporting package", "DONE", "One-command PDF/Excel for any available month; exact pins; scheduled Python 3.11 workflow; clean-environment test; D99 dynamic-department fixture."),
        ("17 · Production go-live", "LIVE", f"Public aggregate dashboard: {link('open app', APP)}. Streamlit selected for fast Python delivery; Render blueprint supplied for the API; secrets stay in host storage."),
        ("18 · KPI explorer", "DONE", "Catalog-driven metric selection, company/department/team drill-down, four demo roles, fixed scope, and minimum-group suppression with documented break tests."),
        ("19 · API and lineage", "DONE", f"Five governed FastAPI metrics with value, definition, source, freshness and privacy. {link('API guide', REPO + '/blob/phase-4/docs/api.md')} and source-to-dashboard lineage included."),
        ("20 · Board release", "DONE", "Nine-slide board pack, release notes, consolidated report, demo script and independent M29 challenge committed on its own branch before merge."),
    ]
    for task, status, evidence in values:
        rows.append([p(task, "CellBoldR"), p(status, "CellBoldR"), p(evidence, "CellR")])
    t = Table(rows, colWidths=[148, 55, 553], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, SOFT]),
        ("GRID", (0, 0), (-1, -1), .4, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (1, 1), (1, -1), TEAL),
    ]))
    return t


def build_phase4():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(PHASE4), pagesize=landscape(A4), leftMargin=15*mm, rightMargin=15*mm, topMargin=13*mm, bottomMargin=15*mm, title="PulseIQ Phase 4 Report", author="Aditya Mergurwar")
    story = [
        p("DATA ANALYTICS TRACK · PHASE 4", "EyebrowR"), p("PulseIQ Phase 4: Release Day", "TitleR"),
        p(f"Aditya Mergurwar · {link('GitHub repository', REPO)} · {link('phase-4 tag', TAG)} · {link('live dashboard', APP)}", "SubR"),
        Spacer(1, 3), phase4_task_table(), Spacer(1, 6),
        p("Release proof", "SectionR"),
        stat_row([("29 / 29", "automated tests pass"), ("11 / 11", "Phase 4 checks pass"), ("29", "governed metrics"), ("0", "declared orphans"), ("18 / 18", "finance months reconcile")]),
        Spacer(1, 5),
        p("The fixed fictional data snapshot ends on 30 September 2026. The workflow rebuilds and validates that snapshot on schedule and when source or pipeline files change. A new source delivery is required to advance the cutoff.", "SmallR"),
        PageBreak(),
        p("RELEASE EVIDENCE", "EyebrowR"), p("Dashboard and board-ready outputs", "TitleR"),
        p("The live product combines governed people, delivery and finance metrics; the board pack reduces those results to decision-oriented evidence and explicit limits.", "SubR"),
        two_pictures(ROOT / "output/evidence/phase3/executive_scorecard.png", "Executive scorecard: eight governed KPIs with target and trend context.", ROOT / "output/evidence/phase4/board_actions.png", "Board recommendation slide: owned actions, timing and measurable outcomes."),
        Spacer(1, 6),
        info_cards([
            ("Reporting", "September PDF and nine-sheet Excel pack rebuild from the warehouse with one command. Files carry the reporting month and data cutoff."),
            ("Deployment", "Streamlit serves the public training dashboard. GitHub Actions runs tests and monthly artifacts; Docker and Render files make the API portable."),
            ("Privacy", "Role scope is applied before queries return. Small groups, employee identifiers and client rows are excluded from release views."),
            ("Decision support", "M29 shows what share of open receivables is already overdue, complementing DSO and the absolute past-due balance."),
        ], width=170),
        PageBreak(),
        p("PROOF AND REFLECTION", "EyebrowR"), p("One number, explained and checked", "TitleR"),
        p("M29 · Overdue receivables share at 30 September 2026", "SectionR"),
        info_cards([
            ("1 · Raw row", "Each invoice supplies invoice date, due date, status and total; payment rows supply payment date and amount."),
            ("2 · Clean", "Contract-passing invoice and payment rows retain dates and numeric amounts; draft and cancelled invoices are excluded."),
            ("3 · Month end", "Payments received by 30 September are subtracted from invoice totals; only positive balances remain open."),
            ("4 · Governed metric", "Past-due open balance is divided by all open balance and multiplied by 100 in metrics.m29_overdue_receivables_share."),
            ("5 · Chart", "The catalog exposes the company aggregate to ADMIN and EXECUTIVE in the KPI explorer; no client row is returned."),
        ], width=138),
        Spacer(1, 6),
        p("Hand proof", "SectionR"),
        p("Past due INR 27,110,866 ÷ open receivables INR 139,394,278 × 100 = <b>19.449%</b>. The automated test independently recomputes the same ratio from the ageing view and matches M29 to eight decimal places.", "BodyR"),
        info_cards([
            ("Reconciliation in plain language", "Reconciliation means two independent routes to the same answer agree. Payroll detail and the ledger match for all 18 months within one paisa."),
            ("Variance in plain language", "Variance is actual minus plan. Positive payroll variance means overspend; negative means cost finished below budget."),
            ("Problem solved", "Unsupported future GitHub Action versions and loose dependencies were replaced with supported actions and exact versions; clean-environment evidence was rerun."),
            ("What was learned", "A release is more than charts: calculations need ownership, freshness, privacy, reproducibility, deployment evidence and an honest operating boundary."),
        ], width=170),
        Spacer(1, 5),
        p("Next phase plan: connect a changing source feed, deploy the API blueprint in the selected hosting account, observe the first scheduled production run, and add actual months so forecast accuracy becomes measurable.", "SmallR"),
    ]
    doc.build(story, onFirstPage=footer("PulseIQ Phase 4 · Aditya Mergurwar", 3), onLaterPages=footer("PulseIQ Phase 4 · Aditya Mergurwar", 3))
    return PHASE4


def module_table():
    rows = [[p("Layer", "HeadR"), p("Build", "HeadR"), p("Control", "HeadR")],
            [p("Source + raw", "CellBoldR"), p("29 supplied CSV tables retained as delivered", "CellR"), p("Row counts, source dictionary and unexpected-column logging", "CellR")],
            [p("Clean + audit", "CellBoldR"), p("Type/contract checks, corrections and quarantine", "CellR"), p("Reason, source row and JSON evidence preserved", "CellR")],
            [p("Warehouse", "CellBoldR"), p("Conformed dimensions and employee-key facts", "CellR"), p("Declared relationship audit; zero orphan rows", "CellR")],
            [p("Metrics", "CellBoldR"), p("M01-M29 governed views and safe presentation views", "CellR"), p("Definition, grain, owner, caveat and privacy floor", "CellR")],
            [p("Products", "CellBoldR"), p("Streamlit, FastAPI, PDF, Excel and board deck", "CellR"), p("Tests, freshness, release tags and scheduled rebuild", "CellR")]]
    t = Table(rows, colWidths=[125, 305, 326], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), INK), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, SOFT]), ("GRID", (0, 0), (-1, -1), .4, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def report_page(story, eyebrow, title, subtitle=None):
    story.extend([p(eyebrow, "EyebrowR"), p(title, "TitleR")])
    if subtitle:
        story.append(p(subtitle, "SubR"))


def build_consolidated():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(CONSOLIDATED), pagesize=landscape(A4), leftMargin=15*mm, rightMargin=15*mm, topMargin=13*mm, bottomMargin=15*mm, title="PulseIQ Consolidated Report", author="Aditya Mergurwar")
    s = []
    report_page(s, "DATA ANALYTICS TRACK · FINAL RELEASE", "PulseIQ", "A governed workforce, delivery and finance analytics product for Zenith Nova Technologies' fictional training data.")
    s += [Spacer(1, 18), p("From supplied rows to board decisions", "QuoteR"), Spacer(1, 12),
          info_cards([("Repository", link("github.com/adityamergurwar/pulseiq", REPO)), ("Live dashboard", link("pulseiq-workforce.streamlit.app", APP)), ("Release", link("phase-4 · v1.0.0", TAG)), ("Board pack", "Nine slides · September 2026")], width=170), Spacer(1, 18),
          stat_row([("29", "governed metrics"), ("12", "analytics pages"), ("29 / 29", "tests pass"), ("0", "declared orphans"), ("18 / 18", "finance months tie")]), Spacer(1, 12),
          p("Build scope: reproducible data pipeline, data quality, workforce and people analytics, team delivery, payroll and budget, P&L and cash, AI review signals, executive scorecard, role-aware exploration, API, scheduled reporting and board release artifacts.", "BodyR"),
          PageBreak()]

    report_page(s, "1 · PRODUCT", "What PulseIQ solves", "Leaders need one consistent view of workforce scale, cost, delivery, cash and risk without exposing individual records.")
    s += [info_cards([("Users", "Executive leaders, HR, finance, engineering managers and analytics administrators."), ("Decisions", "Hiring and capacity, attendance follow-up, budget ownership, collections, delivery health and review priorities."), ("Product rule", "Every number must carry a definition, grain, source, freshness and privacy decision."), ("Data boundary", "Fictional fixed snapshot through 30 September 2026; forecasts begin after observed actuals.")], width=170), Spacer(1, 8),
          two_pictures(ROOT / "output/evidence/PulseIQ_Workforce_Overview_2026-09.png", "Workforce overview: month-end headcount, hires, exits and department mix.", ROOT / "output/evidence/phase3/executive_scorecard.png", "Executive scorecard: a compact route from governed KPIs to detail pages."), PageBreak()]

    report_page(s, "2 · ARCHITECTURE", "How the build is governed", "Each product reads controlled views instead of repeating calculations inside charts.")
    s += [module_table(), Spacer(1, 10),
          info_cards([("Raw evidence", "Source values are never overwritten. Invalid records keep their source table, row number and reason."), ("Conformed truth", "Documented SCD and ledger corrections are recorded in audit tables; facts join employee history through employee_key."), ("Metric contract", "M01-M29 share a dictionary/catalog. The dashboard, API and reports consume the same governed calculations."), ("Release path", "Pinned runtime → tests → validation → packs → tagged commit → scheduled refresh and hosted products.")], width=170), Spacer(1, 10),
          p("Core relationship: source CSV → raw → clean/quarantine → warehouse → governed metric → dashboard/API/report. This separation keeps evidence, calculation and presentation independently testable.", "BodyR"), PageBreak()]

    report_page(s, "3 · PHASE 1", "Foundation: contracts, warehouse and first dashboard", "The first release established repeatable ingestion, traceable quality controls and reusable metrics.")
    s += [two_pictures(ROOT / "output/evidence/PulseIQ_Live_Dashboard_2026-10-22.png", "Published Streamlit dashboard evidence.", ROOT / "output/evidence/PulseIQ_Attendance_Leave_2026-09.png", "Attendance view built from scheduled working-day denominators."), Spacer(1, 7),
          info_cards([("Ingestion", "29 tables load with rows-in, passed, quarantined and reconciliation totals."), ("Quality", "Fourteen checks detect the validation-vault issue categories; dispositions remain auditable."), ("Warehouse", "Conformed dimensions/facts pass every declared relationship check with zero orphans."), ("Metrics", "Definitions, source, grain, owner, unit, caveat and minimum-group size govern reuse.")], width=170), PageBreak()]

    report_page(s, "4 · PHASE 2", "People and team performance", "Attendance, attrition, productivity, payroll and budget views combine formulas with visible decision context.")
    s += [two_pictures(ROOT / "output/evidence/PulseIQ_Phase2_Attendance_2026-10-31.png", "Attendance and leave trends with calendar context.", ROOT / "output/evidence/PulseIQ_Phase2_Budget_2026-10-31.png", "Payroll budget versus actual with signed department variance."), Spacer(1, 7),
          info_cards([("Attendance", "95.2% latest rate; holidays, leave, lateness and overtime remain separate signals."), ("Attrition", "Observed exits and predicted risk are separated; predictions are grouped and labelled."), ("Delivery", "Velocity, cycle time, on-time rate and completion retain blocked/reopened context."), ("Payroll", "Aggregate-only pay views reconcile to the ledger; four invalid payroll rows are excluded with reasons.")], width=170), PageBreak()]

    report_page(s, "5 · PHASE 3", "Money and insight", "P&L, receivables, department impact, anomaly review and the executive scorecard extend the same governed layer.")
    s += [two_pictures(ROOT / "output/evidence/phase3/pnl_expenses.png", "September P&L: revenue, operating expense, profit and margin.", ROOT / "output/evidence/phase3/receivables_cash.png", "Open receivables, past-due value, DSO and ageing."), Spacer(1, 7),
          info_cards([("P&L", "September revenue INR 80.27m; net profit INR 14.99m; operating margin 18.67%."), ("Receivables", "Open INR 139.39m; past due INR 27.11m; DSO 48.0 days."), ("Department", "Aggregate-first joins avoid fan-out and suppress the one-person D00 group."), ("AI signals", "405 flags and INR 31.42m reported at risk are review prompts, not confirmed loss.")], width=170), PageBreak()]

    report_page(s, "6 · PHASE 4", "Release engineering and controlled exploration", "The final phase turns a working analysis into a repeatable, deployable and reviewable product.")
    s += [two_pictures(ROOT / "output/evidence/phase4/board_snapshot.png", "Board snapshot with workforce, profit, cash and collections signals.", ROOT / "output/evidence/phase4/board_quality.png", "Quality and release guardrails included in the board narrative."), Spacer(1, 7),
          info_cards([("Automation", "Exact pins, Python 3.11 workflow, manual/monthly triggers and versioned report artifacts."), ("Explorer", "ADMIN, HR, MANAGER and EXECUTIVE scopes; company/department/team drill-down where supported."), ("API", "Five metrics return value, definition, source, freshness and privacy through FastAPI/OpenAPI."), ("Challenge", "M29 overdue share was built on its own branch, tested independently and merged into release.")], width=170), PageBreak()]

    report_page(s, "7 · ONE NUMBER", "Trace and prove M29 overdue receivables share", "A complete lineage explanation from first row to governed chart.")
    s += [info_cards([("Raw", "Invoice INV rows provide due date and total; linked payment rows provide dated receipts."), ("Clean", "Valid invoice/payment rows retain numeric values. Draft and cancelled invoices are excluded."), ("As of date", "Receipts through month end reduce invoice totals; positive balances remain open."), ("Metric", "100 × overdue open balance ÷ total open balance in metrics.m29_overdue_receivables_share."), ("Explorer", "Catalog entry exposes the company result to ADMIN and EXECUTIVE; no client row is returned.")], width=138), Spacer(1, 10),
          p("Manual proof", "SectionR"), p("INR 27,110,866 ÷ INR 139,394,278 × 100 = <b>19.449%</b>. The automated challenge test recomputes the ratio from the independent ageing presentation view and matches to eight decimal places.", "BodyR"),
          info_cards([("Reconciliation", "Two independent routes agree. Eighteen monthly payroll detail totals and salary-ledger totals match within INR 0.01."), ("Variance", "Actual minus budget. Positive is overspend; negative is under budget. September company payroll is INR 664,616 below plan."), ("Freshness", "Observed cutoff 30 September 2026. A scheduled rebuild does not invent later source rows."), ("Privacy", "Only company aggregate is returned; no employee or client identifier appears in M29.")], width=170), PageBreak()]

    report_page(s, "8 · VALIDATION", "Proof the product works", "Automated tests, independent calculations and release checks cover both happy paths and failure boundaries.")
    s += [stat_row([("29 / 29", "automated tests"), ("11 / 11", "Phase 4 groups"), ("12 / 12", "Phase 3 groups"), ("0", "orphan rows"), ("INR 0.00000004", "max payroll gap")]), Spacer(1, 10),
          module_table(), Spacer(1, 8),
          p("The clean-environment run installed only the exact requirements, rebuilt the database, ran the suite and generated both monthly packs. A D99 fixture proves new departments are discovered from data. Privacy tests prove managers and HR cannot widen scope and executives cannot request sensitive payroll detail.", "BodyR"),
          p("Raw training defects remain visible as review findings; passing release calculations do not erase source evidence. The clean layer applies only documented corrections or quarantines.", "BodyR"), PageBreak()]

    report_page(s, "9 · BOARD HANDOFF", "Decisions, limits and next release", "The board pack and demo script present the evidence without overstating forecasts or automation.")
    s += [two_pictures(ROOT / "output/evidence/phase4/board_actions.png", "Three owned actions: collections, people/capacity and governance.", ROOT / "output/evidence/phase3/forecasts_anomalies.png", "Anomaly and forecast outputs are explicitly labelled for human review."), Spacer(1, 7),
          info_cards([("Immediate", "Review the overdue book, D01 cost/capacity, attendance outliers and high-value anomaly types."), ("Operational", "Connect a changing source feed, observe the first scheduled run and deploy the API blueprint."), ("Measurement", "Add actual periods overlapping the forecast horizon before calculating forecast error."), ("Owner actions", "Record the face-and-screen demonstration and upload the final PDF through the programme form.")], width=170), Spacer(1, 7),
          p(f"Artifacts: {link('public repository', REPO)} · {link('live dashboard', APP)} · board pack `output/pptx/PulseIQ_Board_Pack_September_2026.pptx` · Phase 4 validation `docs/phase4_validation.md` · demo guide `docs/board_demo_script.md`.", "BodyR")]

    doc.build(s, onFirstPage=footer("PulseIQ consolidated report · Aditya Mergurwar", 10), onLaterPages=footer("PulseIQ consolidated report · Aditya Mergurwar", 10))
    return CONSOLIDATED


if __name__ == "__main__":
    print(build_phase4())
    print(build_consolidated())
