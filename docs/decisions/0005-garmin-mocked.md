# 0005 — Ingestion Garmin simulée

## Contexte

Une vraie intégration Garmin (OAuth, API partenaire, quotas) est lourde et hors
sujet pour un MVP dont l'enjeu est la *fusion* des signaux, pas la plomberie
d'ingestion.

## Décision

L'ingestion Garmin est **simulée** : `POST /api/garmin/ingest` accepte un payload
de métriques quotidiennes + RPE montre (`source` par défaut `garmin_faked`), et
le générateur synthétique produit des données de **forme équivalente** à ce que
fournirait la vraie montre.

## Conséquences

- Le pipeline aval (stockage `daily_metrics`, watch-hint maladie, fusion) est
  développé et testé contre un payload réaliste.
- Brancher la vraie API Garmin plus tard = remplacer la source d'ingestion, sans
  toucher au reste.
- Le `source` distingue déjà l'origine des métriques.
