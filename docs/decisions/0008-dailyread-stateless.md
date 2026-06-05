# 0008 — `DailyRead` stateless (recalculé, non persisté)

## Contexte

La readiness du jour pourrait être matérialisée dans une table. Mais elle dépend
de seuils, de baselines et d'un état moteur susceptibles d'évoluer ; une valeur
persistée se périme silencieusement.

## Décision

`DailyRead` (et `compute_daily_read`) est **stateless** : recalculé à chaque
requête `GET /api/insights/today` à partir des données brutes (base + moteur).
Aucune table de readiness, aucun cache persistant.

## Conséquences

- La readiness reflète toujours les données et les seuils actuels.
- Pas de logique d'invalidation de cache ni de migration de schéma pour les
  insights.
- Coût : recalcul à chaque lecture — acceptable vu le volume (fenêtres de
  quelques dizaines de jours par utilisateur).
