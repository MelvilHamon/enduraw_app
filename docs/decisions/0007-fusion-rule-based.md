# 0007 — Fusion rule-based, sans ML en MVP

## Contexte

La readiness pourrait être un modèle appris. Mais en MVP, sans dataset réel
étiqueté, un modèle serait opaque, non auditable et difficile à justifier auprès
d'un athlète ou d'un coach.

## Décision

La fusion est **rule-based** : 6 règles en fonctions pures (`app/fusion/rules.py`)
avec des seuils explicites et nommés (`app/fusion/thresholds.py`), un score
composite par moyenne pondérée des sévérités, et une recommandation par priorités.
Chaque `Signal` porte sa valeur, sa référence et une explication lisible.

## Conséquences

- Chaque recommandation est **explicable** et traçable jusqu'à un seuil.
- Les règles sont testables sans base ni réseau (pures).
- Les seuils sont calés sur les mêmes définitions que le générateur synth
  (`baselines.py`), ce qui aligne génération et détection.
- Migration vers du ML possible plus tard sans changer le contrat (les règles
  restent une baseline interprétable).
