# Pipeline de compilation Unity (GameCI) — PRÉPARÉ, VÉRIFIÉ, DÉCLENCHABLE SANS MAIN

Statut honnête : **préparé et vérifié statiquement, jamais exécuté**
(aucune compilation Unity, aucune APK — la licence n est pas encore
configurée). Le workflow réel vit sur la branche `warships/android-build`
(`.github/workflows/warships-gameci.yml`), PR #16 ouverte, **main INTACT**.

## T-013.2 — déclenchement SANS fusion et SANS main

- `workflow_dispatch` n est PAS utilisable depuis l interface GitHub
  tant que le workflow n existe pas sur la branche par défaut (main) —
  jamais touché.
- Solution : déclenchement par **push limité à la branche
  `warships/android-build`** avec **filtre de chemins** : la compilation
  ne part QUE si le fichier `warships/unity/ci/BUILD-TRIGGER.md` est
  modifié (commit explicite, éditable depuis le navigateur du téléphone).
- Aucune compilation automatique inutile : les modifications sans
  rapport avec le jeu (docs, noyau, validateurs) ne touchent pas le
  fichier déclencheur et ne lancent RIEN.
- Les secrets du dépôt sont disponibles pour les événements push de la
  branche (vérifiés SANS jamais être affichés dans les logs).
- `workflow_dispatch` est conservé pour usage futur (après une
  éventuelle fusion — décision de Lassana).
- Run rouge « secret absent » sur le commit d intégration : ATTENDU —
  la vérification des secrets échoue AVANT toute compilation Unity.

## Compilation (étapes exactes, téléphone uniquement)

1. Secrets du dépôt (Settings > Secrets and variables > Actions) :
   `UNITY_EMAIL`, `UNITY_PASSWORD` (compte Unity GRATUIT Personal avec
   2FA DÉSACTIVÉE — compte dédié au CI recommandé), sans espaces
   parasites autour. Plus de fichier de licence (T-013.7 : Unity a
   retiré l activation manuelle des licences Personal ; le build
   demande un siège Personal par identifiants, dans son conteneur).
2. Ouvrir `warships/unity/ci/BUILD-TRIGGER.md` sur GitHub (navigateur
   mobile), crayon, incrémenter le compteur, commiter sur la branche.
3. Le job build-android : vérifie les secrets, libère l espace disque,
   installe GameCI CLI v0.1.72 (action officielle, version épinglée par
   le tag, checksums vérifiés), puis UNE SEULE commande `game-ci build`
   fait tout dans UN SEUL conteneur : siège Personal par identifiants,
   compilation (image unityci/editor 2022.3.62f1-android, buildMethod
   WarshipsBuildScript.BuildAndroid — scène incluse EXPLICITEMENT),
   restitution du siège même en cas d échec (trap EXIT), vérifie l APK
   (taille + sha256), l uploade en artefact et crée une release
   brouillon.
4. Télécharger l APK : artefact `omni-warships-apk` ou release brouillon
   `android-build-N`.

## Licence Unity sans PC (T-013.7 — méthode personal PAR IDENTIFIANTS, audit réel du code)

Audit du code source réel (07/11/2026) : action game-ci/unity-activate
v2 (package 2.0.0, tête 2e3cdcc0, tag v2 = 33cd3ea9 ; inputs réelles :
unityVersion, cliVersion, githubToken — AUCUNE input identifiants) et
game-ci/cli (v0.1.72, commit 7da0cea2 ; PAS de v1.5.1). Conclusions :

- Unity a SUPPRIMÉ l activation manuelle (hors-ligne) des licences
  Personal : license.unity3d.com/manual redirige vers /new et répond
  que l activation hors-ligne est réservée aux sièges Enterprise et
  Industry. L ancien flux .alf/.ulf (T-013.2 à T-013.5, y compris l
  outillage npm + navigateur de 2022) est OBSOLÈTE et RETIRÉ du
  dépôt (dossier license-tools supprimé).
