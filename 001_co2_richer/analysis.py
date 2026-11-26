"""
Question: Can a country get richer while cutting its CO2 emissions?

Dataset: Our World in Data, CO2 and Greenhouse Gas Emissions
         https://github.com/owid/co2-data  (GDP series from the Maddison Project)
Window:  2000 -> latest year where GDP and consumption-based CO2 both exist.

Every number that may appear in the video is written to facts.json.
The script writer is only allowed to cite values from that file.
"""
import json
import sys
from pathlib import Path

import pandas as pd

DATA_FILES = {"owid-co2.csv": "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"}

MIN_POP = 10_000_000  # only countries with 10M+ people, to avoid tiny-country noise
START = 2000


def run(csv_path: str, out_dir: str) -> dict:
    d = pd.read_csv(csv_path)
    d = d[d["iso_code"].notna() & ~d["iso_code"].astype(str).str.startswith("OWID")]  # countries only

    # Latest year where every country-level series we need is reported
    have = d.dropna(subset=["gdp", "co2_per_capita", "consumption_co2_per_capita", "population"])
    end = int(have.groupby("year")["country"].count().loc[lambda s: s >= 100].index.max())

    def snap(year):
        s = d[d["year"] == year].set_index("country")
        return pd.DataFrame({
            "gdp_pc": s["gdp"] / s["population"],
            "co2_pc": s["co2_per_capita"],
            "cons_pc": s["consumption_co2_per_capita"],
            "pop": s["population"],
        })

    a, b = snap(START), snap(end)
    t = a.join(b, lsuffix="_start", rsuffix="_end").dropna()
    t = t[t["pop_end"] >= MIN_POP]

    t["gdp_change_pct"] = (t["gdp_pc_end"] / t["gdp_pc_start"] - 1) * 100
    t["co2_change_pct"] = (t["co2_pc_end"] / t["co2_pc_start"] - 1) * 100
    t["cons_change_pct"] = (t["cons_pc_end"] / t["cons_pc_start"] - 1) * 100

    richer = t["gdp_change_pct"] > 0
    cut_prod = t["co2_change_pct"] < 0
    cut_cons = t["cons_change_pct"] < 0
    decoupled = t[richer & cut_prod].sort_values("co2_change_pct")
    still_after_trade = decoupled[decoupled["cons_change_pct"] < 0]

    # Automated check: an end year distorted by a shock (war, collapse) makes the comparison misleading.
    prev = d[d["year"] == end - 1].set_index("country")
    cur = d[d["year"] == end].set_index("country")
    gdp_jump = (cur["gdp"] / prev["gdp"] - 1) * 100
    shocked = sorted(c for c in decoupled.index if c in gdp_jump and abs(gdp_jump[c]) >= 15)

    top = decoupled.head(10)
    r1 = lambda x: round(float(x), 1)

    facts = {
        "question": "Can a country get richer while cutting its CO2 emissions?",
        "source": "Our World in Data, CO2 and Greenhouse Gas Emissions dataset (GDP from Maddison Project)",
        "source_url": "https://github.com/owid/co2-data",
        "data_years": f"{START}-{end}",
        "filters": f"Countries with at least {MIN_POP:,} people in {end}",
        "n_countries": int(len(t)),
        "n_richer": int(richer.loc[t.index].sum()),
        "n_decoupled": int(len(decoupled)),
        "n_decoupled_consumption": int(len(still_after_trade)),
        "n_richer_and_more_co2": int((richer & ~cut_prod).loc[t.index].sum()),
        "pct_of_richer_where_co2_rose": round(100 * int((richer & ~cut_prod).sum()) / int(richer.sum())),
        "lost_on_consumption": [
            {
                "country": c,
                "co2_per_capita_change_pct": r1(row.co2_change_pct),
                "consumption_co2_per_capita_change_pct": r1(row.cons_change_pct),
            }
            for c, row in decoupled[decoupled["cons_change_pct"] >= 0].iterrows()
        ],
        "top_decouplers": [
            {
                "country": c,
                "gdp_per_capita_change_pct": r1(row.gdp_change_pct),
                "co2_per_capita_change_pct": r1(row.co2_change_pct),
                "consumption_co2_per_capita_change_pct": r1(row.cons_change_pct),
                "co2_per_capita_start_t": r1(row.co2_pc_start),
                "co2_per_capita_end_t": r1(row.co2_pc_end),
            }
            for c, row in top.iterrows()
        ],
        "review_flags": [
            f"{c}: GDP changed {gdp_jump[c]:+.0f}% in {end} alone; endpoint may be distorted" for c in shocked
        ],
        "caveats": [
            "Production-based CO2 counts emissions inside a country's borders; consumption-based adjusts for traded goods.",
            "GDP per person is inflation-adjusted (Maddison Project, international dollars).",
            "CO2 only; other greenhouse gases are not included.",
        ],
    }

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "facts.json").write_text(json.dumps(facts, indent=2))
    t.round(2).to_csv(out / "analysis_table.csv")  # published for the "fact-check us" link
    return facts


def viewer_table(out_dir):
    """Readable table published with the video (the 'fact-check us' link)."""
    t = pd.read_csv(Path(out_dir) / "analysis_table.csv", index_col=0).rename_axis("Country").reset_index()
    v = pd.DataFrame({
        "Country": t["Country"],
        "Income per person 2000 (intl $)": t["gdp_pc_start"].round(0),
        "Income per person 2022 (intl $)": t["gdp_pc_end"].round(0),
        "Income change %": t["gdp_change_pct"].round(1),
        "CO2 per person 2000 (t)": t["co2_pc_start"].round(2),
        "CO2 per person 2022 (t)": t["co2_pc_end"].round(2),
        "CO2 change % (made at home)": t["co2_change_pct"].round(1),
        "CO2 change % (incl. imports)": t["cons_change_pct"].round(1),
    })
    v["Richer AND less CO2?"] = (v["Income change %"] > 0) & (v["CO2 change % (made at home)"] < 0)
    v["Still true incl. imports?"] = v["Richer AND less CO2?"] & (v["CO2 change % (incl. imports)"] < 0)
    v.sort_values("CO2 change % (made at home)").to_csv(Path(out_dir) / "data_table.csv", index=False)


def analyze(raw_dir, out_dir):
    facts = run(str(Path(raw_dir) / "owid-co2.csv"), out_dir)
    viewer_table(out_dir)
    return facts


if __name__ == "__main__":
    f = run(sys.argv[1], sys.argv[2])
    print(json.dumps({k: v for k, v in f.items() if k != "top_decouplers"}, indent=2))
    for r in f["top_decouplers"]:
        print(r)
