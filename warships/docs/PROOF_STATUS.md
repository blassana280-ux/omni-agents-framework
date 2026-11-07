# Statuts de preuve — OMNI WARSHIPS

Échelle officielle (jamais de saut d'étape, jamais de simulation) :

prévue → en développement → implémentée (code écrit) → testée (test écrit)
→ tests réussis (exécutés en CI, run visible) → compilée (APK/AAB)
→ installée → testée sur appareil réel → validée (critères mesurés).

## État au 06/11/2026 (T-013 + T-013.1 + T-013.2, branche warships/android-build, PR #16)

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
| Générateurs 3D Blender (7 scripts : destroyer, frégate, porte-avions, sous-marin, aéronefs, équipements + module commun) | **EXÉCUTÉS EN CI** (Blender 4.2.3 LTS portable, run vert 42282487303, job 38 s) — les 6 FBX sont produits avec tailles réelles vérifiées | tools/omni-asset-factory/ + .github/workflows/warships-blender-fbx.yml + commit 9c1db33a (FBX dans Resources/Models) + artefact omni-warships-fbx |
| Modèles 3D FBX (LOD 0/1/2, pivots tourelles/radars/rotors) | **produits** : destroyer 2 404 572 o, frégate 2 278 988 o, porte-avions 2 255 020 o, sous-marin 343 676 o, aéronefs 502 428 o, équipements 354 524 o (total ≈ 8,1 Mo) | warships/unity/Assets/OmniWarships/Resources/Models/ (commit du bot CI 9c1db33a) |
| Couche Unity (contrôleurs, HUD, océan visuel, noyau copié) | implémentée (code écrit + structure et copies octet par octet validées en CI ; compilation Unity requise) | warships/unity + job CI « Couche Unity » (validate_unity_layer.py) |
| Environnement naval 3D (jour/nuit, météo pluie/tempête, ciel procédural étoilé, écume de sillage) | implémentée (code écrit, structure validée en CI ; compilation Unity requise) | Scripts/WeatherDirector.cs, WakeFoamController.cs + Shaders/OmniSky, OmniFoam |
| Combat visuel (traînées missiles, bulles torpilles, tracers AA, dégâts progressifs, écume voie d'eau) | implémentée (code écrit, relié aux événements réels du noyau ; compilation Unity requise) | Scripts/CombatEffects.cs, ShipDamageVisuals.cs |
| Chargement modèles FBX + LOD 0/1/2 + tourelles/radars animés | implémentée (code écrit ; FBX désormais présents dans Resources/Models, chargés par ShipModelLibrary) | Scripts/ShipModelLibrary.cs |
| Pause + 5 profils graphiques (Ultra/Élevé/Moyen/Faible/Adaptatif) | implémentée (code écrit ; compilation Unity requise) | Scripts/PauseMenu.cs, QualityProfiles.cs |
| Garde-fou scène de bataille (chemin unique Assets/OmniWarships/Battle.unity, création auto, inclusion EXPLICITE dans BuildPlayerOptions.scenes, échec clair sinon) | implémentée (code écrit + vérifiée en CI par validate_unity_layer.py/check_scene_build) | Editor/BattleSceneGuard.cs + Editor/WarshipsBuildScript.cs |
| Préparation build Android (ARM64, IL2CPP, paysage, minSdk 24, identifiant, APK pas AAB) | implémentée (script éditeur écrit ; exécution dans Unity requise) | Editor/AndroidBuildConfig.cs (menu OMNI WARSHIPS, scene garantie par BattleSceneGuard) |
| Pipeline GameCI Android (compilation APK cloud) | préparée et VÉRIFIÉE (T-013.1 + T-013.2 : inputs v4 réelles, expressions propres, permissions contents: write, secrets vérifiés sans affichage, APK vérifiée taille+sha256, job actionlint en CI ; déclenchement par push limité à warships/android-build + BUILD-TRIGGER.md — utilisable SANS fusion et SANS main) — aucune exécution tant que Lassana ne fournit pas les secrets de licence et ne déclenche pas | .github/workflows/warships-gameci.yml + warships/unity/ci/BUILD-TRIGGER.md + job CI « Workflows (actionlint) » + unity/ci/README-GAMECI.md |
| Namespaces des API Build (BuildReport/BuildResult dans UnityEditor.Build.Reporting) | corrigée (T-013.2 : using ajouté aux deux scripts éditeur de compilation) + garde-fou CI check_build_reporting (l erreur CS0246 ne peut plus revenir) | Editor/WarshipsBuildScript.cs, Editor/AndroidBuildConfig.cs + validate_unity_layer.py |
| Acquisition de la licence Unity sans PC (workflow dédié, TOTP obligatoire, parcours email neutralisé) | préparée, NON exécutée (T-013.4 : outils reproductibles — npm ci depuis license-tools/package-lock.json, 67 paquets, intégrité sha512, unity-license-activate 0.3.9 épinglé ; PAT injecté uniquement au stockage puis effacé ; aucun identifiant dans les logs : add-mask + sortie filtrée ; sera prouvée à sa première exécution réelle) | .github/workflows/warships-license.yml + warships/unity/ci/LICENSE-TRIGGER.md + warships/unity/ci/license-tools/ |
| Garde-fou anti-publication du .ulf (dépôt public) | vérifiée en CI (check_ulf_publication + check_workflow_security STRUCTUREL : aucun artefact/release/commit/capture de .ulf, ACCESS_TOKEN limité à l étape de stockage) | warships/tools/omni-unity-bridge/validate_unity_layer.py |
| Garde-fous T-013.4 (isolation PAT, TOTP obligatoire, parcours email neutralisé, sorties filtrées, arbre verrouillé) | vérifiée en CI (check_workflow_security structurel sur les steps + SELF-TESTS de non-régression sur 8 snippets ; check_license_lock : 67 paquets, intégrité sha512 ; job CI npm ci --ignore-scripts installe exactement l arbre verrouillé) | warships/tools/omni-unity-bridge/validate_unity_layer.py + warships/unity/ci/license-tools/package-lock.json |
| Installation npm réellement maitrisee (T-013.5 : --ignore-scripts dans les DEUX workflows, audit 67/67 = exactement 3 scripts d installation tous bloques, Chromium curl URL epinglee 982053 sha256 consigne, version 101.0.4951 verifiee, resolution Puppeteer verifiee, nettoyage runner always(), validateur : lock reellement verifie + 13 self-tests + domaines en liste blanche) | verifiee en CI (npm ci reproductibilite + tests reels domaines/scripts/cross-fichiers dans warships-ci.yml) | .github/workflows/warships-license.yml + .github/workflows/warships-ci.yml + warships/tools/omni-unity-bridge/validate_unity_layer.py + warships/unity/ci/license-tools/ |
| APK Android | prévue | nécessite licence Unity : chemin A (Unity local, menu AndroidBuildConfig) ou chemin B (GameCI, secrets licence puis BUILD-TRIGGER.md) |
| 30 FPS sur Tecno KN3 | prévue | nécessite APK + appareil réel (aucune mesure inventée) |

## Blocages matériels honnêtes

- Compilation Unity / APK : aucun Unity ni SDK Android dans l'environnement
  d'exécution de l'assistant. Chemins prêts : (a) Lassana ouvre le projet
  dans Unity 2022.3 (licence personnelle gratuite) et utilise le menu
  « OMNI WARSHIPS / Android » (AndroidBuildConfig.cs) ; (b) CI GameCI :
  secrets de licence puis édition de warships/unity/ci/BUILD-TRIGGER.md
  (push limité à la branche, sans fusion, sans main) — décision de Lassana.
- Modèles 3D : PLUS UN BLOCAGE — les 6 FBX sont générés réellement en CI
  (Blender 4.2.3 LTS, run 42282487303, commit 9c1db33a) et intégrés dans
  le projet Unity (Resources/Models) ; artefact téléchargeable
  omni-warships-fbx (FBX + logs Blender).
- Mesures FPS : nécessitent l'APK + appareil réel (Tecno KN3).

