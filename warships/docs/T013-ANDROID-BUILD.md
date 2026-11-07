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

## 10. T-013.4 — durcissement final de l activation (audit externe, 07/11/2026)

### 10.1 Isolation stricte du PAT
- ACCESS_TOKEN retiré de l étape de vérification ; injecté UNIQUEMENT dans
  l étape de stockage ; présence vérifiée sans affichage ; après usage :
  unset ulf_value + ACCESS_TOKEN puis vérification d absence ; permissions
  minimales inchangées (fine-grained, seul dépôt, Secrets: Read and write,
  ~30 jours) ; permissions du workflow : contents: read.
- Interprétation de « vérifier son absence » : (a) le validateur CI impose
  structurellement que le PAT n apparaisse dans AUCUN autre step ;
  (b) l étape de stockage vérifie sa présence sans affichage avant toute
  opération ; (c) après usage, unset + re-vérification d absence.

### 10.2 Fuite des identifiants Unity — parcours email neutralisé
- Faille réelle (audit du code source 0.3.9, lib/activate.js) : dans le
  parcours 2FA email, l outil fait console.log d une commande
  unity-verify-code avec EMAIL et PASSWORD en clair, puis tente une
  récupération automatique du code — identifiants exposés dans les logs.
- Corrections (le TOTP obligatoire NE SUFFIT PAS : le parcours email est
  neutralisé indépendamment) :
  * TOTP OBLIGATOIRE (UNITY_TOTP_KEY exigé, --authenticator-key) ;
  * shim unity-verify-code (garde unity-email-guard, en tête de PATH) qui
    échoue sans rien transmettre et pose un marqueur BLOCKED — aucune
    récupération automatique possible ;
  * masquage GitHub ::add-mask:: des trois secrets (toute occurrence
    serait *** même si elle passait) ;
  * sortie de l outil CAPTURÉE puis FILTRÉE (grep -vFf fichier de
    masques) — aucune ligne contenant un identifiant n est affichée,
    même en cas d erreur ;
  * captures d erreur de l outil (error.png, error.html, code.txt)
    supprimées, jamais publiées ; set -x interdit par le validateur.
- stdout et stderr de l outil sont capturés ensemble (2>&1) puis
  filtrés ; les sorties de npm ci et gh ne contiennent aucun secret.

### 10.3 Reproductibilité des dépendances (fin de npx --yes / @latest)
- Arbre verrouillé dans warships/unity/ci/license-tools : package.json
  (unity-license-activate 0.3.9 EXACT) + package-lock.json
  (lockfileVersion 2) ; 67 paquets résolus depuis le registry npm avec
  intégrité sha512 par paquet (puppeteer 13.7.0, crypto-js 4.2.0, etc.) ;
  le workflow lance npm ci et le binaire node_modules/.bin.
- Scripts d installation réels de l arbre (audités) : puppeteer
  (node install.js — télécharge Chromium depuis storage.googleapis.com),
  bufferutil + utf-8-validate (node-gyp-build — binaires locaux, aucun
  réseau). Aucun autre script.
- Job CI « Couche Unity » : npm ci --ignore-scripts installe EXACTEMENT
  l arbre verrouillé (versions 0.3.9 / 13.7.0 vérifiées, aucun script
  exécuté, aucun téléchargement Chromium).
- Domaines externes documentés (workflow entier) : registry.npmjs.org,
  storage.googleapis.com, license.unity3d.com, api.github.com,
  hub.docker.com.

### 10.4 Garde-fous CI structurels + self-tests
- check_workflow_security (STRUCTUREL : parse les steps, pas une
  recherche de chaînes) : ACCESS_TOKEN dans la seule étape de stockage
  (env + unset + vérification d absence + gh secret set/list), add-mask
  des 3 secrets, TOTP obligatoire, garde anti-email, filtrage des
  sorties, npm ci, binaire de l arbre verrouillé ; interdit npx,
  @latest, unity-license-activate@X, upload-artifact, git add/commit/
  push, set -x, tout appel unity-verify-code hors garde.
