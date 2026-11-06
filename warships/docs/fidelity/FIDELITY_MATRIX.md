# Matrice de fidélité — OMNI WARSHIPS vs Modern Warships

Source de vérité : fidelity-matrix.json (validée en CI :
`python3 tools/omni-fidelity-lab/validate_matrix.py`).

## Méthode

Chaque entrée porte : référence citée, description, propriétés
observables, méthode de reproduction, **critère mesurable** (métrique +
cible + méthode de mesure), statut de développement, tests, écarts
restants. Aucun score global de fidélité : seuls des critères mesurables
comptent, et chaque statut "tested" est prouvé par un test CI nommé.

## Résumé (détail dans le JSON)

| Domaine | Entrées | Testées en CI |
|---|---|---|
| Flotte / classes | 1 | 1 |
| Physique navale | 3 | 3 |
| Environnement / océan | 2 | 1 |
| Combat / armement | 5 | 4 |
| Capteurs / contre-mesures | 2 | 2 |
| IA | 1 | 1 |
| Aviation / sous-marins | 2 | 0 (Phase 5) |
| Interface / contenu / technique | 3 | 0 (Unity/appareil requis) |

## Comparaison permanente

La matrice évolue avec le développement : chaque système livré met son
entrée à jour (statut + tests + écarts restants). Les régressions (une
entrée "tested" dont le test échoue) cassent la CI — la fidélité est
ainsi continuellement vérifiée, jamais déclarée.

## Sources consultées (06/11/2026)

- Wiki officiel Modern Warships : ship classes, game settings
- Modern Warships Wiki (Fandom) : 11 classes, tiers
- Preses/revues : Pocket Gamer, ApkFab, Softonic, Steam, guides communautaires
  (définitions VLS/CIWS/SSM/ASW, gameplay porte-avions, sous-classes de sous-marins)

Aucun asset, modèle, texture, son ou code du jeu de référence n'a été
copié — uniquement des mécaniques observables (non protégées) et des
paramètres originaux.
