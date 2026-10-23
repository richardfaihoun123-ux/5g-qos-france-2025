"""Tableau de bord QoS mobile 5G France 2025.

Lancer :  streamlit run app/streamlit_app.py
Utilise uniquement les tables agrégées et l'échantillon versionnés dans data/ (pas le fichier brut).
"""
import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
OPS = ["Orange", "Bouygues", "SFR", "Free"]
COL = {"Orange": "#ff7900", "Bouygues": "#1f77b4", "SFR": "#d62728", "Free": "#555555"}
ALL = "Tous"

st.set_page_config(page_title="QoS mobile 5G France 2025", page_icon="📶", layout="wide")


@st.cache_data
def load():
    agg = pd.read_csv(ROOT / "data/aggregates/agg_core.csv")
    hour = pd.read_csv(ROOT / "data/aggregates/agg_hour.csv")
    dep = pd.read_csv(ROOT / "data/aggregates/agg_departements.csv", dtype={"dep": str})
    pts = pd.read_csv(ROOT / "data/sample/points_sample.csv.gz", dtype={"dep": str})
    geo = json.load(open(ROOT / "data/departements.geojson", encoding="utf-8"))
    names = {f["properties"]["code"]: f["properties"]["nom"] for f in geo["features"]}
    return agg, hour, dep, pts, geo, names


agg, hour, dep, pts, geo, names = load()

st.title("📶 Qualité de service mobile 5G en France — 2025")
st.caption("Mesures de qualité de service mobile (≈ 354 000 tests, mai-septembre 2025, 4 opérateurs, 1 682 communes). "
           "Les médianes affichées sont calculées sur les mesures correspondant exactement aux filtres choisis.")

with st.sidebar:
    st.header("Filtres")
    op = st.selectbox("Opérateur", [ALL] + OPS)
    zone = st.selectbox("Zone", [ALL, "Dense", "Intermédiaire", "Touristique", "Rurale"])
    sit = st.selectbox("Situation", [ALL, "Outdoor", "Indoor", "Incar"], help="« Incar » (en voiture) n'existe que pour la navigation web.")
    st.markdown("---")
    st.markdown("**À savoir** : pour le téléchargement et l'envoi, « réussite » signifie que le fichier a été transféré "
                "dans le temps imparti (seuil ≈ 209 Mbit/s en descendant). Ce n'est pas une panne.")


def pick(operator=None, zone_=None, sit_=None, protocol=None):
    d = agg
    for col, val in [("operator", operator or op), ("zone", zone_ or zone), ("situation", sit_ or sit), ("protocol", protocol)]:
        if val is not None:
            d = d[d[col] == val]
    return d


def val(df, col):
    return df[col].iloc[0] if len(df) and pd.notna(df[col].iloc[0]) else None


def fmt(x, unit="", nd=0):
    return "—" if x is None else f"{x:,.{nd}f} {unit}".strip().replace(",", " ")


dlr, ulr, webr = pick(protocol="DOWNLOAD"), pick(protocol="UPLOAD"), pick(protocol="WEB")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Débit descendant médian", fmt(val(dlr, "dl_median"), "Mbit/s"), help=f"{fmt(val(dlr, 'n'))} mesures")
c2.metric("Débit montant médian", fmt(val(ulr, "ul_median"), "Mbit/s", 1), help=f"{fmt(val(ulr, 'n'))} mesures")
fail = None if val(webr, "success_rate") is None else (1 - val(webr, "success_rate")) * 100
c3.metric("Échecs de navigation web", fmt(fail, "%", 1), help=f"{fmt(val(webr, 'n'))} mesures")
c4.metric("Pages chargées en moins de 5 s", fmt(None if val(webr, "web_lt5s") is None else val(webr, "web_lt5s") * 100, "%", 1))

t1, t2, t3, t4, t5 = st.tabs(["Comparaison", "Carte", "Heures", "Mesures", "À propos"])

with t1:
    a, b = st.columns(2)
    d = agg[(agg.operator != ALL) & (agg.zone == zone) & (agg.situation == sit) & (agg.protocol == "DOWNLOAD")]
    fig = px.bar(d, x="operator", y="dl_median", color="operator", color_discrete_map=COL, category_orders={"operator": OPS},
                 labels={"dl_median": "Mbit/s", "operator": ""}, title="Débit descendant médian par opérateur")
    fig.update_layout(showlegend=False); a.plotly_chart(fig, width="stretch")
    d = agg[(agg.operator == op) & (agg.zone != ALL) & (agg.situation == sit) & (agg.protocol == "DOWNLOAD")]
    fig = px.bar(d, x="zone", y="dl_median", color="zone", category_orders={"zone": ["Dense", "Intermédiaire", "Touristique", "Rurale"]},
                 labels={"dl_median": "Mbit/s", "zone": ""}, title=f"Débit descendant médian par zone ({op})")
    fig.update_layout(showlegend=False); b.plotly_chart(fig, width="stretch")
    a, b = st.columns(2)
    d = agg[(agg.operator != ALL) & (agg.zone == zone) & (agg.situation == sit) & agg.protocol.isin(["WEB", "STREAM", "ICMP", "ULH"])].copy()
    d["reussite"] = d.success_rate * 100
    fig = px.bar(d, x="protocol", y="reussite", color="operator", barmode="group", color_discrete_map=COL,
                 category_orders={"operator": OPS, "protocol": ["WEB", "STREAM", "ICMP", "ULH"]},
                 labels={"reussite": "% de réussite", "protocol": "Service"}, title="Taux de réussite par service")
    fig.update_yaxes(range=[60, 100]); a.plotly_chart(fig, width="stretch")
    d = agg[(agg.operator != ALL) & (agg.zone == zone) & (agg.situation == sit) & (agg.protocol == "UPLOAD")]
    fig = px.bar(d, x="operator", y="ul_median", color="operator", color_discrete_map=COL, category_orders={"operator": OPS},
                 labels={"ul_median": "Mbit/s", "operator": ""}, title="Débit montant médian par opérateur")
    fig.update_layout(showlegend=False); b.plotly_chart(fig, width="stretch")

