# Where Can You Afford to Rent in Atlanta?

An analysis of rent affordability across 150 ZIP codes in the Atlanta metro, combining Zillow
rent data (through September 2026) with U.S. Census income data.

**Question:** Which Atlanta neighborhoods are affordable for the people who rent there, where are
rents rising faster than incomes, and where can someone on a typical entry-level salary live?

**Tools:** Python (pandas, requests) · SQL (DuckDB) · Tableau Public

**Dashboard:** [Tableau Public](https://public.tableau.com/app/profile/amal.pushp2875/viz/WhereCanYouAffordtoRentinAtlanta/AtlantaRentAffordability)

---

## Key findings

**1. Most of Atlanta is rent-burdened.** In 107 of 138 ZIP codes (78%), a year of typical rent
costs more than 30% of the typical renter household's income, the standard line for
"rent-burdened." The median ZIP sits at 35.7%. The Census's own survey agrees: in the median
ZIP, 55% of renter households are cost-burdened.

**2. Rents grew about twice as fast as renter incomes.** Over matching windows centered on
2019 → 2022, median rent rose 35.7% while median renter income rose 18.5%. Rent outpaced income
in 84 of 97 ZIPs with data for both.

**3. The cheapest neighborhoods got expensive fastest.** ZIPs in the cheaper half in 2019 saw
rents climb a median of 56% by 2026, versus 38% for the pricier half (correlation between 2019
rent and growth: −0.66). The biggest jumps were on the south side: Jonesboro (+81%), Riverdale
(+72%), West End / 30310 (+71%), East Point (+71%). The places that used to be the affordable
option are where renters are being squeezed hardest.

**4. "Affordable" neighborhoods are mostly wealthy ones.** The ZIPs with the lowest rent-to-income
ratio are Alpharetta, Vinings, Cumming and Sandy Springs. Rents there aren't low; the incomes
are high. Judged only by local income, a neighborhood can look affordable to its current
residents while being out of reach for anyone moving in.

**5. A $50,000 salary works in only 1 of 149 ZIP codes.** Staying under 30% of income on
$50k means rent of $1,250/month or less. Today only Forest Park (30297, $1,220) qualifies.
The bar for the typical ZIP ($1,863/month) is an income of about $74,500.

| Annual salary | ZIPs where rent stays under 30% of income |
|---|---|
| $50,000 | 1 of 149 |
| $60,000 | 13 of 149 |
| $75,000 | 79 of 149 |
| $100,000 | 149 of 149 |

## Recommendations

- **For renters on entry-level salaries:** plan on roommates or a budget above 30%. The
  dashboard's salary filter shows which ZIPs fit a given income.
- **For employers hiring in Atlanta:** the $60k–$75k salary range is where the metro opens up
  (13 → 79 ZIPs). Salaries below it limit where new hires can live without long commutes.
- **For policymakers and housing groups:** the fastest rent growth is in historically affordable
  south-side ZIPs (Clayton County and southwest Atlanta), where most renters were already
  burdened. That's where help for renters would make the most difference.

## Dashboard

**[View the interactive dashboard on Tableau Public](https://public.tableau.com/app/profile/amal.pushp2875/viz/WhereCanYouAffordtoRentinAtlanta/AtlantaRentAffordability)**

- Map of ZIP codes colored by rent as a share of renter income
- "Where can I afford?" map driven by a salary slider ($30k–$150k)
- Median asking rent, 2015–2026, for the five core counties
- Rent growth vs renter income growth by ZIP, 2019–2022

## Data

| Source | What it provides |
|---|---|
| [Zillow Observed Rent Index (ZORI)](https://www.zillow.com/research/data/) | Typical monthly asking rent by ZIP, 2015 – Sept 2026 |
| [Census ACS 5-year, 2020–2024](https://www.census.gov/programs-surveys/acs) | Median renter household income (B25119), median household income (B19013), median gross rent (B25064), rent as a share of income (B25070) |
| Census ACS 5-year, 2017–2021 | Renter income for the growth comparison |

## Method

1. **Download** (`scripts/01_download.py`): the Zillow ZIP-level file, plus four Census tables
   for two survey periods from the Census bulk summary files, filtered to Georgia ZIPs.
2. **Clean and join** (`sql/build.sql`, run by `scripts/02_build.py`):
   - Reshape Zillow's one-column-per-month layout into one row per ZIP per month.
   - Convert the Census's "not available" codes (large negative numbers) to NULL.
   - Join on ZIP, and compute the rent-to-income share, the income needed for each ZIP, and
     growth rates.
3. **Analyze** (`scripts/03_findings.py`): the queries behind every number above.

**Affordability measure:** average 2024 Zillow rent × 12 ÷ median 2024 renter household income.
Using renter income (not all households) matters: renters earn much less than homeowners, so
all-household income would make neighborhoods look more affordable than they are for renters.

### Judgment calls and limitations

- **Matching time periods.** A Census 5-year estimate describes the whole period, so the
  2017–21 and 2020–24 estimates are centered on 2019 and 2022. Rent growth is measured over
  2019 → 2022 so the two growth rates cover the same years.
- **Two kinds of rent.** Zillow measures asking rent on new leases, while the Census measures
  what all current renters pay, including long-time tenants. The two correlate at 0.63, and
  Zillow runs about 5% higher. That fits, since new leases price in recent increases.
- **Student outlier.** Downtown 30303 (Georgia State's campus) shows rent at 162% of income,
  because student households report little income and live on loans and family support. It is
  flagged in the data and excluded from the summary numbers.
- **Coverage.** Zillow publishes rents for 150 Atlanta-metro ZIPs, mostly the larger rental
  markets; smaller rural ZIPs aren't included. 11 ZIPs lack 2024 rent data and 53 lack 2019
  data, so counts vary by metric.

## Run it yourself

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/01_download.py   # ~10 MB of raw data
python scripts/02_build.py      # builds data/processed/*.csv
python scripts/03_findings.py   # prints the findings
```

The two CSVs in `data/processed/` are the inputs to the Tableau dashboard.
`python scripts/04_tableau_workbook.py` builds the Tableau workbook and data extracts from them
(written to `dashboard/`).
