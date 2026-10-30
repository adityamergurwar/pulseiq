"""Build the concise PulseIQ Phase 1 project report and dashboard evidence PDF."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "DataAnalytics_Aditya_Mergurwar_Phase1_Report.pdf"
SCREENSHOTS = [
    (
        ROOT / "output" / "evidence" / "PulseIQ_Workforce_Overview_2026-09.png",
        "Workforce overview | September 2026: 441 employees, 17 hires, 3 exits and net growth of 14.",
    ),
    (
        ROOT / "output" / "evidence" / "PulseIQ_Attendance_Leave_2026-09.png",
        "Attendance and Leave | Approved leave peaked at 573 days in January 2026; late arrivals reached 7.5% and overtime share 0.5%.",
    ),
]

INK = colors.HexColor("#14213d")
TEAL = colors.HexColor("#117c78")
PALE = colors.HexColor("#e8f3f1")
MUTED = colors.HexColor("#526179")
LINE = colors.HexColor("#d4dde7")
BLUE = colors.HexColor("#1269a8")
REPO_URL = "https://github.com/adityamergurwar/pulseiq"
APP_URL = "https://pulseiq-workforce.streamlit.app"


def para(text, style="BodyCustom"):
    return Paragraph(text, styles[style])


def make_table(rows, widths, header=False, cell_style="TableCell"):
    data = []
    for index, row in enumerate(rows):
        style = styles["TableHeader" if header and index == 0 else cell_style]
        data.append([
            value if isinstance(value, Paragraph) else Paragraph(str(value), style)
            for value in row
        ])
    table = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1 if header else 0)
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0, 0), (-1, 0), INK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ]
    if len(rows) > (1 if header else 0):
        commands.append(("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, PALE]))
    table.setStyle(TableStyle(commands))
    return table


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="TitleSimple", parent=styles["Title"], fontName="Helvetica-Bold",
    fontSize=23, leading=28, textColor=INK, alignment=TA_LEFT, spaceAfter=5,
))
styles.add(ParagraphStyle(
    name="Links", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8.4, leading=12, textColor=BLUE, spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="Intro", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=9.8, leading=14, textColor=INK, spaceAfter=7,
))
styles.add(ParagraphStyle(
    name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold",
    fontSize=12, leading=15, textColor=TEAL, spaceBefore=6, spaceAfter=5,
))
styles.add(ParagraphStyle(
    name="BodyCustom", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=9, leading=12, textColor=INK, spaceAfter=5,
))
styles.add(ParagraphStyle(
    name="TableCell", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8.35, leading=11, textColor=INK,
))
styles.add(ParagraphStyle(
    name="TableHeader", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=8.5, leading=10, textColor=colors.white,
))
styles.add(ParagraphStyle(
    name="Caption", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8.1, leading=10, textColor=MUTED, spaceBefore=2, spaceAfter=5,
))


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    for screenshot, _ in SCREENSHOTS:
        if not screenshot.is_file():
            raise FileNotFoundError(screenshot)

    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=14 * mm, bottomMargin=16 * mm,
        title="PulseIQ Phase 1 Foundation", author="Aditya Mergurwar",
        subject="PulseIQ project overview",
    )
    width = A4[0] - 36 * mm
    story = [
        para("PulseIQ Phase 1 Foundation", "TitleSimple"),
        para(
            f'GitHub: <link href="{REPO_URL}" color="#1269a8">{REPO_URL}</link><br/>'
            f'Dashboard: <link href="{APP_URL}" color="#1269a8">{APP_URL}</link>',
            "Links",
        ),
        para(
            "PulseIQ brings workforce and finance analysis into one application. A repeatable data pipeline "
            "checks source files, organizes accepted records in a DuckDB warehouse, and supplies governed "
            "metrics to the dashboard, API, and monthly reporting outputs.",
            "Intro",
        ),
        para("Project overview", "Section"),
        make_table([
            ["People analytics", "Finance analytics", "Decision support"],
            [
                "Headcount, hiring and exits, attendance and leave, attrition risk, team productivity, and department impact.",
                "Payroll and labor cost, budget versus actual, profit and loss, expenses, receivables, and cash collection.",
                "Forecasts and anomalies, executive scorecard, KPI builder, and data quality and lineage views.",
            ],
        ], [width / 3] * 3, header=True),
        para("Project components", "Section"),
        make_table([
            ["29", "28", "12", "5"],
            ["CSV source feeds", "governed metrics", "dashboard pages", "API metrics"],
        ], [width / 4] * 4, header=False),
        para(
            "The dashboard groups related measures into focused pages and supports department and month filters. "
            "Metric definitions are shared across the dashboard and API so the same measure keeps consistent "
            "meaning wherever it is viewed.",
            "BodyCustom",
        ),
        para("Example dashboard results", "Section"),
        para(
            "In the September 2026 workforce view, headcount is 441, with 17 hires and 3 exits for a net "
            "increase of 14; headcount is 3.3% above the prior month. Attendance views show approved leave "
            "peaking at 573 days in January 2026, late arrivals peaking at 7.5%, and overtime share peaking "
            "at 0.5% of payroll cost.",
            "BodyCustom",
        ),
        PageBreak(),
        para("How the project works", "TitleSimple"),
        para(
            "The implementation connects source data to decision-ready views through four layers. Each step "
            "keeps the data traceable and reuses the same governed definitions.",
            "Intro",
        ),
        make_table([
            ["Stage", "What happens"],
            [
                "1. Ingest and validate",
                "The pipeline reads 29 source CSV feeds. Schema and data-contract rules check expected types, required values, and feed-specific formats. Invalid records are kept in the audit trail with their source row and reason.",
            ],
            [
                "2. Shape the warehouse",
                "DuckDB organizes raw, clean, warehouse, metrics, and audit layers. Conformed dimensions and fact tables support joined analysis, including employee history, while refresh and quarantine records provide an audit trail.",
            ],
            [
                "3. Serve governed measures",
                "Metrics M01-M28 define shared workforce and finance calculations. Twelve Streamlit pages present them through filters, charts, and short insights. The FastAPI service exposes five selected metrics with definitions, lineage, data cutoff, and privacy metadata.",
            ],
            [
                "4. Package and refresh",
                "Monthly PDF and Excel builders create shareable snapshots; the workbook has nine sheets. Docker and Compose package the services. A GitHub Actions workflow is configured for monthly, manual, and source or pipeline change runs.",
            ],
        ], [42 * mm, width - 42 * mm], header=True),
        para("Validation results", "Section"),
        make_table([
            ["Check", "Result"],
            ["Automated tests", "13 passed."],
            ["ETL repeatability", "29 source feeds processed consistently across two ETL runs."],
            ["Row disposition", "62,770 input rows: 62,739 accepted and 31 quarantined with recorded reasons."],
            ["Metric layer", "28 of 28 governed metric views returned results."],
            ["Payroll reconciliation", "18 of 18 reference periods reconciled within INR 0.01."],
        ], [47 * mm, width - 47 * mm], header=True),
        para(
            "Together, these checks show how the supplied snapshot moves through validation and into the "
            "same metric layer used for interactive analysis and reporting.",
            "BodyCustom",
        ),
        PageBreak(),
        para("Dashboard screenshots", "TitleSimple"),
        para(
            "The two views below show the workforce summary and attendance analysis available in the app.",
            "Intro",
        ),
    ]

    for screenshot, caption in SCREENSHOTS:
        story.append(Image(str(screenshot), width=width, height=width * 9 / 16, kind="bound"))
        story.append(para(caption, "Caption"))
        story.append(Spacer(1, 5))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, 12 * mm, A4[0] - 18 * mm, 12 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(A4[0] - 18 * mm, 8 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return OUTPUT


if __name__ == "__main__":
    print(build())
