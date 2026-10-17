"""Generate the Tableau workbook (dashboard/atlanta_rent.twb) from the processed CSVs.

Open the result in Tableau Public, then File -> Save to Tableau Public.
"""
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from tableauhyperapi import (Connection, CreateMode, HyperProcess, SqlType, TableDefinition,
                             TableName, Telemetry, escape_string_literal)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "processed"
OUT = ROOT / "dashboard" / "atlanta_rent.twb"

AFF = "federated.atlanta_aff"
MON = "federated.atlanta_monthly"
SALARY = "[Parameters].[Parameter 1]"

AFF_COLUMNS = [
    ("zip", "string"), ("city", "string"), ("county", "string"),
    ("rent_latest", "real"), ("latest_month", "date"),
    ("rent_avg_2019", "real"), ("rent_avg_2024", "real"),
    ("median_income_2024", "integer"), ("renter_income_2024", "integer"),
    ("census_median_rent_2024", "integer"), ("renters_2024", "integer"),
    ("rent_share_of_income_pct", "real"), ("income_needed_today", "real"),
    ("pct_renters_burdened", "real"), ("pct_renters_severely_burdened", "real"),
    ("rent_growth_2019_2022_pct", "real"), ("renter_income_growth_pct", "real"),
    ("rent_growth_2019_latest_pct", "real"), ("data_note", "string"),
]
MON_COLUMNS = [
    ("zip", "string"), ("city", "string"), ("county", "string"),
    ("month", "date"), ("rent", "real"),
]

CAPTIONS = {
    "zip": "ZIP", "city": "City", "county": "County",
    "rent_latest": "Rent now ($/mo)", "rent_avg_2024": "Avg rent 2024 ($/mo)",
    "renter_income_2024": "Median renter income", "rent_share_of_income_pct": "Rent share of income (%)",
    "income_needed_today": "Income needed today", "pct_renters_burdened": "Renters burdened (%)",
    "rent_growth_2019_2022_pct": "Rent growth 2019-22 (%)", "renter_income_growth_pct": "Renter income growth (%)",
    "rent_growth_2019_latest_pct": "Rent growth since 2019 (%)", "month": "Month", "rent": "Rent ($/mo)",
}

CALCS = {
    AFF: [
        ("Calculation_afford", "Affordable on your salary",
         f'IF [rent_latest] * 12 <= {SALARY} * 0.30 THEN "Affordable" ELSE "Over 30% of salary" END'),
        ("Calculation_outpaced", "Which grew faster",
         'IF [rent_growth_2019_2022_pct] > [renter_income_growth_pct] THEN "Rent grew faster" '
         'ELSE "Income grew faster" END'),
    ],
    MON: [],
}

GENERATED_GEO = (
    "<column aggregation='Avg' datatype='real' name='[Latitude (generated)]' role='measure' "
    "semantic-role='[Geographical].[Latitude]' type='quantitative' />"
    "<column aggregation='Avg' datatype='real' name='[Longitude (generated)]' role='measure' "
    "semantic-role='[Geographical].[Longitude]' type='quantitative' />"
)


HYPER_TYPES = {"string": SqlType.text(), "real": SqlType.double(),
               "integer": SqlType.big_int(), "date": SqlType.date()}
EXTRACT_TABLE = TableName("Extract", "Extract")


def build_extracts():
    """Tableau Public only opens workbooks whose data is an extract (.hyper), so build them."""
    with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        for filename, columns in (("atlanta_zip_affordability.csv", AFF_COLUMNS),
                                  ("atlanta_rent_monthly.csv", MON_COLUMNS)):
            hyper_path = OUT.parent / filename.replace(".csv", ".hyper")
            table = TableDefinition(EXTRACT_TABLE, [
                TableDefinition.Column(n, HYPER_TYPES[t]) for n, t in columns])
            with Connection(hyper.endpoint, hyper_path, CreateMode.CREATE_AND_REPLACE) as conn:
                conn.catalog.create_schema("Extract")
                conn.catalog.create_table(table)
                rows = conn.execute_command(
                    f"COPY {EXTRACT_TABLE} FROM {escape_string_literal(str(DATA_DIR / filename))} "
                    "WITH (format csv, header, NULL '')")
            print(f"wrote {hyper_path.name} ({rows} rows)")


