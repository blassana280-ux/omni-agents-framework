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
## 8. T-013.2 — audit final du compilateur et déclenchement Android sans main

### 8.1 Namespaces des API Build corrigés (audit externe confirmé)
- Bug réel : `WarshipsBuildScript.cs` et `AndroidBuildConfig.cs`
  utilisaient `BuildReport` et `BuildResult` avec seulement
  `using UnityEditor;` — ces types vivent dans
  `UnityEditor.Build.Reporting` (CS0246 à la compilation réelle).
  Corrigé : `using UnityEditor.Build.Reporting;` ajouté aux deux
  fichiers.
- Autres API Build de Unity 2022.3.62f1 vérifiées : BuildPipeline.
  BuildPlayer(BuildPlayerOptions), BuildOptions, BuildTarget,
  EditorUserBuildSettings (androidBuildSystem, buildAppBundle),
  PlayerSettings (SetApplicationIdentifier, SetScriptingBackend),
  AndroidArchitecture / AndroidSdkVersions / UIOrientation,
  EditorSceneManager, AssetDatabase, EditorApplication.Exit — toutes
  dans les namespaces déjà importés (UnityEditor,
  UnityEditor.SceneManagement, UnityEngine). Aucune autre référence
  Build cassée.
- Garde-fou validateur : `check_build_reporting()` — tout script
  éditeur utilisant BuildReport/BuildResult DOIT importer
  `using UnityEditor.Build.Reporting;` (ou noms complets) ; l erreur
  CS0246 ne peut plus revenir sans faire échouer la CI.

### 8.2 Déclenchement GameCI sans fusion et sans toucher main
- Problème confirmé : `workflow_dispatch` n est PAS utilisable depuis
  l interface tant que le workflow n existe pas sur la branche par
  défaut (main) — jamais touché, PRs #13/#14/#15/#16 ouvertes.
- Solution : `on: push` limité à `warships/android-build` + filtre de
  chemins sur `warships/unity/ci/BUILD-TRIGGER.md` (le « bouton de
  compilation », éditable au téléphone). Aucun build inutile : les
  modifications sans rapport avec le jeu ne touchent pas ce fichier.
  `workflow_dispatch` conservé pour usage futur. Les secrets du dépôt
  sont disponibles pour les événements push de la branche.
- Le commit d intégration de T-013.2 déclenche un run qui s arrête à
  la vérification des secrets (run rouge ATTENDU, AUCUNE compilation
  Unity lancée) — preuve réelle que le déclenchement fonctionne sans
  main.

### 8.3 Licence Unity sans PC — workflow warships-license.yml
- Constat (docs game.ci v4, 06/11/2026) : la méthode officielle pour
  une licence Personal est Unity Hub sur machine locale, puis copie
  du .ulf (C:\ProgramData\Unity\Unity_lic.ulf, /Library/Application
  Support/Unity/Unity_lic.ulf ou ~/.local/share/unity3d/Unity/
  Unity_lic.ulf) dans les secrets. Lassana n a pas de PC : cette
  méthode officielle est impossible pour lui. L action game-ci/
  unity-request-activation-file est DÉPRÉCIÉE (déc. 2023) ; le site
  license.unity3d.com masque l option Personal (CSS display:none —
  contournement manuel au téléphone non praticable).
- Méthode implémentée (outillage game-ci maintenu) : workflow
  `.github/workflows/warships-license.yml`, déclenché par
  `warships/unity/ci/LICENSE-TRIGGER.md` :
  1. l image Docker officielle unityci/editor 2022.3.62f1-android
     génère le fichier de DEMANDE .alf (drapeau documenté
     -createManualActivationFile — aucune licence requise) ;
  2. l outil npm game-ci unity-license-activate (organisation
     game-ci, maintenu, support TOTP) automatise l activation sur
     license.unity3d.com (il sélectionne l option Personal masquée
     via puppeteer) et produit le .ulf ;
  3. le .ulf est stocké AUTOMATIQUEMENT dans le secret UNITY_LICENSE
     si le secret ACCESS_TOKEN (PAT fine-grained, permission Secrets
     en écriture) est présent, sinon publié en artefact privé
     unity-ulf ;
  4. en cas d échec : artefact screenshot-error.
- Distinctions (jamais confondues) : .alf = demande générée par
  Unity ; .ulf = licence obtenue ; secrets GitHub = conteneurs des
  valeurs (licence, email, mot de passe, PAT).
- Honnêteté : ce flux n est pas celui de la documentation officielle
  actuelle (Unity Hub) ; il ne sera PROUVÉ qu à sa première exécution
  réelle (aucune simulation). Sans TOTP, Unity peut exiger un code
  envoyé par email que le workflow ne sait pas lire — TOTP
  fortement recommandé.

### 8.4 Statut (honnête)
- Validation STATIQUE (CI verte : 34 tests, validateurs, actionlint,
  Blender) ≠ COMPILATION RÉELLE Unity : aucune compilation n a été
  exécutée, aucune APK produite. Le projet ne sera « compilé » qu après
  un run GameCI vert avec APK vérifiée (taille + sha256).
