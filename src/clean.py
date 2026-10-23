"""Nettoyage du fichier brut ARCEP QoS 2025 (habitations) et production des tables du projet.

Usage :
    python src/clean.py --input data/raw/2025_QoS_Metropole_data_habitations.csv

Sorties :
    data/processed/clean.parquet            (local, ignoré par git : trop volumineux)
    data/sample/points_sample.csv.gz        échantillon stratifié de 40 000 mesures (versionné)
    data/aggregates/*.csv                   tables agrégées pour le tableau de bord (versionnées)
"""
import argparse
import itertools
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
USECOLS = ["date_start", "hour_start", "insee_com", "zone_name", "operator", "situation", "terminal", "zone",
           "protocole", "Result", "latitude_start", "longitude_start", "rsrp", "rsrq", "acess_duration",
           "bitrate_dl", "bitrate_ul", "loaded_in_less_5_secondes", "quality_perfect"]
ZONES = {"Zones denses": "Dense", "Zones intermediaires": "Intermédiaire",
         "Zones rurales": "Rurale", "Zones touristiques": "Touristique"}
ALL = "Tous"


def num(s):
    return pd.to_numeric(s.str.replace(",", ".", regex=False), errors="coerce")


def load_and_clean(path):
    df = pd.read_csv(path, sep=";", encoding="latin-1", usecols=USECOLS, dtype=str, low_memory=False)
    for c in ["latitude_start", "longitude_start", "rsrp", "rsrq", "acess_duration", "bitrate_dl", "bitrate_ul",
              "loaded_in_less_5_secondes", "quality_perfect"]:
        df[c] = num(df[c])
    df = df.rename(columns={"latitude_start": "lat", "longitude_start": "lon", "acess_duration": "access_s",
                            "loaded_in_less_5_secondes": "web_lt5s", "quality_perfect": "stream_perfect",
                            "Result": "result", "protocole": "protocol", "zone_name": "commune"})
    df["date"] = pd.to_datetime(df.date_start, format="%d/%m/%Y")
    df["hour"] = df.hour_start.str[:2].astype(int)
    df["situation"] = df.situation.str.capitalize()
    df["zone"] = df.zone.map(ZONES)
    df["insee_com"] = df.insee_com.str.zfill(5)          # codes à 4 chiffres : zéro initial perdu
    df["dep"] = df.insee_com.str[:2]
    df["success"] = (df.result == "Success").astype(int)
    # valeurs radio aberrantes -> manquantes
    df.loc[~df.rsrp.between(-140, -40), "rsrp"] = np.nan
    df.loc[~df.rsrq.between(-30, 0), "rsrq"] = np.nan
    df = df.drop(columns=["date_start", "hour_start"])
    return df.reset_index(drop=True)   # aucun doublon dans le fichier brut (vérifié sur les 103 colonnes)


def cube(df, dims, protocol_col="protocol", agg=None, extra=()):
    """Agrégats pour toutes les combinaisons de filtres, avec la valeur « Tous » pour chaque dimension de `dims`.
    Les médianes sont exactes (calculées sur les lignes concernées, pas recombinées).
    `extra` : colonnes de regroupement toujours conservées (ex. l'heure)."""
    out = []
    for r in range(len(dims) + 1):
        for fixed in itertools.combinations(dims, r):          # dimensions mises à « Tous »
            keep = [d for d in dims if d not in fixed] + [protocol_col] + list(extra)
            g = df.groupby(keep, observed=True).apply(agg, include_groups=False).reset_index()
            for d in fixed:
                g[d] = ALL
            out.append(g)
    res = pd.concat(out, ignore_index=True)
    first = dims + [protocol_col] + list(extra)
    return res[first + [c for c in res.columns if c not in first]]


def kpi(g):
    return pd.Series({"n": len(g), "success_rate": g.success.mean(), "dl_median": g.bitrate_dl.median(),
                      "ul_median": g.bitrate_ul.median(), "rsrp_median": g.rsrp.median(),
                      "rsrq_median": g.rsrq.median(), "web_lt5s": g.web_lt5s.mean(),
                      "access_median_s": g.access_s.median()})


def build_aggregates(df, out):
    out.mkdir(parents=True, exist_ok=True)
    core = cube(df, ["operator", "zone", "situation"], agg=kpi)
    core.round(4).to_csv(out / "agg_core.csv", index=False)
    hourly = cube(df, ["operator", "zone"], extra=["hour"], agg=lambda g: pd.Series(
        {"n": len(g), "success_rate": g.success.mean(), "dl_median": g.bitrate_dl.median()}))
    hourly.round(4).to_csv(out / "agg_hour.csv", index=False)
    dep_rows = []
    for op in [ALL] + sorted(df.operator.unique()):
        d = df if op == ALL else df[df.operator == op]
        g = d.groupby(["dep", "protocol"]).apply(kpi, include_groups=False).reset_index()
        g.insert(0, "operator", op)
        dep_rows.append(g)
    pd.concat(dep_rows).round(4).to_csv(out / "agg_departements.csv", index=False)


def stratified_sample(df, n=40000, seed=42):
    frac = n / len(df)
    s = df.groupby(["operator", "protocol"]).sample(frac=frac, random_state=seed)
    return s[["date", "hour", "dep", "commune", "operator", "situation", "zone", "protocol", "result", "lat", "lon",
              "rsrp", "rsrq", "bitrate_dl", "bitrate_ul", "access_s"]].dropna(subset=["lat", "lon"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(ROOT / "data/raw/2025_QoS_Metropole_data_habitations.csv"))
    a = ap.parse_args()
    df = load_and_clean(a.input)
    (ROOT / "data/processed").mkdir(parents=True, exist_ok=True)
    (ROOT / "data/sample").mkdir(parents=True, exist_ok=True)
    df.to_parquet(ROOT / "data/processed/clean.parquet", index=False)
    stratified_sample(df).to_csv(ROOT / "data/sample/points_sample.csv.gz", index=False)
    build_aggregates(df, ROOT / "data/aggregates")
    print(f"{len(df):,} mesures nettoyées | {df.commune.nunique()} communes | {df.dep.nunique()} départements")
