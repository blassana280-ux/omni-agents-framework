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
   `UNITY_LICENSE` (contenu du .ulf), `UNITY_EMAIL`, `UNITY_PASSWORD` —
   sans espaces parasites autour.
2. Ouvrir `warships/unity/ci/BUILD-TRIGGER.md` sur GitHub (navigateur
   mobile), crayon, incrémenter le compteur, commiter sur la branche.
3. Le job build-android : vérifie les secrets, libère l espace disque,
   compile (image unityci/editor 2022.3.62f1-android, buildMethod
   WarshipsBuildScript.BuildAndroid — scène incluse EXPLICITEMENT),
   vérifie l APK (taille + sha256), l uploade en artefact et crée une
   release brouillon.
4. Télécharger l APK : artefact `omni-warships-apk` ou release brouillon
   `android-build-N`.

## Licence Unity sans PC (T-013.3 — workflow warships-license.yml sécurisé)

La documentation officielle actuelle de game.ci recommande Unity Hub
sur un PC — Lassana n en a pas. Le workflow
`.github/workflows/warships-license.yml` (déclenché par le fichier
`warships/unity/ci/LICENSE-TRIGGER.md`) permet d obtenir le .ulf
ENTIÈREMENT depuis le téléphone, SANS JAMAIS publier le .ulf (dépôt
public) :

1. Compte Unity gratuit (id.unity.com, navigateur).
2. Secrets : `UNITY_EMAIL`, `UNITY_PASSWORD`, `UNITY_TOTP_KEY` (clé
   authenticator TOTP — sans elle, Unity peut exiger un code envoyé par
   email que le workflow ne sait pas lire) et `ACCESS_TOKEN`
   **obligatoire** (PAT fine-grained limité à CE dépôt, permission
   « Secrets » en écriture seule, expiration courte ~30 jours — cf.
   LICENSE-TRIGGER.md).
3. Modifier `LICENSE-TRIGGER.md` (incrémenter le compteur) : le workflow
   génère le .alf (image Docker unityci/editor, drapeau documenté
   -createManualActivationFile, aucune licence requise), l échange
   contre un .ulf via l outil ÉPINGLÉ `unity-license-activate@0.3.9`
   (organisation game-ci, audité : seul domaine contacté =
   license.unity3d.com ; aucun script d installation ; intégrité
   vérifiée par npm à l installation), puis stocke le .ulf DIRECTEMENT
   dans le secret `UNITY_LICENSE` via l API GitHub — le PAT est injecté
   UNIQUEMENT dans cette étape, jamais dans l activation.
4. Sans `ACCESS_TOKEN` : échec explicite — AUCUN repli par artefact
   (un .ulf en artefact n est jamais privé sur un dépôt public).
5. Aucune capture ni artefact publié ; en cas d échec, consulter les
   logs du run.

Honnêteté : l activation manuelle Personal via license.unity3d.com n
est pas officiellement prise en charge par Unity (option masquée) ;
l outil sélectionne cette option masquée — l authentification complète
(mot de passe + TOTP) reste TOUJOURS requise, aucune protection de
compte n est contournée. Flux prouvé à sa première exécution réelle.
Ne JAMAIS communiquer identifiants, PAT ou licence dans une conversation.

## Ce que ce pipeline NE fait PAS

- Il ne mesure pas les FPS sur Tecno KN3 (aucun appareil réel branché) ;
- il ne remplace pas la validation manuelle sur appareil ;
- il n est pas compté comme « compilée » tant que le run n est pas vert
  AVEC une APK vérifiée en sortie (taille + sha256).
