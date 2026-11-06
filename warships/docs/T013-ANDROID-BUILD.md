# T-013 — Première APK Android réellement jouable : audit, production d'assets, chemins de compilation

Date : 06/11/2026. Branche : warships/android-build (empilée sur warships/unity-3d), PR #16.

## 1. Audit des PR #13 / #14 / #15 (réel, lecture croisée du code)

Méthode : chaque référence croisée des scripts T-012 a été vérifiée contre le
code réellement présent dans le dépôt (lecture des fichiers, pas de mémoire).

Conclusions :
- **API confirmées conformes** : BattleDirector (Sim, PlayerShip, Views,
  ViewOf, Input, Effects, Cam, Restart, OnSimTicked, Outcome), EffectsPool
  (Explosion/Splash/MuzzleFlash/Smoke/QuadMesh), ShipView (State, Spec,
  BowWorldPos, MarkDamage, BeginSink, MakeFlashMaterial), QualityProfiles,
  TouchInputController (BuildCommand, CurrentTargetId), noyau (Projectile,
  CompartmentState, WeaponKind.Rocket, OceanModel.HeightAt, Intercept).
- **1 bug critique trouvé et corrigé** : parse_args_after_dashes() avait un
  parseur argparse VIDE — args.out aurait levé AttributeError et fait
  échouer les générateurs au premier appel réel (commit 784e613e).
- **1 bug réel corrigé grâce à l'exécution CI** : gen_aircraft_blender.py
  appelait add_cone sans l'argument r2 (TypeError) — révélé par le
  traceback CI, corrigé (commit 7e1aa424). Le validateur (py_compile) ne
  pouvait pas l'attraper : preuve que le validateur n'est pas une compilation.
- Limite cosmétique (non bloquante) : le bouton PAUSE peut démarrer une
  orbite caméra d'un frame.

## 2. Production RÉELLE des FBX — FAITE (Blender 4.2.3 LTS en CI)

Workflow .github/workflows/warships-blender-fbx.yml. Historique honnête des
runs (chaque échec corrigé puis re-testé) :
1. ref checkout invalide (backslash parasite) — corrigé (bb8ed144) ;
2. chemins relatifs faux + blender renvoie exit 0 malgré une erreur
   Python — corrigés (1a3427a9) ;
3. apt-get install blender > 20 min sur l'image Ubuntu 26 (timeout 25 min)
   — remplacé par Blender portable 4.2.3 LTS téléchargé directement
   (0b2288d7) ;
4. traceback du générateur aéronefs révélé par l'annotation CI — corrigé
   (7e1aa424) ;
5. **RUN VERT (38 s)** : run 42282487303 — les 6 générateurs exécutés,
   FBX vérifiés (tailles réelles), committés par le bot (9c1db33a) et
   publiés en artefact omni-warships-fbx (FBX + logs) ;
6. re-run déclenché par le push des docs : le filtre paths s'évalue sur
   le diff cumulé de la PR → les FBX régénérés (horodatage binaire neuf)
   ont été RE-commités par le bot (078bd4ec) — churn qui déplace la tête
   de la PR à chaque push sans jamais stabiliser les checks ;
7. **correctif d'idempotence (904cd4f7)** : le workflow ne committe plus
   que si Resources/Models ne contient aucun .fbx. La génération reste
   vérifiée à chaque run (job vert), sans commit ni déplacement de tête.

FBX réellement produits (tailles vérifiées dans le dépôt, commit 9c1db33a) :

| Fichier | Taille (octets) |
|---|---|
| ws-destroyer-01.fbx | 2 404 572 |
| ws-frigate-01.fbx | 2 278 988 |
| ws-carrier-01.fbx | 2 255 020 |
| ws-submarine-01.fbx | 343 676 |
| ws-aircraft.fbx | 502 428 |
| ws-equipment.fbx | 354 524 |
| **Total** | **8 139 208 (≈ 8,1 Mo)** |

Tailles actuelles sur la tête de branche (FBX régénérés au commit bot
078bd4ec, horodatage binaire différent) : destroyer 2 404 716 o,
frégate 2 279 020 o, porte-avions 2 254 604 o, sous-marin 343 836 o,
aéronefs 502 124 o, équipements 354 892 o — total 8 139 192 o (≈ 8,1 Mo).

Intégration : warships/unity/Assets/OmniWarships/Resources/Models/ — chargés
au runtime par ShipModelLibrary (LOD 0/1/2 nommés _LOD1/_LOD2, pivots
tourelles/radars/rotors exportés comme EMPTY).