- check_license_lock : 67 paquets, intégrité sha512 partout, resolved
  sur registry.npmjs.org, racine épinglée 0.3.9, hasInstallScripts
  déclaré pour puppeteer.
- SELF-TESTS de non-régression (dans validate_unity_layer.py) : un
  snippet SAIN (0 erreur attendue) + 8 snippets FAUX (PAT déplacé,
  add-mask manquant, npx @latest, upload-artifact, unity-verify-code
  direct, PAT non effacé, set -x, TOTP facultatif) — chaque régression
  détectée fait échouer la CI.

### 10.5 Statut inchangé (honnête)
- Aucune acquisition réelle déclenchée, aucun secret demandé, aucune
  compilation Unity, aucune APK. La méthode Personal reste NON
  officiellement supportée (option masquée) ; l authentification
  complète (mot de passe + TOTP) reste toujours requise ; preuve =
  première exécution réelle. Repli : Unity Hub sur un PC emprunté.

## 11. T-013.5 — dernier audit du pipeline d activation (07/11/2026)

### 11.1 Audit des scripts d installation (67/67, contre le registry)
- Difference réelle corrigée : le workflow de licence installait avec
  npm ci simple (scripts exécutés) alors que la CI vérifiait
  --ignore-scripts. Les DEUX utilisent désormais
  npm ci --ignore-scripts --no-audit --no-fund.
- Audit réel des 67 entrées du lock : EXACTEMENT 3 paquets déclarent
  des scripts d installation — puppeteer 13.7.0 (« install » = node
  install.js, télécharge Chromium), bufferutil 4.1.0 et utf-8-validate
  5.0.10 (« install » = node-gyp-build, binaires locaux). Aucun autre
  script (les prepare/prebuild/postpublish des deps du registre ne
  s exécutent jamais). Le champ hasInstallScripts du lock porte
  exactement ces 3 paquets — vérifié par le validateur ET un test grep
  réel en CI.
- Le lock n est PAS considéré comme une garantie : le validateur exige
  --ignore-scripts dans le workflow, interdit tout « node ...
  install.js », et un test CI réel vérifie que .local-chromium est
  ABSENT après l installation (aucun téléchargement durant npm ci).

### 11.2 Chromium maitrise (sans casser Puppeteer)
- Origine ÉPINGLÉE : curl (donnée, pas un script npm) vers
  https://storage.googleapis.com/chromium-browser-snapshots/Linux_x64/982053/chrome-linux.zip
  — révision 982053 figée dans revisions.js de puppeteer 13.7.0 =
  Chromium 101.0.4951.64. Le zip est dézippé à l emplacement attendu :
  node_modules/puppeteer/.local-chromium/linux-982053.
- Empreinte : sha256sum consigné dans les logs (Google ne publie PAS de
  checksum pour ce snapshot — garantie = HTTPS + hôte épinglé +
  révision figée + version vérifiée à l exécution : chrome --version
  doit rendre 101.0.4951.x sinon échec).
- Résolution vérifiée : require('puppeteer').executablePath() DOIT
  retourner le binaire dézippé, sinon échec — Puppeteer fonctionne
  sans qu aucun script npm ne s exécute.
- Exécutables additionnels autorisés : curl, unzip, node -e
  (résolution) — c est tout ; aucun script tiers.

### 11.3 Domaines externes (liste blanche structurelle)
- registry.npmjs.org (arbre 67 paquets) ; storage.googleapis.com
  (UNIQUEMENT l URL épinglée 982053) ; license.unity3d.com (via l
  outil d activation) ; api.github.com (stockage du secret) ;
  hub.docker.com (image unityci/editor). Le validateur rejette tout
  autre domaine du workflow ; un test CI réel vérifie que le lock ne
  résout QUE registry.npmjs.org.

### 11.4 Correctif du validateur (bug réel trouvé par l audit)
- check_license_lock() retournait sa liste d erreurs mais main()
  IGNORAIT la valeur de retour : tous les checks du lock étaient du
  code mort. Corrigé : chaque erreur fait désormais échouer la CI ;
  le comptage doublé a été corrigé et le check exige exactement les
  3 paquets hasInstallScripts attendus.
