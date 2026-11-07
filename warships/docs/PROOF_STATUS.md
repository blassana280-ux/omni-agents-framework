# Statuts de preuve — OMNI WARSHIPS

Échelle officielle (jamais de saut d'étape, jamais de simulation) :

prévue → en développement → implémentée (code écrit) → testée (test écrit)
→ tests réussis (exécutés en CI, run visible) → compilée (APK/AAB)
→ installée → testée sur appareil réel → validée (critères mesurés).

## État au 07/11/2026 (T-013 à T-013.9, branche warships/android-build, PR #16)

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
| Activation de la licence Unity sans PC (T-013.7 : méthode personal PAR IDENTIFIANTS — Unity a retiré l activation manuelle des licences Personal, le flux .alf/.ulf et l outillage npm license-tools sont SUPPRIMÉS ; le client de licence Unity demande un siège Personal avec UNITY_EMAIL/UNITY_PASSWORD DANS l unique conteneur de la commande game-ci build (GameCI CLI v0.1.72 — T-013.8 : l action de build v4 est ÉCARTÉE, ses scripts montés dans /steps ne contiennent pas le chemin personal), 2FA du compte DÉSACTIVÉE requise, siège rendu automatiquement par trap EXIT même en cas d échec ; warships-license.yml = garde de vérification sans activation) | préparée, NON exécutée (aucune activation réelle déclenchée, aucun secret utilisé ; preuve = premier run réel du build) | .github/workflows/warships-gameci.yml + .github/workflows/warships-license.yml + warships/unity/ci/BUILD-TRIGGER.md + scripts d activation game-ci (mesures publiques sur Unity 2022.3.62f3) |
| Moteur d activation du build T-013.9 (CLI GameCI CORRIGÉ v0.1.72 + heritage ENV des identifiants, un seul conteneur : siège Personal + compilation + restitution) | **VÉRIFIÉ SANS ACTIVATION** en CI : vulnérabilité d audit corrigée — le CLI officiel v0.1.72 émettait `--env UNITY_PASSWORD="valeur"` dans la chaîne passée à `sh -c` (argv des processus du runner) ; le CLI corrigé (source officielle épinglée 7da0cea2 + overlay minimal committé, dépôt officiel JAMAIS modifié, fork 403 documenté) transmet les identifiants par ENV hérité (références `--env` SANS valeur), prouvé par 5 tests bun à valeurs factices verts en CI (secrets hors chaîne Docker, transmission par environnement, conteneur servi) ; binaire publié en release IMMUABLE gameci-cli-secure-v0.1.72w1 (archive sha256 49c49df3f4af768e0cae82fc7c92b6ae6fa3769ae8703b50d8b9d35f830fc3a7 + checksums.txt + patch diff), empreinte ANCRÉE DANS GIT (artifact-checksum.txt + BUILD-INFO.txt, commit du bot) ; installation du workflow de build UNIQUEMENT par verify-gameci-cli.sh (checksum STRICT : checksums.txt inaccessible, empreinte absente, divergence, mismatch = FATAL ; binaire installé comparé bit à bit ; scripts personal + trap EXIT requis dans l artefact) — l installateur officiel est ÉCARTÉ (il poursuit après un échec de checksum) ; scripts personal intacts (dist/ bit-exact, assertion git en CI), options prouvées sur les sources du tag, résolution du projet warships/unity (ProjectVersion.txt 2022.3.62f1, buildMethod dans le .cs réel), artefact publié vérifié en ligne + garde anti-staleness — AUCUNE commande ne touche Unity : ce job ne prouve PAS une activation (siège = premier run réel du build) | job CI « GameCI CLI corrige T-013.9 (source patchee + tests + verificateur, sans activation) » + step « Artefact publie VERIFIE » dans .github/workflows/warships-ci.yml + verify-gameci-cli.sh (vérificateur strict) + test-verify-gameci-cli.sh (9 cas : 1 acceptation + 8 refus, fixtures factices) + warships-cli-release.yml + check_gameci_workflow et check_gameci_cli_secure (validate_unity_layer.py) |
| Garde-fou anti-publication du .ulf (dépôt public) | vérifiée en CI (check_ulf_publication + check_workflow_security STRUCTUREL : aucun artefact/release/commit/capture de .ulf, ACCESS_TOKEN limité à l étape de stockage) | warships/tools/omni-unity-bridge/validate_unity_layer.py |
| Garde-fous T-013.4/T-013.5 (isolation PAT, TOTP, sorties filtrées, arbre npm verrouillé) — HISTORIQUE : flux .alf/.ulf retiré en T-013.7 | remplacés en T-013.7 par check_workflow_security refondu (workflow de licence = vérification sans activation, 21 motifs interdits, TOTP et UNITY_LICENSE proscrits) + check_license_tools (license-tools absent de tous les workflows) + 8 self-tests de non-régression rejoués | warships/tools/omni-unity-bridge/validate_unity_layer.py |
| Installation npm réellement maitrisee (T-013.5) — HISTORIQUE : l outillage npm (license-tools, 67 paquets, navigateur Chromium 101 d avril 2022) est SUPPRIMÉ en T-013.7 (Unity a retiré l activation manuelle des licences Personal ; plus aucun navigateur obsolète exposé aux identifiants réels) | obsolète et retirée (dossier license-tools supprimé du dépôt ; workflows et validateur nettoyés, vérifiés en CI) | .github/workflows/warships-ci.yml (step T-013.8) + warships/tools/omni-unity-bridge/validate_unity_layer.py |
| APK Android | prévue | nécessite licence Unity : chemin A (Unity local, menu AndroidBuildConfig) ou chemin B (GameCI : secrets UNITY_EMAIL/UNITY_PASSWORD, compte 2FA désactivée, puis BUILD-TRIGGER.md) |
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