def column_def(name, dtype):
    role, kind = ("dimension", "nominal") if dtype == "string" else (
        ("dimension", "ordinal") if dtype == "date" else ("measure", "quantitative"))
    extra = " semantic-role='[ZipCode].[Name]'" if name == "zip" else ""
    caption = f" caption={quoteattr(CAPTIONS[name])}" if name in CAPTIONS else ""
    return (f"<column{caption} datatype='{dtype}' name='[{name}]' role='{role}' "
            f"type='{kind}'{extra} />")


def calc_def(name, caption, formula):
    return (f"<column caption={quoteattr(caption)} datatype='string' name='[{name}]' role='dimension' "
            f"type='nominal'><calculation class='tableau' formula={quoteattr(formula)} /></column>")


def datasource(ds, caption, filename, columns):
    stem = filename.removesuffix(".csv")
    relation_cols = "".join(
        f"<column datatype='{t}' name='{n}' ordinal='{i}' />" for i, (n, t) in enumerate(columns))
    return f"""
  <datasource caption={quoteattr(caption)} inline='true' name='{ds}' version='18.1'>
    <connection class='federated'>
      <named-connections>
        <named-connection caption='{stem}' name='textscan.{stem}'>
          <connection class='textscan' directory={quoteattr(str(DATA_DIR))} filename='{filename}' password='' server='' />
        </named-connection>
      </named-connections>
      <relation connection='textscan.{stem}' name='{filename}' table='[{stem}#csv]' type='table'>
        <columns character-set='UTF-8' header='yes' locale='en_US' separator=','>{relation_cols}</columns>
      </relation>
    </connection>
    <aliases enabled='yes' />
    {"".join(column_def(n, t) for n, t in columns)}
    {"".join(calc_def(*c) for c in CALCS[ds])}
    <extract count='-1' enabled='true' units='records'>
      <connection access_mode='readonly' authentication='auth-none' author-locale='en_US' class='hyper'
                  dbname={quoteattr(str(OUT.parent / filename.replace(".csv", ".hyper")))}
                  default-settings='hyper' schema='Extract' sslmode='' tablename='Extract'
                  username='tableau_internal_user'>
        <relation name='Extract' table='[Extract].[Extract]' type='table' />
        <refresh increment-key='' incremental-updates='false' />
      </connection>
    </extract>
  </datasource>"""


PARAMETERS = f"""
  <datasource hasconnection='false' inline='true' name='Parameters' version='18.1'>
    <aliases enabled='yes' />
    <column caption='Your salary' datatype='integer' name='[Parameter 1]' param-domain-type='range'
            role='measure' type='quantitative' value='50000'>
      <calculation class='tableau' formula='50000' />
      <range granularity='5000' max='150000' min='30000' />
    </column>
  </datasource>"""


def instance(field, derivation):
    """Return (column-instance xml, qualified reference) for a field + aggregation."""
    prefix, kind, suffix = {
        "None": ("none", "nominal", "nk"), "Sum": ("sum", "quantitative", "qk"),
        "Median": ("median", "quantitative", "qk"), "Month-Trunc": ("tmn", "quantitative", "qk"),
        "Attribute": ("attr", "nominal", "nk"),  # dimensions shown in tooltips
    }[derivation]
    name = f"[{prefix}:{field}:{suffix}]"
    xml = (f"<column-instance column='[{field}]' derivation='{derivation}' name='{name}' "
           f"pivot='key' type='{kind}' />")
    return xml, name


