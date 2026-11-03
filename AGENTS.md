# AGENTS.md — omni-agents-framework

Ce dépôt **est** le cerveau du réseau. Toute IA qui travaille ici implémente ou
maintient OmniBrain, elle ne se contente pas de le documenter.

## Source de vérité

- `OMNIBRAIN.md` — spécification de l'orchestrateur (rôle, algorithme, gates, limites).
- `omni/orchestrator.py` — implémentation de référence.
- `registry/*.json` — agents, skills, routage, permissions.
- `docs/GITHUB-AUDIT.md` — audit reproductible du compte.
- `docs/INTEGRATIONS.md` — ce qui est réellement intégré, et ce qui ne l'est pas.

> La référence `blassana280-ux/optimiser-mes-agents-IA` est **inaccessible**
> (403) et n'a jamais été lue : ne la citez pas comme existante.

## Règles de travail dans ce dépôt

1. **Aucune fausse intégration.** Une capacité est soit mesurée, soit déclarée
   absente. `ManualProvider` existe précisément pour ne jamais simuler.
2. **Pas de secret dans le dépôt.** Providers et tokens passent par
   l'environnement ; les livrables sont scannés et rédigés.
3. **Jamais d'écriture sur `main`.** `omni/gitops.py` refuse ; on passe par une
   branche et une PR.
4. **Dépendances : stdlib uniquement.** Tests avec `unittest`. Toute dépendance
   ajoutée doit être justifiée et épinglée.
5. **Toute modification de registre doit laisser `python3 -m omni registry`
   vert** — une référence pendante est un bug bloquant.
6. **Tout nouveau comportement arrive avec son test.** Le verdict `READY` sans
   provider réel doit rester impossible.
7. **Réutiliser avant de créer.** Si une spécialité manque, chercher d'abord
   dans `registry/skills.json` (`python3 -m omni skills <termes>`).

## Réseau blassana280-ux

Pour les autres dépôts du compte : `AGENTS.md` du dépôt concerné prévaut. Les
overlays qui pointent vers ce dépôt doivent viser `OMNIBRAIN.md` et
`registry/`, jamais un chemin non vérifié.

## Vérification avant toute PR

```bash
python3 -m unittest discover -s tests -t .   # doit être vert
python3 -m omni registry                     # doit être cohérent
python3 -m omni providers                    # état réel des providers
```
