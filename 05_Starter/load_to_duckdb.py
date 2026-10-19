"""Loads every CSV in ../03_Data/csv into a local DuckDB file as schema 'raw'.  Run:  python load_to_duckdb.py
This is only the 'bronze' copy of the exports. PQ-01 (ETL) and PQ-02 (warehouse) are YOUR job: validate, clean, then build the star schema on top.
Open the result with any SQL tool, or:  duckdb pulseiq.duckdb"""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "03_Data" / "csv"
con = duckdb.connect(str(ROOT / "pulseiq.duckdb"))
con.execute("CREATE SCHEMA IF NOT EXISTS raw")
for f in sorted(DATA.glob("*.csv")):
    t = f.stem
    con.execute(f'CREATE OR REPLACE TABLE raw."{t}" AS SELECT * FROM read_csv_auto(?, header=true)', [str(f)])
    count = con.execute(f'SELECT COUNT(*) FROM raw."{t}"').fetchone()[0]
    print(f"raw.{t:<32}{count:>8} rows")
con.close()
