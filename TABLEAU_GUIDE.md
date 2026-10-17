# Building the dashboard in Tableau Public

Plan for about 1–2 hours. Uses the two CSVs in `data/processed/`.

## Setup
1. Make a free account at public.tableau.com and install **Tableau Public** (desktop app).
2. Open it → **Connect → Text file** → `atlanta_zip_affordability.csv`.
3. In the data pane, click the type icon on **zip**. Set it to **String**, then
   **Geographic Role → ZIP Code/Postcode**. Tableau can now draw ZIPs on a map.
4. Add the second file: **Data → New Data Source → Text file** → `atlanta_rent_monthly.csv`.
   Set its **zip** column the same way.

## Sheet 1: Affordability map
1. Double-click **zip**. Tableau draws a map with a dot per ZIP.
2. Change the mark type (Marks card dropdown) from Automatic to **Map** to fill each ZIP area.
3. Drag **rent_share_of_income_pct** to **Color**. Edit colors → diverging palette (e.g.
   Orange-Blue, reversed), **Center** at 30, so ZIPs above 30% show orange and below show blue.
4. Drag **city**, **rent_latest**, **renter_income_2024**, **pct_renters_burdened** to
   **Tooltip**.
5. Drag **data_note** to **Filter** → keep only Null, to hide the student ZIP.
6. Title it: *"Rent as a share of renter income, by ZIP (30%+ = rent-burdened)"*.

## Sheet 2: "Where can I afford?"
1. **Create Parameter** → name it *Salary*, type Integer, current value 50000, range 30000 to
   150000, step 5000. Right-click it → **Show Parameter**.
2. **Create Calculated Field** *Affordable on salary*:
   ```
   IF [rent_latest] * 12 <= [Salary] * 0.30 THEN "Affordable" ELSE "Over 30%" END
   ```
3. Duplicate the map sheet and put *Affordable on salary* on **Color** instead (green / gray).
4. Add a text box or title: *"Moving the salary slider shows which ZIPs fit your budget"*.

## Sheet 3: Rent trends
1. Switch to the **atlanta_rent_monthly** data source.
2. **month** to Columns (right-click → **Month**, continuous), **rent** to Rows
   (aggregation **Median** for the metro line).
3. Drag **zip** to **Filter** → show filter as a single-value dropdown, so viewers can pick a
   ZIP. Optionally drag **county** to Color for a county comparison.

## Sheet 4: Rent growth vs income growth
1. Back on the affordability source: **renter_income_growth_pct** to Columns,
   **rent_growth_2019_2022_pct** to Rows, **zip** to Detail. You get a scatter plot.
2. Add a reference line where x = y (Analysis → Trend Lines, or a calculated field equal to x).
   Every dot above it is a ZIP where rent grew faster than renter income.

## Dashboard
1. **New Dashboard**, size **Automatic**. Drag in the map (big, top left), the salary map,
   the trend chart and the scatter plot.
2. Add a title and a text box with the three headline findings from the README.
3. On the map, **Use as Filter** (funnel icon), so clicking a ZIP filters the trend chart.
4. **File → Save to Tableau Public**. Copy the link into the README's Dashboard section and
   into your LinkedIn Featured section.
