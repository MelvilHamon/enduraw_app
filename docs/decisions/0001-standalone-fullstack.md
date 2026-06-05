# 0001 — App full-stack standalone (pas thin-client)

## Contexte

L'app pourrait n'être qu'une fine couche de saisie devant CoachAgent, ou bien un
système autonome. Un thin-client ne démontre rien sans le moteur réel et bloque
les tests, la démo et le développement.

## Décision

L'app est **full-stack et autonome** : base propre (SQLite), modèles de domaine,
readiness calculée localement. CoachAgent est un **connecteur optionnel**, pas un
prérequis. En `ENGINE_MODE=mock`, l'app tourne de bout en bout sans réseau.

## Conséquences

- Démo et tests sans dépendance externe (cf. `MockEngine`, `scripts/seed.py`).
- L'app possède son propre modèle de données et reste la source de vérité du
  subjectif (voir [0002](0002-sync-write-only.md)).
- Coût : une couche moteur à abstraire (voir [0004](0004-engineport-two-modes.md)).
