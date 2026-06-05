# 0006 — Les signaux subjectifs restent subjectifs

## Contexte

Tentation classique : « corriger » le ressenti de l'athlète avec les données
objectives, ou les moyenner en un score unique. Cela détruit précisément
l'information qui nous intéresse.

## Décision

Les signaux subjectifs ne sont **ni corrigés ni fusionnés** dans une moyenne avec
l'objectif. Leur valeur est l'**écart** : la règle phare
`divergence_subj_obj` compare le z-score de la forme ressentie au z-score de la
forme moteur et signale la divergence (et son sens : athlète optimiste vs
pessimiste).

## Conséquences

- L'app montre *où* le ressenti et le mesuré désaccordent — l'angle mort — plutôt
  qu'un nombre lissé sans information.
- Implémente la devise « ne demander à l'humain que ce que seul l'humain peut
  savoir » : le subjectif est traité comme une mesure de plein droit.
- Voir `app/fusion/rules.py` (`divergence_subj_obj`).
