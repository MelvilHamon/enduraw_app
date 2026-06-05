# 0010 — bcrypt utilisé en direct (pas passlib)

## Contexte

`passlib` est l'habitude pour le hash de mots de passe, mais ajoute une couche
d'indirection et a connu des frictions de compatibilité avec les versions
récentes de `bcrypt`.

## Décision

Le hash/verify utilise la bibliothèque **`bcrypt` directement**
(`app/security.py`), sans `passlib`. Le JWT est géré par `python-jose`.

## Conséquences

- Une dépendance de moins, surface plus simple, pas de couche d'adaptation.
- Code de sécurité explicite et facile à auditer.
- Si une stratégie de hash multiple devenait nécessaire, réintroduire un
  abstracteur resterait possible.
