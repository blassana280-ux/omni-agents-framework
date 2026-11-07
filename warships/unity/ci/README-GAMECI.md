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
   compile (image unityci/editor 2022.3.62f1-android, buildMethod
   WarshipsBuildScript.BuildAndroid — scène incluse EXPLICITEMENT),
   vérifie l APK (taille + sha256), l uploade en artefact et crée une
   release brouillon.
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
  game-ci sur 2022.3.62f3, voisin direct de notre 2022.3.62f1). C est
  le flux standard unity-builder@v4 de warships-gameci.yml.
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
