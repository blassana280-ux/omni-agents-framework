# DECLENCHEUR DE BUILD ANDROID — OMNI WARSHIPS (T-013.10)

Ce fichier est le BOUTON DE COMPILATION de Lassana : sans PC, sans main,
depuis le navigateur du telephone.

## Lancer un build APK

1. Verifier les secrets du depot (Settings > Secrets and variables >
   Actions) : UNITY_EMAIL, UNITY_PASSWORD (compte Unity GRATUIT
   Personal DEDIE au CI, avec 2FA DESACTIVEE sur ce compte dedie
   UNIQUEMENT — JAMAIS le compte principal de Lassana, dont la 2FA
   reste activee). Plus de secret de licence : le build demande un siege
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
   d echec), compilation (image docker
   unityci/editor:ubuntu-2022.3.62f1-android-3 — nom EXACT T-013.13 :
   prefix ubuntu, version 2022.3.62f1 du projet, plateforme android,
   suffixe rolling 3 par defaut du CLI ; tag actif sur Docker Hub,
   verifie 07/11/2026), verification de l APK (taille + sha256),
   upload en artefact et release brouillon.
5. Une fois le run vert : APK telechargeable via l artefact
   omni-warships-apk ou la release brouillon android-build-N. ATTENTION
   (T-013.13) : un run VERT ne prouve PAS que le siege a ete rendu —
   voir l avertissement ci-dessous.

## En cas d echec

- « secret ... absent ou vide » : renseigner UNITY_EMAIL /
   UNITY_PASSWORD puis re-modifier ce fichier (incrementer le
   compteur) pour relancer.
- Defi 2FA ou verification d appareil : la 2FA ne peut etre DESACTIVEE
   QUE sur le COMPTE CI DEDIE — JAMAIS sur le compte principal de Lassana
   (l activation headless ne peut repondre a aucun defi 2FA).
   Verifier le compte CI dedie puis relancer.
- « no available seats » : un siege precedent n a pas ete rendu —
   patienter (sieges limites) puis relancer ; voir aussi
   « Recuperation du siege » ci-dessous.
- « checksum MISMATCH » ou empreinte absente/divergente
   (verify-gameci-cli.sh) : l archive de la release ne correspond PLUS
   a l empreinte ancree dans git — NE PAS relancer le build ; verifier
   la release gameci-cli-secure-v0.1.72w1 et republier le CLI corrige
   via RELEASE-TRIGGER.md (gameci-cli-secure).
- Run rouge sur le commit d integration : ATTENDU si les secrets ne
   sont pas encore configures — la verification s arrete AVANT toute
   installation CLI et toute compilation Unity.

## AVERTISSEMENT (T-013.13) : une restitution echouee laisse le job VERT

La restitution du siege Personal (trap EXIT de runsteps.sh) est
best-effort : si elle echoue, le job reste VERT avec seulement un
warning « Failed to return the Personal license seat ... Release it
at https://id.unity.com or run 'game-ci return-license' ». Apres
CHAQUE build, ouvrir les logs et verifier que le siege a bien ete
rendu, meme si le run est vert — sinon le build suivant echouera sur
« no available seats ».

## SIGKILL / timeout : le siege peut rester retenu (T-013.13)

runsteps.sh n arme QUE le trap EXIT (aucun trap INT/TERM). Un signal
fatal non pige ou un arret brutal ne declenche AUCUNE restitution :
timeout du job (timeout-minutes: 90 dans warships-gameci.yml —
verifie T-013.13, c est le delai applicable a NOTRE pipeline),
SIGKILL de docker, panne du runner. Le siege Personal peut alors
rester actif cote Unity, sans AUCUNE trace dans les logs du run.

### Recuperation du siege

1. Navigateur du telephone : https://id.unity.com > Preferences >
   Seats : liberer le siege encore actif du compte CI dedie.
2. Ou depuis un PC : game-ci return-license (CLI corrige).
3. Patienter quelques minutes puis relancer le build (incrementer le
   compteur ci-dessus).
