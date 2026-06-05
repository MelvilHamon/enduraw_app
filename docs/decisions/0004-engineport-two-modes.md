# 0004 — `EnginePort` à deux modes (Mock / CoachAgent)

## Contexte

L'app doit fonctionner sans CoachAgent (démo, tests, dev) tout en se branchant
sur le vrai moteur en production. Coder en dur l'un ou l'autre rendrait l'app
inutilisable hors de son contexte cible.

## Décision

Un seul `Protocol` `EnginePort` (`app/engines/port.py`) définit le contrat
(`get_state`, `get_timeseries`, `get_activities`, `push_*`). Deux
implémentations : `MockEngine` (snapshots JSON locaux) et `CoachAgentEngine`
(client HTTP `/api/v1`). `factory.get_engine(user, settings)` choisit selon
`ENGINE_MODE`.

## Conséquences

- Bascule mock/live par une seule variable d'environnement.
- Les tests injectent un faux moteur trivialement (le port est un Protocol).
- Tout nouveau backend moteur n'a qu'à implémenter le port.
- Le contrat de push uniformise les deux modes via `PushOutcome`
  (`"sent"`/`"skipped"`).
