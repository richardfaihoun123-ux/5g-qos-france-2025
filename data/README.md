# Données

| Fichier / dossier | Contenu | Versionné |
|---|---|---|
| `raw/2025_QoS_Metropole_data_habitations.csv` | fichier brut de mesures de qualité de service mobile 2025 (354 282 lignes, 103 colonnes, ≈ 93 Mo) | ❌ à placer manuellement |
| `processed/clean.parquet` | données nettoyées (généré par `src/clean.py`) | ❌ |
| `sample/points_sample.csv.gz` | échantillon stratifié de 40 000 mesures (opérateur × service) | ✅ |
| `aggregates/*.csv` | tables agrégées utilisées par le tableau de bord | ✅ |
| `departements.geojson` | contours simplifiés des départements français (projet open source france-geojson) | ✅ |

## Reproduire
1. Placer le fichier brut dans `data/raw/` (séparateur `;`, encodage latin-1).
2. `python src/clean.py` puis `python src/analysis.py`.

## Source
Mesures de qualité de service mobile 2025 en France métropolitaine, publiées en open data par l'Arcep :
- Communiqué : https://www.arcep.fr/actualites/actualites-et-communiques/detail/n/qualite-des-services-mobiles-en-metropole-201125.html
- Données ouvertes : https://data.arcep.fr/mobile/
Licence de réutilisation : à vérifier sur la page du jeu de données.

## Nettoyage appliqué
- Décimales à virgule converties, valeurs radio aberrantes mises à vide (RSRP hors −140 / −40 dBm, RSRQ hors −30 / 0 dB).
- `situation` harmonisée (majuscules/minuscules), zones renommées (Dense, Intermédiaire, Rurale, Touristique).
- Codes commune à 4 chiffres complétés par un zéro initial (23 940 lignes) ; département = deux premiers caractères.
- Aucune ligne supprimée (aucun doublon dans le fichier brut). Seules 29 colonnes sur 103 contiennent des données ; les autres sont ignorées.
