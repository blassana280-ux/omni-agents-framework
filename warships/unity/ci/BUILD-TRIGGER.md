# DECLENCHEUR DE BUILD ANDROID — OMNI WARSHIPS (T-013.10)

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
   jeu. Le build verifie les secrets, puis installe le CLI CORRIGE
   T-013.9 UNIQUEMENT par verify-gameci-cli.sh depuis la release
   gameci-cli-secure-v0.1.72w1 (empreinte sha256 ANCRE DANS GIT via
   artifact-checksum.txt ; checksum STRICT : tout remplacement de
   l archive est FATAL. T-013.10 : l API GitHub declare cette release
   non immuable (immutable: false) — la protection reelle est
   l empreinte ancree dans git ; identifiants transmis par ENV herite,
   jamais dans l argv des processus du runner). Puis UNE SEULE commande
   de build fait tout dans UN SEUL conteneur : siege Personal par
   identifiants (rendu automatiquement par trap EXIT, meme en cas
   d echec), compilation (image unityci/editor 2022.3.62f1-android),
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
- « checksum MISMATCH » ou empreinte absente/divergente
   (verify-gameci-cli.sh) : l archive de la release ne correspond PLUS
   a l empreinte ancree dans git — NE PAS relancer le build ; verifier
   la release gameci-cli-secure-v0.1.72w1 et republier le CLI corrige
   via RELEASE-TRIGGER.md (gameci-cli-secure).
- Run rouge sur le commit d integration : ATTENDU si les secrets ne
   sont pas encore configures — la verification s arrete AVANT toute
   installation CLI et toute compilation Unity.
