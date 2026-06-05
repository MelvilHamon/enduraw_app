# Données synthétiques

`app/synth/` génère des historiques d'athlètes **complets et déterministes** : à
`(persona, seed, days, end_date)` fixés, le dataset est identique. C'est ce qui
permet de tester la fusion contre une vérité terrain connue et de seeder des
démos reproductibles.

Le principe directeur (voir [docs/architecture.md](architecture.md)) : simuler un
**état latent** physiologique, puis **émettre des observations bruitées** par
dessus. Les divergences subjectif↔objectif émergent du bruit et des biais de
traits, pas d'un truquage.

## Modèle de Banister (état latent)

Pour chaque jour, à partir de la charge d'entraînement quotidienne :

```
fitness[t] = fitness[t-1] · exp(-1/42) + load[t]      (FITNESS_TAU = 42 j)
fatigue[t] = fatigue[t-1] · exp(-1/7)  + load[t]      (FATIGUE_TAU = 7 j)
form[t]    = fitness[t] − 5.5 · fatigue[t]
```

- **ACWR** (acute:chronic workload ratio) = `mean(load[t-6 … t]) / mean(load[t-27 … t])`,
  indéfini (`None`) tant qu'il n'y a pas assez d'historique.
- **Burn-in de 120 jours** simulés avant la fenêtre émise : l'impulsion lente de
  fitness (τ = 42) et les baselines glissantes 28 j sont déjà chaudes au premier
  jour visible.

Les mêmes formules de z-scores glissants et d'ACWR vivent dans
`app/fusion/baselines.py` — fusion et synth partagent la définition, pas une
copie qui dérive.

## Traits & presets

Chaque athlète est un **vecteur de traits continus** (`TRAIT_RANGES`,
`app/synth/personas.py`) : cible de TRIMP hebdo, volatilité de charge, poids et
biais subjectifs, bruit de check-in, bases physiologiques (HRV, RHR, sommeil),
sensibilité à la fatigue, hazard de blessure, fitness initiale, bases de
saut/temps de réaction, taux de maladie annuel.

Cinq **presets** servent d'ancres — chacun est `(mean, sd)` par trait + des poids
catégoriels de zone corporelle ; l'échantillonnage tire `Normal(mean, sd)` puis
clampe dans la plage du trait :

| Preset | Profil |
| ------ | ------ |
| `Regular` | Équilibré, charge modérée, faible hazard. |
| `OverTrainer` | Charge élevée + volatilité, hazard et maladies en hausse. |
| `PoorSleeper` | Poids sommeil élevé, HRV de base plus basse. |
| `InjuryProne` | Hazard élevé, biais de zone large. |
| `Beginner` | Faible charge, fitness initiale basse, volatilité notable. |

## Émissions

À partir du latent (et de `fat_z`, le z-score glissant de fatigue) :

- **Métriques Garmin** : HRV, RHR, sommeil, respiration, body battery, stress,
  readiness, VO2max — chacune fonction de la base du trait ± un terme en `fat_z`
  et un bruit gaussien.
- **Check-ins subjectifs** : `form_vs_normal`, `fatigue`, `motivation`
  combinent les z-scores latents pondérés par les poids subjectifs du trait,
  plus un biais et un bruit propres à l'athlète (≈ 12 % de jours sautés). C'est
  ici que naît la divergence : un trait `subj_bias` positif émet un ressenti
  systématiquement au-dessus de la forme réelle.
- **Mini-tests** : saut (temps de vol → hauteur par la physique) et temps de
  réaction, dégradés par `fat_z`.
- **Feedback de séance** : RPE et affect dérivés de la charge et des z-scores,
  remplis ~65 % du temps, moitié sur la montre / moitié en saisie manuelle.

## Niggles

Onset modélisé par un **processus de Poisson** dont le hazard monte avec la
charge :

```
λ = hazard_base + α · max(0, acwr − 1.3) + β · max(0, load_ratio − 1)
```

Chaque niggle tire une région (selon les poids de zone du preset) et un
archétype cohérent (type de douleur, pattern mécanique, timing). Sa **trajectoire
multi-reports** escalade sous charge et se résorbe sinon (un report tous les 2–4
jours). Au plus 2 niggles actifs simultanément. Cette structure alimente
directement les règles d'escalade et de corrélation niggle×charge de la fusion.

## Épisodes de maladie

Nombre d'épisodes tiré d'un Poisson calé sur `illness_rate` (par an), chacun de
3–7 jours avec 2–4 symptômes. Pendant un épisode, les métriques se dégradent de
façon réaliste (HRV ↓, RHR ↑, respiration ↑, score de sommeil ↓), ce qui fait
ressortir le watch-hint maladie de la fusion (HRV↓ + RHR↑ + resp↑ simultanés).

## Déterminisme

`generate(persona, seed, days=180, end_date=None)` est une fonction pure de ses
arguments : même seed ⇒ même dataset. `generate_cohort([(preset, seed), …])`
produit une cohorte. Le seeder (`app/synth/seeder.py`) persiste un dataset en
base et, optionnellement, écrit le snapshot moteur correspondant dans
`MOCK_ENGINE_DIR`. CLI : `python -m scripts.seed --personas N --seed S --days D
[--reset]`.