- check_workflow_security +4 règles T-013.5 : npm ci --ignore-scripts
  obligatoire ; node install.js interdit ; URL Chromium épinglée
  obligatoire ; domaines du workflow en liste blanche. SELF-TESTS
  portés à 12 snippets FAUX + 1 sain (13 au total).

### 11.5 Nettoyage du runner (échecs intermédiaires)
- Nouveau step final « Nettoyage du runner » (if: always()) : log d
  activation, fichier de masques, zip Chromium, shim anti-email,
  .alf/.ulf, captures (error.png/error.html/code.txt) supprimés MÊME
  SI un step précédent échoue. Les secrets de step ne vivent que
  dans env GitHub (jamais écrits sur disque) ; masks.txt (valeurs de
  masquage) supprimé.

### 11.6 Statut inchangé (honnête)
- Aucune acquisition réelle déclenchée, aucun secret demandé, aucune
  fusion, main intacte. Preuve = première exécution réelle.

## 12. T-013.7 — vérification de la migration GameCI et réconciliation (07/11/2026)

### 12.1 Réconciliation GitHub (divergence T-013.6)
- Le rapport T-013.6 annonçait un commit 26344d2a « livré » : il n a
  JAMAIS existé sur GitHub (branche toujours sur 0e5ec86d, aucun run
  pour ce SHA, PR #16 intacte, aucune trace dans la base de
  connaissance). La migration « game-ci/unity-activate v2 + CLI
  v1.5.1 » de T-013.6 était THÉORIQUE et partiellement inventée
  (inputs username/password/totp inexistantes dans l action v2 ;
  version v1.5.1 de la CLI inexistante). T-013.7 repart de la tête
  réelle 0e5ec86d et ne pousse que du travail vérifié, commit par
  commit, sur GitHub.

### 12.2 Audit réel de game-ci/unity-activate (v2)
- Dépôt github.com/game-ci/unity-activate, tête main 2e3cdcc0,
  package version 2.0.0, action node20 ; tag v2 = commit 33cd3ea9.
- action.yml : inputs RÉELLES = unityVersion (inutilisée, pure
  compatibilité), cliVersion (défaut latest, épinglable),
  githubToken (défaut github.token, sert UNIQUEMENT à résoudre
  « latest » en tag via api.github.com). AUCUNE input
  username/password/totp ou credentials : les secrets Unity sont lus
  par la CLI depuis l ENVIRONNEMENT (jamais en arguments de ligne de
  commande — pas de fuite par table des processus ou logs de job).
- src/index.ts lance « game-ci activate <path> » ; l action wrapper
  transmet GITHUB_WORKSPACE comme projet racine — inadapté à notre
  projet (warships/unity) : nous n utilisons PAS l action wrapper
  mais unity-builder@v4 (build complet, conteneur unique).

### 12.3 Audit réel de game-ci/cli et réponse « Personal sans PC »
- Versions RÉELLES : v0.1.x, dernière v0.1.72 (2026-10-03, commit
  7da0cea2) — PAS de v1.5.1. Releases binaires par OS/architecture
  avec checksums.txt (sha256).
- Scripts d activation (activate.sh, licensing_method.sh) : chaîne
  de méthode = file → serial → floating → personal ; « personal » =
  UNITY_EMAIL + UNITY_PASSWORD seuls : le Unity Licensing Client
  (« --activate-all --include-personal --username --password »)
  obtient un siège Personal SANS fichier de licence et SANS
  navigateur. Mesuré publiquement par game-ci sur Unity
  2022.3.62f3 (voisin direct de notre 2022.3.62f1).
- .alf/.ulf : MORT pour Personal — license.unity3d.com/manual
  redirige vers /new (« Offline activation is available only for
  Enterprise and Industry seats »). Le flux T-013.2 à T-013.5 est
  périmé côté Unity et retiré du dépôt.
- 2FA : aucun défi 2FA ni vérification d appareil ne peut recevoir
  de réponse en headless → compte Unity avec 2FA DÉSACTIVÉE
  obligatoire (compte dédié au CI recommandé, jamais le compte
  principal). Le TOTP de T-013.4 concernait l ancien parcours
  navigateur : retiré.
