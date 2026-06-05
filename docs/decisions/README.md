# Décisions d'architecture (ADR)

Un ADR par décision **verrouillée et adossée au code**. Format court :
*Contexte / Décision / Conséquences*. Les ADR documentent le *pourquoi* ; le
*comment* vit dans le code et les autres docs.

| # | Décision |
| - | -------- |
| [0001](0001-standalone-fullstack.md) | App full-stack standalone (pas thin-client) |
| [0002](0002-sync-write-only.md) | Sync write-only app → CoachAgent |
| [0003](0003-fusion-in-app.md) | La fusion vit dans l'app, pas dans CoachAgent |
| [0004](0004-engineport-two-modes.md) | `EnginePort` à deux modes (Mock / CoachAgent) |
| [0005](0005-garmin-mocked.md) | Ingestion Garmin simulée |
| [0006](0006-subjective-signals-stay-subjective.md) | Les signaux subjectifs restent subjectifs |
| [0007](0007-fusion-rule-based.md) | Fusion rule-based, sans ML en MVP |
| [0008](0008-dailyread-stateless.md) | `DailyRead` stateless (recalculé, non persisté) |
| [0009](0009-enums-varchar.md) | Enums stockés en `VARCHAR` |
| [0010](0010-bcrypt-direct.md) | bcrypt utilisé en direct (pas passlib) |
| [0011](0011-synth-traits-presets.md) | Synth : traits continus + presets |

> La décision **frontend / PWA** n'a pas encore d'ADR : aucun code client dans ce
> dépôt. Voir la section « Frontend (à venir) » de
> [docs/architecture.md](../architecture.md).