## 3. Mission « première bataille jouable » — correspondance code réel

| Exigence | Implémentation (déjà en place, audité) |
|---|---|
| Destroyer contrôlable | BattleBootstrap/BattleConfig : joueur = ws-destroyer-01, équipe blue |
| Ennemi IA | ws-frigate-01, équipe red, IsAi=true (TacticalAI décide à chaque tick) |
| Océan 3D + environnement | OceanController + shader OmniOcean (même formule Gerstner/graine que le noyau) ; WeatherDirector (jour/nuit, météo, pluie, éclairs) |
| Radar et ciblage | SensorModel (noyau) + HUD radar + TouchInputController.CycleTarget |
| Canons + missiles fonctionnels | BuildCommand → BattleSim.TryFire (obus balistique exact, SSM guidage PN, torpilles armées) |
| Impacts et dégâts visibles | Explosion + MarkDamage + ShipDamageVisuals (fumées, écume voie d'eau) |
| Destruction et naufrage | Sunk → BeginSink + Explosion |
| Victoire / défaite | BattleDirector.UpdateOutcome + messages HUD |
| Pause et reprise | PauseMenu (timeScale 0 + noyau arrêté proprement) |
| Commandes tactiles Android | TouchInputController (joystick, boutons d'armes, orbite, pincer) |
| Solo hors ligne | Aucune dépendance réseau ; specs embarquées Resources/Ships |

## 4. Optimisation Android (Tecno KN3, 4 Go RAM)

5 profils (QualityProfiles) : Ultra / Élevé / Moyen / Faible / Adaptatif
(segments océan 128→48, ombres, renderScale 1.00→0.75, effets on/off).
Mesures FPS : exigent l'APK + l'appareil réel. **Aucun chiffre FPS n'est
annoncé sans mesure.**

## 5. Compilation Unity et APK — deux chemins prêts, un blocage : la licence

- **Chemin A (local, gratuit)** : Lassana ouvre warships/unity dans
  Unity 2022.3 (licence personnelle gratuite), menu « OMNI WARSHIPS →
  Android → 1. Preparer le build KN3 » puis « 2. Compiler l'APK »
  (AndroidBuildConfig.cs : identifiant ml.bah.omniwarships, ARM64, IL2CPP,
  paysage verrouillé, Gradle APK, minSdk 24). L'APK sort dans
  Builds/omni-warships-v0.1.0.apk. La scène de bataille est garantie par
  BattleSceneGuard (créée si absente, incluse explicitement).
- **Chemin B (cloud, GameCI, sans PC personnel — navigateur uniquement)** :
  .github/workflows/warships-gameci.yml, activation manuelle
  (workflow_dispatch). Prérequis : secrets UNITY_LICENSE / UNITY_EMAIL /
  UNITY_PASSWORD (licence Unity — l'activation exigée par Unity est la
  seule étape impossible à faire à la place de Lassana). Produit
  l'artefact APK + une release GitHub en brouillon, avec vérification
  taille + sha256 de l'APK (aucune simulation).
- Permissions Android du jeu : **aucune** (hors ligne complet).

## 6. Blocages documentés (honnêtes)

- Aucun Unity/SDK Android dans l'environnement assistant : la compilation
  Unity et l'APK ne peuvent pas être produites ici. Les FBX, eux, sont
  réellement produits en CI (Blender GPL, section 2).
- Licence Unity : indispensable pour tout build (locale ou cloud).
  Décision et activation = Lassana (un clic en local + 3 secrets pour GameCI).
- FPS Tecno KN3 : à mesurer après installation de l'APK réelle.

## 7. T-013.1 — corrections finales avant build (06/11/2026, audit externe)

La PR #16 a été vérifiée indépendamment. Corrections apportées :

### 7.1 Workflow GameCI corrigé (.github/workflows/warships-gameci.yml)
- **Expressions `${{ }}` propres** : les backslashs parasites (`\${{ ... }}`)
  devant secrets.UNITY_LICENSE / secrets.UNITY_EMAIL / secrets.UNITY_PASSWORD,
  secrets.GITHUB_TOKEN et github.run_number auraient transmis une chaîne
  littérale au lieu des valeurs — build condamné. Tous supprimés.
- **Inputs remplacées par les inputs RÉELLES de game-ci/unity-builder@v4**
  (vérifiées contre son action.yml) : androidBuildAppType,
  androidBuildSystem et androidArchitecture N'EXISTENT PAS en v4 ;
  l'input correcte pour une APK est `androidExportType: androidPackage`.
  ARM64 et IL2CPP sont réglés par le projet (AndroidBuildConfig.Configure,
  appelé par buildMethod) — pas par le workflow.
- **permissions: contents: write** ajouté (requis pour gh release create).
- **Vérification des secrets** (présence + absence de caractères parasites
  en début/fin) SANS jamais les afficher dans les logs.
- **Vérification de l'APK produite** (taille + sha256, via glob+stat,
  sans ls) : le job échoue explicitement si aucune APK n'est présente —
  jamais de simulation.
- **buildMethod explicite** : OmniWarships.Unity.EditorTools.
  WarshipsBuildScript.BuildAndroid (scène incluse explicitement).

### 7.2 Scène de bataille — chemin unique et inclusion explicite
- **Bug réel corrigé** : le menu éditeur créait la scène dans
  Assets/OmniWarships/Battle.unity, mais AndroidBuildConfig cherchait
  Assets/Scenes/Battle.unity — la scène n'aurait donc JAMAIS été incluse
  dans le build. Un seul chemin désormais : BattleSceneGuard.cs.
- **BattleSceneGuard.cs** (nouveau, Editor) :
  - la scène est créée automatiquement si elle manque (création additive,
    la scène ouverte n'est jamais écrasée) ;
  - elle est enregistrée dans le dossier correct
    (Assets/OmniWarships/Battle.unity) et dans les Build Settings ;
  - elle est incluse EXPLICITEMENT dans BuildPlayerOptions.scenes ;
  - le build échoue clairement si aucune scène valide n'est disponible
    (jamais de supposition que le bootstrap runtime suffit).
- **WarshipsBuildScript.cs** (nouveau, Editor) : méthode de build GameCI —
  Configure + scène garantie + échec → EditorApplication.Exit(1).
- **Validateur CI étendu (check_scene_build)** : vérifie en CI le chemin
  unique, l'usage de BattleSceneGuard.BuildScenesOrAbort() par les deux
  systèmes de compilation, l'inclusion explicite (`scenes = scenes`) et
  interdit le retour du chemin faux Assets/Scenes/.

### 7.3 Validation des workflows — actionlint EN CI (2 runs rouges, puis vert)
- actionlint indisponible dans l'environnement assistant (aucun réseau,
  aucun binaire) : intégré comme job CI réel (« Workflows (actionlint) »
  dans warships-ci.yml, v1.7.7 épinglée) qui valide YAML + expressions +
  inputs des 3 workflows warships à chaque push.
- Historique honnête des 3 runs :
  1. run 1 ROUGE : le script officiel download-actionlint.bash a pour
     signature `[[VERSION] DIR]` — l'argument `/tmp` seul était interprété
     comme VERSION et rejeté. Corrigé : `1.7.7 /tmp` explicite ;
  2. run 2 ROUGE : actionlint s'est exécuté et a trouvé 2 vrais problèmes
     shellcheck dans le workflow GameCI — SC2034 (variable `name`
     inutilisée dans verify_secret) et SC2012 (`ls` pour lister l'APK).
     Corrigés : messages via `$1` direct, énumération par glob bash +
     stat (aucun ls) ;
  3. run 3 VERT (head 002c0d68) : les 5 checks de la PR sont verts,
     y compris actionlint — le job aurait aussi attrapé les inputs
     inexistantes de unity-builder@v4.

### 7.4 Pipeline Android vérifié (fichiers réels du dépôt)
- Unity 2022.3.62f1 : ProjectSettings/ProjectVersion.txt ✓ ;
- URP 14.0.11 : Packages/manifest.json ✓ ;
- ARM64 + IL2CPP + minSdk 24 + paysage verrouillé : AndroidBuildConfig.cs ✓ ;
- APK et non AAB : buildAppBundle = false + androidExportType: androidPackage ✓ ;
- 6 FBX intégrés : Assets/OmniWarships/Resources/Models/ (chargés par
  ShipModelLibrary) ✓ ;
- aucune dépendance réseau pour la bataille solo : specs embarquées dans
  Resources/Ships, aucune permission Android ✓.

### 7.5 Statut inchangé (honnête)
- Aucune compilation Unity exécutée, aucune APK produite, installée ou
  testée — la licence Unity reste le seul blocage (décision de Lassana).
- Les 34 tests noyau, les validateurs, les 6 générateurs Blender et
  actionlint sont vérifiés verts en CI à chaque push (5 checks sur la PR).
