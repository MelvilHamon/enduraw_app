# 0011 — Synth : traits continus + presets

## Contexte

Pour générer des athlètes variés et réalistes, deux extrêmes : quelques personas
codés en dur (rigides, peu nombreux) ou un tirage purement aléatoire (sans
cohérence ni intention). Il fallait des profils contrôlables *et* diversifiés.

## Décision

Modèle hybride : un **vecteur de traits continus** (`TRAIT_RANGES`) gouverne tout
le comportement, et cinq **presets** servent d'ancres `(mean, sd)` par trait
(`Regular`, `OverTrainer`, `PoorSleeper`, `InjuryProne`, `Beginner`).
L'échantillonnage tire `Normal(mean, sd)` puis clampe dans la plage du trait. Le
tout est déterministe par seed.

## Conséquences

- Profils nommés et lisibles, mais chaque tirage produit un athlète distinct.
- Les presets sont **alignés sur les détecteurs** : `OverTrainer` doit déclencher
  les règles de charge, `InjuryProne` les règles de niggle, etc.
- Reproductibilité totale `(persona, seed, days, end_date)`.
- Voir `app/synth/personas.py` et [docs/synthetic-data.md](../synthetic-data.md).