- Sièges : un siège Personal est TENU jusqu à restitution, et la
  restitution n est fiable que DANS LE MÊME CONTENEUR que l
  activation (game-ci activate-only laisse le siège actif ; le
  retour entre conteneurs distincts échoue : « bound to a different
  machine »). Décision : activation + build + restitution dans le
  MÊME run unity-builder@v4 ; AUCUN workflow d activation standalone.

### 12.4 Décision d architecture (T-013.7)
- warships-gameci.yml (déclenché par BUILD-TRIGGER.md) = point d
  activation UNIQUE : méthode personal par identifiants dans le
  conteneur du builder, siège rendu automatiquement (trap EXIT du
  conteneur, même en cas d échec du build). Plus d exigence
  UNITY_LICENSE.
- warships-license.yml devient une GARDE DE VÉRIFICATION sans
  activation : vérifie UNITY_EMAIL/UNITY_PASSWORD (propres, jamais
  affichés), ne contacte PAS Unity, ne produit AUCUN fichier,
  nettoie always() (dont /tmp/alfdir, résidu des anciens flux).
  Plus de PAT, plus de TOTP, plus de dépendance npm, plus de
  navigateur de 2022.
- Suppression de warships/unity/ci/license-tools (67 paquets,
  puppeteer 13.7.0, Chromium 101 d avril 2022) : plus de navigateur
  obsolète exposé à des identifiants réels.
- Secrets requis : UNIQUEMENT UNITY_EMAIL + UNITY_PASSWORD (compte
  Unity gratuit Personal, 2FA désactivée). Plus de UNITY_LICENSE,
  UNITY_TOTP_KEY ni ACCESS_TOKEN.

### 12.5 Garde-fous CI refondus
- check_workflow_security (T-013.7) : step de vérification des
  secrets (env + verify_secret sans affichage, TOTP proscrit), step
  nettoyage always() avec /tmp/alfdir, 21 motifs interdits sur les
  lignes actives (outils npm, navigateur, image docker d activation,
  fichiers de licence, PAT, TOTP, UNITY_SERIAL...), set -x /
  upload-artifact / opérations git interdits.
- SELF-TESTS refondus : 1 snippet sain + 8 snippets FAUX (relance
  docker du flux .alf, outil npm réintroduit, stockage de fichier de
  licence via PAT, TOTP exigé, set -x, always() retiré,
  UNITY_LICENSE exigé, activation par navigateur) — tous rejoués en
  simulation avant le push (aucun non-détecté).
- check_license_tools : AUCUN workflow ne référence license-tools ;
  le step CI T-013.7 vérifie en plus 16 motifs interdits sur le
  workflow de licence ENTIER (commentaires compris) et l absence d
  exigence UNITY_LICENSE sur le workflow de build.

### 12.6 Statut (honnête)
- Réponse à « Unity Personal sans PC ? » : OUI pour le mécanisme —
  prouvé par le code source des scripts d activation game-ci et
  leurs mesures publiques (2022.3.62f3) ; la PREUVE d obtention ne
  peut exister qu au premier run réel du build avec les identifiants
  de Lassana (aucun identifiant réel utilisé dans cet audit, aucune
  activation déclenchée, aucun fichier de licence publié). Un test
  avec de faux identifiants ne prouve rien : il sera explicitement
  rouge sans siège.
- Licence MIT de game-ci ≠ licence Unity (jamais confondues).
- Blocages : identifiants Unity = décision de Lassana (compte dédié
  CI, 2FA désactivée) ; le support Personal des scripts v4
  embarqués dans l image du builder sera tranché par le premier run
  réel (repli documenté : game-ci/cli directement dans le
  conteneur).

## 13. T-013.8 — correction du moteur d activation réel : GameCI CLI v0.1.72 (07/11/2026)

