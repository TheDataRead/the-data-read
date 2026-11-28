"""
Long video L01: 25 years of the world's electricity, in data.
Dataset: Our World in Data, Energy dataset (Ember; Energy Institute)  https://github.com/owid/energy-data
"""
import json
from pathlib import Path

import pandas as pd

DATA_FILES = {"energy.csv": "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"}
START, MID = 2000, 2015
SOURCES = {"coal": "Coal", "gas": "Gas", "hydro": "Hydro", "nuclear": "Nuclear", "wind": "Wind",
           "solar": "Solar", "oil": "Oil", "biofuel": "Bioenergy"}
MIN_TWH = 20


def analyze(raw_dir, out_dir):
    e = pd.read_csv(Path(raw_dir) / "energy.csv")
    w = e[e.country == "World"].set_index("year")
    need = ["electricity_generation"] + [f"{k}_electricity" for k in SOURCES]
    end = int(w[need].dropna().index.max())
    s, t = w.loc[START], w.loc[end]
    r = lambda x: int(round(float(x)))
    c = e[e["iso_code"].notna() & ~e["iso_code"].astype(str).str.startswith("OWID")]
    cy = lambda y: c[c.year == y].set_index("country")

    mix = [{"source": n, "twh_start": r(s[f"{k}_electricity"]), "twh_end": r(t[f"{k}_electricity"]),
            "share_end": round(float(t[f"{k}_share_elec"]), 1),
            "change_pct": r((t[f"{k}_electricity"] / s[f"{k}_electricity"] - 1) * 100)} for k, n in SOURCES.items()]
    mix.sort(key=lambda m: -m["twh_end"])
    sw = w["solar_electricity"] + w["wind_electricity"]
    passed = lambda other: int(next(y for y in w.loc[START:end].index if sw[y] > w.loc[y, other]))

    a, b = cy(START), cy(end)
    coal_d = (b["coal_electricity"] - a["coal_electricity"]).dropna().sort_values()
    up, down = coal_d[coal_d > 0][::-1].head(3), coal_d[coal_d < 0].head(3)
    m15 = cy(MID)
    df = pd.DataFrame({"s": m15["low_carbon_share_elec"], "e": b["low_carbon_share_elec"], "twh": b["electricity_generation"],
                       "sw": (b["solar_share_elec"] + b["wind_share_elec"]) - (m15["solar_share_elec"] + m15["wind_share_elec"]),
                       "nuc": b["nuclear_share_elec"] - m15["nuclear_share_elec"],
                       "hyd": b["hydro_share_elec"] - m15["hydro_share_elec"]}).dropna()
    df = df[df.twh >= MIN_TWH]
    df["gain"] = df.e - df.s
    routes = {n: {"start": r(x.s), "end": r(x.e), "gain": r(x.gain), "solar_wind": r(x.sw), "nuclear": r(x.nuc), "hydro": r(x.hyd)}
              for n, x in df.sort_values("gain", ascending=False).head(5).iterrows()}
    big3 = b.loc[["China", "United States", "India"], "electricity_generation"]
    china_start_share = float(a.loc["China", "electricity_generation"] / s["electricity_generation"] * 100)
    uk = c[c.country == "United Kingdom"].set_index("year")["coal_share_elec"]

    facts = {
        "question": "How has the world's electricity changed in 25 years?",
        "source": "Our World in Data, Energy dataset (Ember; Energy Institute Statistical Review)",
        "source_short": "Our World in Data (Ember, Energy Institute)",
        "source_url": "https://github.com/owid/energy-data",
        "data_years": f"{START}-{end}",
        "filters_short": "electricity generation",
        "start_year": START, "mid_year": MID, "end_year": end, "span_years": end - START, "min_twh": MIN_TWH,
        "solar_passed_wind": int(next(y for y in w.loc[START:end].index
                                      if w.loc[y, "solar_electricity"] > w.loc[y, "wind_electricity"])),
        "china_share_of_coal_increase_pct": r(coal_d.get("China", 0) / coal_d[coal_d > 0].sum() * 100),
        "china_coal_end": r(b.loc["China", "coal_electricity"]),
        "total_start": r(s["electricity_generation"]), "total_end": r(t["electricity_generation"]),
        "total_change_pct": r((t["electricity_generation"] / s["electricity_generation"] - 1) * 100),
        "mix": mix,
        "fossil_share_start": r(s["fossil_share_elec"]), "fossil_share_end": r(t["fossil_share_elec"]),
        "low_carbon_share_start": r(s["low_carbon_share_elec"]), "low_carbon_share_end": r(t["low_carbon_share_elec"]),
        "solar_mid": r(w.loc[MID, "solar_electricity"]), "solar_end": r(t["solar_electricity"]),
        "solar_multiple": r(t["solar_electricity"] / w.loc[MID, "solar_electricity"]),
        "wind_mid": r(w.loc[MID, "wind_electricity"]), "wind_end": r(t["wind_electricity"]),
        "sw_start": r(sw[START]), "sw_end": r(sw[end]),
        "sw_passed_nuclear": passed("nuclear_electricity"), "sw_passed_hydro": passed("hydro_electricity"),
        "coal_share_start": r(s["coal_share_elec"]), "coal_share_end": r(t["coal_share_elec"]),
        "coal_start": r(s["coal_electricity"]), "coal_end": r(t["coal_electricity"]),
        "coal_change_pct": r((t["coal_electricity"] / s["coal_electricity"] - 1) * 100),
        "coal_up": [{"country": k, "twh": r(v)} for k, v in up.items()],
        "coal_down": [{"country": k, "twh": r(v)} for k, v in down.items()],
        "uk_coal_share_start": r(uk.loc[START]), "uk_coal_share_end": round(float(uk.loc[end]), 1),
        "routes": routes,
        "big3": [{"country": k, "twh": r(v), "share": r(v / t["electricity_generation"] * 100)} for k, v in big3.items()],
        "big3_share": r(big3.sum() / t["electricity_generation"] * 100),
        "china_share_start": r(china_start_share),
        "series": {"year": [int(y) for y in w.loc[START:end].index],
                   "total": [r(v) for v in w.loc[START:end, "electricity_generation"]],
                   "coal": [r(v) for v in w.loc[START:end, "coal_electricity"]],
                   "gas": [r(v) for v in w.loc[START:end, "gas_electricity"]],
                   "solar": [r(v) for v in w.loc[START:end, "solar_electricity"]],
                   "wind": [r(v) for v in w.loc[START:end, "wind_electricity"]],
                   "nuclear": [r(v) for v in w.loc[START:end, "nuclear_electricity"]],
                   "hydro": [r(v) for v in w.loc[START:end, "hydro_electricity"]]},
        "review_flags": [f"{end}: figures are preliminary estimates and may be revised",
                         "Hydro: output swings with rainfall, so one year can move a country"],
    }
    out = Path(out_dir)
    (out / "facts.json").write_text(json.dumps(facts, indent=2))
    cols = ["electricity_generation", "coal_electricity", "gas_electricity", "hydro_electricity", "nuclear_electricity",
            "wind_electricity", "solar_electricity", "low_carbon_share_elec", "coal_share_elec"]
    tbl = c[c.year.isin([START, MID, end])].pivot_table(index="country", columns="year", values=cols)
    tbl.columns = [f"{m.replace('_electricity', ' (TWh)').replace('_share_elec', ' share (%)').replace('_', ' ')} {y}"
                   for m, y in tbl.columns]
    tbl.round(1).to_csv(out / "data_table.csv")
    return facts
