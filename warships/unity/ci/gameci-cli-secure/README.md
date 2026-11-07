# gameci-cli-secure — CLI game-ci corrige (T-013.9)

## Pourquoi

L audit T-013.9 a constate que le CLI officiel game-ci v0.1.72 (commit
7da0cea2f31799a4cbd79c1d452c254023f4f678) met le mot de passe Unity DANS
la chaine de commande docker :

- src/model/image-environment-factory.ts : getEnvVarString() emet
  `--env UNITY_PASSWORD="valeur"` pour toute valeur sur une ligne ;
- src/model/system/system.ts : System.run() passe la commande entiere a
  `sh -c` — le secret apparait donc dans l ARGV des processus du runner
  (sh ET docker), visible dans un ps / listing de processus.

SecretRedaction protege les LOGS, pas l argv : deux problemes differents.
Aucun fix en amont n etant disponible au tag epingle, ce dossier fournit
un CLI corrige, construit et publie par NOTRE CI.

## Le correctif (minimal et tracable)

patched-src/src/model/image-environment-factory.ts = le fichier du tag
officiel avec UN SEUL changement : une liste credentialEnvNames
(UNITY_EMAIL, UNITY_PASSWORD, UNITY_SERIAL, UNITY_LICENSING_SERVER,
ANDROID_KEYSTORE_PASS, ANDROID_KEYALIAS_PASS, USYM_UPLOAD_AUTH_TOKEN,
PRIVATE_REGISTRY_TOKEN) ajoutee a isInheritedByName. Effet :

- la commande docker ne contient plus que des references sans valeur :
  `--env UNITY_EMAIL`, `--env UNITY_PASSWORD` ;
- les valeurs voyagent par l ENVIRONNEMENT du processus docker
  (getInheritedEnvVars — mecanisme deja utilise par le CLI pour les
  valeurs multilignes), donc jusqu au conteneur.

patched-src/src/model/secure-env.test.ts = les tests prouvant le
correctif (valeurs 100% factices, jamais affichees) : references sans
valeur, valeurs absentes de la chaine, valeurs presentes dans l env
herite, conteneur servi, argv propre, scripts personal intacts.

Le depot officiel game-ci/cli n est PAS modifie. Le fork GitHub etant
bloque pour l integration (scope Administration manquant, 403), la
source epinglee + l overlay commite ici jouent le meme role : le workflow
de release verifie que l overlay touche EXACTEMENT 2 fichiers et que
dist/ (scripts personal du conteneur) reste INTACT octet par octet.

## Chaine de confiance (installation jamais non verifiee)

1. warships-cli-release.yml : checkout game-ci/cli au commit epingle
   (integrite par SHA git) + overlay + tests + build (Bun 1.3.13 epinglee,
   cf release-cli.yml officiel) + archive + checksums.txt.
2. Release publiée : tag gameci-cli-secure-v0.1.72w1 (NON immuable
   selon l API GitHub — un admin peut remplacer l archive : la
   protection est l empreinte ancrée au point 3, toute divergence
   est FATALE), assets archive +
   checksums.txt + T013-9-patch.diff (preuve du correctif) + test.
3. Empreinte ancree dans git : artifact-checksum.txt + BUILD-INFO.txt
   commites par le bot — la divergence entre checksums.txt et l empreinte
   ancree est FATALE a l installation.
4. verify-gameci-cli.sh (STRICT, aucun soft-skip — l installateur
   officiel du CLI poursuit APRES un echec de checksum, lui) : echoue si
   checksums.txt est inaccessible, si l empreinte attendue est absente,
   en cas de divergence, si le binaire installe differe de celui de
   l archive verifiee, ou si les scripts personal (activate.sh
   --include-personal, runsteps.sh trap EXIT, return_license.sh,
   entrypoint.sh) manquent a l appel.
5. test-verify-gameci-cli.sh eprouve les 8 modes d echec + l acceptation
   (fixtures factices).

## Ce que ce dossier ne fait JAMAIS

- aucune activation Unity, aucune connexion, aucun secret reel ;
- ne declenche jamais le build Android (BUILD-TRIGGER.md) ;
- ne modifie ni main ni le depot officiel game-ci.

## Declencher une nouvelle release

Voir RELEASE-TRIGGER.md (bouton de publication, pattern BUILD-TRIGGER).
