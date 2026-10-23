# 5G-QoS France 2025 — Rapport d'analyse

*Données : 354 282 mesures de qualité de service mobile, 26 mai - 2 septembre 2025, 4 opérateurs, 1 682 communes, 96 départements de métropole. Toutes les mesures démarrent en 5G.*

## 1. Les données en bref
- Services testés : navigation web (253 260 mesures), téléchargement (33 384), ping (17 328), streaming vidéo (16 933), envoi de fichier (16 695 + 16 682 en débit montant).
- Zones : rurales (116 589), denses (113 902), intermédiaires (103 573), touristiques (20 218). Chaque opérateur compte environ 88 500 mesures : la comparaison est équilibrée.
- **Point d'attention** : pour le téléchargement, « Success » signifie que le fichier de 250 Mo a été transféré en 10 secondes (seuil ≈ 209,5 Mbit/s) ; ce n'est pas une panne. Pour cette raison, j'analyse les **débits** plutôt que ce taux de « réussite ».

## 2. Opérateurs : débits (figure 01)
| Opérateur | Débit descendant médian | Débit montant médian | Navigation web réussie | Pages en moins de 5 s |
|---|---|---|---|---|
| Orange | 232,2 Mbit/s | 14,2 | 93,6 % | 89,3 % |
| Bouygues | 154,7 | 9,2 | 91,0 % | 85,2 % |
| SFR | 131,0 | 9,2 | 90,9 % | 85,1 % |
| Free | 100,8 | 5,0 | 88,7 % | 82,3 % |

En **zone dense**, l'ordre est net, avec des intervalles de confiance à 95 % qui ne se chevauchent pas : Orange 325 Mbit/s, Bouygues 267, SFR 234, Free 151. En **zone rurale**, Orange reste en tête (58 Mbit/s, IC 51-64), de peu devant Free (45, IC 39-50) ; Bouygues (33, IC 29-35) et SFR (38, IC 35-41) sont quasiment indiscernables, et Free dépasse Bouygues. Sur les services applicatifs (web, streaming, envoi de fichier), Orange est devant et Free derrière ; sur le ping, Orange et SFR sont à égalité (93,3 %).

## 3. La fracture rurale (figures 02 et 03)
Le débit descendant médian est de **244 Mbit/s en zone dense contre 41 Mbit/s en zone rurale**. Rapporté à la zone dense, le débit rural représente 17,8 % (Orange), 12,2 % (Bouygues), 16,0 % (SFR) et 29,8 % (Free) : Free perd le moins en rural parce qu'il part de moins haut.
Les échecs de navigation web suivent la même logique : en zone rurale, 12,8 % (Orange), 18,9 % (Bouygues), 15,9 % (SFR) et 18,7 % (Free), contre 2 à 7 % en zone dense. La zone touristique est intermédiaire (168 Mbit/s).

## 4. Intérieur contre extérieur (figure 04)
Le signal médian est de −102,7 dBm en extérieur, −103,5 en voiture et −105,8 en intérieur, soit une perte de **3,2 dB** à l'intérieur. Pour le téléchargement, cela se traduit par **−28,5 % de débit** (119 Mbit/s en intérieur contre 167 en extérieur).

## 5. Cartographie (figure 06)
Les écarts entre départements sont considérables. Débit descendant médian (départements avec au moins 30 tests de téléchargement) :
- **Les moins bien servis** : Lot 3,9 Mbit/s, Aisne 4,7, Corrèze 8,6, Creuse 11,4, Lot-et-Garonne 18,8, Lozère 20,0, Territoire de Belfort 20,2, Jura 26,9.
- **Les mieux servis** : Hauts-de-Seine 301, Loire 285, Haute-Garonne 269, Gironde 268, Paris 266, Seine-Saint-Denis 252, Val-de-Marne 249, Alpes-Maritimes 219.

Ces médianes reposent sur quelques dizaines de tests par opérateur et département : elles sont à lire comme des tendances. Le détail par opérateur varie : dans le Lot, les quatre opérateurs sont sous 10 Mbit/s (Orange 8,1 ; Bouygues 3,6 ; SFR 3,9 ; Free 1,7) ; dans l'Aisne seul Orange s'en sort (38 Mbit/s contre 1 à 4 pour les autres) ; en Corrèze seul Free dépasse 10 (33 contre 2 à 9). Avec 27 à 46 tests par opérateur et par département, ces chiffres sont indicatifs.