def worksheet(name, title, ds, deps, rows, cols, mark, encodings, filters="", style=""):
    instances = "".join(x for x, _ in deps.values())
    col_defs = "".join(
        column_def(n, t) for n, t in (AFF_COLUMNS if ds == AFF else MON_COLUMNS)
        if any(f"[{n}]" in x for x, _ in deps.values()))
    calc_defs = "".join(calc_def(*c) for c in CALCS[ds] if any(f"[{c[0]}]" in x for x, _ in deps.values()))
    uses_salary = "Calculation_afford" in instances
    param_deps = ("<datasource-dependencies datasource='Parameters'>"
                  "<column caption='Your salary' datatype='integer' name='[Parameter 1]' "
                  "param-domain-type='range' role='measure' type='quantitative' value='50000'>"
                  "<calculation class='tableau' formula='50000' />"
                  "<range granularity='5000' max='150000' min='30000' /></column>"
                  "</datasource-dependencies>") if uses_salary else ""
    enc = "".join(f"<{kind} column='[{ds}].{deps[key][1]}' />" for kind, key in encodings)
    return f"""
    <worksheet name={quoteattr(name)}>
      <layout-options><title><formatted-text><run bold='true' fontsize='13'>{escape(title)}</run></formatted-text></title></layout-options>
      <table>
        <view>
          <datasources>
            <datasource name='{ds}' />
            {"<datasource name='Parameters' />" if uses_salary else ""}
          </datasources>
          {param_deps}
          <datasource-dependencies datasource='{ds}'>
            {col_defs}{calc_defs}{GENERATED_GEO if mark == "Multipolygon" else ""}{instances}
          </datasource-dependencies>
          {filters}
          <aggregation value='true' />
        </view>
        <style>{style}</style>
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class='{mark}' />
            <encodings>{enc}</encodings>
          </pane>
        </panes>
        <rows>{rows}</rows>
        <cols>{cols}</cols>
      </table>
    </worksheet>"""


def null_only_filter(ds, ref):
    """Keep only rows where the field is NULL (hides the flagged student ZIP)."""
    return (f"<filter class='categorical' column='[{ds}].{ref}'>"
            f"<groupfilter function='member' level='{ref}' member='%null%' "
            f"user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' />"
            f"</filter><slices><column>[{ds}].{ref}</column></slices>")


def members_filter(ds, ref, values):
    """Keep only rows whose field is one of `values`."""
    members = "".join(
        f"<groupfilter function='member' level='{ref}' member={quoteattr(chr(34) + v + chr(34))} />"
        for v in values)
    return (f"<filter class='categorical' column='[{ds}].{ref}'>"
            f"<groupfilter function='union' user:ui-domain='database' user:ui-enumeration='inclusive' "
            f"user:ui-marker='enumerate'>{members}</groupfilter>"
            f"</filter><slices><column>[{ds}].{ref}</column></slices>")


CORE_COUNTIES = ["Fulton County", "Dekalb County", "Cobb County", "Gwinnett County", "Clayton County"]