### 13.1 Bug bloquant T-013.7 (audit indépendant confirmé)
- warships-gameci.yml utilisait game-ci/unity-builder@v4 : cette
  action lance son propre conteneur et monte SES scripts dans /steps
  (volume docker), ÉCRASANT ceux de l image. Ces scripts v4 ne
  contiennent PAS le chemin personal de la CLI (siège demandé avec
  UNITY_EMAIL + UNITY_PASSWORD seuls) : avec notre configuration
  T-013.7 (plus de UNITY_SERIAL ni UNITY_LICENSE), l activation
  aurait ÉCHOUÉ AVANT la compilation. Le « repli documenté » de la
  section 12.6 (game-ci/cli directement) devient le chemin
  PRINCIPAL.

### 13.2 Audit réel au tag v0.1.72 (commit 7da0cea2, celui de la release)
- Installation : l action composite à la racine du dépôt game-ci/cli
  (inputs args, version, working-directory) a été ÉCARTÉE après test
  réel : son install.sh racine est commité sans bit exécutable (mode
  100644 dans l arbre git du tag v0.1.72), le step composite échoue
  donc en exit 126 — constaté par le run CI du commit 07589340
  (job « GameCI CLI v0.1.72 », deux runs identiques). L INSTALLATEUR
  officiel scripts/install.sh (source unique documentée par le dépôt,
  versionnée par le tag, invoquée par curl ... | bash -s -- VERSION
  DEST) est utilisé à la place : il télécharge l archive de la
  release, vérifie le sha256 contre checksums.txt AVANT extraction
  (mismatch = FATAL ; fetch impossible = soft-skip documenté — le
  job CI T-013.8 fait sa propre vérification STRICTE), extrait et
  chmod 755 le binaire.
- src/model/docker.ts : `game-ci build` lance UN SEUL docker run et
  monte SA PROPRE archive (cliDistPath/platforms/ubuntu/steps vers
  /steps, entrypoint.sh vers /entrypoint.sh) : les scripts du
  conteneur sont ceux du CLI v0.1.72, JAMAIS ceux d une action
  tierce. Le workspace du runner est monté (/github/workspace) et le
  CLI refuse un projectPath hors du répertoire courant.
- runsteps.sh : trap `return_license_once` EXIT armé APRÈS la
  réussite de l activation (jamais en activate-only) → siège
  Personal restitué même si le build échoue (set -e, SIGINT/SIGTERM
  compris) ; activate.sh : branche personal = Unity Licensing Client
  (--activate-all --include-personal --username --password), garde
  anti faux-succès (« No seat available » → échec explicite),
  fallback éditeur pour les clients antérieurs à --include-personal ;
  return_license.sh : branche personal dédiée (routes client et
  éditeur, retries sur signatures transitoires, avertissement si le
  siège reste tenu) ; build.sh : appelle notre -executeMethod avec
  -customBuildPath / -androidExportType ; entrypoint.sh : prépare le
  SDK Android (targetAPI lu dans ProjectSettings.asset) puis source
  /steps/runsteps.sh.
- Options réelles vérifiées dans le code : projectPath POSITIONNEL,
  --targetPlatform (OBLIGATOIRE, choix Android), --buildMethod,
  --androidExportType androidPackage, --buildsPath (défaut
  build/<platform>), --versioningStrategy (choix None réel, défaut
  Semantic), secrets UNITY_EMAIL/UNITY_PASSWORD lus dans l ENV du
  processus du CLI (jamais en arguments de sa ligne de commande).

### 13.3 Sécurité (documentée honnêtement)
- Dans le conteneur, le Unity Licensing Client exige le mot de passe
  PAR ARGUMENT DE PROCESSUS (aucune alternative stdin ou fichier n
  existe — documenté dans le code du CLI) : visible dans la liste de
  processus du conteneur pendant l appel, jamais affiché dans les
  logs, aucun set -x sur ce chemin. Acceptable en CI isolée.
- Compte Unity CI DÉDIÉ uniquement (JAMAIS le compte principal de
  Lassana), sa 2FA DÉSACTIVÉE — création et usage = décision
  explicite de Lassana. Aucune activation déclenchée pendant cette
  mission, aucun identifiant demandé, aucun fichier de licence
  publié.

