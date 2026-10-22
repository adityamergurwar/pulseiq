"""Build the governed, print-ready monthly management PDF.

Usage: python scripts/build_monthly_pack.py --month 2026-09
"""
from __future__ import annotations

import argparse
import calendar
from datetime import date
from pathlib import Path
import sys

import duckdb
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether,
)
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.legends import Legend

ROOT=Path(__file__).resolve().parents[1]
DB=Path(__import__("os").environ.get("PULSEIQ_DB_PATH",ROOT/"pulseiq.duckdb"))
OUT=ROOT/"reports"/"monthly"
INK=colors.HexColor("#14213d"); TEAL=colors.HexColor("#117c78"); PALE=colors.HexColor("#e8f3f1")


def query(con,sql,params=None):
    return con.execute(sql,params or []).fetchdf()


def money(v):
    if pd.isna(v): return "-"
    return f"INR {float(v):,.0f}"


def table(data, widths=None, font=7.5):
    rows=[list(map(str,data.columns))]
    for row in data.itertuples(index=False,name=None):
        rows.append(["-" if pd.isna(v) else (f"{v:,.2f}" if isinstance(v,(float,)) else str(v)) for v in row])
    t=Table(rows,colWidths=widths,repeatRows=1,hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),INK),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),font),
        ("LEADING",(0,0),(-1,-1),font+2),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,PALE]),
        ("GRID",(0,0),(-1,-1),.25,colors.HexColor("#cbd5e1")),
        ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))
    return t


def budget_chart(frame):
    d=Drawing(500,205)
    if frame.empty:
        d.add(String(10,100,"No department budget rows for this month.",fontSize=10,fillColor=INK)); return d
    q=frame.sort_values("variance",ascending=False).head(10).sort_values("department_id")
    chart=VerticalBarChart(); chart.x=45; chart.y=42; chart.width=420; chart.height=130
    chart.data=[tuple(float(x) for x in q.budget_cost),tuple(float(x) for x in q.actual_cost)]
    chart.categoryAxis.categoryNames=q.department_id.astype(str).tolist()
    chart.categoryAxis.labels.fontSize=7; chart.valueAxis.labels.fontSize=7
    chart.valueAxis.labelTextFormat="%0.0f"; chart.valueAxis.valueMin=0
    chart.bars[0].fillColor=colors.HexColor("#94a3b8"); chart.bars[1].fillColor=TEAL
    chart.groupSpacing=8; chart.barSpacing=2
    d.add(chart)
    leg=Legend(); leg.x=350; leg.y=178; leg.colorNamePairs=[(colors.HexColor("#94a3b8"),"Budget"),(TEAL,"Actual")]
    leg.fontSize=8; d.add(leg)
    d.add(String(45,190,"Payroll budget and actual by department (INR)",fontSize=9,fillColor=INK))
    return d


def pnl_chart(frame):
    d=Drawing(500,205)
    if frame.empty:
        d.add(String(10,100,"No P&L history is available.",fontSize=10,fillColor=INK)); return d
    q=frame.tail(12)
    plot=LinePlot(); plot.x=50; plot.y=35; plot.width=420; plot.height=130
    plot.data=[[(i,float(v)) for i,v in enumerate(q.revenue)],[(i,float(v)) for i,v in enumerate(q.net_profit)]]
    plot.lines[0].strokeColor=TEAL; plot.lines[1].strokeColor=colors.HexColor("#d17b0f")
    plot.lines[0].strokeWidth=2; plot.lines[1].strokeWidth=2
    plot.xValueAxis.valueMin=0; plot.xValueAxis.valueMax=max(1,len(q)-1)
    plot.xValueAxis.valueSteps=list(range(len(q)))
    plot.xValueAxis.labelTextFormat=lambda i:q.iloc[int(i)].period.strftime("%b\n%y") if 0<=int(i)<len(q) else ""
    plot.xValueAxis.labels.fontSize=6; plot.yValueAxis.labels.fontSize=7
    plot.yValueAxis.labelTextFormat="%0.0f"; d.add(plot)
    leg=Legend();leg.x=360;leg.y=178;leg.colorNamePairs=[(TEAL,"Revenue"),(colors.HexColor("#d17b0f"),"Net profit")];leg.fontSize=8;d.add(leg)
    d.add(String(50,190,"Revenue and net profit: trailing 12 ledger months (INR)",fontSize=9,fillColor=INK))
    return d


