# Pipeline de compilation Unity (GameCI) — PRÉPARÉ, INACTIF, VÉRIFIÉ

Statut honnête : **préparé, vérifié, non activé**. Le workflow réel existe
déjà (`.github/workflows/warships-gameci.yml`) mais ne s'exécute QUE sur
déclenchement manuel (workflow_dispatch) par Lassana. Le fichier
`gameci-example.yml` de ce dossier est la référence documentaire, alignée
en T-013.1 sur le workflow réel.

## Corrections T-013.1 (audit externe)

- Inputs vérifiées contre le action.yml RÉEL de game-ci/unity-builder@v4 :
  `androidExportType: androidPackage` (APK) ; `androidBuildAppType`,
  `androidBuildSystem` et `androidArchitecture` N'EXISTENT PAS en v4.
  ARM64 et IL2CPP sont réglés par le projet (AndroidBuildConfig.Configure).
- Expressions `${{ }}` propres (backslashs parasites supprimés sur les
  secrets et github.run_number) ; `permissions: contents: write` pour la
  release brouillon ; secrets vérifiés sans jamais être affichés ;
  APK vérifiée (taille + sha256) avant artefact et release.
- Build via `buildMethod` explicite :
  `OmniWarships.Unity.EditorTools.WarshipsBuildScript.BuildAndroid` —
  la scène de bataille (Assets/OmniWarships/Battle.unity) est incluse
  EXPLICITEMENT dans BuildPlayerOptions.scenes via BattleSceneGuard ;
  tout échec sort avec EditorApplication.Exit(1).

## Activation (décision de Lassana)

1. Renseigner les secrets du dépôt : UNITY_LICENSE (contenu du fichier
   .ulf), UNITY_EMAIL, UNITY_PASSWORD — sans espaces parasites autour.
2. Onglet Actions → « Warships GameCI (APK Android — activation
   manuelle) » → Run workflow.
3. Le job build-android : vérifie les secrets, compile (image Docker
   unityci/editor 2022.3.62f1-android), produit
   warships/unity/Builds/omni-warships-v0.1.0.apk, vérifie l'APK
   (taille + sha256), l'uploade en artefact et crée une release
   brouillon.

## Ce que ce pipeline NE fait PAS

- Il ne mesure pas les FPS sur Tecno KN3 (aucun appareil réel branché) ;
- il ne remplace pas la validation manuelle sur appareil ;
- il n'est pas compté comme « compilée » tant que le run n'est pas vert
  AVEC une APK vérifiée en sortie.

## Pourquoi l'inactivité

La licence Unity personnelle gratuite couvre ce dépôt, mais son activation
dans une CI exige des secrets et une acceptation explicite de Lassana.
Rien n'est activé sans son accord — règle du projet.

