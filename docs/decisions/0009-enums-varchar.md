# 0009 — Enums stockés en `VARCHAR`

## Contexte

Les types `ENUM` natifs SQL diffèrent entre SQLite (inexistant) et PostgreSQL
(type dédié, migrations rigides pour ajouter une valeur). On vise une parité de
comportement entre le dev (SQLite) et une éventuelle prod (PostgreSQL).

## Décision

Tous les enums de domaine sont persistés en **`VARCHAR`** via le helper
`str_enum()` (`sa.Enum(..., native_enum=False)`), qui génère une colonne texte +
une contrainte `CHECK` sur l'ensemble des valeurs. Les enums Python sous-classent
`(str, Enum)` pour une sérialisation JSON propre.

## Conséquences

- Comportement identique SQLite ↔ PostgreSQL.
- Ajouter une valeur = changer le `CHECK`, pas migrer un type `ENUM`.
- La validation reste garantie côté base (CHECK) **et** côté app (Pydantic).
- Voir `app/models/enums.py` et [docs/data-model.md](../data-model.md).