### 13.4 Nouvelle architecture (warships-gameci.yml)
- Installation : curl épinglé sur scripts/install.sh du tag v0.1.72
  puis bash -s -- v0.1.72 $RUNNER_TEMP/game-ci/bin (installateur
  officiel ; l action composite racine du dépôt est écartée — exit
  126 constaté par run CI réel).
- UNE SEULE commande de build, secrets passés par env (jamais en
  arguments) :
  `game-ci build warships/unity --targetPlatform Android
  --buildMethod OmniWarships.Unity.EditorTools.WarshipsBuildScript.
  BuildAndroid --androidExportType androidPackage
  --versioningStrategy None`
- buildMethod conservé : AndroidBuildConfig.Configure (ARM64, IL2CPP,
  minSdk 24, paysage, URP, profils graphiques) + scène explicite
  (BattleSceneGuard) ; l APK sort dans warships/unity/Builds/ (chemin
  explicite du script, dans le volume monté) — la vérification
  (taille + sha256) cherche là.
- game-ci activate isolé et game-ci/unity-builder@v4 INTERDITS par la
  CI : step T-013.8 de warships-ci.yml (greps structurels),
  check_gameci_workflow du validateur et 4 nouveaux self-tests de
  non-régression (2 snippets sains + régressions v4 / activation
  isolée / build sans buildMethod).

### 13.5 Tests SANS identifiants réels (job CI dédié, exécuté à chaque push)
- Installation réelle du CLI v0.1.72 via l installateur officiel.
- CORRECTIF (retour CI réel du commit 9ee95795) : ce CLI DÉSACTIVE
  --version et --help (src/cli.ts au tag v0.1.72 : .version(false) et
  .help(false), « Fixes broken _handle in yargs 17.0.0 ») — le test
  `game-ci --version` échouait en exit 1 (Unknown argument). La
  preuve de version est donc STRUCTURELLE : checksum sha256 STRICT
  de l archive de la release contre checksums.txt (mismatch = échec,
  pas de soft-skip) PLUS identité bit à bit du binaire installé avec
  le binaire extrait de cette même archive vérifiée.