def build(month: date, output: Path) -> Path:
    if not DB.exists(): raise FileNotFoundError(f"Warehouse missing at {DB}; run python etl.py first.")
    con=duckdb.connect(str(DB),read_only=True)
    month_start=month.replace(day=1); month_end=month.replace(day=calendar.monthrange(month.year,month.month)[1])
    exists=query(con,"SELECT COUNT(*) n FROM metrics.m01_headcount WHERE period=? AND department_id='ALL'",[month_start]).iloc[0,0]
    if not exists: raise ValueError(f"No workforce data for {month_start:%Y-%m}; choose a month in the observed range.")
    cutoff=query(con,"SELECT data_cutoff FROM metrics.dashboard_data_freshness").iloc[0,0]

    workforce=query(con,"""SELECT h.value AS headcount,hi.value AS hires,e.value AS exits,a.value AS monthly_attrition_pct
        FROM metrics.m01_headcount h JOIN metrics.m02_hires hi USING(period,department_id)
        JOIN metrics.m03_exits e USING(period,department_id) JOIN metrics.m04_attrition_monthly a USING(period,department_id)
        WHERE h.period=? AND h.department_id='ALL'""",[month_start])
    payroll=query(con,"""SELECT p.department_id,g.value AS gross_pay,n.value AS net_pay,p.value AS employer_cost,
                       h.value AS cost_per_head
        FROM metrics.m09_payroll_cost p JOIN metrics.m07_gross_pay g USING(period,department_id)
        JOIN metrics.m08_net_pay n USING(period,department_id) JOIN metrics.m10_cost_per_head h USING(period,department_id)
        WHERE p.period=? AND p.department_id<>'ALL' ORDER BY p.value DESC""",[month_start])
    budget=query(con,"SELECT department_id,budget_cost,actual_cost,variance,variance_pct,status FROM metrics.dashboard_budget_actuals WHERE period=? ORDER BY variance DESC",[month_start])
    pnl=query(con,"SELECT period,revenue,other_income,expenses,net_profit,operating_margin_pct,reconciliation_difference FROM metrics.dashboard_pnl_monthly ORDER BY period")
    pnl_row=pnl[pd.to_datetime(pnl.period).dt.date==month_start]
    ageing=query(con,"""SELECT ageing_bucket,COUNT(DISTINCT invoice_id) AS invoices,SUM(balance) AS balance
                     FROM metrics.dashboard_receivables_asof WHERE as_of_date=? GROUP BY 1 ORDER BY 1""",[month_end])
    ar_total=float(ageing.balance.sum()) if not ageing.empty else 0.0
    dso=query(con,"SELECT value FROM metrics.m20_dso WHERE period=?",[month_end])
    cash=query(con,"SELECT cash_in,cash_out,net_movement,closing_balance FROM metrics.dashboard_cash_movement WHERE period=?",[month_start])
    teams=query(con,"""SELECT d.team_name,COUNT(*) FILTER(WHERE t.status<>'Cancelled') AS planned_tasks,
          COUNT(*) FILTER(WHERE t.status='Done') AS done_tasks,
          100.0*COUNT(*) FILTER(WHERE t.status='Done')/NULLIF(COUNT(*) FILTER(WHERE t.status<>'Cancelled'),0) AS completion_pct,
          100.0*COUNT(*) FILTER(WHERE t.completed_on_time='Y')/NULLIF(COUNT(*) FILTER(WHERE t.status='Done'),0) AS on_time_pct,
          SUM(t.story_points) FILTER(WHERE t.status='Done') AS velocity,
          AVG(date_diff('day',t.started_date,t.completed_date)) FILTER(WHERE t.status='Done') AS cycle_time_days
        FROM clean.fact_task t JOIN clean.dim_sprint s USING(sprint_id) JOIN clean.dim_team d USING(team_id)
        WHERE CAST(date_trunc('month',s.start_date) AS DATE)=? GROUP BY 1
        HAVING COUNT(*) FILTER(WHERE t.status<>'Cancelled')>=5 ORDER BY completion_pct DESC""",[month_start])
    con.close()

    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle",parent=styles["Title"],fontSize=22,leading=27,textColor=INK,spaceAfter=5))
    styles.add(ParagraphStyle(name="Section",parent=styles["Heading2"],fontSize=13,leading=16,textColor=TEAL,spaceBefore=7,spaceAfter=5))
    styles.add(ParagraphStyle(name="Small",parent=styles["BodyText"],fontSize=8,leading=10,textColor=colors.HexColor("#475569")))
    styles.add(ParagraphStyle(name="Insight",parent=styles["BodyText"],fontSize=9,leading=13,textColor=INK,backColor=PALE,borderPadding=6,spaceBefore=5,spaceAfter=8))
    output.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(output),pagesize=landscape(A4),rightMargin=15*mm,leftMargin=15*mm,topMargin=17*mm,bottomMargin=15*mm,title=f"PulseIQ Monthly Pack {month_start:%Y-%m}",author="PulseIQ Analytics")
    story=[Paragraph("PulseIQ | Monthly Management Pack",styles["CoverTitle"]),
           Paragraph(f"Reporting period: {month_start:%d %b %Y}-{month_end:%d %b %Y} · Data cut-off: {pd.Timestamp(cutoff):%d %b %Y} · Generated: {date.today():%d %b %Y}",styles["Small"]),Spacer(1,5)]

    story.append(Paragraph("1 · Workforce snapshot",styles["Section"]))
    if not workforce.empty:
        r=workforce.iloc[0]
        w=pd.DataFrame([["Month-end headcount","Hires","Exits","Monthly attrition"],[f"{r.headcount:,.0f}",f"{r.hires:,.0f}",f"{r.exits:,.0f}",f"{r.monthly_attrition_pct:.2f}%"]])
        t=Table(w.values.tolist(),colWidths=[55*mm]*4)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),INK),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),10),("BACKGROUND",(0,1),(-1,1),PALE),("ALIGN",(0,0),(-1,-1),"CENTER"),("BOX",(0,0),(-1,-1),.5,colors.HexColor("#cbd5e1")),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]));story.append(t)
    story.append(Paragraph("2 · Payroll by department (privacy floor applied)",styles["Section"]))
    if not payroll.empty:
        pf=payroll.copy();
        for c in ["gross_pay","net_pay","employer_cost","cost_per_head"]: pf[c]=pf[c].map(money)
        pf.columns=["Department","Gross pay","Net pay","Employer cost","Cost per head"]
        story.append(table(pf,[35*mm,43*mm,43*mm,48*mm,44*mm]))
    story.append(Paragraph("3 · Budget versus actual",styles["Section"]))
    if not budget.empty:
        bf=budget.copy()
        for c in ["budget_cost","actual_cost","variance"]: bf[c]=bf[c].map(money)
        bf["variance_pct"]=budget.variance_pct.map(lambda v:f"{v:+.1f}%")
        bf.columns=["Department","Budget","Actual","Variance","Variance %","Status"]
        story.append(table(bf,[28*mm,38*mm,38*mm,38*mm,28*mm,22*mm],font=7))
    story.append(budget_chart(budget))
    story.append(PageBreak())

    story += [Paragraph("4 · Profit and loss",styles["Section"])]
    if not pnl_row.empty:
        r=pnl_row.iloc[0]
        p=pd.DataFrame([["Revenue","Other income","Operating expense","Net profit","Operating margin"],
                        [money(r.revenue),money(r.other_income),money(r.expenses),money(r.net_profit),f"{r.operating_margin_pct:.1f}%"]])
        t=Table(p.values.tolist(),colWidths=[45*mm]*5)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),INK),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8.5),("BACKGROUND",(0,1),(-1,1),PALE),("ALIGN",(0,0),(-1,-1),"CENTER"),("BOX",(0,0),(-1,-1),.5,colors.HexColor("#cbd5e1")),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]));story.append(t)
        story.append(Paragraph(f"Tie-out: revenue + other income - expenses - net profit = {money(r.reconciliation_difference)}.",styles["Insight"]))
    story.append(pnl_chart(pnl))
    story.append(Paragraph("5 · Open receivables ageing",styles["Section"]))
    if not ageing.empty:
        ag=ageing.copy();ag["balance"]=ag.balance.map(money);ag.columns=["Ageing bucket","Invoices","Open balance"]
        story.append(table(ag,[55*mm,35*mm,55*mm]))
    story.append(Paragraph(f"Total open receivables at {month_end:%d %b %Y}: {money(ar_total)} · DSO: {f'{float(dso.iloc[0,0]):.1f} days' if not dso.empty else 'not available'}.",styles["Insight"]))
    if not cash.empty:
        story.append(PageBreak())
        story.append(Paragraph("6 · Cash movement",styles["Section"]))
        cr=cash.iloc[0]
        c=pd.DataFrame([["Cash-in","Cash-out","Net movement","Cumulative movement balance"],[money(cr.cash_in),money(cr.cash_out),money(cr.net_movement),money(cr.closing_balance)]])
        t=Table(c.values.tolist(),colWidths=[48*mm]*4)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),INK),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),("BACKGROUND",(0,1),(-1,1),PALE),("ALIGN",(0,0),(-1,-1),"CENTER"),("BOX",(0,0),(-1,-1),.5,colors.HexColor("#cbd5e1")),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]));story.append(t)
        story.append(Paragraph("Cash values are movements in ledger account 1001; no opening bank balance was supplied.",styles["Small"]))
    story.append(Paragraph("7 · Team productivity by sprint-start month",styles["Section"]))
    if not teams.empty:
        tf=teams.copy();
        for c in ["completion_pct","on_time_pct"]: tf[c]=tf[c].map(lambda v:f"{v:.1f}%" if pd.notna(v) else "-")
        for c in ["velocity","cycle_time_days"]: tf[c]=tf[c].map(lambda v:f"{v:,.1f}" if pd.notna(v) else "-")
        tf.columns=["Team","Planned tasks","Done tasks","Completion","On-time","Story points","Cycle time days"]
        story.append(table(tf,[49*mm,25*mm,22*mm,25*mm,22*mm,27*mm,27*mm],font=7))
    story.append(Paragraph("Data quality: source issues remain visible in the audit layer. Invalid payroll, post-exit attendance, and invalid task rows are quarantined; raw sources remain preserved. Forecast data is not presented as actual. This pack contains aggregate outputs only.",styles["Small"]))

    def page(canvas,doc):
        canvas.saveState();w,h=doc.pagesize
        canvas.setStrokeColor(colors.HexColor("#dbe3ea"));canvas.line(doc.leftMargin,12*mm,w-doc.rightMargin,12*mm)
        canvas.setFont("Helvetica",7);canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(doc.leftMargin,8*mm,f"PulseIQ · Fictional Zenith Nova training data · Cut-off {pd.Timestamp(cutoff):%d %b %Y}")
        canvas.drawRightString(w-doc.rightMargin,8*mm,f"Page {doc.page}")
        canvas.restoreState()
    doc.build(story,onFirstPage=page,onLaterPages=page)
    return output


def main():
    ap=argparse.ArgumentParser(description="Generate a PulseIQ monthly PDF pack for an observed month.")
    ap.add_argument("--month",help="Report month as YYYY-MM; defaults to the latest observed payroll month.")
    ap.add_argument("--output",type=Path,help="Optional output PDF path.")
    args=ap.parse_args()
    if not DB.exists(): raise SystemExit(f"Warehouse missing at {DB}; run python etl.py first.")
    if args.month:
        if not re_full_month(args.month): raise SystemExit("--month must be YYYY-MM.")
        y,m=map(int,args.month.split("-")); month=date(y,m,1)
    else:
        with duckdb.connect(str(DB),read_only=True) as con:
            val=con.execute("SELECT MAX(period) FROM metrics.m01_headcount WHERE department_id='ALL'").fetchone()[0]
        month=val
    output=args.output or OUT/f"PulseIQ_Monthly_Pack_{month:%Y-%m}.pdf"
    print(build(month,output))


def re_full_month(value):
    return len(value)==7 and value[4]=='-' and value[:4].isdigit() and value[5:7].isdigit() and 1<=int(value[5:7])<=12


if __name__=="__main__":
    main()
