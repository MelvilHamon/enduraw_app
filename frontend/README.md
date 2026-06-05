# Enduraw — Frontend (PWA)

Ébauche fonctionnelle (step 11) : PWA mobile-first React + Vite + TypeScript +
Tailwind, câblée au backend FastAPI. Style volontairement brut (le polish = step 12).

## Prérequis

Node.js ≥ 18 et npm. (Aucun n'est requis côté backend.)

## Développement

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 — proxy /api → http://localhost:8000
```

Lancer le backend en parallèle, **le même jour** que le seed (sinon
`/api/insights/today` n'a pas de données pour aujourd'hui) :

```bash
# depuis la racine du repo
python -m scripts.seed --personas 5 --seed 42 --days 180 --reset
uvicorn app.main:app --reload --port 8000
```

Le seed imprime les emails des athlètes ; le mot de passe est `demo1234`.

## Build de prod (servi par FastAPI)

```bash
cd frontend && npm run build      # → frontend/dist
uvicorn app.main:app --port 8000  # sert l'app + l'API sur http://localhost:8000
```

FastAPI monte `frontend/dist` s'il existe (voir `app/main.py`) : une seule URL.

## Tests

```bash
npm run test       # Vitest (client API + smoke des écrans clés)
```

## Configuration

- `VITE_API_BASE_URL` (voir `.env.example`) : laisser vide en dev (proxy) et en
  prod (même origine). À renseigner seulement pour taper une API distante.

## Écrans

`/login` · `/today` (readiness fusionnée — le payoff) · `/checkin` (3 taps) ·
`/body` (carte corps + niggles) · `/tests` (réaction + saut CMJ) · `/insights`
(courbes + prompt maladie).
