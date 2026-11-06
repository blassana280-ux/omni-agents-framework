# DECLENCHEUR DE BUILD ANDROID — OMNI WARSHIPS (T-013.2)

Ce fichier est le BOUTON DE COMPILATION de Lassana : sans PC, sans main,
depuis le navigateur du telephone.

## Lancer un build APK

1. Verifier les secrets du depot (Settings > Secrets and variables >
   Actions) : UNITY_LICENSE, UNITY_EMAIL, UNITY_PASSWORD.
2. Ouvrir ce fichier sur GitHub (navigateur mobile) et cliquer sur le
   crayon (modifier).
3. Incrementer le compteur ci-dessous puis Commiter directement sur la
   branche warships/android-build.

Dernier build demande : #0 (aucun)

4. Le workflow « Warships GameCI (APK Android) » part automatiquement :
   le declenchement par push est limite a CE fichier — aucune compilation
   inutile lors des modifications sans rapport avec le jeu.
5. Une fois le run vert : APK telechargeable via l artefact
   omni-warships-apk ou la release brouillon android-build-N.

## En cas d echec

- « secret ... absent ou vide » : renseigner les secrets puis
  re-modifier ce fichier (incrementer le compteur) pour relancer.
- Run rouge sur le commit d integration de T-013.2 : ATTENDU — les
  secrets n etaient pas encore configures, la verification s arrete
  AVANT toute compilation Unity.
