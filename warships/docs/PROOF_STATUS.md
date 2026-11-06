# Statuts de preuve — OMNI WARSHIPS

Échelle officielle (jamais de saut d'étape, jamais de simulation) :

prévue → en développement → implémentée (code écrit) → testée (test écrit)
→ tests réussis (exécutés en CI, run visible) → compilée (APK/AAB)
→ installée → testée sur appareil réel → validée (critères mesurés).

## État au 06/11/2026 (T-012 en cours, branche warships/unity-3d)

| Fonctionnalité | Statut | Preuve |
|---|---|---|
| Architecture cœur/présentation | testée | docs + compilation CI |
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
| Générateurs 3D Blender (7 scripts : destroyer, frégate, porte-avions, sous-marin, aéronefs, équipements + module commun) | implémentée (scripts écrits + syntaxe validée en CI ; NON exécutés — Blender absent de l'environnement, aucun FBX produit) | tools/omni-asset-factory/ + job CI « Couche Unity » (py_compile) |
| Couche Unity (contrôleurs, HUD, océan visuel, noyau copié) | implémentée (code écrit + structure et copies octet par octet validées en CI ; compilation Unity requise) | warships/unity + job CI « Couche Unity » (validate_unity_layer.py) |
| Environnement naval 3D (jour/nuit, météo pluie/tempête, ciel procédural étoilé, écume de sillage) | implémentée (code écrit, structure validée en CI ; compilation Unity requise) | Scripts/WeatherDirector.cs, WakeFoamController.cs + Shaders/OmniSky, OmniFoam |
| Combat visuel (traînées missiles, bulles torpilles, tracers AA, dégâts progressifs, écume voie d'eau) | implémentée (code écrit, relié aux événements réels du noyau ; compilation Unity requise) | Scripts/CombatEffects.cs, ShipDamageVisuals.cs |
| Chargement modèles FBX + LOD 0/1/2 + tourelles/radars animés | implémentée (code écrit ; les modèles apparaîtront quand les FBX seront générés — fallback coque procédurale) | Scripts/ShipModelLibrary.cs |
| Pause + 5 profils graphiques (Ultra/Élevé/Moyen/Faible/Adaptatif) | implémentée (code écrit ; compilation Unity requise) | Scripts/PauseMenu.cs, QualityProfiles.cs |
| Pipeline GameCI Android (compilation APK) | préparée (exemple inactif hors .github/workflows — activation = décision licence de Lassana) | unity/ci/README-GAMECI.md + gameci-example.yml |
| APK Android | prévue | nécessite Unity + SDK Android (ou GameCI activé) |
| 30 FPS sur Tecno KN3 | prévue | nécessite APK + appareil réel (aucune mesure inventée) |

## Blocages matériels honnêtes

- Compilation Unity / APK : aucun Unity ni SDK Android dans l'environnement
  d'exécution de l'assistant. Options : (a) Lassana ouvre le projet dans
  Unity sur sa machine ; (b) CI game-ci avec licence Unity (décision de
  Lassana — coût licence) ; (c) machine CI self-hosted.
- Modèles 3D finaux : 7 générateurs Blender écrits et syntaxiquement
  validés en CI ; exécution Blender requise pour produire les FBX
  (destroyer, frégate, porte-avions, sous-marin, aéronefs, équipements).
- Mesures FPS : nécessitent l'APK + appareil réel (Tecno KN3).
