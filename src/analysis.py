"""Analyse QoS mobile 5G France 2025 : comparaison opérateurs/zones, cartes, modèles, profils de communes.

Prérequis : python src/clean.py
Sorties : figures/*.png, reports/*.csv, reports/metrics.json
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
from sklearn.cluster import KMeans
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, mean_absolute_error, r2_score, roc_auc_score, roc_curve
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
FIG, REP = ROOT / "figures", ROOT / "reports"
FIG.mkdir(exist_ok=True); REP.mkdir(exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False, "font.size": 10})
OPS = ["Orange", "Bouygues", "SFR", "Free"]
COL = {"Orange": "#ff7900", "Bouygues": "#1f77b4", "SFR": "#d62728", "Free": "#555555"}
ZONES = ["Dense", "Intermédiaire", "Touristique", "Rurale"]
SPLIT = pd.Timestamp("2025-07-31")
M = {}

df = pd.read_parquet(ROOT / "data/processed/clean.parquet")
geo = json.load(open(ROOT / "data/departements.geojson", encoding="utf-8"))
DEP_NAME = {f["properties"]["code"]: f["properties"]["nom"] for f in geo["features"]}
dl = df[df.protocol == "DOWNLOAD"]
ul = df[df.protocol == "UPLOAD"]
web = df[df.protocol == "WEB"]


def boot_ci(x, n=300, seed=0):
    x = x.dropna().to_numpy(); rng = np.random.default_rng(seed)
    meds = [np.median(rng.choice(x, len(x))) for _ in range(n)]
    return np.percentile(meds, [2.5, 97.5])


def grouped_bars(ax, data, value, cats, title, ylabel, ci=True):
    w = 0.2
    for i, op in enumerate(OPS):
        meds, lo, hi = [], [], []
        for z in cats:
            x = data[(data.operator == op) & (data.zone == z)][value]
            m = x.median(); meds.append(m)
            if ci:
                a, b = boot_ci(x); lo.append(m - a); hi.append(b - m)
        ax.bar(np.arange(len(cats)) + (i - 1.5) * w, meds, w, label=op, color=COL[op],
               yerr=[lo, hi] if ci else None, capsize=2, error_kw={"lw": 0.8})
    ax.set_xticks(range(len(cats))); ax.set_xticklabels(cats); ax.set_title(title); ax.set_ylabel(ylabel)


# ---------------------------------------------------------------- 0. Vue d'ensemble
M["n_measures"] = int(len(df)); M["n_communes"] = int(df.commune.nunique()); M["n_departements"] = int(df.dep.nunique())
M["period"] = [str(df.date.min().date()), str(df.date.max().date())]
M["measures_by_protocol"] = df.protocol.value_counts().to_dict()
M["measures_by_zone"] = df.zone.value_counts().to_dict()
M["dl_threshold_note"] = "DOWNLOAD/UPLOAD : 'Success' = fichier transféré en 10 s (seuil), pas une panne"
M["dl_success_min_mbps"] = round(float(dl[dl.result == "Success"].bitrate_dl.min()), 1)

# ---------------------------------------------------------------- 1. Débits par opérateur et zone
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
grouped_bars(ax[0], dl, "bitrate_dl", ZONES, "Débit descendant médian (IC 95 %)", "Mbit/s")
grouped_bars(ax[1], ul, "bitrate_ul", ZONES, "Débit montant médian (IC 95 %)", "Mbit/s")
ax[0].legend(frameon=False, ncol=4, fontsize=8); fig.tight_layout(); fig.savefig(FIG / "01_debits_operateur_zone.png"); plt.close(fig)
rows = []
for op in OPS:
    for z in ZONES:
        for name, d, c in [("DL", dl, "bitrate_dl"), ("UL", ul, "bitrate_ul")]:
            x = d[(d.operator == op) & (d.zone == z)][c]; a, b = boot_ci(x)
            rows.append(dict(operator=op, zone=z, sens=name, n=len(x), median=round(x.median(), 1), ic95_low=round(a, 1), ic95_high=round(b, 1)))
ci = pd.DataFrame(rows); ci.to_csv(REP / "debits_ic95.csv", index=False)
M["dl_median_by_operator"] = dl.groupby("operator").bitrate_dl.median().round(1).to_dict()
M["ul_median_by_operator"] = ul.groupby("operator").bitrate_ul.median().round(1).to_dict()
M["dl_median_by_zone"] = dl.groupby("zone").bitrate_dl.median().round(1).to_dict()

# ---------------------------------------------------------------- 2. Écart rural / dense
gap = []
for op in OPS:
    r = {"operator": op}
    for name, d, c in [("dl", dl, "bitrate_dl"), ("ul", ul, "bitrate_ul")]:
        m = d[d.operator == op].groupby("zone")[c].median()
        r[f"{name}_dense"], r[f"{name}_rurale"] = m["Dense"], m["Rurale"]
        r[f"{name}_rural_pct_of_dense"] = m["Rurale"] / m["Dense"] * 100
    gap.append(r)
gap = pd.DataFrame(gap).round(1); gap.to_csv(REP / "ecart_rural_dense.csv", index=False)
fig, ax = plt.subplots(figsize=(7, 4))
x = np.arange(len(OPS)); ax.bar(x - 0.2, gap.dl_rural_pct_of_dense, 0.4, label="Descendant", color="#2a9d8f")
ax.bar(x + 0.2, gap.ul_rural_pct_of_dense, 0.4, label="Montant", color="#e9c46a")
ax.axhline(100, color="k", lw=0.8, ls="--"); ax.set_xticks(x); ax.set_xticklabels(OPS)
ax.set(ylabel="% du débit en zone dense", title="Débit en zone rurale rapporté à la zone dense"); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(FIG / "02_ecart_rural_dense.png"); plt.close(fig)
M["rural_pct_of_dense"] = gap.set_index("operator")[["dl_rural_pct_of_dense", "ul_rural_pct_of_dense"]].to_dict("index")

# ---------------------------------------------------------------- 3. Fiabilité des services
svc = ["WEB", "STREAM", "ICMP", "ULH"]
rel = df[df.protocol.isin(svc)].groupby(["operator", "protocol"]).success.mean().unstack()[svc].loc[OPS] * 100
fig, ax = plt.subplots(1, 2, figsize=(12, 4))
for i, op in enumerate(OPS):
    ax[0].bar(np.arange(len(svc)) + (i - 1.5) * 0.2, rel.loc[op], 0.2, label=op, color=COL[op])
ax[0].set_xticks(range(len(svc))); ax[0].set_xticklabels(["Web", "Streaming", "Ping", "Envoi de fichier"])
ax[0].set(ylim=(80, 100), ylabel="% de réussite", title="Taux de réussite par service"); ax[0].legend(frameon=False, ncol=4, fontsize=8)
fz = web.groupby(["operator", "zone"]).success.apply(lambda s: (1 - s.mean()) * 100).unstack()[ZONES].loc[OPS]
for i, op in enumerate(OPS):
    ax[1].bar(np.arange(4) + (i - 1.5) * 0.2, fz.loc[op], 0.2, color=COL[op])
ax[1].set_xticks(range(4)); ax[1].set_xticklabels(ZONES); ax[1].set(ylabel="% d'échecs", title="Échecs de navigation web par zone")
fig.tight_layout(); fig.savefig(FIG / "03_fiabilite_services.png"); plt.close(fig)
M["service_success_pct"] = rel.round(1).to_dict("index")
M["web_failure_pct_by_zone"] = fz.round(1).to_dict("index")
M["web_lt5s_pct_by_operator"] = (web.groupby("operator").web_lt5s.mean() * 100).round(1).to_dict()

# ---------------------------------------------------------------- 4. Signal radio et intérieur / extérieur
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
sit = ["Outdoor", "Incar", "Indoor"]
ax[0].boxplot([df[df.situation == s].rsrp.dropna() for s in sit], tick_labels=["Extérieur", "Voiture", "Intérieur"], showfliers=False)
ax[0].set(ylabel="RSRP (dBm)", title="Puissance du signal selon la situation")
ax[1].boxplot([df[df.zone == z].rsrp.dropna() for z in ZONES], tick_labels=ZONES, showfliers=False)
ax[1].set(title="Puissance du signal selon la zone")
fig.tight_layout(); fig.savefig(FIG / "04_signal_rsrp.png"); plt.close(fig)
med = df.groupby("situation").rsrp.median()
M["rsrp_median_by_situation"] = med.round(1).to_dict()
M["indoor_penalty_db"] = round(float(med["Outdoor"] - med["Indoor"]), 1)
ino = dl[dl.situation.isin(["Indoor", "Outdoor"])].groupby("situation").bitrate_dl.median()
M["dl_median_indoor_outdoor"] = ino.round(1).to_dict()
M["indoor_dl_loss_pct"] = round(float((1 - ino["Indoor"] / ino["Outdoor"]) * 100), 1)

# ---------------------------------------------------------------- 5. Effet de l'heure
h = dl.groupby(["operator", "hour"]).bitrate_dl.agg(["median", "size"]).reset_index()
hw = web.groupby(["operator", "hour"]).success.agg(lambda s: (1 - s.mean()) * 100).reset_index(name="fail")
hn = web.groupby("hour").size()
fig, ax = plt.subplots(1, 2, figsize=(12, 4))
for op in OPS:
    d = h[(h.operator == op) & (h["size"] >= 100)]; ax[0].plot(d.hour, d["median"], marker="o", ms=3, color=COL[op], label=op)
    d = hw[(hw.operator == op) & hw.hour.isin(hn[hn >= 1000].index)]; ax[1].plot(d.hour, d.fail, marker="o", ms=3, color=COL[op])
ax[0].set(title="Débit descendant médian par heure", xlabel="Heure", ylabel="Mbit/s"); ax[0].legend(frameon=False, ncol=4, fontsize=8)
ax[1].set(title="Échecs de navigation web par heure", xlabel="Heure", ylabel="% d'échecs")
fig.tight_layout(); fig.savefig(FIG / "05_heures.png"); plt.close(fig)

# ---------------------------------------------------------------- 6. Cartes par département
def draw_map(ax, values, norm_lim, cmap="viridis", outline_only=False):
    patches, vals = [], []
    for f in geo["features"]:
        g, code = f["geometry"], f["properties"]["code"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for p in polys:
            patches.append(Polygon(np.array(p[0]), closed=True)); vals.append(values.get(code, np.nan))
    pc = PatchCollection(patches, cmap=cmap, edgecolor="white", linewidths=0.2)
    if outline_only:
        pc.set_facecolor("#eeeeee")
    else:
        pc.set_array(np.array(vals)); pc.set_clim(*norm_lim)
    ax.add_collection(pc); ax.set_xlim(-5.5, 10); ax.set_ylim(41.2, 51.3)
    ax.set_aspect(1 / np.cos(np.radians(46.5))); ax.axis("off")
    return pc

dep_dl = dl.groupby(["operator", "dep"]).bitrate_dl.agg(["median", "size"]).reset_index()
dep_dl = dep_dl[dep_dl["size"] >= 15]
lim = (dep_dl["median"].quantile(0.05), dep_dl["median"].quantile(0.95))
fig, axes = plt.subplots(1, 4, figsize=(14, 4.2))
for ax, op in zip(axes, OPS):
    d = dep_dl[dep_dl.operator == op].set_index("dep")["median"].to_dict()
    pc = draw_map(ax, d, lim); ax.set_title(op)
fig.colorbar(pc, ax=axes, shrink=0.7, label="Débit descendant médian (Mbit/s)", pad=0.01)
fig.savefig(FIG / "06_carte_debit_departements.png", bbox_inches="tight"); plt.close(fig)
all_dep = dl.groupby("dep").bitrate_dl.agg(["median", "size"]); all_dep = all_dep[all_dep["size"] >= 30].sort_values("median")
all_dep["departement"] = [DEP_NAME.get(c, c) for c in all_dep.index]
all_dep.round(1).to_csv(REP / "departements_debit_dl.csv")
M["departements_les_moins_bien_servis"] = all_dep.head(8)[["departement", "median"]].round(1).to_dict("records")
M["departements_les_mieux_servis"] = all_dep.tail(8)[["departement", "median"]].round(1).to_dict("records")[::-1]

# ---------------------------------------------------------------- 7. Modèles (découpage temporel : train <= 31/07, test >= 01/08)
FEATS = ["rsrp", "rsrq", "hour", "lat", "lon", "operator", "zone", "situation", "terminal"]
CATS = ["operator", "zone", "situation", "terminal"]

def prep(d):
    X = d[FEATS].copy()
    for c in CATS:
        X[c] = X[c].astype("category")
    return X

# 7a. Qui échoue sur le web ?
w = web.copy(); w["fail"] = 1 - w.success
tr, te = w.date <= SPLIT, w.date > SPLIT
Xw = prep(w)
clf = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.06, max_depth=6, categorical_features="from_dtype", random_state=42)
clf.fit(Xw[tr], w.fail[tr]); p = clf.predict_proba(Xw[te])[:, 1]
base = w[tr].groupby(["operator", "zone", "situation"]).fail.mean().rename("b").reset_index()
pb = w[te].merge(base, how="left", on=["operator", "zone", "situation"]).b.fillna(w[tr].fail.mean()).to_numpy()
noloc = [f for f in FEATS if f not in ("lat", "lon")]
clf2 = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.06, max_depth=6, categorical_features="from_dtype", random_state=42)
clf2.fit(Xw.loc[tr, noloc], w.fail[tr]); p2 = clf2.predict_proba(Xw.loc[te, noloc])[:, 1]
M["model_web_failure"] = {"n_train": int(tr.sum()), "n_test": int(te.sum()), "failure_rate_test": round(float(w.fail[te].mean()), 4),
    "roc_auc": round(roc_auc_score(w.fail[te], p), 3), "pr_auc": round(average_precision_score(w.fail[te], p), 3),
    "roc_auc_baseline_operator_zone_situation": round(roc_auc_score(w.fail[te], pb), 3),
    "roc_auc_without_location": round(roc_auc_score(w.fail[te], p2), 3)}
sub = np.random.default_rng(42).choice(np.where(te)[0], 20000, replace=False)
pi = permutation_importance(clf, Xw.iloc[sub], w.fail.iloc[sub], scoring="roc_auc", n_repeats=5, random_state=42)
imp_a = pd.Series(pi.importances_mean, index=FEATS).sort_values()
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
for pr, lab, c in [(p, "Modèle complet", "#2a9d8f"), (pb, "Référence opérateur × zone × situation", "#999999")]:
    f_, t_, _ = roc_curve(w.fail[te], pr); ax[0].plot(f_, t_, label=lab, color=c)
ax[0].plot([0, 1], [0, 1], "k:", lw=0.8); ax[0].set(xlabel="Faux positifs", ylabel="Vrais positifs", title="Prédire un échec de navigation web (test août)")
ax[0].legend(frameon=False, fontsize=8)
ax[1].barh(imp_a.index, imp_a.values, color="#264653"); ax[1].set(title="Importance par permutation (ΔAUC)")
fig.tight_layout(); fig.savefig(FIG / "07_modele_echec_web.png"); plt.close(fig)
M["model_web_failure"]["top_drivers"] = list(imp_a.index[::-1][:4])

# 7b. Débit descendant
d2 = dl[dl.situation.isin(["Indoor", "Outdoor"])].copy()
tr2, te2 = d2.date <= SPLIT, d2.date > SPLIT
Xd = prep(d2)
reg = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_depth=6, categorical_features="from_dtype", random_state=42)
reg.fit(Xd[tr2], d2.bitrate_dl[tr2]); pr = reg.predict(Xd[te2])
b2 = d2[tr2].groupby(["operator", "zone", "situation"]).bitrate_dl.median().rename("b").reset_index()
pbd = d2[te2].merge(b2, how="left", on=["operator", "zone", "situation"]).b.fillna(d2[tr2].bitrate_dl.median()).to_numpy()
y = d2.bitrate_dl[te2].to_numpy()
M["model_dl_throughput"] = {"n_train": int(tr2.sum()), "n_test": int(te2.sum()), "r2": round(r2_score(y, pr), 3),
    "mae_mbps": round(mean_absolute_error(y, pr), 1), "r2_baseline": round(r2_score(y, pbd), 3),
    "mae_baseline_mbps": round(mean_absolute_error(y, pbd), 1)}
pi = permutation_importance(reg, Xd[te2], d2.bitrate_dl[te2], scoring="r2", n_repeats=5, random_state=42)
imp_b = pd.Series(pi.importances_mean, index=FEATS).sort_values()
M["model_dl_throughput"]["top_drivers"] = list(imp_b.index[::-1][:4])
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
hb = ax[0].hexbin(y, pr, gridsize=40, bins="log", cmap="viridis", extent=(0, 700, 0, 700)); ax[0].plot([0, 700], [0, 700], "w--", lw=0.8)
ax[0].set(xlabel="Débit mesuré (Mbit/s)", ylabel="Débit prédit (Mbit/s)", title="Débit descendant : prédit vs mesuré (test août)")
ax[1].barh(imp_b.index, imp_b.values, color="#264653"); ax[1].set(title="Importance par permutation (ΔR²)")
fig.tight_layout(); fig.savefig(FIG / "08_modele_debit.png"); plt.close(fig)

# ---------------------------------------------------------------- 8. Profils de communes
c = df.groupby("commune").agg(dep=("dep", "first"), lat=("lat", "median"), lon=("lon", "median"),
                              zone=("zone", lambda s: s.mode().iat[0]), n=("success", "size"))
c["n_dl"] = dl.groupby("commune").size(); c["dl_med"] = dl.groupby("commune").bitrate_dl.median()
c["n_web"] = web.groupby("commune").size(); c["web_fail"] = web.groupby("commune").success.apply(lambda s: (1 - s.mean()) * 100)
c["rsrp_med"] = df.groupby("commune").rsrp.median(); c["web_access_s"] = web.groupby("commune").access_s.median()
ce = c[(c.n_dl >= 8) & (c.n_web >= 50)].dropna(subset=["dl_med", "web_fail", "rsrp_med", "web_access_s"]).copy()
Z = StandardScaler().fit_transform(ce[["dl_med", "web_fail", "rsrp_med", "web_access_s"]])
ce["cluster"] = KMeans(n_clusters=4, n_init=20, random_state=42).fit_predict(Z)
order = ce.groupby("cluster").dl_med.median().sort_values().index
names = dict(zip(order, ["Mal servies", "Débit limité", "Bien servies", "Très bien servies"]))
ce["profil"] = ce.cluster.map(names)
prof = ce.groupby("profil").agg(communes=("n", "size"), dl_med=("dl_med", "median"), web_fail=("web_fail", "mean"),
                                rsrp=("rsrp_med", "median"), access_s=("web_access_s", "median"),
                                part_rurale=("zone", lambda s: (s == "Rurale").mean() * 100)).round(1)
prof = prof.loc[["Mal servies", "Débit limité", "Bien servies", "Très bien servies"]]; prof.to_csv(REP / "profils_communes.csv")
ce.reset_index().round(2).to_csv(REP / "communes_profils_detail.csv", index=False)
M["communes_eligibles"] = int(len(ce)); M["profils_communes"] = prof.reset_index().to_dict("records")
fig, ax = plt.subplots(1, 2, figsize=(13, 5.2), gridspec_kw={"width_ratios": [1, 1.1]})
cols = {"Mal servies": "#d62728", "Débit limité": "#ff7f0e", "Bien servies": "#2ca02c", "Très bien servies": "#1f77b4"}
for n_, d in ce.groupby("profil"):
    ax[0].scatter(d.rsrp_med, d.dl_med, s=14, alpha=0.7, color=cols[n_], label=f"{n_} ({len(d)})")
ax[0].set(xlabel="Signal médian RSRP (dBm)", ylabel="Débit descendant médian (Mbit/s)", title="Profils de communes")
ax[0].legend(frameon=False, fontsize=8)
draw_map(ax[1], {}, (0, 1), outline_only=True)
for n_, d in ce.groupby("profil"):
    ax[1].scatter(d.lon, d.lat, s=9, color=cols[n_], alpha=0.85)
ax[1].set_title("Localisation des communes")
fig.tight_layout(); fig.savefig(FIG / "09_profils_communes.png"); plt.close(fig)

# ---------------------------------------------------------------- Classement synthétique
tab = pd.DataFrame({"dl_median_mbps": dl.groupby("operator").bitrate_dl.median(), "ul_median_mbps": ul.groupby("operator").bitrate_ul.median(),
                    "web_success_pct": web.groupby("operator").success.mean() * 100, "web_lt5s_pct": web.groupby("operator").web_lt5s.mean() * 100,
                    "stream_success_pct": df[df.protocol == "STREAM"].groupby("operator").success.mean() * 100,
                    "rsrp_median_dbm": df.groupby("operator").rsrp.median()}).loc[OPS].round(1)
tab.to_csv(REP / "classement_operateurs.csv")
json.dump(M, open(REP / "metrics.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2,
          default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
print(json.dumps(M, ensure_ascii=False, indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o)))
