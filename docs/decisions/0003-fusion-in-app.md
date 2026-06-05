# 0003 — La fusion vit dans l'app, pas dans CoachAgent

## Contexte

La readiness fusionnée (divergence subjectif↔objectif, signaux, recommandation)
pourrait être calculée côté CoachAgent et simplement affichée. Mais la valeur du
produit *est* cette fusion, et elle doit rester utile même sans moteur externe.

## Décision

La couche fusion (`app/fusion/`) vit **dans l'app**. CoachAgent ne fournit que
des entrées objectives via `EnginePort` ; l'assemblage des signaux, le score
composite et la recommandation sont calculés localement.

## Conséquences

- La readiness fonctionne en standalone (moteur simulé) comme en live.
- La logique de décision est versionnée et testée ici, sans dépendre du cycle de
  release d'un service tiers.
- L'app doit lire à la fois la base et le moteur — assumé par `fusion/service.py`
  (voir [0007](0007-fusion-rule-based.md)).
