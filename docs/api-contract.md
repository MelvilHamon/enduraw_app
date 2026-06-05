# Contrat d'API

Deux contrats coexistent : **(1)** le contrat que l'app *expose* à ses clients,
et **(2)** le contrat que l'app *consomme* côté CoachAgent en mode `live`. Le
schéma machine de l'app est versionné dans [openapi.json](openapi.json)
(régénérable via `python -m scripts.export_openapi`).

## CoachAgent (consommé en mode `live`)

Implémenté par `CoachAgentEngine` (`app/engines/coach_agent.py`). Verrouillé.

- **Base URL** : `COACHAGENT_BASE_URL`, préfixe **`/api/v1`**.
- **Auth** : `Authorization: Bearer <COACHAGENT_API_KEY>` sur chaque requête.
- **Timeout / retries** : `COACHAGENT_TIMEOUT_S=10.0`, `COACHAGENT_MAX_RETRIES=3`
  (backoff exponentiel sur erreurs transitoires).

### Lectures (objectif → app)

| Méthode | Chemin | Paramètres | Retour |
| ------- | ------ | ---------- | ------ |
| GET | `/api/v1/engine/state` | `date` (ISO) | `EngineState` (fitness, fatigue, form, acwr, load_7d, load_28d, trend_form_7d, readiness_hint) |
| GET | `/api/v1/engine/timeseries` | `from`, `to`, `metrics` (CSV) | `EngineTimeseries` (séries par métrique) |
| GET | `/api/v1/activities` | `from`, `to`, `limit` | `list[EngineActivity]` (du plus récent) |

Métriques timeseries autorisées : `fitness`, `fatigue`, `form`, `load`, `acwr`
(`TIMESERIES_METRICS`).

### Écritures (app → objectif, write-only)

| Méthode | Chemin | Corps |
| ------- | ------ | ----- |
| POST | `/api/v1/wellness/daily` | `WellnessDailyPayload` (date, form_vs_normal, motivation, fatigue, active_niggles) |
| POST | `/api/v1/feedback/session` | `SessionFeedbackPayload` (activity_id, rpe, affect, reported_at) |

L'app ne pousse jamais les niggles individuellement : le wellness quotidien
porte un compteur `active_niggles` (voir
[ADR sync write-only](decisions/0002-sync-write-only.md)).

### Erreurs

Les réponses HTTP sont mappées vers des exceptions typées
(`app/engines/errors.py`) :

| HTTP | Exception | Sémantique |
| ---- | --------- | ---------- |
| 401 | `EngineAuthError` | Clé d'API invalide. |
| 404 | `EngineNotFound` | Ressource / jour absent. |
| 4xx | `EngineBadRequest` | Requête invalide (échec rapide, pas de retry). |
| 5xx / timeout | `EngineUpstreamError` | Après épuisement des retries. |

Le résultat d'un push est un `PushOutcome` : `"sent"` (mode live, accepté) ou
`"skipped"` (mode mock, no-op). La sync ne marque une ligne `synced` que sur
`"sent"`.

## Routes exposées par l'app

Toutes les routes métier requièrent `Authorization: Bearer <token>` (JWT émis par
`/api/auth/login` ou `/api/auth/register`) et sont cantonnées à l'utilisateur
courant : une ressource d'un autre utilisateur renvoie `404`. La pagination des
listes utilise `limit` (1–200, défaut 50) et `offset` (défaut 0) ; les fenêtres
de dates utilisent les alias `from` / `to`.

| Méthode | Chemin | Auth | Description |
| ------- | ------ | ---- | ----------- |
| GET | `/api/health` | — | Liveness (`{"status":"ok","version":…}`) |
| POST | `/api/auth/register` | — | Créer un compte, renvoie un token (`201`, `409` si email pris) |
| POST | `/api/auth/login` | — | Token JWT (`200`, `401`) |
| GET | `/api/auth/me` | ✓ | Utilisateur courant |
| POST | `/api/checkin` | ✓ | Upsert checkin du jour (`201`/`200`) |
| GET | `/api/checkin/today` | ✓ | Checkin du jour (`404` si absent) |
| GET | `/api/checkin` | ✓ | Liste des checkins |
| POST | `/api/niggles` | ✓ | Ouvrir un niggle (+ report initial optionnel) |
| GET | `/api/niggles` | ✓ | Liste (`active` optionnel) |
| GET | `/api/niggles/{niggle_id}` | ✓ | Détail + reports |
| PATCH | `/api/niggles/{niggle_id}` | ✓ | MAJ `closed_at`/`structure`/`notes` |
| POST | `/api/niggles/{niggle_id}/reports` | ✓ | Ajouter un report (`409` si fermé) |
| POST | `/api/mini-tests` | ✓ | Enregistrer un test (`jump`/`reaction`) |
| GET | `/api/mini-tests` | ✓ | Liste des mini-tests |
| GET | `/api/mini-tests/baseline` | ✓ | Baseline glissante par `type` |
| POST | `/api/feedback/session` | ✓ | Upsert feedback par `activity_id` |
| GET | `/api/feedback/session` | ✓ | Liste des feedbacks |
| POST | `/api/illness` | ✓ | Upsert flag maladie du jour |
| GET | `/api/illness` | ✓ | Liste des flags |
| GET | `/api/illness/hint` | ✓ | Watch-hint maladie pour un jour |
| POST | `/api/garmin/ingest` | ✓ | Ingestion batch (daily + RPE montre) |
| GET | `/api/garmin/daily` | ✓ | Liste des métriques quotidiennes |
| GET | `/api/insights/today` | ✓ | Readiness du jour (signaux + reco) |
| GET | `/api/insights/timeseries` | ✓ | Moteur + subjectif + divergence |
| GET | `/api/insights/correlations` | ✓ | Synthèse niggle×charge |
| POST | `/api/sync/coachagent` | ✓ | Flush write-only vers CoachAgent |

Les corps de requête/réponse (schémas Pydantic) sont décrits exhaustivement dans
[openapi.json](openapi.json) et explorables sur `/docs`.
