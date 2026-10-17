-- Builds the Atlanta rent affordability tables (DuckDB SQL).
-- Run from the project root via scripts/02_build.py.

-- 1. Zillow rents: wide (one column per month) -> long (one row per ZIP per month),
--    Atlanta metro only.
CREATE OR REPLACE TABLE zillow_monthly AS
WITH atlanta AS (
    SELECT * EXCLUDE (RegionID, SizeRank, RegionType, StateName, State, Metro)
    FROM read_csv_auto('data/raw/zillow_zori_zip.csv')
    WHERE Metro = 'Atlanta-Sandy Springs-Alpharetta, GA'
)
UNPIVOT atlanta
ON COLUMNS(* EXCLUDE (RegionName, City, CountyName))
INTO NAME month_end VALUE rent;

CREATE OR REPLACE TABLE rent_monthly AS
SELECT
    lpad(CAST(RegionName AS VARCHAR), 5, '0') AS zip,
    City AS city,
    CountyName AS county,
    CAST(month_end AS DATE) AS month,
    round(rent, 0) AS rent
FROM zillow_monthly
WHERE rent IS NOT NULL;

-- 2. Census tables: keep ZIP + the estimate columns we need. The Census uses large
--    negative codes (e.g. -666666666) for "not available", so those become NULL.
CREATE OR REPLACE MACRO census_value(v) AS CASE WHEN v < 0 THEN NULL ELSE v END;

CREATE OR REPLACE MACRO acs(year, tbl) AS TABLE
    SELECT *, right(GEO_ID, 5) AS zip
    FROM read_csv('data/raw/acs_' || year || '_' || tbl || '_ga_zcta.psv', delim = '|', header = true);

CREATE OR REPLACE TABLE census AS
SELECT
    i24.zip,
    census_value(i24.B19013_E001)          AS median_income_2024,
    census_value(r24.B25119_E003)          AS renter_income_2024,
    census_value(r21.B25119_E003)          AS renter_income_2021,
    census_value(g24.B25064_E001)          AS census_median_rent_2024,
    -- Rent-burdened = paying 30% or more of income on rent. Households where the
    -- Census could not compute a share (no income / no cash rent) are excluded.
    census_value(b24.B25070_E001) - census_value(b24.B25070_E011) AS renters_2024,
    b24.B25070_E007 + b24.B25070_E008 + b24.B25070_E009 + b24.B25070_E010 AS rent_burdened_2024,
    b24.B25070_E010                        AS severely_burdened_2024
FROM acs(2024, 'b19013') i24
JOIN acs(2024, 'b25119') r24 USING (zip)
JOIN acs(2021, 'b25119') r21 USING (zip)
JOIN acs(2024, 'b25064') g24 USING (zip)
JOIN acs(2024, 'b25070') b24 USING (zip);

-- 3. One row per ZIP: rents at key points in time, joined to Census incomes.
CREATE OR REPLACE TABLE zip_summary AS
WITH rents AS (
    SELECT
        zip,
        any_value(city)   AS city,
        any_value(county) AS county,
        avg(rent) FILTER (WHERE year(month) = 2019) AS rent_avg_2019,
        avg(rent) FILTER (WHERE year(month) = 2022) AS rent_avg_2022,
        avg(rent) FILTER (WHERE year(month) = 2024) AS rent_avg_2024,
        arg_max(rent, month)                        AS rent_latest,
        max(month)                                  AS latest_month
    FROM rent_monthly
    GROUP BY zip
)
SELECT
    r.zip,
    r.city,
    r.county,
    round(r.rent_latest)   AS rent_latest,
    r.latest_month,
    round(r.rent_avg_2019) AS rent_avg_2019,
    round(r.rent_avg_2024) AS rent_avg_2024,
    c.median_income_2024,
    c.renter_income_2024,
    c.census_median_rent_2024,
    c.renters_2024,

    -- Affordability: a year of typical 2024 asking rent as a share of the typical
    -- renter household's 2024 income. 30%+ is the standard "rent-burdened" line.
    round(100 * r.rent_avg_2024 * 12 / c.renter_income_2024, 1) AS rent_share_of_income_pct,

    -- Income needed to rent here today without being rent-burdened.
    round(r.rent_latest * 12 / 0.30, -2) AS income_needed_today,

    -- Census-reported share of renters who are actually rent-burdened (cross-check).
    round(100 * c.rent_burdened_2024 / nullif(c.renters_2024, 0), 1)     AS pct_renters_burdened,
    round(100 * c.severely_burdened_2024 / nullif(c.renters_2024, 0), 1) AS pct_renters_severely_burdened,

    -- Growth over matching windows: the 2017-21 and 2020-24 Census periods are centered
    -- on 2019 and 2022, so rents are compared over 2019 -> 2022 as well.
    round(100 * (r.rent_avg_2022 / r.rent_avg_2019 - 1), 1)              AS rent_growth_2019_2022_pct,
    round(100 * (c.renter_income_2024 / c.renter_income_2021 - 1), 1)    AS renter_income_growth_pct,
    round(100 * (r.rent_latest / r.rent_avg_2019 - 1), 1)                AS rent_growth_2019_latest_pct,

    -- Downtown 30303 is Georgia State's campus: its renters are mostly students whose
    -- reported income excludes loans and family support, which inflates the rent share.
    CASE WHEN r.zip = '30303' THEN 'Student-heavy ZIP (Georgia State campus): income understates ability to pay'
    END AS data_note
FROM rents r
LEFT JOIN census c USING (zip);