with t2:
    metric = st.radio("Indicateur", ["Débit descendant (Mbit/s)", "Échecs de navigation web (%)", "Signal RSRP (dBm)"], horizontal=True)
    nmin = st.slider("Nombre minimal de mesures par département", 5, 100, 15)
    proto = {"Débit descendant (Mbit/s)": "DOWNLOAD", "Échecs de navigation web (%)": "WEB", "Signal RSRP (dBm)": "WEB"}[metric]
    d = dep[(dep.operator == op) & (dep.protocol == proto) & (dep.n >= nmin)].copy()
    if metric.startswith("Débit"):
        d["valeur"] = d.dl_median
    elif metric.startswith("Échecs"):
        d["valeur"] = (1 - d.success_rate) * 100
    else:
        d["valeur"] = d.rsrp_median
    d["Département"] = d.dep.map(names)
    fig = px.choropleth(d, geojson=geo, locations="dep", featureidkey="properties.code", color="valeur", hover_name="Département",
                        hover_data={"dep": False, "n": True, "valeur": ":.1f"}, color_continuous_scale="Viridis_r" if "Échecs" in metric else "Viridis",
                        labels={"valeur": metric, "n": "mesures"})
    fig.update_geos(fitbounds="locations", visible=False); fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=560)
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Opérateur : {op}. Les filtres « zone » et « situation » ne s'appliquent pas à la carte (tous types de zones).")
    with st.expander("Départements les moins bien / mieux servis"):
        s = d.sort_values("valeur")[["Département", "valeur", "n"]].rename(columns={"valeur": metric, "n": "mesures"})
        x, y = st.columns(2); x.write("Valeurs les plus basses"); x.dataframe(s.head(10), hide_index=True)
        y.write("Valeurs les plus hautes"); y.dataframe(s.tail(10).iloc[::-1], hide_index=True)

with t3:
    d = hour[(hour.operator != ALL) & (hour.zone == zone) & (hour.protocol == "DOWNLOAD") & (hour.n >= 30)]
    fig = px.line(d, x="hour", y="dl_median", color="operator", markers=True, color_discrete_map=COL,
                  labels={"hour": "Heure", "dl_median": "Mbit/s"}, title=f"Débit descendant médian par heure (zone : {zone})")
    st.plotly_chart(fig, width="stretch")
    d = hour[(hour.operator != ALL) & (hour.zone == zone) & (hour.protocol == "WEB") & (hour.n >= 300)].copy()
    d["echecs"] = (1 - d.success_rate) * 100
    fig = px.line(d, x="hour", y="echecs", color="operator", markers=True, color_discrete_map=COL,
                  labels={"hour": "Heure", "echecs": "% d'échecs"}, title=f"Échecs de navigation web par heure (zone : {zone})")
    st.plotly_chart(fig, width="stretch")
    st.caption("Les heures avec trop peu de mesures sont masquées. Les mesures ont été réalisées en journée (7 h - 20 h).")

with t4:
    d = pts if op == ALL else pts[pts.operator == op]
    if zone != ALL:
        d = d[d.zone == zone]
    if sit != ALL:
        d = d[d.situation == sit]
    st.write(f"Échantillon de {len(d):,} mesures (sur 40 000 versionnées)".replace(",", " "))
    st.map(d, latitude="lat", longitude="lon", size=300)
    st.dataframe(d.head(500), hide_index=True)
    st.download_button("Télécharger l'échantillon filtré (CSV)", d.to_csv(index=False).encode("utf-8"), "echantillon_qos.csv", "text/csv")

with t5:
    st.markdown("""
**Source** : fichier de mesures de qualité de service mobile 2025 en France métropolitaine (campagne « habitations »), à citer avec sa source officielle.

**Ce que mesure chaque test** : navigation web (WEB), téléchargement (DOWNLOAD, 250 Mo en 10 s maximum), envoi de fichier (UPLOAD, ULH), streaming vidéo (STREAM) et ping (ICMP).

**Limites** : toutes les mesures démarrent en 5G ; les mesures sont faites en journée ; les médianes par département reposent parfois sur peu de tests ; les écarts entre opérateurs ne sont pas tous statistiquement significatifs (voir le rapport).
""")
