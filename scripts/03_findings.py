"""Print the headline findings used in the README."""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
SALARY = 50_000

con = duckdb.connect(str(ROOT / "data" / "atlanta_rent.duckdb"), read_only=True)


def show(title, sql):
    print(f"\n## {title}")
    print(con.sql(sql))


# Exclude the flagged student ZIP from metro-wide summaries
BASE = "FROM zip_summary WHERE data_note IS NULL"

show("Metro overview", f"""
    SELECT count(*) AS zips,
           median(rent_latest) AS median_rent_now,
           median(rent_avg_2019) AS median_rent_2019,
           median(rent_share_of_income_pct) AS median_rent_share_pct,
           count(*) FILTER (WHERE rent_share_of_income_pct >= 30) AS zips_over_30pct,
           count(rent_share_of_income_pct) AS zips_with_share,
           median(pct_renters_burdened) AS median_pct_renters_burdened,
           median(income_needed_today) AS median_income_needed
    {BASE}""")

show("Rent growth vs renter income growth (2019 -> 2022 windows)", f"""
    SELECT count(*) AS zips_compared,
           median(rent_growth_2019_2022_pct) AS median_rent_growth,
           median(renter_income_growth_pct) AS median_income_growth,
           count(*) FILTER (WHERE rent_growth_2019_2022_pct > renter_income_growth_pct) AS rent_outpaced_income
    {BASE} AND rent_growth_2019_2022_pct IS NOT NULL AND renter_income_growth_pct IS NOT NULL""")

show("Least affordable ZIPs", f"""
    SELECT zip, city, county, rent_avg_2024, renter_income_2024, rent_share_of_income_pct, pct_renters_burdened
    {BASE} ORDER BY rent_share_of_income_pct DESC NULLS LAST LIMIT 10""")

show("Most affordable ZIPs", f"""
    SELECT zip, city, county, rent_avg_2024, renter_income_2024, rent_share_of_income_pct, pct_renters_burdened
    {BASE} AND rent_share_of_income_pct IS NOT NULL ORDER BY rent_share_of_income_pct LIMIT 10""")

show(f"Where a ${SALARY:,} salary works today (rent <= 30% of income)", f"""
    SELECT count(*) FILTER (WHERE rent_latest * 12 <= {SALARY} * 0.30) AS affordable_zips,
           count(*) AS all_zips,
           string_agg(zip || ' ' || city, ', ' ORDER BY rent_latest)
               FILTER (WHERE rent_latest * 12 <= {SALARY} * 0.30) AS which
    {BASE}""")

show("Fastest rent growth since 2019", f"""
    SELECT zip, city, rent_avg_2019, rent_latest, rent_growth_2019_latest_pct
    {BASE} AND rent_growth_2019_latest_pct IS NOT NULL ORDER BY rent_growth_2019_latest_pct DESC LIMIT 8""")

show("By county", f"""
    SELECT county, count(*) AS zips, median(rent_latest) AS median_rent_now,
           median(rent_share_of_income_pct) AS median_rent_share_pct,
           median(pct_renters_burdened) AS median_pct_burdened
    {BASE} GROUP BY county HAVING count(*) >= 4 ORDER BY median_rent_share_pct DESC""")
