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

## Licence Unity sans PC (T-013.2 — workflow warships-license.yml)

La documentation officielle actuelle de game.ci recommande Unity Hub
sur un PC — Lassana n en a pas. Le workflow
`.github/workflows/warships-license.yml` (déclenché par le fichier
`warships/unity/ci/LICENSE-TRIGGER.md`) permet d obtenir le .ulf
ENTIÈREMENT depuis le téléphone :

1. Compte Unity gratuit (id.unity.com, navigateur).
2. Secrets : `UNITY_EMAIL`, `UNITY_PASSWORD`, et idéalement
   `UNITY_TOTP_KEY` (clé authenticator TOTP — sans elle, Unity peut
   exiger un code envoyé par email que le workflow ne sait pas lire) ;
   `ACCESS_TOKEN` (PAT fine-grained, permission Secrets en écriture)
   pour que le .ulf soit stocké AUTOMATIQUEMENT dans `UNITY_LICENSE`.
3. Modifier `LICENSE-TRIGGER.md` (incrémenter le compteur) : le workflow
   génère le .alf (image Docker unityci/editor, drapeau documenté
   -createManualActivationFile, aucune licence requise), l échange
   contre un .ulf via l outil game-ci `unity-license-activate`
   (navigateur automatisé sur license.unity3d.com), et stocke ou
   publie le .ulf.
4. Sans ACCESS_TOKEN : télécharger l artefact `unity-ulf` et copier TOUT
   son contenu dans le secret `UNITY_LICENSE`.
5. Échec : artefact `screenshot-error` + logs du run.

Honnêteté : ce flux n est pas celui de la documentation officielle
actuelle de game.ci (qui exige Unity Hub) ; il s appuie sur l outil
maintenu de l organisation game-ci. Il ne sera PROUVÉ qu à sa première
exécution réelle — aucun statut n est prétendu avant. Ne JAMAIS
communiquer identifiants, secrets ou licence dans une conversation.

## Ce que ce pipeline NE fait PAS

- Il ne mesure pas les FPS sur Tecno KN3 (aucun appareil réel branché) ;
- il ne remplace pas la validation manuelle sur appareil ;
- il n est pas compté comme « compilée » tant que le run n est pas vert
  AVEC une APK vérifiée en sortie (taille + sha256).
