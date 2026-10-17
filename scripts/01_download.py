"""Download raw data.

- Zillow Observed Rent Index (ZORI) by ZIP code, monthly.
- Census ACS 5-year detailed tables by ZIP Code Tabulation Area (ZCTA), from the
  bulk summary files (no API key needed). Only Georgia ZCTAs (30xxx-31xxx) are kept.
"""
from pathlib import Path

import requests

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

ZILLOW_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zori/"
    "Zip_zori_uc_sfrcondomfr_sm_month.csv"
)

ACS_URL = (
    "https://www2.census.gov/programs-surveys/acs/summary_file/{year}/"
    "table-based-SF/data/5YRData/acsdt5y{year}-{table}.dat"
)
# 2017-2021 and 2020-2024 5-year estimates (earliest and latest in the bulk format)
ACS_YEARS = [2021, 2024]
ACS_TABLES = {
    "b19013": "median household income",
    "b25119": "median household income by tenure (owner / renter)",
    "b25064": "median gross rent",
    "b25070": "gross rent as a percentage of household income",
}
GEORGIA_ZCTA_PREFIXES = ("860Z200US30", "860Z200US31")


def download_zillow():
    resp = requests.get(ZILLOW_URL, timeout=300)
    resp.raise_for_status()
    dest = RAW / "zillow_zori_zip.csv"
    dest.write_bytes(resp.content)
    print(f"saved {dest.name} ({len(resp.content) / 1e6:.1f} MB)")


def download_acs_table(year, table):
    """Stream a nationwide table file and keep the header plus Georgia ZCTA rows."""
    dest = RAW / f"acs_{year}_{table}_ga_zcta.psv"
    kept = 0
    with requests.get(ACS_URL.format(year=year, table=table), stream=True, timeout=300) as resp:
        resp.raise_for_status()
        resp.encoding = "utf-8"  # census.gov sends no charset, so requests would yield bytes
        lines = resp.iter_lines(decode_unicode=True)
        with dest.open("w") as out:
            out.write(next(lines) + "\n")
            for line in lines:
                if line.startswith(GEORGIA_ZCTA_PREFIXES):
                    out.write(line + "\n")
                    kept += 1
    print(f"saved {dest.name} ({kept} Georgia ZIPs)")


def main():
    download_zillow()
    for year in ACS_YEARS:
        for table in ACS_TABLES:
            download_acs_table(year, table)


if __name__ == "__main__":
    main()
