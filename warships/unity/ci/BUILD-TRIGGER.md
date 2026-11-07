# DECLENCHEUR DE BUILD ANDROID — OMNI WARSHIPS (T-013.8)

Ce fichier est le BOUTON DE COMPILATION de Lassana : sans PC, sans main,
depuis le navigateur du telephone.

## Lancer un build APK

1. Verifier les secrets du depot (Settings > Secrets and variables >
   Actions) : UNITY_EMAIL, UNITY_PASSWORD (compte Unity GRATUIT
   Personal DEDIE au CI avec 2FA DESACTIVEE — jamais le compte
   principal). Plus de secret de licence : le build demande un siege
   Personal PAR IDENTIFIANTS dans son conteneur (T-013.7/T-013.8 —
   Unity a supprime l activation manuelle des licences Personal).
2. Ouvrir ce fichier sur GitHub (navigateur mobile) et cliquer sur le
   crayon (modifier).
3. Incrementer le compteur ci-dessous puis Commiter directement sur la
   branche warships/android-build.

Dernier build demande : #0 (aucun)

4. Le workflow « Warships GameCI (APK Android) » part automatiquement :
   le declenchement par push est limite a CE fichier — aucune
   compilation inutile lors des modifications sans rapport avec le
   jeu. Le build verifie les secrets, installe GameCI CLI v0.1.72
   (installateur officiel du depot game-ci/cli, epingle au tag,
   checksum sha256 verifie), puis UNE SEULE commande de build fait
   tout dans UN SEUL conteneur : siege Personal par identifiants
   (rendu automatiquement par trap EXIT, meme en cas d echec),
   compilation (image unityci/editor 2022.3.62f1-android),
   verification de l APK (taille + sha256), upload en artefact et
   release brouillon.
5. Une fois le run vert : APK telechargeable via l artefact
   omni-warships-apk ou la release brouillon android-build-N.

## En cas d echec

- « secret ... absent ou vide » : renseigner UNITY_EMAIL /
   UNITY_PASSWORD puis re-modifier ce fichier (incrementer le
   compteur) pour relancer.
- Defi 2FA ou verification d appareil : DESACTIVER la 2FA du compte
   Unity (l activation headless ne peut y repondre), puis relancer.
- « no available seats » : un siege precedent n a pas ete rendu —
   patienter (sieges limites) puis relancer.
- Run rouge sur le commit d integration : ATTENDU si les secrets ne
   sont pas encore configures — la verification s arrete AVANT toute
   compilation Unity.
