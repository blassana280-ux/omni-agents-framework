# Statuts de preuve — OMNI WARSHIPS

Échelle officielle (jamais de saut d'étape, jamais de simulation) :

prévue → en développement → implémentée (code écrit) → testée (test écrit)
→ tests réussis (exécutés en CI, run visible) → compilée (APK/AAB)
→ installée → testée sur appareil réel → validée (critères mesurés).

## État au 06/11/2026

| Fonctionnalité | Statut | Preuve |
|---|---|---|
| Architecture cœur/presentation | testée | docs + compilation CI |
| Moteur naval (inertie, virage, propulsion) | tests réussis | dotnet test en CI (warships-ci.yml) |
| Dégâts localisés + systèmes dégradés | tests réussis | idem |
| Voie d'eau / naufrage | tests réussis | idem |
| Balistique obus + guidage missile + torpilles | tests réussis | idem |
| Radar/sonar/détection/brouillage | tests réussis | idem |
| IA tactique (cibles, menaces, états) | tests réussis | idem |
| Océan Gerstner (cœur mathématique) | tests réussis | idem |
| Replay déterministe | tests réussis | idem (égalité d'états sur 200 ticks) |
| Matrice de fidélité | validée (données) | validateur python en CI |
| Scénarios Battle Sandbox | validée (données) | validateur python en CI |
| Générateurs d'assets Blender | en développement (outils écrits, non exécutés — Blender indisponible ici) | tools/omni-asset-factory |
| Couche Unity (contrôleurs, HUD, océan visuel) | implémentée (code écrit, compilation Unity requise) | unity/ |
| APK Android | prévue | nécessite Unity + SDK Android |
| 30 FPS sur Tecno KN3 | prévue | nécessite appareil réel |

## Blocages matériels honnêtes

- Compilation Unity / APK : aucun Unity ni SDK Android dans l'environnement
  d'exécution de l'assistant. Options : (a) Lassana ouvre le projet dans
  Unity sur sa machine ; (b) CI game-ci avec licence Unity (décision de
  Lassana — coût licence) ; (c) machine CI self-hosted.
- Assets 3D finaux : générateurs Blender écrits ; exécution Blender requise.
- Mesures FPS : nécessitent l'APK + appareil réel.
