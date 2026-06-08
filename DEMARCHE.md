# Démarche, choix & axes d'amélioration

> Document de synthèse du test Enduraw — *application de collecte quotidienne de
> l'état de forme d'un athlète d'endurance*. Il explique **pourquoi** l'app est
> faite ainsi, **quelles métriques** elle présente et **où elle peut aller**.
> Pour le « comment » technique : voir [`README.md`](./README.md) et
> [`docs/`](./docs/) (architecture, modèle de données, contrat d'API, ADRs).

---

## 1. Contexte & problème

Un athlète ne vit jamais deux journées identiques. Un matin les sensations sont
bonnes ; le lendemain, sans raison évidente, tout est plus lourd. Fatigue
latente, accumulation invisible, impact des dernières séances, mauvais sommeil…
Ces signaux existent mais sont **diffus, difficiles à capter et à structurer**.

Le pari du projet tient en une phrase :

> **Ne demander à l'humain que ce que seul l'humain peut savoir.**

La montre mesure déjà très bien le *mesurable* (HRV, sommeil, charge). Ce qu'elle
ne sait pas, c'est ce que l'athlète **ressent** et **où ça tire**. Le produit ne
cherche donc pas à empiler une métrique de plus : il capte le **subjectif et le
localisé**, puis les confronte au moteur objectif. Le signal phare n'est pas une
valeur isolée mais la **divergence subjectif ↔ objectif** — l'écart entre le
ressenti et le mesuré, là où se cachent la fatigue masquée et le sur-risque.

Garde-fou assumé : toute sortie liée à une blessure est **une incitation à
consulter un physio, jamais un diagnostic**.

---

## 2. Démarche

### 2.1 La friction d'abord
Une donnée quotidienne n'a de valeur que si elle est saisie **tous les jours**.
La contrainte de conception n°1 est donc le temps de saisie : viser **~30 s,
gestuel, sans clavier**.

La routine de check-in repose sur des **swipe-cards** (une question, un geste) :

| Geste | Sens |
| --- | --- |
| ↑ vers le haut | bien plus que d'habitude (+2) |
| → vers la droite | un peu plus (+1) |
| double-tap | comme d'habitude (0) |
| ← vers la gauche | un peu moins (−1) |
| ↓ vers le bas | bien moins (−2) |

Le geste vaut mieux qu'un curseur numérique : il est rapide, kinesthésique, et il
encode naturellement *un ressenti relatif* plutôt qu'une note absolue (voir §3).

### 2.2 Trois sources, une lecture fusionnée
Les données sont volontairement séparées en trois familles :

- **Subjectif** *(seul l'humain le sait)* — check-in du jour, gênes/blessures
  localisées, mini-tests neuromusculaires.
- **Objectif montre** *(capté passivement)* — HRV (RMSSD), sommeil, FC de repos,
  stress, body battery, VO2max.
- **Moteur** *(calculé)* — modèle de Banister (fitness / fatigue / forme), ACWR,
  charge aiguë & chronique.

Une **couche de fusion** confronte ces sources et produit une *readiness* du jour
**expliquée** (un score + les signaux qui l'ont déclenché), plutôt qu'un nombre
opaque.

### 2.3 Architecture en couches
```
routes → services → fusion → EnginePort → Mock | CoachAgent
```
Le moteur est abstrait derrière un `EnginePort` à deux implémentations : un
**mode standalone** (snapshots JSON locaux, aucune dépendance externe) et un
**mode live** (REST vers CoachAgent). L'app reste démontrable seule tout en étant
prête à se brancher sur l'écosystème Enduraw.

### 2.4 Le mode *live* : l'intégration CoachAgent

> **À propos — projet personnel.** **CoachAgent est mon projet personnel** : un
> moteur qui **analyse les signaux de course à pied** (charge d'entraînement,
> fitness/fatigue façon Banister, ACWR, activités). Cette app Enduraw en est le
> **complément naturel** : elle capte ce que le moteur ne voit pas — le
> *subjectif et le localisé* (ressenti, gênes, mini-tests) — et le lui renvoie.
> Ensemble, ils ferment la boucle : **donnée objective + ressenti humain = une
> lecture de readiness plus juste**.

Concrètement, l'app dialogue avec CoachAgent via un client HTTP asynchrone
(`httpx`) **caché derrière l'`EnginePort`** (`app/engines/coach_agent.py`) — le
reste du code ignore quel moteur répond. Trois endpoints en lecture, deux en
écriture (write-only) :

| Sens | Endpoint | Donnée |
| --- | --- | --- |
| Lecture | `GET /api/v1/engine/state` | forme / fitness / fatigue / ACWR du jour |
| Lecture | `GET /api/v1/engine/timeseries` | séries temporelles des métriques moteur |
| Lecture | `GET /api/v1/activities` | séances d'entraînement |
| Écriture | `POST /api/v1/wellness/daily` | check-in subjectif (+ compteur de gênes) |
| Écriture | `POST /api/v1/feedback/session` | RPE + affect post-séance |

**Robustesse.** Authentification par *bearer token* ; timeout configurable
(10 s par défaut) ; les erreurs transitoires (5xx, timeouts, erreurs de
transport) sont **réessayées avec backoff exponentiel**, les 4xx échouent vite,
et tout est mappé en **exceptions typées** (auth / introuvable / requête
invalide / upstream) pour que l'app reste agnostique du backend. Les POST sont
idempotents (*upsert*), donc sûrs à rejouer. En **mode standalone**, exactement
la même interface est servie par un `MockEngine` (snapshots JSON) : l'app se
démontre seule, sans CoachAgent.

### 2.5 Données synthétiques déterministes
Pour démontrer le produit sans dépendre d'un vrai athlète, un générateur
(`app/synth/`) produit des **cohortes déterministes par seed** : des personas
(régulier, sur-entraîné, mauvais dormeur, sujet aux blessures, débutant) avec des
historiques cohérents — la charge nourrit le Banister, la fatigue dégrade HRV et
sommeil, les blessures s'allument après les pics d'ACWR. Cela rend les démos
reproductibles et les règles de fusion testables.

---

## 3. Choix (et pourquoi)

| Choix | Pourquoi | Référence |
| --- | --- | --- |
| **Échelles signées −2..+2** pour forme, motivation, stress | Mesurer un *écart à son propre normal* ancre la réponse sur l'athlète et réduit le biais d'échelle (chacun n'a pas la même « note de 7/10 »). | `app/schemas/checkin.py` |
| **Fatigue en 1..5** (absolu) | La fatigue se vit comme un niveau, pas comme un écart ; une échelle ordinale courte suffit. | `app/schemas/checkin.py` |
| **Stress optionnel** | Ne pas forcer une réponse de plus chaque jour : la friction prime. | `stress: int \| None` |
| **Fusion à base de règles, pas de ML** (MVP) | Explicabilité : on peut toujours dire *pourquoi* (les 2 signaux dominants) ; pas de boîte noire, pas besoin d'un gros historique pour démarrer. | [`docs/decisions/`](./docs/decisions/) (ADR 0007), `app/fusion/` |
| **Divergence = signal le plus pondéré (0.30)** | C'est l'ancre produit : l'écart ressenti/mesuré est plus informatif que chaque métrique prise seule. | `app/fusion/thresholds.py` |
| **Sync write-only (app → moteur)** | L'app est la **source de vérité du subjectif** ; elle pousse vers le moteur mais ne se laisse pas réécrire. | `app/services/sync_service.py` (ADR 0002) |
| **`EnginePort` à deux modes** | Démo standalone *et* intégration live, même schéma de données. | `app/engines/` (ADR 0004) |
| **Readiness recalculée (stateless)** | Pas de cache à invalider : la lecture du jour reflète toujours les dernières données. | ADR 0008 |
| **Mini-tests neuromusculaires dans l'app** (saut CMJ, temps de réaction) | Des proxys *objectifs* captés directement par le téléphone, qui complètent la montre et révèlent une dégradation avant le ressenti. | `app/models/mini_test.py` |
| **Design system warm-black + accent flamme** | Priorité lisibilité / contraste / mobile ; états de chargement et états vides explicites. | `frontend/src/lib/palette.ts`, `Skeleton.tsx` |

### Les signaux de fusion
Six règles pures, chacune produit un signal `(déclenché ?, sévérité 0..1,
évidence lisible)`. Le score composite est leur moyenne pondérée ; la
recommandation suit une cascade de priorité **`consulter physio` → `repos` →
`alléger` → `comme prévu`**.

| Signal | Poids | Ce qu'il détecte |
| --- | --- | --- |
| `divergence_subj_obj` | 0.30 | ressenti vs forme moteur (≥ 1,5 σ d'écart) |
| `illness_hint` | 0.25 | motif maladie (HRV↓ + FC repos↑ + respiration↑) |
| `niggle_escalation` | 0.20 | intensité d'une gêne en hausse (pente des reports) |
| `niggle_load_correlation` | 0.15 | gêne ouverte après un pic d'ACWR (> 1,3) |
| `wellness_divergence` | 0.15 | HRV / sommeil / FC repos hors bande personnelle |
| `mini_test_trend` | 0.10 | saut ou réaction qui se dégrade vs baseline |

*(poids et seuils : `app/fusion/thresholds.py`)*

---

## 4. Métriques présentées — et pourquoi celles-ci

L'app est un **shell produit à 5 onglets** (`frontend/src/components/BottomNav.tsx`).
Chaque écran répond à **une** question de l'athlète.

### Accueil — « Est-ce que je dévie de mon normal ? »
Snapshot du check-in du jour + comparaison **aujourd'hui · hier · moyenne 7 j**
pour forme, fatigue, motivation, stress, plus temps de réaction et saut **exprimés
en écart à la baseline**.
- *Pourquoi l'écart plutôt que la valeur brute ?* Un « temps de réaction de
  290 ms » ne dit rien ; « +18 ms vs ta moyenne » dit immédiatement *tu es plus
  lent que d'habitude*. La dérive personnelle est le vrai signal.

| Métrique | Échelle | Lecture |
| --- | --- | --- |
| Forme ressentie | −2..+2 | vs un jour normal |
| Fatigue | 1..5 | 1 = frais · 5 = épuisé |
| Motivation | −2..+2 | vs un jour normal |
| Stress | −2..+2 | vs un jour normal |
| Temps de réaction | ms (écart) | plus bas = mieux |
| Saut (CMJ) | cm (écart) | plus haut = mieux |

### Charge — « Suis-je en train de surcharger ? »
- **VO2max** sur l'échelle Garmin 5 bandes (faible → supérieur) : le repère de
  capacité aérobie que l'athlète connaît déjà.
- **ACWR** (ratio charge aiguë 7 j / chronique 28 j) avec **zone sûre 0,8–1,3** :
  l'indicateur de référence du risque de blessure par surcharge.
- **Forme (Banister)** : positif = frais, négatif = chargé.

### Routine — « Mon check-in du jour »
Le cœur de la collecte : 4 swipe-cards (forme, fatigue, motivation, stress) puis
2 mini-jeux (réaction, saut). C'est ici que se joue la friction minimale.

### Santé — « Comment je récupère ? »
Signaux objectifs de récupération issus de la montre :

| Métrique | Échelle | Lecture |
| --- | --- | --- |
| HRV (RMSSD) | ms, moyenne 7 j | plus haut = mieux récupéré |
| Sommeil | /100 | score de la dernière nuit |
| Body battery | /100 | réserve d'énergie estimée |
| Stress (montre) | /100 | plus bas = mieux |

### Profil — « Globalement, où j'en suis aujourd'hui ? »
L'écran de **synthèse en langage clair** (« Ton état de santé, en clair ») —
volontairement **sans** recommandation entraîne/repos :
- **Indice du jour** : le score composite (0–100) traduit en mots
  (*Tout est au vert* < 34 · *Quelques signaux* < 67 · *Plusieurs signaux* ≥ 67).
  À 0, tout est dans la norme ; plus il monte, plus il y a de signaux à surveiller.
- **Tes ressentis vs tes données** : la divergence subjectif↔objectif expliquée
  (« tu te sens mieux que tes données — attention à ne pas surcharger », ou
  « moins bien — sois patient, ça remonte »).
- **Signaux hors normes** : les signaux déclenchés du jour, avec leur évidence.

Les réglages et le compte vivent derrière l'icône engrenage (écran `/settings`
dédié), pour garder le Profil centré sur l'**état de l'athlète**, pas sur l'admin.

> **Le fil rouge de toutes ces métriques :** elles ne servent pas à juger une
> performance, mais à **détecter une dérive** par rapport au normal de l'athlète,
> et à rendre lisible la divergence ressenti ↔ mesuré.

---

## 5. État actuel (transparence)

Pour que ce document soit *conforme* au dépôt, voici l'état réel — sans survente :

- ✅ **5 onglets** en place : Accueil, Charge, Routine, Santé, Profil.
- ✅ **Collecte subjective complète** : check-in signé, mini-tests, et tout le
  back-office **gênes/blessures** — modèle `Niggle` / `NiggleReport`, enum
  **`BodyRegion` (23 zones)** + `Side`, `PainType`, `MechanicalPattern`, `Timing`,
  et l'API `/api/niggles*` (`app/models/enums.py`, `app/models/niggle.py`).
- ✅ **Fusion + sync** opérationnelles (`/api/insights/*`, `/api/sync/coachagent`).
- 🚧 **Saisie d'une gêne dans l'app** : un écran `BodyMapPage` existe mais reste,
  pour l'instant, **accessible par URL (`/body`) et non encore branché dans la
  navigation** — écran *hérité en cours de portage* dans le shell à 5 onglets
  (cf. commentaire dans `frontend/src/App.tsx`). Idem pour `TodayPage` (`/today`)
  et `InsightsPage` (`/insights`), dont la logique est en cours d'intégration aux
  onglets. C'est précisément ce point que l'axe d'amélioration ci-dessous vient
  renforcer.

---

## 6. Axes d'amélioration

### ★ Maquette 3D du corps humain pour signaler une gêne *(prioritaire)*

**Le besoin.** Le cœur de la thèse est « subjectif **et localisé** » : *où ça
tire*. Aujourd'hui, la région se choisit dans une liste de 23 zones — fonctionnel,
mais lent et abstrait. Une **maquette 3D d'un corps humain** rendrait la saisie
immédiate et sans ambiguïté : l'athlète **tape directement la zone** qui le gêne.

**Ce que ça apporte.**
- Saisie plus rapide et plus précise de la localisation (moins de friction, plus
  de justesse).
- **Visualisation** : afficher l'historique d'intensité par zone en *heatmap* sur
  le corps (zones qui « chauffent » = gênes récurrentes ou en escalade).
- Une lecture instantanée pour l'athlète *et* pour le moteur de readiness.

**Approche technique pressentie.**
- `react-three-fiber` + `@react-three/drei` ; un mesh de corps **segmenté par
  zones** mappées **1-pour-1 sur l'enum `BodyRegion`** existante ; latéralité via
  l'enum `Side`.
- **Aucun changement de modèle de données** : on réutilise tel quel l'API
  `/api/niggles` + `NiggleReport` (intensité 0–10, `PainType`,
  `MechanicalPattern`, `Timing`). La 3D n'est qu'une **nouvelle vue de saisie et
  de visualisation** par-dessus le back-end déjà en place.

**Chemin réaliste (incrémental).**
1. Rendre la BodyMap 2D pleinement interactive (zones cliquables → report de
   gêne) et la **remettre dans la navigation**.
2. Prototype 3D en lecture seule (rotation + zones colorées par intensité).
3. *Tap-to-report* sur le mesh 3D + heatmap historique.

### Autres axes
- **ML sur la divergence** une fois assez d'historique accumulé (la fusion à base
  de règles reste le socle explicable, l'apprentissage l'affine).
- **Notifications de check-in** pour soutenir l'usage quotidien.
- **Intégration Garmin réelle** en remplacement de l'ingestion simulée.
- **Baselines personnalisées** (fenêtres adaptées au profil de l'athlète).
- **Mode hors-ligne PWA complet** (saisie sans réseau, sync différée).

---

*Ce document décrit l'intention produit et l'état réel du dépôt à la date de
rédaction. Les détails d'implémentation et de calcul vivent dans
[`docs/`](./docs/).*