- La méthode Personal SANS PC et SANS fichier de licence : le client
  de licence Unity, DANS LE CONTENEUR DU BUILD, demande un siège
  Personal avec UNITY_EMAIL + UNITY_PASSWORD (chaîne file → serial →
  floating → personal des scripts d activation game-ci ; mesurée par
  game-ci sur 2022.3.62f3, voisin direct de notre 2022.3.62f1). Depuis
  T-013.8, c est le flux de la commande de build de GameCI CLI v0.1.72
  dans warships-gameci.yml (un seul conteneur — voir section T-013.8).
- 2FA : l activation headless ne peut répondre à AUCUN défi 2FA ni
  vérification d appareil — le compte Unity utilisé DOIT avoir la 2FA
  DÉSACTIVÉE (compte dédié au CI recommandé). Plus de TOTP (il
  concernait l ancien parcours navigateur).
- Siège : rendu automatiquement à la fin du build (retour de licence
  armé sur le trap EXIT du MÊME conteneur, même en cas d échec) —
  c est pourquoi activation et compilation vivent dans le MÊME
  conteneur unity-builder@v4 (le retour de siège entre conteneurs
  distincts n est PAS fiable).
- warships-license.yml (déclenché par LICENSE-TRIGGER.md) est devenu
  une GARDE DE VÉRIFICATION SANS AUCUNE ACTIVATION : il vérifie
  UNIQUEMENT la présence et la propreté des secrets, sans jamais les
  afficher, sans contacter Unity, sans produire aucun fichier, avec
  nettoyage always(). Le validateur CI (validate_unity_layer.py)
  interdit structurellement tout retour des anciens motifs (outils
  npm, navigateur, fichiers de licence, PAT, TOTP) — 8 self-tests de
  non-régression.

Honnêteté : mécanisme prouvé par le code source et les mesures
publiques de game-ci, MAIS l obtention réelle ne sera PROUVÉE que par
le premier run réel du build avec les secrets de Lassana (aucune
simulation, aucun identifiant réel utilisé pendant l audit). Ne
JAMAIS communiquer identifiants ou licence dans une conversation.
Licence MIT de game-ci ≠ licence Unity.

## T-013.8 — build par GameCI CLI v0.1.72 (correction du bug bloquant, audit réel)

Un audit indépendant a révélé un bug bloquant dans le flux T-013.7 :
l action de build v4 lance son propre conteneur et monte SES scripts
dans /steps (volume docker), ÉCRASANT ceux de l image — or ces scripts
v4 ne contiennent PAS le chemin personal de la CLI (siège demandé avec
UNITY_EMAIL + UNITY_PASSWORD seuls). Avec notre configuration T-013.7
(plus de UNITY_SERIAL ni UNITY_LICENSE), l activation aurait ÉCHOUÉ
AVANT la compilation.

Migration (auditee au tag v0.1.72 du dépôt game-ci/cli, commit 7da0cea2
= celui de la release) :

- Installation : l INSTALLATEUR OFFICIEL du dépôt game-ci/cli
  (scripts/install.sh, source unique documentée par le dépôt, épinglé
  au tag : curl sur raw.githubusercontent.com/game-ci/cli/v0.1.72/
  scripts/install.sh puis bash -s -- v0.1.72). L action composite
  racine du même dépôt est ÉCARTÉE : son install.sh racine est
  commité sans bit exécutable (mode 100644 dans l arbre git du tag
  v0.1.72) et échoue en exit 126 — constaté par un run CI réel puis
  vérifié dans l arbre git du tag. L installateur vérifie le sha256
  de l archive contre checksums.txt AVANT extraction (mismatch =
  FATAL).