## 6. Effet de l'heure (figure 05)
Les mesures s'étalent de 7 h à 21 h, avec l'essentiel entre 8 h et 18 h ; au-delà, trop peu de tests pour conclure. Le débit descendant médian baisse en fin de journée (≈ 166 Mbit/s à 11 h contre ≈ 97 à 17 h) et les échecs web montent (7 % à 13 h, 13 % à 18 h). **Une grande partie de cet effet est un effet de composition** : la part de mesures en zone rurale passe de 28 % à midi à 46 % à 17 h. À zone constante (zone dense), une baisse subsiste mais elle est plus modeste : ≈ 280 Mbit/s à 11 h contre ≈ 225 entre 14 h et 17 h (environ −20 %). En zone rurale, les valeurs sont trop dispersées pour dégager une tendance.

## 7. Modèles prédictifs
Découpage temporel : entraînement sur les mesures jusqu'au 31 juillet, test sur août et début septembre, pour éviter de « voir le futur ».

**Prédire un échec de navigation web** (65 973 mesures de test, 6,7 % d'échecs) : ROC-AUC **0,93** et précision moyenne 0,65 (hasard : 0,07), contre un ROC-AUC de 0,70 pour une simple référence « opérateur × zone × situation ». Les facteurs dominants sont la puissance (RSRP) et la qualité (RSRQ) du signal. Retirer la localisation GPS ne change pas le résultat (0,93) : la position n'apporte rien au-delà du signal. Ce score est élevé en partie parce qu'un signal très faible implique mécaniquement un échec ; le modèle confirme que **l'échec dépend avant tout de la qualité du signal reçu, et peu de l'opérateur seul**. (figure 07)

**Prédire le débit descendant** (8 742 mesures de test, intérieur et extérieur) : R² = **0,55** et erreur absolue moyenne de 91 Mbit/s, contre R² = 0,20 et 124 Mbit/s pour la référence. Facteurs dominants : RSRP, zone, opérateur, RSRQ. Le modèle capte la tendance mais pas la variabilité d'un test à l'autre, qui est grande. (figure 08)

## 8. Profils de communes (figure 09)
Les 1 682 communes sont regroupées en 4 profils (KMeans sur débit, échecs web, signal et temps d'accès) :

| Profil | Communes | Débit médian | Échecs web | RSRP médian | Part de communes rurales |
|---|---|---|---|---|---|
| Mal servies | 84 | 0,1 Mbit/s | 63,9 % | −116,2 dBm | 82 % |
| Débit limité | 301 | 19,1 | 25,9 % | −111,8 | 70 % |
| Bien servies | 753 | 107,6 | 4,1 % | −106,8 | 46 % |
| Très bien servies | 544 | 299,6 | 2,0 % | −97,8 | 13 % |

Environ **23 % des communes** (385 sur 1 682) sont mal ou peu servies, et elles sont majoritairement rurales. Dans les 84 communes « mal servies », le débit médian est quasi nul pour Bouygues, Free et SFR et de 1,2 Mbit/s pour Orange : tous les opérateurs sont touchés. Sur l'ensemble des 385 communes mal ou peu servies, Orange se démarque (16,5 Mbit/s contre 5 environ pour les trois autres).

## 9. Limites
- Les mesures démarrent toutes en 5G : aucune comparaison avec la 4G. Un débit proche de 0 reflète un échec de transfert ou une coupure, pas nécessairement l'absence totale de réseau.
- Mesures de jour uniquement, sur une campagne de quelques mois ; peu de tests par département et par opérateur pour les cartes.
- Le zonage (dense, intermédiaire, rural, touristique) est celui du fichier source.
- Le modèle de débit est descriptif : le RSRP est mesuré au moment du test et n'est pas connu à l'avance.

## 10. Pistes
Ajouter la 4G si disponible, croiser avec des données de population ou de relief (INSEE, IGN), comparer plusieurs campagnes dans le temps, déployer le tableau de bord sur Streamlit Community Cloud.
