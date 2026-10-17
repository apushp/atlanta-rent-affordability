"""Run sql/build.sql in DuckDB and export Tableau-ready CSVs to data/processed/."""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(ROOT / "data" / "atlanta_rent.duckdb"))
    # Paths in the SQL are relative to the project root
    con.execute(f"SET file_search_path = '{ROOT}'")
    con.execute((ROOT / "sql" / "build.sql").read_text())

    con.execute(f"COPY zip_summary TO '{OUT / 'atlanta_zip_affordability.csv'}' (HEADER)")
    con.execute(f"COPY (SELECT * FROM rent_monthly ORDER BY zip, month) "
                f"TO '{OUT / 'atlanta_rent_monthly.csv'}' (HEADER)")
    for table in ("rent_monthly", "census", "zip_summary"):
        n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        print(f"{table}: {n} rows")


if __name__ == "__main__":
    main()