- UNE SEULE commande `game-ci build warships/unity --targetPlatform
  Android --buildMethod OmniWarships.Unity.EditorTools.
  WarshipsBuildScript.BuildAndroid --androidExportType androidPackage
  --versioningStrategy None` lance UN SEUL conteneur (src/model/
  docker.ts : le CLI monte SA PROPRE archive de scripts dans /steps,
  jamais ceux d une action tierce) : siège Personal → compilation →
  restitution (trap EXIT armé par runsteps.sh après la réussite de l
  activation, même en cas d échec du build).
- buildMethod conservé : ARM64, IL2CPP, minSdk 24, URP, profils
  graphiques, scène de bataille explicite ; l APK sort dans
  warships/unity/Builds/ (chemin explicite du script, dans le volume
  monté) — c est là que la vérification taille + sha256 la cherche.
- Sécurité : le CLI lit les secrets dans l ENV de son processus
  (jamais en arguments) ; DANS le conteneur, le Unity Licensing Client
  exige le mot de passe PAR ARGUMENT DE PROCESSUS (aucune alternative
  stdin/fichier n existe — documenté dans le code du CLI) : visible
  dans la liste de processus du conteneur pendant l appel, jamais
  affiché dans les logs, aucun set -x. Compte Unity CI DÉDIÉ requis
  (jamais le compte principal), 2FA de ce compte désactivée.
- CI : l action de build v4 et une activation isolée (`game-ci
  activate`) sont INTERDITES (step T-013.8 de warships-ci.yml,
  check_gameci_workflow du validateur, 4 nouveaux self-tests) ; le
  job « GameCI CLI v0.1.72 (installation réelle, sans activation) »
  prouve à chaque push : identité du binaire installé (checksum sha256
  strict de l archive contre checksums.txt + comparaison bit à bit
  avec le binaire extrait de cette même archive — ce CLI n expose PAS
  --version : .version(false) dans son src/cli.ts au tag), options
  réelles prouvées sur les sources du tag v0.1.72,
  présence des scripts personal (activate.sh/runsteps.sh/
  return_license.sh/entrypoint.sh) dans l archive, résolution du
  projet (ProjectVersion.txt 2022.3.62f1, buildMethod dans le .cs
  réel). AUCUNE commande de ce job ne touche Unity : il ne prouve PAS
  une activation (siège = premier run réel du build).

## Historique licence (T-013.2 à T-013.5 — flux .alf/.ulf, RETIRÉ)

- T-013.2 à T-013.5 avaient construit un flux complet d acquisition
  du fichier de licence (.alf → .ulf) avec outillage npm verrouillé
  (67 paquets, --ignore-scripts) et navigateur épinglé : durcissement
  réel (anti-publication, isolation du PAT, TOTP, filtrage des
  sorties, nettoyage always()), mais PÉRIMÉ côté Unity — l activation
  manuelle des licences Personal n existe plus (T-013.7). Tout ce
  flux est retiré du dépôt ; le validateur interdit son retour.

## Ce que ce pipeline NE fait PAS

- Il ne mesure pas les FPS sur Tecno KN3 (aucun appareil réel branché) ;
- il ne remplace pas la validation manuelle sur appareil ;
- il n est pas compté comme « compilée » tant que le run n est pas vert
  AVEC une APK vérifiée en sortie (taille + sha256).

Intégration T-013.8 : 07/11/2026 — correctifs issus des retours CI
réels : (1) nom de step YAML (deux-points non quoté, ligne 123) ;
(2) installation par l installateur officiel scripts/install.sh du
tag v0.1.72 à la place de l action composite racine (exit 126 :
install.sh racine commité sans bit exécutable) ; (3) le test
`game-ci --version` du job CLI échouait en exit 1 : ce CLI DÉSACTIVE
--version et --help (.version(false) / .help(false) dans src/cli.ts
au tag, « Fixes broken _handle in yargs 17.0.0 ») — la preuve de
version est donc le checksum sha256 strict de l archive PLUS l
identité bit à bit du binaire installé, et les options de build
sont prouvées sur les sources du tag. Aucune activation, aucune
compilation déclenchée par ces correctifs.
