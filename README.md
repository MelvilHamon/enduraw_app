# Enduraw Form Tracker

Enduraw Form Tracker is a standalone API to monitor and analyse the **readiness
and form** of endurance athletes. Athletes log daily check-ins, niggles and
mini-tests; the service fuses these signals into actionable insights. It is built
for coaches and self-coached endurance athletes who want an honest, data-driven
read on whether to push or recover. It runs fully on its own and can optionally
plug into an external training engine (CoachAgent) over REST.

## Stack

- Python 3.12 · FastAPI · Uvicorn
- SQLAlchemy 2.0 (typed `Mapped[...]`) · SQLite · Alembic
- Pydantic v2 · pydantic-settings
- python-jose (JWT) · bcrypt
- pytest · ruff · black · mypy · pre-commit

## Quickstart

```bash
cp .env.example .env          # 1. configure environment
docker compose up --build     # 2. build + run (migrations applied on boot)
curl localhost:8000/api/health  # 3. {"status":"ok","version":"0.1.0"}
```

Interactive API docs: <http://localhost:8000/docs> (and `/redoc`).

### Local (without Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Endpoints (step 1)

| Method | Path                | Description                  |
| ------ | ------------------- | ---------------------------- |
| GET    | `/api/health`       | Liveness probe               |
| POST   | `/api/auth/register`| Create an account            |
| POST   | `/api/auth/login`   | Obtain a JWT bearer token    |
| GET    | `/api/auth/me`      | Current user (Bearer required)|

## Run tests

```bash
pytest -v
```

Lint / format / types:

```bash
ruff check .
black --check .
mypy app/
```

## Roadmap

- [x] **Step 1** — Backend skeleton: Docker, health, JWT auth, `User` model, tooling & CI
- [ ] Step 2 — Domain models (checkin, niggle, mini_test, daily_metric…)
- [ ] Step 3 — Business routes (check-ins, niggles)
- [ ] Step 4 — Personas & demo seeding
- [ ] Step 5 — Synthetic data generator
- [ ] Step 6 — EnginePort + MockEngine
- [ ] Step 7 — CoachAgentEngine (live REST integration)
- [ ] Step 8 — Signal fusion
- [ ] Step 9 — Insights
- [ ] Step 10 — Hardening & release

## License

MIT — see [LICENSE](./LICENSE).
