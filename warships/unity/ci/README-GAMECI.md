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

## Licence Unity sans PC (T-013.4 + T-013.5 — workflow durci, installation maitrisee)

La documentation officielle actuelle de game.ci recommande Unity Hub sur
un PC — Lassana n en a pas. Le workflow
`.github/workflows/warships-license.yml` (déclenché par
`warships/unity/ci/LICENSE-TRIGGER.md`) permet d obtenir le .ulf
ENTIÈREMENT depuis le téléphone, SANS JAMAIS publier le .ulf (dépôt
public) et SANS JAMAIS exposer les identifiants :

1. Compte Unity gratuit (id.unity.com) + TOTP activé.
2. Secrets : `UNITY_EMAIL`, `UNITY_PASSWORD`, `UNITY_TOTP_KEY`
   (OBLIGATOIRE — le parcours de vérification par email est neutralisé :
   si Unity le présente, arrêt propre, aucun identifiant transmis, aucune
   récupération automatique) et `ACCESS_TOKEN` (PAT fine-grained limité
   à CE dépôt, permission « Secrets » en lecture/écriture seule,
   expiration ~30 jours — cf. LICENSE-TRIGGER.md).
3. Modifier `LICENSE-TRIGGER.md` : le workflow installe l arbre
   VERROUILLÉ (`npm ci --ignore-scripts` depuis `license-tools/package-lock.json`, 67
   paquets, intégrité sha512 — plus aucun `npx --yes` ni `@latest`),
   génère le .alf (image unityci/editor, drapeau documenté
   -createManualActivationFile), l échange contre un .ulf via le binaire
   de l arbre verrouillé (unity-license-activate 0.3.9, seul site
   fonctionnel : license.unity3d.com), avec sortie CAPTURÉE et FILTRÉE
   + masquage GitHub (`::add-mask::`) — aucun identifiant dans les
   logs, même en cas d erreur.
4. Stockage DIRECT du .ulf dans le secret `UNITY_LICENSE` via l API
   GitHub : le PAT est injecté UNIQUEMENT dans cette étape, puis effacé
   de la mémoire (`unset` + vérification d absence). Sans
   `ACCESS_TOKEN` : échec explicite — AUCUN repli par artefact.
5. Aucune capture ni artefact publié ; fichiers d erreur de l outil
   supprimés (error.png / error.html) ; en cas d échec, consulter les
   logs filtrés.

Honnêteté : méthode réelle mais NON officiellement prise en charge
(option Personal masquée) ; authentification complète toujours requise ;
prouvée à sa première exécution réelle. Ne JAMAIS communiquer
identifiants, PAT ou licence dans une conversation.

## T-013.5 — installation réellement maitrisee (audit 67/67)

- Les DEUX workflows (licence et CI) installent avec `npm ci
  --ignore-scripts` : aucun script d installation tiers ne s exécute.
  Audit réel des 67 paquets du lock : EXACTEMENT 3 scripts déclarés
  (puppeteer install.js, bufferutil et utf-8-validate node-gyp-build)
  — tous bloqués, aucune compilation native, aucun téléchargement
  pendant l installation.
- Chromium est installé séparément par curl depuis l URL ÉPINGLÉE
  https://storage.googleapis.com/chromium-browser-snapshots/Linux_x64/982053/chrome-linux.zip
  (révision 982053 = Chromium 101.0.4951.64) ; sha256 consigné dans
  les logs, version vérifiée à l exécution, résolution Puppeteer
  vérifiée (executablePath) — l activation fonctionne sans exécuter
  un seul script npm.
- Domaines autorisés (liste blanche structurelle dans le validateur) :
  registry.npmjs.org, storage.googleapis.com (URL épinglée),
  license.unity3d.com, api.github.com, hub.docker.com.
- Nettoyage final du runner (if: always(), même en cas d échec) : log
  d activation, masques, zip Chromium, shim anti-email, .alf/.ulf et
  captures supprimés.

## Ce que ce pipeline NE fait PAS

- Il ne mesure pas les FPS sur Tecno KN3 (aucun appareil réel branché) ;
- il ne remplace pas la validation manuelle sur appareil ;
- il n est pas compté comme « compilée » tant que le run n est pas vert
  AVEC une APK vérifiée en sortie (taille + sha256).
