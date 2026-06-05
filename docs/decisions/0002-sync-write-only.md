# 0002 — Sync write-only app → CoachAgent

## Contexte

Données subjectives (check-ins, RPE, affect) et niggles naissent dans l'app ;
fitness/fatigue/charge naissent dans CoachAgent. Il fallait décider du sens de
synchronisation et de la source de vérité, pour éviter les conflits bidirectionnels.

## Décision

Synchronisation **write-only** (option A) : l'app **pousse** son subjectif vers
CoachAgent (`push_wellness_daily`, `push_session_feedback`) et **ne réimporte
jamais** ces données. L'app est la source de vérité du subjectif et des niggles.
Le wellness quotidien porte un compteur `active_niggles` au lieu de pousser les
niggles individuellement. Les lignes ne sont marquées `synced` que sur un
`PushOutcome="sent"` ; le flush est idempotent (`flush_user`).

## Conséquences

- Pas de réconciliation bidirectionnelle, pas de conflit d'écriture.
- En `mock`, le push est un no-op (`"skipped"`) qui **préserve le backlog** :
  les lignes restent non synchronisées jusqu'à un vrai moteur.
- CoachAgent ne reçoit qu'un agrégat de niggles, pas le détail clinique.
- Voir `app/services/sync_service.py` et le [contrat](../api-contract.md).