- Pipeline prêt : secrets → BUILD-TRIGGER.md → APK. Licence : compte
  Unity gratuit + secrets → LICENSE-TRIGGER.md → .ulf → build.
## 9. T-013.3 — sécurisation du workflow de licence (dépôt PUBLIC)

### 9.1 Aucune publication du .ulf (audit externe confirmé)
- Faille réelle : le workflow T-013.2 publiait le .ulf en artefact
  (`upload-artifact`, chemin `*.ulf`) et une capture d erreur
  (`screenshot-error`) — inacceptable sur un dépôt public (les
  artefacts ne sont PAS privés) : le .ulf est une licence Unity
  nominative, la capture peut contenir des informations de compte.
- Corrections : suppression TOTALE des étapes de publication
  (artefact .ulf ET capture) ; si `ACCESS_TOKEN` est absent, arrêt
  explicite (AUCUN repli par artefact) ; si présent, transmission
  DIRECTE du .ulf au secret `UNITY_LICENSE` via l API GitHub, valeur
  jamais affichée ; vérification de la mise à jour SANS lire la
  valeur (`gh secret list` → horodatage `updatedAt`) ; suppression
  locale du .ulf après stockage ; PAT injecté UNIQUEMENT dans l
  étape de stockage.

### 9.2 Outil d activation épinglé et audité (pas de @latest)
- `npx --yes unity-license-activate@0.3.9` : version EXACTE épingle
  (plus de `@latest` flottant). Métadonnées npm vérifiées le
  06/11/2026 : 0.3.9 = dernière version publiée ; intégrité
  `sha512-MBn+IFFv0rLfLNowT2zFXVYUia9Ls2QSjeEB8jv8wCoUHHTJhvAUBw3oKigl2StzFdQYSJfXmBzqno2ccnFAiA==`
  (vérifiée par npm à l installation) ; AUCUN script d installation
  dans le package (champ scripts = test uniquement) ; dépendances
  directes : `crypto-js@^4.1.1`, `puppeteer@^13.7.0` (télécharge
  Chromium — comportement connu).
- Audit du code réellement exécuté (`lib/cli.js`, `lib/activate.js`
  du dépôt game-ci/unity-license-activate, master = 0.3.9) : UNIQUE
  URL contactée = `https://license.unity3d.com/manual` (formulaire de
  connexion Unity ID) ; les identifiants et la clé TOTP ne sont
  envoyés qu à ce formulaire ; support TOTP natif
  (`--authenticator-key`) ; aucune télémétrie tierce dans le code.
- Limites documentées (honnête, aucune certification excessive) :
  dépendances transitives résolues par npm et non figées ; le
  gestionnaire `unity-verify-code` (2FA email via IMAP) n est PAS
  utilisé par ce workflow.

### 9.3 Faisabilité licence Personal — statut honnête
- Distinction claire : la création du `.alf` (drapeau Unity
  documenté, aucune licence requise) ≠ l obtention du `.ulf`
  (passe par license.unity3d.com).
- La documentation officielle Unity n inscrit PAS la licence Personal
  dans le flux d activation manuelle (l option est masquée sur la
  page). L outil game-ci sélectionne cette option masquée (puppeteer)
  — l authentification complète (mot de passe + TOTP) reste TOUJOURS
  requise : aucune authentification ni protection de compte n est
  contournée. Le README de l outil (org game-ci) le revendique
  explicitement conçu pour les licences Personal avec GameCI.
- Statut : méthode RÉELLE mais NON officiellement prise en charge ;
  prouvée seulement à sa première exécution réelle. Blocages
  documentés : 2FA par email (code illisible par le workflow → TOTP
  fortement recommandé), modifications du site Unity (l outil
  casserait), expiration périodique des licences Personal (relancer
  LICENSE-TRIGGER.md). Repli honnête : Unity Hub sur n importe quel
  PC emprunté (une seule fois, puis copie du .ulf dans les secrets).

### 9.4 PAT ACCESS_TOKEN — permissions minimales vérifiées
- Documentation REST GitHub officielle (actions/secrets) : les
  endpoints de secrets de dépôt exigent pour un token fine-grained
  la permission « Secrets » (write pour créer/mettre à jour, read
  pour lister — utilisé pour vérifier la mise à jour sans lire la
  valeur).
- Spécification du PAT : fine-grained ; resource owner =
  blassana280-ux ; accès au SEUL dépôt omni-agents-framework ;
  permission unique « Secrets : Read and write » (+ Metadata:read
  automatique et obligatoire) ; expiration courte (30 jours
  recommandés).
- Injection : le PAT est passé UNIQUEMENT à l étape « Stockage du
  secret UNITY_LICENSE » (env de step) — jamais à l étape d
  activation. Permissions du workflow : `contents: read` uniquement.

### 9.5 Garde-fou CI
- `check_ulf_publication()` dans validate_unity_layer.py : interdit
  tout `upload-artifact` dont le chemin cible un `.ulf`, toute
  association `.ulf` + release dans les 4 workflows, exige que le
  workflow de licence ne publie AUCUN artefact, exige ACCESS_TOKEN
  et l épingle 0.3.9 — la faille ne peut plus revenir sans faire
  échouer la CI.