- Options réelles prouvées sur les SOURCES du tag épinglé
  (src/command-options/*.ts) : .option('targetPlatform' et
  unityLicensingMethod (auto : serial, file, floating, personal) dans
  unity-options.ts ; .option('buildsPath' et .option('buildMethod'
  dans build-options.ts ; .option('versioningStrategy' (choix None
  réel) dans versioning-options.ts ; androidExportType avec choices
  androidPackage/androidAppBundle/androidStudioProject dans
  android-options.ts — l identité binaire ↔ tag étant déjà prouvée
  par le checksum.
- Preuve des scripts du conteneur réel : grep de --include-personal
  (activate.sh), du trap return_license_once EXIT (runsteps.sh), de la
  branche personal (return_license.sh) et de l orchestration
  (entrypoint.sh) dans l archive installée — les scripts que le CLI
  montera dans /steps.
- Résolution du projet : ProjectVersion.txt = 2022.3.62f1 ;
  namespace, classe et méthode du buildMethod présents dans le .cs
  réel.
- AUCUNE commande ne touche Unity : ce job ne prouve PAS une
  activation (siège = premier run réel du build). YAML/actionlint,
  34 tests noyau, vérifications des données et générateurs Blender :
  inchangés et exécutés comme avant.

### 13.6 Statut (honnête)
- Aucune activation réelle, aucune connexion Unity, aucun identifiant
  demandé, aucun fichier de licence publié ; aucune fusion, main
  intacte, PRs #13/#14/#15/#16 ouvertes.
- Limites restantes : chemin personal expérimental (mesuré
  publiquement par game-ci sur 2020.3.49f1/2022.3.62f3/6000.x, mais
  jamais exécuté sur NOTRE compte) ; mot de passe transmis au
  Licensing Client par argument de processus dans le conteneur ;
  compte CI dédié + 2FA désactivée = décision explicite de Lassana ;
  le premier run réel du build reste la SEULE preuve d obtention du
  siège.

### 13.7 Intégration (tête réelle GitHub)

- Architecture, workflows, validateur et rapport T-013.8 poussés par le
  commit 0758934022c43e1adc7fb7bd9eefaaf8b06335c7 (07/11/2026, branche
  warships/android-build, PR #16) — ce commit déclenche le run rouge
  ATTENDU du workflow de build (vérification des secrets absents,
  arrêt AVANT toute installation CLI, activation et compilation).
- Premier retour RÉEL de la CI sur ce commit : 2 échecs authentiques,
  tous deux corrigés — (1) le nom d un step du workflow de build
  contenait « : » non quoté (YAML invalide, actionlint l a rejete :
  « mapping values are not allowed in this context », ligne 123) ;
  (2) l action composite game-ci/cli@v0.1.72 échoue en exit 126 :
  son install.sh racine est commité sans bit exécutable (mode 100644
  dans l arbre git du tag — vérifié) ; l installation passe donc par
  l installateur officiel scripts/install.sh épinglé au tag. Chaque
  échec est resté sans aucune activation ni connexion Unity.
- Chronologie réelle de l intégration : commit 07589340 (architecture,
  workflows, validateur, rapport — run rouge ATTENDU du workflow de
  build : vérification des secrets absents, arrêt AVANT toute
  installation CLI, activation et compilation) ; commit 69000ecc
  (statut) dont la CI a révélé 2 échecs réels (YAML deux-points ligne
  123 ; action composite racine exit 126 : install.sh commité sans
  bit exécutable) ; commit 3499e07d (correctif des 2 échecs) ; commit
  9ee95795 (docs seules — ne touche PAS BUILD-TRIGGER.md, aucune
  compilation déclenchée) dont la CI a révélé un 3e échec réel : le
  job « GameCI CLI v0.1.72 » testait `game-ci --version`, or ce CLI
  désactive --version et --help (.version(false)/.help(false) dans
  src/cli.ts au tag) — exit 1 (Unknown argument). Présent correctif :
  preuve d identité par checksum sha256 strict + comparaison bit à
  bit du binaire installé avec l archive vérifiée de la release,
  options de build prouvées sur les sources du tag, docs mises à
  jour. Chaque échec est resté sans aucune activation ni connexion
  Unity.
- Aucune fusion, main intacte, PRs #13/#14/#15/#16 ouvertes.


## 14. T-013.9 — sécurisation finale du CLI GameCI avant tout identifiant réel (07/11/2026)

### 14.1 Audit indépendant : le mot de passe dans l argv des processus

- Constat (lecture du code du tag v0.1.72) :
  ImageEnvironmentFactory.getEnvVarString() émet des paires
  `--env UNITY_PASSWORD="valeur"` (src/model/image-environment-factory.ts,
  src/model/docker.ts, src/model/system/system.ts,
  src/logic/unity/environment.ts) ; System.run() transmet la commande
  à `sh -c` : le secret apparaît dans la liste d arguments des
  processus du runner. SecretRedaction protège les LOGS, pas l argv —
  deux problèmes différents, aucun ne remplace l autre.
- Correction appliquée : les identifiants sensibles (UNITY_EMAIL,
  UNITY_PASSWORD, UNITY_SERIAL, UNITY_LICENSING_SERVER,
  ANDROID_KEYSTORE_PASS, ANDROID_KEYALIAS_PASS,
  USYM_UPLOAD_AUTH_TOKEN, PRIVATE_REGISTRY_TOKEN) sont transmis par
  ENVIRONNEMENT HÉRITÉ — le constructeur Docker émet des références
  SANS valeur (`--env UNITY_EMAIL`, `--env UNITY_PASSWORD`), les
  valeurs arrivent au processus docker par son environnement.

### 14.2 CLI corrigé reproductible (dépôt officiel JAMAIS modifié)

- Fork GitHub de game-ci/cli : bloqué en 403 (documenté dans
  warships/unity/ci/gameci-cli-secure/README.md) — le correctif vit
  dans NOTRE dépôt : source officielle ÉPINGLÉE au commit git
  7da0cea2f31799a4cbd79c1d452c254023f4f678 (checkout du workflow de
  release, intégrité par SHA git) + overlay MINIMAL committé
  (2 fichiers exacts, assertion git status en CI ; dist/ INTACTE
  octet par octet, assertion git diff --quiet -- dist/).
- Construction : warships-cli-release.yml (déclenché par
  RELEASE-TRIGGER.md, compteur #1) — bun 1.3.13 (1.4.0 casse
  --compile), bun build src/index.ts --compile --target
  bun-linux-x64, dist/ recopiée, archive
  gameci-cli-secure-linux-x64.tar.gz + checksums.txt, release
  IMMUABLE gameci-cli-secure-v0.1.72w1 (assets : archive,
  checksums, T013-9-patch.diff, T013-9-secure-env.test.ts),
  empreinte ANCRÉE DANS GIT par le commit du bot
  (artifact-checksum.txt + BUILD-INFO.txt, built_from_commit=
  46bda44aeb5dd23b364c6d0a473fd9df7d1b8a34).
- sha256 de l archive publiée :
  49c49df3f4af768e0cae82fc7c92b6ae6fa3769ae8703b50d8b9d35f830fc3a7
  (identique au fichier ancré dans git — la divergence est FATALE).

### 14.3 Checksum STRICT dans le workflow de compilation

- warships-gameci.yml n accepte AUCUNE installation non vérifiée :
  l installation passe UNIQUEMENT par verify-gameci-cli.sh
  (échec FATAL si checksums.txt est inaccessible, si l empreinte
  attendue est absente — de checksums.txt OU du fichier ancré dans
  git artifact-checksum.txt —, en cas de divergence ou de mismatch
  sha256 ; comparaison bit à bit du binaire installé avec celui de
  l archive vérifiée ; preuve des scripts personal + trap EXIT dans
  l artefact).
- L installateur officiel du dépôt game-ci/cli est ÉCARTÉ : il
  poursuit l installation après un ÉCHEC de checksum (soft-fail,
  constaté dans son code), et son binaire non corrigé met les
  identifiants dans la chaîne sh -c.
- Le job CI « GameCI CLI corrige T-013.9 » vérifie en plus l artefact
  PUBLIÉ en ligne + une garde anti-staleness (git diff du
  patched-src entre le commit de build et la tête : un correctif
  modifié sans republication fait échouer la CI).

### 14.4 Tests automatisés (valeurs 100 % factices, jamais imprimées)

- 5 tests bun (secure-env.test.ts) : UNITY_PASSWORD et UNITY_EMAIL
  absents de la chaîne Docker générée, présents dans l env hérité,
  conteneur servi avec les identifiants, System.run spawné avec env —
  verts en CI.
- 9 cas du vérificateur (test-verify-gameci-cli.sh) : 1 acceptation
  (archive correcte + empreinte ancrée concordante) + 8 refus
  (checksums.txt inaccessible ; empreinte absente de checksums.txt ;
  checksum incorrect ; empreinte absente du fichier ancré ;
  divergence checksums.txt/ancré ; binaire absent de l archive ;
  scripts personal absents ; archive elle-même inaccessible).
- Historique honnête : le premier run de ces tests a échoué en CI
  (8 cas écrits pour un total attendu de 9 — le compteur final
  exigeait 9 réussites) ; corrigé par le commit
  46bda44aeb5dd23b364c6d0a473fd9df7d1b8a34 (9e cas : archive
  inaccessible), après quoi le run release a construit et publié le
  CLI corrigé (runs verts : warships-ci push 42400543237, PR
  42400546502, release 42400543225, bot commit b12c7b9ccc).

### 14.5 Ce qui ne change PAS

- Scripts personal, build Android et restitution du siège : dist/
  recopiée INTACTE dans l artefact (assertion git en CI), commande
  de build inchangée (un seul conteneur : siège Personal +
  compilation + restitution par trap EXIT).
- AUCUNE activation, AUCUNE connexion Unity, AUCUN secret réel,
  AUCUN compte Unity créé ou modifié, 2FA jamais désactivée,
  BUILD-TRIGGER.md JAMAIS touché (RELEASE-TRIGGER.md, compteur #1,
  est un bouton DIFFÉRENT : il publie le CLI corrigé, il ne
  déclenche JAMAIS le build Android).
