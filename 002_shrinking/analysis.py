"""
Question: Which countries are already shrinking?
Dataset: World Bank population estimates, via datasets/population on GitHub
         https://github.com/datasets/population
"""
import json
from pathlib import Path

import pandas as pd

DATA_FILES = {"pop.csv": "https://raw.githubusercontent.com/datasets/population/main/data/population.csv"}
# World Bank regional / income aggregates (not countries)
AGG = set("""AFE AFW ARB CEB CSS EAP EAR EAS ECA ECS EMU EUU FCS HIC HPC IBD IBT IDA IDB IDX INX LAC LCN LDC LIC LMC LMY
LTE MEA MIC MNA NAC OED OSS PRE PSS PST SAS SSA SSF SST TEA TEC TLA TMN TSA TSS UMC WLD""".split())
MIN_PEAK = 1_000_000  # ignore very small countries


def analyze(raw_dir, out_dir):
    p = pd.read_csv(Path(raw_dir) / "pop.csv")
    p = p[~p["Country Code"].isin(AGG)]
    end = int(p["Year"].max())
    rows = []
    for (name, code), g in p.groupby(["Country Name", "Country Code"]):
        g = g.set_index("Year")["Value"]
        if end not in g.index:
            continue
        peak_year = int(g.idxmax())
        peak, now = float(g.max()), float(g.loc[end])
        rows.append({"country": name, "code": code, "peak_year": peak_year, "peak": peak, "now": now,
                     "pop_1990": float(g.get(1990, float("nan"))),
                     "drop_pct": (now / peak - 1) * 100, "drop_people": now - peak})
    d = pd.DataFrame(rows)
    big = d[d["peak"] >= MIN_PEAK]
    shrinking = big[(big["peak_year"] < end) & (big["drop_pct"] <= -1)]
    by_pct = shrinking.sort_values("drop_pct").head(5)
    by_people = shrinking.sort_values("drop_people").head(5)
    world_people_shrinking = shrinking["now"].sum() / big["now"].sum() * 100
    china = d[d["code"] == "CHN"].iloc[0]
    japan = d[d["code"] == "JPN"].iloc[0]

    facts = {
        "question": "Which countries are already shrinking?",
        "source": "World Bank population estimates (via datasets/population on GitHub)",
        "source_short": "World Bank population estimates",
        "source_url": "https://github.com/datasets/population",
        "data_years": f"1960-{end}",
        "filters_short": f"countries over 1 million people",
        "end_year": end,
        "n_countries": int(len(big)),
        "n_shrinking": int(len(shrinking)),
        "share_people_in_shrinking_pct": round(world_people_shrinking),
        "top_pct": [{"country": r.country, "peak_year": int(r.peak_year), "drop_pct": round(r.drop_pct)}
                    for r in by_pct.itertuples()],
        "top_people": [{"country": r.country, "peak_year": int(r.peak_year), "drop_m": round(-r.drop_people / 1e6, 1)}
                       for r in by_people.itertuples()],
        "china_peak_year": int(china.peak_year), "china_drop_m": round(-china.drop_people / 1e6, 1),
        "japan_peak_year": int(japan.peak_year), "japan_drop_m": round(-japan.drop_people / 1e6, 1),
        "review_flags": [],
    }
    flagged = {"Ukraine", "Syrian Arab Republic", "Venezuela, RB"} & set(by_pct.country) | \
              {"Ukraine", "Syrian Arab Republic", "Venezuela, RB"} & set(by_people.country)
    if flagged:
        facts["review_flags"].append("Emigration: war and people moving abroad shrink some countries, not only low birth rates")
    out = Path(out_dir)
    (out / "facts.json").write_text(json.dumps(facts, indent=2))
    t = big.rename(columns={"country": "Country", "peak_year": "Peak year", "peak": "Peak population",
                            "now": f"Population {end}", "drop_pct": "Change since peak (%)"})
    t[["Country", "Peak year", "Peak population", f"Population {end}", "Change since peak (%)"]].round(1) \
        .sort_values("Change since peak (%)").to_csv(out / "data_table.csv", index=False)
    return facts
