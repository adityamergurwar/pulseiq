"""Governed PulseIQ metric and presentation views."""
from __future__ import annotations

import re


METRIC_VIEWS = {
    "M01": "m01_headcount", "M02": "m02_hires", "M03": "m03_exits",
    "M04": "m04_attrition_monthly", "M05": "m05_attrition_rolling_12m",
    "M06": "m06_voluntary_attrition", "M07": "m07_gross_pay", "M08": "m08_net_pay",
    "M09": "m09_payroll_cost", "M10": "m10_cost_per_head", "M11": "m11_overtime_share",
    "M12": "m12_variable_pay_share", "M13": "m13_attendance_rate",
    "M14": "m14_late_arrival_rate", "M15": "m15_lop_days", "M16": "m16_revenue",
    "M17": "m17_net_profit", "M18": "m18_operating_margin", "M19": "m19_payroll_pct_revenue",
    "M20": "m20_dso", "M21": "m21_overdue_receivables", "M22": "m22_task_completion",
    "M23": "m23_on_time_delivery", "M24": "m24_velocity", "M25": "m25_cycle_time",
    "M26": "m26_anomaly_flag_rate", "M27": "m27_high_risk_share", "M28": "m28_forecast_error",
}


def create_metric_views(con) -> None:
    """Create all 28 dictionary-backed views and privacy-safe dashboard views."""
    rows = con.execute(
        "SELECT metric_id, minimum_group_size FROM clean.metric_dictionary"
    ).fetchall()
    thresholds = {}
    for metric_id, value in rows:
        match = re.search(r"\d+", str(value)) if value is not None else None
        thresholds[metric_id] = int(match.group()) if match else 0
    t = lambda metric_id, floor=0: max(thresholds.get(metric_id, 0), floor)

    sql = {
        "m01_headcount": f"""WITH base AS (
            SELECT month_start_date AS period, department_id, SUM(headcount_end) AS value,
                   SUM(headcount_end) AS group_size
            FROM clean.fact_headcount_monthly GROUP BY 1,2
        )
        SELECT period, department_id, value FROM base WHERE department_id <> 'D00' AND group_size >= {t('M01')}
        UNION ALL SELECT period, 'ALL', SUM(value) FROM base GROUP BY 1""",
        "m02_hires": f"""WITH base AS (
            SELECT month_start_date AS period, department_id, SUM(hires) AS value,
                   MAX(headcount_end) AS group_size
            FROM clean.fact_headcount_monthly GROUP BY 1,2
        )
        SELECT period, department_id, value FROM base WHERE department_id <> 'D00' AND group_size >= {t('M02')}
        UNION ALL SELECT period, 'ALL', SUM(value) FROM base GROUP BY 1""",
        "m03_exits": f"""WITH base AS (
            SELECT month_start_date AS period, department_id, SUM(exits) AS value,
                   MAX(headcount_end) AS group_size
            FROM clean.fact_headcount_monthly GROUP BY 1,2
        )
        SELECT period, department_id, value FROM base WHERE department_id <> 'D00' AND group_size >= {t('M03')}
        UNION ALL SELECT period, 'ALL', SUM(value) FROM base GROUP BY 1""",
        "m04_attrition_monthly": f"""WITH base AS (
            SELECT month_start_date AS period, department_id, SUM(exits) AS exits,
                   SUM(headcount_start) AS headcount_start
            FROM clean.fact_headcount_monthly GROUP BY 1,2
        )
        SELECT period, department_id, 100.0*exits/NULLIF(headcount_start,0) AS value
        FROM base WHERE department_id <> 'D00' AND headcount_start >= {t('M04')}
        UNION ALL SELECT period, 'ALL', 100.0*SUM(exits)/NULLIF(SUM(headcount_start),0) FROM base GROUP BY 1
        HAVING SUM(headcount_start) >= {t('M04')}""",
        "m05_attrition_rolling_12m": f"""WITH base AS (
            SELECT month_start_date AS period, department_id, SUM(exits) AS exits,
                   SUM(headcount_end) AS headcount_end
            FROM clean.fact_headcount_monthly GROUP BY 1,2
        ), roll AS (
            SELECT period, department_id,
                   SUM(exits) OVER (PARTITION BY department_id ORDER BY period ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS exits_12m,
                   AVG(headcount_end) OVER (PARTITION BY department_id ORDER BY period ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS avg_headcount_12m
            FROM base
        ) SELECT period, department_id, 100.0*exits_12m/NULLIF(avg_headcount_12m,0) AS value
          FROM roll WHERE department_id <> 'D00' AND avg_headcount_12m >= {t('M05')}
          UNION ALL
          SELECT period, 'ALL', 100.0*SUM(exits_12m)/NULLIF(SUM(avg_headcount_12m),0)
          FROM roll GROUP BY period HAVING SUM(avg_headcount_12m) >= {t('M05')}""",
        "m06_voluntary_attrition": f"""WITH base AS (
            SELECT month_start_date AS period, department_id, SUM(voluntary_exits) AS exits,
                   SUM(headcount_end) AS headcount_end
            FROM clean.fact_headcount_monthly GROUP BY 1,2
        ), roll AS (
            SELECT period, department_id,
                   SUM(exits) OVER (PARTITION BY department_id ORDER BY period ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS exits_12m,
                   AVG(headcount_end) OVER (PARTITION BY department_id ORDER BY period ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS avg_headcount_12m
            FROM base
        ) SELECT period, department_id, 100.0*exits_12m/NULLIF(avg_headcount_12m,0) AS value
          FROM roll WHERE department_id <> 'D00' AND avg_headcount_12m >= {t('M06')}
          UNION ALL
          SELECT period, 'ALL', 100.0*SUM(exits_12m)/NULLIF(SUM(avg_headcount_12m),0)
          FROM roll GROUP BY period HAVING SUM(avg_headcount_12m) >= {t('M06')}""",
    }

    payroll_metrics = {
        "m07_gross_pay": "SUM(p.gross_pay)",
        "m08_net_pay": "SUM(p.net_pay)",
        "m09_payroll_cost": "SUM(p.employer_cost)",
        "m10_cost_per_head": "SUM(p.employer_cost)/NULLIF(COUNT(DISTINCT p.employee_id),0)",
        "m11_overtime_share": "100.0*SUM(p.overtime_pay)/NULLIF(SUM(p.employer_cost),0)",
        "m12_variable_pay_share": "100.0*SUM(p.variable_pay)/NULLIF(SUM(p.gross_pay),0)",
        "m15_lop_days": "SUM(p.lop_days)",
    }
    metric_ids = {view: mid for mid, view in METRIC_VIEWS.items()}
    for name, measure in payroll_metrics.items():
        floor = t(metric_ids[name])
        if name in {"m10_cost_per_head", "m11_overtime_share", "m12_variable_pay_share"}:
            if name == "m10_cost_per_head":
                value = "SUM(p.employer_cost)/NULLIF(COUNT(DISTINCT p.employee_id),0)"
                company = "SUM(p.employer_cost)/NULLIF(COUNT(DISTINCT p.employee_id),0)"
            elif name == "m11_overtime_share":
                value = "100.0*SUM(p.overtime_pay)/NULLIF(SUM(p.employer_cost),0)"
                company = "100.0*SUM(p.overtime_pay)/NULLIF(SUM(p.employer_cost),0)"
            else:
                value = "100.0*SUM(p.variable_pay)/NULLIF(SUM(p.gross_pay),0)"
                company = "100.0*SUM(p.variable_pay)/NULLIF(SUM(p.gross_pay),0)"
            sql[name] = f"""WITH base AS (
                SELECT CAST(date_trunc('month',p.period_end_date) AS DATE) AS period,COALESCE(e.department_id,'UNKNOWN') AS department_id,
                       {value} AS value,COUNT(DISTINCT p.employee_id) AS group_size
                FROM clean.fact_payroll p LEFT JOIN warehouse.dim_employee e ON e.employee_key=p.employee_key
                GROUP BY 1,2
            ) SELECT period,department_id,value FROM base WHERE department_id<>'D00' AND group_size>={floor}
              UNION ALL SELECT CAST(date_trunc('month',p.period_end_date) AS DATE),'ALL',{company} FROM clean.fact_payroll p GROUP BY 1"""
            continue
        sql[name] = f"""WITH base AS (
            SELECT CAST(date_trunc('month',p.period_end_date) AS DATE) AS period, COALESCE(e.department_id, 'UNKNOWN') AS department_id,
                   {measure} AS value, COUNT(DISTINCT p.employee_id) AS group_size
            FROM clean.fact_payroll p
            LEFT JOIN warehouse.dim_employee e ON e.employee_key=p.employee_key
            GROUP BY 1,2
        ) SELECT period, department_id, value FROM base WHERE department_id <> 'D00' AND group_size >= {floor}
          UNION ALL SELECT period, 'ALL', SUM(value) FROM base GROUP BY 1"""

    sql["m13_attendance_rate"] = f"""WITH base AS (
        SELECT CAST(date_trunc('month',a.period_end_date) AS DATE) AS period, COALESCE(e.department_id, a.department_id, 'UNKNOWN') AS department_id,
               SUM(a.present_days+0.5*a.half_days_unpaid) AS attendance_days,
               SUM(a.scheduled_days) AS scheduled_days,COUNT(DISTINCT a.employee_id) AS group_size
        FROM clean.fact_attendance_monthly a
        LEFT JOIN warehouse.dim_employee e ON e.employee_key=a.employee_key GROUP BY 1,2
        ) SELECT period, department_id, attendance_days/NULLIF(scheduled_days,0) AS value
          FROM base WHERE department_id <> 'D00' AND group_size >= {t('M13')}
          UNION ALL SELECT period, 'ALL', SUM(attendance_days)/NULLIF(SUM(scheduled_days),0) FROM base GROUP BY 1"""
    sql["m14_late_arrival_rate"] = f"""WITH base AS (
        SELECT CAST(date_trunc('month',a.period_end_date) AS DATE) AS period, COALESCE(e.department_id, a.department_id, 'UNKNOWN') AS department_id,
               SUM(a.late_arrivals) AS late_arrivals,SUM(a.present_days) AS present_days,
               COUNT(DISTINCT a.employee_id) AS group_size
        FROM clean.fact_attendance_monthly a
        LEFT JOIN warehouse.dim_employee e ON e.employee_key=a.employee_key GROUP BY 1,2
        ) SELECT period, department_id, late_arrivals/NULLIF(present_days,0) AS value
          FROM base WHERE department_id <> 'D00' AND group_size >= {t('M14')}
          UNION ALL SELECT period, 'ALL', SUM(late_arrivals)/NULLIF(SUM(present_days),0) FROM base GROUP BY 1"""

    sql["m16_revenue"] = """SELECT CAST(date_trunc('month',entry_date) AS DATE) AS period,
        -SUM(signed_amount_debit_positive) AS value FROM warehouse.fact_ledger
        WHERE TRY_CAST(account_code AS INTEGER) BETWEEN 4001 AND 4004 GROUP BY 1"""
    sql["m17_net_profit"] = """SELECT CAST(date_trunc('month',entry_date) AS DATE) AS period,
        -SUM(signed_amount_debit_positive) AS value FROM warehouse.fact_ledger
        WHERE TRY_CAST(account_code AS INTEGER) BETWEEN 4000 AND 5999 GROUP BY 1"""
    sql["m18_operating_margin"] = """WITH ledger AS (
        SELECT CAST(date_trunc('month',entry_date) AS DATE) AS period,
        SUM(CASE WHEN TRY_CAST(account_code AS INTEGER) BETWEEN 4001 AND 4004 THEN -signed_amount_debit_positive ELSE 0 END) AS revenue,
        SUM(CASE WHEN TRY_CAST(account_code AS INTEGER) BETWEEN 4000 AND 5999 THEN -signed_amount_debit_positive ELSE 0 END) AS profit
        FROM warehouse.fact_ledger GROUP BY 1
        ) SELECT period, 100.0*profit/NULLIF(revenue,0) AS value FROM ledger"""
    sql["m19_payroll_pct_revenue"] = """WITH ledger AS (
        SELECT CAST(date_trunc('month',entry_date) AS DATE) AS period,
          SUM(CASE WHEN TRY_CAST(account_code AS INTEGER) BETWEEN 5001 AND 5005 THEN signed_amount_debit_positive ELSE 0 END) AS payroll_cost,
          SUM(CASE WHEN TRY_CAST(account_code AS INTEGER) BETWEEN 4001 AND 4004 THEN -signed_amount_debit_positive ELSE 0 END) AS revenue
        FROM warehouse.fact_ledger GROUP BY 1
        ) SELECT period, 100.0*payroll_cost/NULLIF(revenue,0) AS value FROM ledger"""
    sql["m20_dso"] = """WITH bounds AS (
        SELECT CAST(date_trunc('month',(SELECT MIN(entry_date) FROM clean.fact_ledger)) AS DATE) AS first_period,
               CAST(date_trunc('month',(SELECT MAX(invoice_date) FROM clean.fact_invoice)) AS DATE) AS last_period
        ), months AS (
        SELECT d.month_end_date AS period FROM clean.dim_date d,bounds b
        WHERE d.is_month_end='Y' AND d.month_end_date>=b.first_period+INTERVAL 1 MONTH-INTERVAL 1 DAY
          AND d.month_end_date<=b.last_period+INTERVAL 1 MONTH-INTERVAL 1 DAY GROUP BY 1
        ), receivables AS (
        SELECT m.period, SUM(GREATEST(i.total_amount-COALESCE((SELECT SUM(p.amount) FROM clean.fact_invoice_payment p
            WHERE p.invoice_id=i.invoice_id AND p.payment_date<=m.period),0),0)) AS amount
        FROM months m JOIN clean.fact_invoice i ON i.invoice_date<=m.period
        WHERE i.status NOT IN ('DRAFT','CANCELLED') GROUP BY 1
        ), sales AS (
        SELECT m.period, SUM(i.total_amount) AS amount_90d FROM months m JOIN clean.fact_invoice i
        ON i.invoice_date<=m.period AND i.invoice_date>m.period-INTERVAL 90 DAY
        WHERE i.status NOT IN ('DRAFT','CANCELLED') GROUP BY 1
        ) SELECT r.period, 90.0*r.amount/NULLIF(s.amount_90d,0) AS value
        FROM receivables r JOIN sales s USING(period)"""
    sql["m21_overdue_receivables"] = """WITH bounds AS (
        SELECT CAST(date_trunc('month',(SELECT MIN(entry_date) FROM clean.fact_ledger)) AS DATE) AS first_period,
               CAST(date_trunc('month',(SELECT MAX(invoice_date) FROM clean.fact_invoice)) AS DATE) AS last_period
        ), months AS (
        SELECT d.month_end_date AS period FROM clean.dim_date d,bounds b
        WHERE d.is_month_end='Y' AND d.month_end_date>=b.first_period+INTERVAL 1 MONTH-INTERVAL 1 DAY
          AND d.month_end_date<=b.last_period+INTERVAL 1 MONTH-INTERVAL 1 DAY GROUP BY 1
        ) SELECT m.period,
          SUM(GREATEST(i.total_amount-COALESCE((SELECT SUM(p.amount) FROM clean.fact_invoice_payment p
              WHERE p.invoice_id=i.invoice_id AND p.payment_date<=m.period),0),0)) AS value
        FROM months m JOIN clean.fact_invoice i ON i.due_date<m.period AND i.invoice_date<=m.period
        WHERE i.status NOT IN ('DRAFT','CANCELLED') GROUP BY 1"""
    sql["m22_task_completion"] = f"""SELECT sprint_id, team_id,
        100.0*COUNT(*) FILTER(WHERE status='Done')/NULLIF(COUNT(*) FILTER(WHERE status<>'Cancelled'),0) AS value
        FROM clean.fact_task GROUP BY 1,2 HAVING COUNT(*) FILTER(WHERE status<>'Cancelled') >= {t('M22')}"""
    sql["m23_on_time_delivery"] = f"""SELECT sprint_id, team_id,
        100.0*COUNT(*) FILTER(WHERE completed_on_time='Y')/NULLIF(COUNT(*) FILTER(WHERE status='Done'),0) AS value
        FROM clean.fact_task GROUP BY 1,2 HAVING COUNT(*) FILTER(WHERE status='Done') >= {t('M23')}"""
    sql["m24_velocity"] = """SELECT sprint_id, team_id,
        SUM(story_points) FILTER(WHERE status='Done') AS value
        FROM clean.fact_task GROUP BY 1,2"""
    sql["m25_cycle_time"] = f"""SELECT sprint_id, team_id,
        AVG(date_diff('day',started_date,completed_date)) FILTER(WHERE status='Done') AS value
        FROM clean.fact_task GROUP BY 1,2 HAVING COUNT(*) FILTER(WHERE status='Done') >= {t('M25')}"""
    sql["m26_anomaly_flag_rate"] = """SELECT source_dataset, CAST(date_trunc('month',period) AS DATE) AS period,
        100.0*AVG(CASE WHEN flagged='Y' THEN 1.0 ELSE 0 END) AS value
        FROM clean.fact_anomaly GROUP BY 1,2"""
    sql["m27_high_risk_share"] = f"""WITH latest AS (
        SELECT MAX(as_of_date) AS as_of_date FROM clean.fact_attrition_risk
        ) SELECT r.as_of_date AS period, r.department_id,
        100.0*COUNT(*) FILTER(WHERE r.risk_band='High')/NULLIF(COUNT(*),0) AS value
        FROM clean.fact_attrition_risk r, latest l WHERE r.as_of_date=l.as_of_date
        GROUP BY 1,2 HAVING COUNT(DISTINCT r.employee_id) >= {t('M27')}"""
    sql["m28_forecast_error"] = """SELECT f.forecast_month AS period, f.department_id,
        CASE WHEN h.headcount_end IS NULL OR h.headcount_end=0 THEN NULL
             ELSE 100.0*ABS(f.forecast_value-h.headcount_end)/h.headcount_end END AS value,
        h.headcount_end AS actual_value, f.forecast_value, f.lower_80, f.upper_80,
        CASE WHEN h.headcount_end IS NULL THEN 'Awaiting actuals' ELSE 'Measured' END AS measurement_status
        FROM clean.fact_forecast f LEFT JOIN clean.fact_headcount_monthly h
          ON f.metric='headcount_end' AND f.department_id=h.department_id AND f.forecast_month=h.month_start_date
        WHERE f.metric='headcount_end'"""

    for view_name, query in sql.items():
        con.execute(f"CREATE OR REPLACE VIEW metrics.{view_name} AS {query}")

    con.execute("""CREATE OR REPLACE VIEW metrics.metric_catalog AS
        SELECT d.metric_id, d.metric_name, d.business_definition, d.formula, d.source_table,
               d.grain, d.time_period, d.owner_team, d.unit, d.good_direction, d.caveat,
               TRY_CAST(regexp_extract(d.minimum_group_size,'[0-9]+',0) AS INTEGER) AS minimum_group_size,
               v.view_name
        FROM clean.metric_dictionary d
        JOIN (VALUES
          ('M01','m01_headcount'),('M02','m02_hires'),('M03','m03_exits'),
          ('M04','m04_attrition_monthly'),('M05','m05_attrition_rolling_12m'),('M06','m06_voluntary_attrition'),
          ('M07','m07_gross_pay'),('M08','m08_net_pay'),('M09','m09_payroll_cost'),('M10','m10_cost_per_head'),
          ('M11','m11_overtime_share'),('M12','m12_variable_pay_share'),('M13','m13_attendance_rate'),
          ('M14','m14_late_arrival_rate'),('M15','m15_lop_days'),('M16','m16_revenue'),('M17','m17_net_profit'),
          ('M18','m18_operating_margin'),('M19','m19_payroll_pct_revenue'),('M20','m20_dso'),
          ('M21','m21_overdue_receivables'),('M22','m22_task_completion'),('M23','m23_on_time_delivery'),
          ('M24','m24_velocity'),('M25','m25_cycle_time'),('M26','m26_anomaly_flag_rate'),
          ('M27','m27_high_risk_share'),('M28','m28_forecast_error')
        ) AS v(metric_id,view_name) USING(metric_id)""")

    # A single snapshot rule keeps SCD versions deterministic when a source overlap is flagged.
    snapshot = """WITH month_ends AS (
      SELECT DISTINCT month_start_date AS period,
             CAST(month_start_date+INTERVAL 1 MONTH-INTERVAL 1 DAY AS DATE) AS month_end
      FROM clean.fact_headcount_monthly
      ), active_versions AS (
      SELECT m.period, e.employee_id, e.department_id, e.job_level, e.work_location,
             e.work_mode, l.city_tier,
             ROW_NUMBER() OVER(PARTITION BY m.period,e.employee_id ORDER BY e.valid_from DESC,e.employee_key DESC) AS rn
      FROM month_ends m JOIN warehouse.dim_employee e
        ON e.hire_date<=m.month_end AND (e.exit_date IS NULL OR e.exit_date>m.month_end)
       AND e.valid_from<=m.month_end AND e.valid_to>=m.month_end
      LEFT JOIN warehouse.dim_location l USING(work_location)
      WHERE e.employee_id<>'UNKNOWN' AND e.department_id<>'D00'
      ) SELECT period, employee_id, department_id,
          COALESCE(CAST(job_level AS VARCHAR),'Unknown') AS level_label,
          COALESCE(CAST(city_tier AS VARCHAR),'Unknown') AS location_tier,
          COALESCE(work_mode,'Unknown') AS work_mode
        FROM active_versions WHERE rn=1"""
    con.execute(f"CREATE OR REPLACE VIEW metrics._employee_snapshot AS {snapshot}")
    for dim, label, view in [
        ("department_id", "department_name", "dashboard_department_mix"),
        ("level_label", "label", "dashboard_level_mix"),
        ("location_tier", "label", "dashboard_location_tier"),
        ("work_mode", "label", "dashboard_work_mode"),
    ]:
        if dim == "department_id":
            grouped = "SELECT period,department_id,COUNT(DISTINCT employee_id) AS value FROM metrics._employee_snapshot GROUP BY 1,2"
            con.execute(f"""CREATE OR REPLACE VIEW metrics.{view} AS
                SELECT g.period,g.department_id,d.department_name AS label,g.value
                FROM ({grouped}) g JOIN warehouse.dim_department d USING(department_id)
                WHERE g.value >= {t('M01')}
                UNION ALL SELECT period,'ALL','All departments',COUNT(DISTINCT employee_id)
                FROM metrics._employee_snapshot GROUP BY 1""")
        else:
            base = f"SELECT period,department_id,{dim} AS label,COUNT(DISTINCT employee_id) AS value FROM metrics._employee_snapshot GROUP BY 1,2,3"
            con.execute(f"""CREATE OR REPLACE VIEW metrics.{view} AS
                SELECT period,department_id,label,value FROM ({base}) WHERE value >= {t('M01')}
                UNION ALL SELECT period,'ALL',{dim},COUNT(DISTINCT employee_id)
                FROM metrics._employee_snapshot GROUP BY 1,3 HAVING COUNT(DISTINCT employee_id)>={t('M01')}""")

    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_attendance AS
        SELECT period,department_id,value AS attendance_rate
        FROM metrics.m13_attendance_rate WHERE department_id<>'ALL'""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_overtime AS
        SELECT period,department_id,value AS overtime_share_pct
        FROM metrics.m11_overtime_share WHERE department_id<>'ALL'""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_leave_monthly AS
        SELECT CAST(date_trunc('month',l.start_date) AS DATE) AS period,
               COALESCE(e.department_id,'UNKNOWN') AS department_id,
               SUM(l.days) AS leave_days, COUNT(DISTINCT l.employee_id) AS group_size
        FROM clean.fact_leave l LEFT JOIN warehouse.dim_employee e ON e.employee_key=l.employee_key
        WHERE l.status='Approved' GROUP BY 1,2 HAVING COUNT(DISTINCT l.employee_id)>=5
        UNION ALL SELECT CAST(date_trunc('month',l.start_date) AS DATE),'ALL',SUM(l.days),COUNT(DISTINCT l.employee_id)
        FROM clean.fact_leave l WHERE l.status='Approved' GROUP BY 1 HAVING COUNT(DISTINCT l.employee_id)>=5""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_leave_holiday AS
        WITH requests AS (
          SELECT l.leave_request_id,l.employee_id,COALESCE(e.department_id,'UNKNOWN') AS department_id,
            CAST(date_trunc('month',l.start_date) AS DATE) AS period,
            MAX(CASE WHEN d.is_holiday='Y' THEN 1 ELSE 0 END) AS overlaps_holiday
          FROM clean.fact_leave l LEFT JOIN warehouse.dim_employee e ON e.employee_key=l.employee_key
          JOIN clean.dim_date d ON d.date BETWEEN l.start_date AND l.end_date
          WHERE l.status='Approved' GROUP BY 1,2,3,4
        ) SELECT period,department_id,CASE WHEN overlaps_holiday=1 THEN 'Overlaps a public holiday' ELSE 'No public-holiday overlap' END AS holiday_group,
            COUNT(DISTINCT leave_request_id) AS requests,COUNT(DISTINCT employee_id) AS people
          FROM requests GROUP BY 1,2,3 HAVING COUNT(DISTINCT employee_id)>=5
        UNION ALL SELECT period,'ALL',CASE WHEN overlaps_holiday=1 THEN 'Overlaps a public holiday' ELSE 'No public-holiday overlap' END,
            COUNT(DISTINCT leave_request_id),COUNT(DISTINCT employee_id)
          FROM requests GROUP BY 1,3 HAVING COUNT(DISTINCT employee_id)>=5""")

    con.execute(f"""CREATE OR REPLACE VIEW metrics.dashboard_leave_type_monthly AS
        WITH by_department AS (
          SELECT CAST(date_trunc('month',l.start_date) AS DATE) AS period,
            COALESCE(e.department_id,'UNKNOWN') AS department_id,
            COALESCE(t.leave_type_name,l.leave_type_code) AS leave_type,
            SUM(l.days) AS leave_days,COUNT(DISTINCT l.employee_id) AS people
          FROM clean.fact_leave l
          LEFT JOIN warehouse.dim_employee e ON e.employee_key=l.employee_key
          LEFT JOIN clean.dim_leave_type t USING(leave_type_code)
          WHERE l.status='Approved' GROUP BY 1,2,3
        ), company AS (
          SELECT CAST(date_trunc('month',l.start_date) AS DATE) AS period,'ALL' AS department_id,
            COALESCE(t.leave_type_name,l.leave_type_code) AS leave_type,
            SUM(l.days) AS leave_days,COUNT(DISTINCT l.employee_id) AS people
          FROM clean.fact_leave l
          LEFT JOIN clean.dim_leave_type t USING(leave_type_code)
          WHERE l.status='Approved' GROUP BY 1,3
        )
        SELECT period,department_id,leave_type,leave_days,people FROM by_department
          WHERE department_id<>'D00' AND people>={t('M15')}
        UNION ALL
        SELECT period,department_id,leave_type,leave_days,people FROM company WHERE people>={t('M15')}""")

    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_calendar_monthly AS
        SELECT CAST(date_trunc('month',date) AS DATE) AS period,
          COUNT(*) FILTER(WHERE is_holiday='Y') AS public_holiday_count,
          COUNT(*) FILTER(WHERE is_holiday='Y' AND day_of_week IN ('Friday','Monday')) AS long_weekend_holiday_count,
          string_agg(CAST(date AS VARCHAR) || ' (' || day_of_week || ')', ', ' ORDER BY date)
            FILTER(WHERE is_holiday='Y') AS holiday_dates
        FROM clean.dim_date GROUP BY 1""")

    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_attrition AS
        SELECT h.month_start_date AS period,h.department_id,h.exits,h.voluntary_exits,
               a.value AS attrition_pct
        FROM clean.fact_headcount_monthly h LEFT JOIN metrics.m04_attrition_monthly a
          ON a.period=h.month_start_date AND a.department_id=h.department_id
        WHERE h.department_id<>'D00' AND h.headcount_start>=10""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_attrition_company AS
        SELECT month_start_date AS period,'ALL' AS department_id,
          SUM(exits) AS exits,SUM(voluntary_exits) AS voluntary_exits,
          100.0*SUM(exits)/NULLIF(SUM(headcount_start),0) AS attrition_pct
        FROM clean.fact_headcount_monthly GROUP BY 1""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_exit_tenure AS
        WITH latest AS (
          SELECT *,ROW_NUMBER() OVER(PARTITION BY employee_id ORDER BY valid_from DESC,employee_key DESC) AS rn
          FROM clean.dim_employee
        ), exits AS (
          SELECT e.employee_id,e.employee_key,e.department_id,e.hire_date,e.exit_date,
            COALESCE(NULLIF(e.change_reason,''),'Reason not recorded') AS exit_reason,
            GREATEST(date_diff('month',e.hire_date,e.exit_date),0) AS tenure_months,
            CASE WHEN date_diff('month',e.hire_date,e.exit_date)<12 THEN 'Under 1 year'
                 WHEN date_diff('month',e.hire_date,e.exit_date)<36 THEN '1-3 years'
                 WHEN date_diff('month',e.hire_date,e.exit_date)<60 THEN '3-5 years'
                 ELSE '5+ years' END AS tenure_band
          FROM latest e WHERE e.rn=1 AND e.exit_date IS NOT NULL
        ), groups AS (
          SELECT department_id,tenure_band,COUNT(DISTINCT employee_id) AS exits
          FROM exits GROUP BY 1,2
        ) SELECT department_id,tenure_band,exits FROM groups
          WHERE department_id<>'D00' AND exits>=5
        UNION ALL SELECT 'ALL',tenure_band,SUM(exits) FROM groups GROUP BY tenure_band HAVING SUM(exits)>=5""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_exit_reasons AS
        WITH latest AS (
          SELECT *,ROW_NUMBER() OVER(PARTITION BY employee_id ORDER BY valid_from DESC,employee_key DESC) AS rn
          FROM clean.dim_employee
        ), groups AS (
          SELECT department_id,COALESCE(NULLIF(change_reason,''),'Reason not recorded') AS reason,
            COUNT(DISTINCT employee_id) AS exits
          FROM latest WHERE rn=1 AND exit_date IS NOT NULL GROUP BY 1,2
        ) SELECT department_id,reason,exits FROM groups
          WHERE department_id<>'D00' AND exits>=5
        UNION ALL SELECT 'ALL',reason,SUM(exits) FROM groups GROUP BY reason HAVING SUM(exits)>=5""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_predicted_risk AS
        WITH latest AS (SELECT MAX(as_of_date) AS as_of_date FROM clean.fact_attrition_risk)
        SELECT r.as_of_date,r.department_id,r.risk_band,COUNT(DISTINCT r.employee_id) AS people,
               AVG(r.risk_score_12m) AS average_risk_score
        FROM clean.fact_attrition_risk r,latest l WHERE r.as_of_date=l.as_of_date
        GROUP BY 1,2,3 HAVING COUNT(DISTINCT r.employee_id)>=10""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_predicted_risk_company AS
        WITH latest AS (SELECT MAX(as_of_date) AS as_of_date FROM clean.fact_attrition_risk)
        SELECT r.as_of_date,r.risk_band,COUNT(DISTINCT r.employee_id) AS people,
               AVG(r.risk_score_12m) AS average_risk_score
        FROM clean.fact_attrition_risk r,latest l WHERE r.as_of_date=l.as_of_date
        GROUP BY 1,2 HAVING COUNT(DISTINCT r.employee_id)>=10""")

    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_task_operations AS
        SELECT t.sprint_id,t.team_id,d.team_name,d.department_id,
          COUNT(*) FILTER(WHERE t.status<>'Cancelled') AS planned_tasks,
          COUNT(*) FILTER(WHERE t.status='Done') AS done_tasks,
          COUNT(*) FILTER(WHERE t.is_overdue_at_cutoff='Y' AND t.status<>'Cancelled') AS overdue_tasks,
          COUNT(*) FILTER(WHERE t.status='Blocked') AS blocked_tasks,
          SUM(t.reopened_count) AS reopened_count,
          MAX(c.value) AS completion_pct, MAX(o.value) AS on_time_pct,
          MAX(v.value) AS velocity, MAX(ct.value) AS cycle_time_days
        FROM clean.fact_task t JOIN clean.dim_team d USING(team_id)
        LEFT JOIN metrics.m22_task_completion c USING(sprint_id,team_id)
        LEFT JOIN metrics.m23_on_time_delivery o USING(sprint_id,team_id)
        LEFT JOIN metrics.m24_velocity v USING(sprint_id,team_id)
        LEFT JOIN metrics.m25_cycle_time ct USING(sprint_id,team_id)
        GROUP BY 1,2,3,4""")

    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_budget_actuals AS
        WITH actual AS (
          SELECT period,department_id,value AS actual_cost FROM metrics.m09_payroll_cost WHERE department_id<>'ALL'
        ) SELECT b.month AS period,b.department_id,b.budget_payroll_cost AS budget_cost,
          a.actual_cost,a.actual_cost-b.budget_payroll_cost AS variance,
          100.0*(a.actual_cost-b.budget_payroll_cost)/NULLIF(b.budget_payroll_cost,0) AS variance_pct,
          CASE WHEN a.actual_cost<=b.budget_payroll_cost THEN 'GREEN'
               WHEN a.actual_cost<=b.budget_payroll_cost*1.05 THEN 'AMBER' ELSE 'RED' END AS status,
          CASE WHEN a.actual_cost<=b.budget_payroll_cost THEN 'Within payroll budget; maintain current staffing plan.'
               WHEN a.actual_cost<=b.budget_payroll_cost*1.05 THEN 'Review open roles and overtime before next month close.'
               ELSE 'Reforecast this department and review hiring, overtime and payroll adjustments.' END AS recommendation
        FROM clean.budget_payroll_dept_month b LEFT JOIN actual a
          ON a.period=b.month AND a.department_id=b.department_id
        WHERE b.department_id<>'D00' AND a.actual_cost IS NOT NULL""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_kpi_targets AS
        WITH attendance AS (
          SELECT period,department_id,100.0*value AS actual_value
          FROM metrics.m13_attendance_rate WHERE department_id<>'ALL'
        ), overtime AS (
          SELECT period,department_id,value AS actual_value
          FROM metrics.m11_overtime_share WHERE department_id<>'ALL'
        ), attrition AS (
          SELECT period,department_id,value AS actual_value
          FROM metrics.m04_attrition_monthly WHERE department_id<>'ALL'
        ), tasks AS (
          SELECT CAST(date_trunc('month',s.start_date) AS DATE) AS period,tm.department_id,
            100.0*COUNT(*) FILTER(WHERE t.status='Done')/
              NULLIF(COUNT(*) FILTER(WHERE t.status<>'Cancelled'),0) AS actual_value,
            COUNT(*) FILTER(WHERE t.status<>'Cancelled') AS sample_tasks
          FROM clean.fact_task t JOIN clean.dim_sprint s USING(sprint_id)
          JOIN clean.dim_team tm USING(team_id) GROUP BY 1,2
          HAVING COUNT(*) FILTER(WHERE t.status<>'Cancelled')>=5
        ), long_targets AS (
          SELECT month AS period,department_id,'Attendance rate' AS metric,
            100.0*attendance_rate_target AS target_value,'Higher is better' AS direction FROM clean.kpi_targets
          UNION ALL SELECT month,department_id,'Overtime share',overtime_share_target_pct,'Lower is better' FROM clean.kpi_targets
          UNION ALL SELECT month,department_id,'Monthly attrition',attrition_monthly_target_pct,'Lower is better' FROM clean.kpi_targets
          UNION ALL SELECT month,department_id,'Task completion',task_completion_target_pct,'Higher is better' FROM clean.kpi_targets
        ), actuals AS (
          SELECT period,department_id,'Attendance rate' AS metric,actual_value,NULL::BIGINT AS sample_size FROM attendance
          UNION ALL SELECT period,department_id,'Overtime share',actual_value,NULL::BIGINT FROM overtime
          UNION ALL SELECT period,department_id,'Monthly attrition',actual_value,NULL::BIGINT FROM attrition
          UNION ALL SELECT period,department_id,'Task completion',actual_value,sample_tasks FROM tasks
        ) SELECT t.period,t.department_id,t.metric,t.target_value,a.actual_value,t.direction,a.sample_size,
          CASE WHEN a.actual_value IS NULL THEN 'NO DATA'
               WHEN t.direction='Higher is better' AND a.actual_value>=t.target_value THEN 'GREEN'
               WHEN t.direction='Lower is better' AND a.actual_value<=t.target_value THEN 'GREEN'
               ELSE 'RED' END AS status,
          a.actual_value-t.target_value AS variance
        FROM long_targets t LEFT JOIN actuals a USING(period,department_id,metric)""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_task_completion_monthly AS
        WITH tasks AS (
          SELECT CAST(date_trunc('month',s.start_date) AS DATE) AS period,tm.department_id,
            COUNT(*) FILTER(WHERE t.status<>'Cancelled') AS planned_tasks,
            COUNT(*) FILTER(WHERE t.status='Done') AS done_tasks
          FROM clean.fact_task t JOIN clean.dim_sprint s USING(sprint_id)
          JOIN clean.dim_team tm USING(team_id) GROUP BY 1,2
        ) SELECT period,department_id,planned_tasks,done_tasks,
          100.0*done_tasks/NULLIF(planned_tasks,0) AS value FROM tasks
          WHERE department_id<>'D00' AND planned_tasks>=5
        UNION ALL SELECT period,'ALL',SUM(planned_tasks),SUM(done_tasks),
          100.0*SUM(done_tasks)/NULLIF(SUM(planned_tasks),0) FROM tasks GROUP BY 1""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_pnl_monthly AS
        WITH ledger AS (
          SELECT CAST(date_trunc('month',entry_date) AS DATE) AS period,
            SUM(CASE WHEN TRY_CAST(account_code AS INTEGER) BETWEEN 4001 AND 4004 THEN -signed_amount_debit_positive ELSE 0 END) AS revenue,
            SUM(CASE WHEN TRY_CAST(account_code AS INTEGER) BETWEEN 5000 AND 5999 THEN signed_amount_debit_positive ELSE 0 END) AS expenses,
            SUM(CASE WHEN TRY_CAST(account_code AS INTEGER)=4900 THEN -signed_amount_debit_positive ELSE 0 END) AS other_income,
            SUM(CASE WHEN TRY_CAST(account_code AS INTEGER) BETWEEN 4000 AND 5999 THEN -signed_amount_debit_positive ELSE 0 END) AS net_profit
          FROM warehouse.fact_ledger GROUP BY 1
        ) SELECT period,revenue,other_income,expenses,net_profit,
          revenue+other_income-expenses-net_profit AS reconciliation_difference,
          100.0*net_profit/NULLIF(revenue,0) AS operating_margin_pct
          FROM ledger""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_expense_category AS
        SELECT CAST(date_trunc('month',e.expense_date) AS DATE) AS period,e.category_account,a.account_name,
               SUM(e.total_amount) AS spend FROM clean.fact_expense e JOIN clean.dim_account a
          ON e.category_account=a.account_code GROUP BY 1,2,3""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_vendor_spend AS
        SELECT CAST(date_trunc('month',e.expense_date) AS DATE) AS period,e.vendor_id,v.vendor_name,
               SUM(e.total_amount) AS spend FROM clean.fact_expense e JOIN clean.dim_vendor v USING(vendor_id)
        GROUP BY 1,2,3""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_receivables_asof AS
        WITH bounds AS (
          SELECT CAST(date_trunc('month',(SELECT MIN(entry_date) FROM clean.fact_ledger)) AS DATE) AS first_period,
                 CAST(date_trunc('month',(SELECT MAX(invoice_date) FROM clean.fact_invoice)) AS DATE) AS last_period
        ), report_dates AS (
          SELECT DISTINCT d.month_start_date AS period,d.month_end_date AS as_of_date
          FROM clean.dim_date d,bounds b WHERE d.is_month_end='Y'
            AND d.month_end_date>=b.first_period+INTERVAL 1 MONTH-INTERVAL 1 DAY
            AND d.month_end_date<=b.last_period+INTERVAL 1 MONTH-INTERVAL 1 DAY
        ), outstanding AS (
          SELECT r.period,r.as_of_date,i.invoice_id,i.client_id,i.invoice_date,i.due_date,
            GREATEST(i.total_amount-COALESCE(SUM(p.amount) FILTER(WHERE p.payment_date<=r.as_of_date),0),0) AS balance
          FROM report_dates r JOIN clean.fact_invoice i ON i.invoice_date<=r.as_of_date
          LEFT JOIN clean.fact_invoice_payment p USING(invoice_id)
          WHERE i.status NOT IN ('DRAFT','CANCELLED')
          GROUP BY 1,2,3,4,5,6,i.total_amount
        ) SELECT o.*,CASE WHEN o.due_date>=o.as_of_date THEN 'Not due'
             WHEN date_diff('day',o.due_date,o.as_of_date)<=30 THEN '1-30 days'
             WHEN date_diff('day',o.due_date,o.as_of_date)<=60 THEN '31-60 days'
             WHEN date_diff('day',o.due_date,o.as_of_date)<=90 THEN '61-90 days' ELSE '90+ days' END AS ageing_bucket
        FROM outstanding o WHERE o.balance>0""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_receivables AS
        SELECT * FROM metrics.dashboard_receivables_asof
        WHERE as_of_date=(SELECT MAX(as_of_date) FROM metrics.dashboard_receivables_asof)""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_receivables_by_client AS
        SELECT r.as_of_date,r.client_id,c.client_name,SUM(r.balance) AS balance,
               AVG(date_diff('day',r.invoice_date,r.as_of_date)) AS average_days_open,
               COUNT(*) AS open_invoices
        FROM metrics.dashboard_receivables r JOIN clean.dim_client c USING(client_id)
        GROUP BY 1,2,3 HAVING COUNT(DISTINCT r.invoice_id)>=5""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_overdue_by_client AS
        SELECT r.as_of_date,r.client_id,c.client_name,SUM(r.balance) AS overdue_balance,
               COUNT(DISTINCT r.invoice_id) AS overdue_invoices,
               AVG(date_diff('day',r.due_date,r.as_of_date)) AS average_days_past_due
        FROM metrics.dashboard_receivables_asof r JOIN clean.dim_client c USING(client_id)
        WHERE r.ageing_bucket<>'Not due' GROUP BY 1,2,3
        HAVING COUNT(DISTINCT r.invoice_id)>=5""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_client_collection AS
        WITH paid AS (
          SELECT client_id,AVG(days_to_pay) AS average_days_to_pay,COUNT(DISTINCT invoice_id) AS paid_invoices
          FROM clean.fact_invoice WHERE status='PAID' AND days_to_pay IS NOT NULL GROUP BY 1
          HAVING COUNT(DISTINCT invoice_id)>=5
        ) SELECT p.client_id,c.client_name,p.average_days_to_pay,p.paid_invoices,
          COALESCE(r.balance,0) AS open_receivables,r.average_days_open
        FROM paid p JOIN clean.dim_client c USING(client_id)
        LEFT JOIN metrics.dashboard_receivables_by_client r USING(client_id)""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_cash_movement AS
        WITH monthly AS (
          SELECT CAST(date_trunc('month',entry_date) AS DATE) AS period,
            SUM(GREATEST(signed_amount_debit_positive,0)) AS cash_in,
            SUM(GREATEST(-signed_amount_debit_positive,0)) AS cash_out,
            SUM(signed_amount_debit_positive) AS net_movement
          FROM warehouse.fact_ledger WHERE TRY_CAST(account_code AS INTEGER)=1001 GROUP BY 1
        ) SELECT period,cash_in,cash_out,net_movement,
          SUM(net_movement) OVER(ORDER BY period ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS closing_balance
        FROM monthly""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_forecast AS
        SELECT f.forecast_month AS period,f.department_id,f.metric,f.forecast_value,
               f.lower_80,f.upper_80,h.headcount_end AS actual_value,
               CASE WHEN h.headcount_end IS NULL THEN 'Forecast; actual not yet available' ELSE 'Actual observed' END AS status
        FROM clean.fact_forecast f LEFT JOIN clean.fact_headcount_monthly h
          ON f.metric='headcount_end' AND f.department_id=h.department_id AND f.forecast_month=h.month_start_date
        WHERE f.metric='headcount_end'""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_salary_detail AS
        SELECT CAST(date_trunc('month',p.period_end_date) AS DATE) AS period,p.employee_id,e.department_id,e.role_title,
               p.gross_pay,p.net_pay,p.employer_cost
        FROM clean.fact_payroll p LEFT JOIN warehouse.dim_employee e ON e.employee_key=p.employee_key
        WHERE p.employee_id<>'UNKNOWN'""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_department_impact AS
        WITH payroll AS (
          SELECT CAST(date_trunc('month',p.period_end_date) AS DATE) AS period,e.department_id,
                 SUM(p.employer_cost) AS payroll_cost,SUM(p.gross_pay) AS gross_pay,
                 SUM(p.overtime_pay) AS overtime_pay,COUNT(DISTINCT p.employee_id) AS paid_people
          FROM clean.fact_payroll p JOIN warehouse.dim_employee e ON e.employee_key=p.employee_key
          WHERE e.department_id<>'UNKNOWN' GROUP BY 1,2
        ), attendance AS (
          SELECT CAST(date_trunc('month',a.period_end_date) AS DATE) AS period,e.department_id,
                 SUM(a.overtime_hours) AS overtime_hours,SUM(a.late_arrivals) AS late_arrivals,
                 SUM(a.present_days+0.5*a.half_days_unpaid) AS attendance_numerator,
                 SUM(a.scheduled_days) AS scheduled_days,
                 SUM(a.present_days+0.5*a.half_days_unpaid)/NULLIF(SUM(a.scheduled_days),0) AS attendance_rate
          FROM clean.fact_attendance_monthly a JOIN warehouse.dim_employee e ON e.employee_key=a.employee_key
          WHERE e.department_id<>'UNKNOWN' GROUP BY 1,2
        ), leave_by_month AS (
          SELECT CAST(date_trunc('month',l.start_date) AS DATE) AS period,e.department_id,
                 SUM(l.days) AS approved_leave_days
          FROM clean.fact_leave l JOIN warehouse.dim_employee e ON e.employee_key=l.employee_key
          WHERE l.status='Approved' AND e.department_id<>'UNKNOWN' GROUP BY 1,2
        ), attrition AS (
          SELECT month_start_date AS period,department_id,SUM(exits) AS exits,SUM(hires) AS hires,
                 SUM(headcount_start) AS headcount_start,SUM(headcount_end) AS headcount_end,
                 100.0*SUM(exits)/NULLIF(SUM(headcount_start),0) AS attrition_pct
          FROM clean.fact_headcount_monthly GROUP BY 1,2
        ), tasks AS (
          SELECT CAST(date_trunc('month',s.start_date) AS DATE) AS period,t.department_id,
            COUNT(*) FILTER(WHERE f.status<>'Cancelled') AS planned_tasks,
            COUNT(*) FILTER(WHERE f.status='Done') AS done_tasks,
            SUM(f.story_points) FILTER(WHERE f.status='Done') AS story_points_done
          FROM clean.fact_task f JOIN clean.dim_sprint s USING(sprint_id)
          JOIN clean.dim_team t USING(team_id) GROUP BY 1,2
        ) SELECT p.period,p.department_id,p.payroll_cost,p.paid_people,a.overtime_hours,
                 p.gross_pay,p.overtime_pay,a.late_arrivals,a.attendance_rate,a.attendance_numerator,a.scheduled_days,
                 t.headcount_start,t.headcount_end,t.hires,t.exits,t.attrition_pct,
                 k.planned_tasks,k.done_tasks,k.story_points_done,
                 100.0*k.done_tasks/NULLIF(k.planned_tasks,0) AS task_completion_pct,
                 p.payroll_cost/NULLIF(p.paid_people,0) AS cost_per_head,
                 100.0*p.overtime_pay/NULLIF(p.payroll_cost,0) AS overtime_share_pct,
                 l.approved_leave_days,
                 l.approved_leave_days/NULLIF(t.headcount_end,0) AS leave_days_per_head
          FROM payroll p LEFT JOIN attendance a USING(period,department_id)
          LEFT JOIN leave_by_month l USING(period,department_id)
          LEFT JOIN attrition t USING(period,department_id)
          LEFT JOIN tasks k USING(period,department_id)
        WHERE p.paid_people>=5""")
    con.execute("""CREATE OR REPLACE VIEW metrics.dashboard_data_freshness AS
        SELECT CAST(MAX(r.finished_at) AS VARCHAR) AS last_successful_refresh,
          GREATEST((SELECT MAX(period_end_date) FROM clean.fact_payroll),
                   (SELECT MAX(entry_date) FROM clean.fact_ledger),
                   (SELECT MAX(invoice_date) FROM clean.fact_invoice),
                   (SELECT MAX(period_end_date) FROM clean.fact_attendance_monthly),
                   (SELECT MAX(month_start_date) FROM clean.fact_headcount_monthly))::DATE AS data_cutoff,
          CASE WHEN MAX(r.finished_at)>=now()-INTERVAL 24 HOUR THEN 'Fresh' ELSE 'Stale' END AS status
        FROM audit.etl_run_log r WHERE r.status='SUCCESS'""")