def build():
    geo_rows, geo_cols = f"[{AFF}].[Latitude (generated)]", f"[{AFF}].[Longitude (generated)]"
    tooltip_fields = ["city", "rent_latest", "renter_income_2024", "pct_renters_burdened",
                      "income_needed_today"]

    def map_deps(color_field, color_deriv):
        deps = {"zip": instance("zip", "None"), "note": instance("data_note", "None"),
                "color": instance(color_field, color_deriv)}
        for f in tooltip_fields:
            deps[f] = instance(f, "Attribute" if f == "city" else "Sum")
        return deps

    tooltips = [("tooltip", f) for f in tooltip_fields]

    share = map_deps("rent_share_of_income_pct", "Sum")
    share_map = worksheet(
        "Affordability Map", "Rent as a share of renter income (orange = rent-burdened, over 30%)", AFF, share,
        geo_rows, geo_cols, "Multipolygon",
        [("color", "color"), ("lod", "zip")] + tooltips,
        filters=null_only_filter(AFF, share["note"][1]),
        style=(f"<style-rule element='mark'><encoding attr='color' field='[{AFF}].{share['color'][1]}' "
               f"palette='orange_blue_diverging_10_0' type='interpolated' center='30' reverse='true' />"
               f"</style-rule>"))

    salary = map_deps("Calculation_afford", "None")
    salary_map = worksheet(
        "Salary Map", "Where can you afford? (blue = under 30% of salary)", AFF, salary,
        geo_rows, geo_cols, "Multipolygon",
        [("color", "color"), ("lod", "zip")] + tooltips,
        filters=null_only_filter(AFF, salary["note"][1]))

    trend = {"month": instance("month", "Month-Trunc"), "rent": instance("rent", "Median"),
             "county": instance("county", "None")}
    trend_sheet = worksheet(
        "Rent Trend", "Median asking rent, core counties, 2015-2026", MON, trend,
        f"[{MON}].{trend['rent'][1]}", f"[{MON}].{trend['month'][1]}", "Line",
        [("color", "county")],
        filters=members_filter(MON, trend["county"][1], CORE_COUNTIES))

    scatter = {"x": instance("renter_income_growth_pct", "Sum"),
               "y": instance("rent_growth_2019_2022_pct", "Sum"),
               "zip": instance("zip", "None"), "color": instance("Calculation_outpaced", "None"),
               "city": instance("city", "Attribute")}
    scatter_sheet = worksheet(
        "Growth Scatter", "Rent vs income growth, 2019-22 (orange = rent faster)", AFF,
        scatter, f"[{AFF}].{scatter['y'][1]}", f"[{AFF}].{scatter['x'][1]}", "Circle",
        [("color", "color"), ("lod", "zip"), ("tooltip", "city")])

    findings = ("78% of Atlanta ZIP codes are rent-burdened. Rents grew about twice as fast as "
                "renter incomes (2019-2022), fastest in the cheapest neighborhoods. "
                "A $50k salary affords only 1 of 149 ZIPs.")
    dashboard = f"""
    <dashboard name='Atlanta Rent Affordability'>
      <style />
      <size maxheight='800' maxwidth='1200' minheight='800' minwidth='1200' />
      <zones>
        <zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>
          <zone h='6000' id='2' type-v2='text' w='100000' x='0' y='0'>
            <formatted-text><run bold='true' fontsize='20'>Where Can You Afford to Rent in Atlanta?</run></formatted-text>
          </zone>
          <zone h='6000' id='3' type-v2='text' w='100000' x='0' y='6000'>
            <formatted-text><run fontsize='11'>{escape(findings)}</run></formatted-text>
          </zone>
          <zone h='44000' id='4' name='Affordability Map' w='50000' x='0' y='12000' />
          <zone h='37000' id='5' name='Salary Map' w='50000' x='50000' y='12000' />
          <zone h='7000' id='6' mode='slider' param='{SALARY}' type-v2='paramctrl' w='50000' x='50000' y='49000' />
          <zone h='41000' id='7' name='Rent Trend' w='38000' x='0' y='56000' />
          <zone h='41000' id='10' name='Rent Trend' param='[{MON}].[none:county:nk]' type-v2='color' w='12000' x='38000' y='56000' />
          <zone h='41000' id='8' name='Growth Scatter' w='50000' x='50000' y='56000' />
          <zone h='3000' id='9' type-v2='text' w='100000' x='0' y='97000'>
            <formatted-text><run fontsize='9'>Sources: Zillow Observed Rent Index (through Sept 2026); U.S. Census ACS 5-year 2017-21 and 2020-24.</run></formatted-text>
          </zone>
        </zone>
      </zones>
    </dashboard>"""

    # Tableau needs a window per sheet and an active (maximized) one to open on.
    sheet_names = ["Affordability Map", "Salary Map", "Rent Trend", "Growth Scatter"]
    sheet_cards = (
        "<cards><edge name='left'><strip size='160'><card type='pages' /><card type='filters' />"
        "<card type='marks' /></strip></edge><edge name='top'><strip size='2147483647'>"
        "<card type='columns' /></strip><strip size='2147483647'><card type='rows' /></strip>"
        "<strip size='31'><card type='title' /></strip></edge></cards>")
    windows = "".join(
        f"\n    <window class='worksheet' name={quoteattr(n)}>{sheet_cards}</window>" for n in sheet_names)
    windows += (
        "\n    <window class='dashboard' maximized='true' name='Atlanta Rent Affordability'>"
        "<viewpoints>" + "".join(f"<viewpoint name={quoteattr(n)} />" for n in sheet_names) +
        "</viewpoints><active id='-1' /><device-preview /></window>")

    workbook = f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook original-version='18.1' source-build='2025.2.0 (20252.25.0603.1006)' source-platform='mac' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <datasources>
    {PARAMETERS}
    {datasource(AFF, "ZIP affordability", "atlanta_zip_affordability.csv", AFF_COLUMNS)}
    {datasource(MON, "Monthly rents", "atlanta_rent_monthly.csv", MON_COLUMNS)}
  </datasources>
  <worksheets>{share_map}{salary_map}{trend_sheet}{scatter_sheet}
  </worksheets>
  <dashboards>{dashboard}
  </dashboards>
  <windows source-height='30'>{windows}
  </windows>
</workbook>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    build_extracts()
    OUT.write_text(workbook)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
