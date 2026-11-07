# DECLENCHEUR D ACQUISITION DE LICENCE UNITY — OMNI WARSHIPS (T-013.4)

Ce fichier est le BOUTON D ACQUISITION DU .ULF de Lassana : obtenir la
licence Unity Personal SANS PC, SANS Unity Hub, depuis le telephone.

SECURITE (depot public, T-013.4) :
- le .ulf n est JAMAIS publie (ni artefact, ni release, ni commit, ni
  capture) : il va UNIQUEMENT dans le secret UNITY_LICENSE via l API
  GitHub ;
- le PAT ACCESS_TOKEN n est injecte QUE dans l etape de stockage, puis
  efface de la memoire (unset + verification d absence) ;
- les identifiants Unity ne figurent JAMAIS dans les logs : masquage
  GitHub (::add-mask::) + sortie de l outil capturee et FILTREE ;
- TOTP OBLIGATOIRE : si Unity demande une verification par EMAIL,
  arret propre immediat — aucun identifiant transmis, aucune
  recuperation automatique ;
- outils reproductibles : npm ci depuis license-tools/package-lock.json
  (67 paquets, integrite sha512, plus aucun npx/@latest).

## Prerequis (une seule fois)

1. Compte Unity gratuit (id.unity.com) — aucune carte bancaire.
2. Activer le TOTP : id.unity.com > Security > Two-Factor
   Authentication > App d authentification > « Impossible de scanner le
   code ? » -> sauvegarder la cle.
3. Secrets du depot (Settings > Secrets and variables > Actions) :
   - UNITY_EMAIL : adresse du compte Unity ;
   - UNITY_PASSWORD : mot de passe du compte Unity ;
   - UNITY_TOTP_KEY : cle authenticator TOTP (OBLIGATOIRE — sans elle le
     workflow s arrete : le parcours de verification par email est
     neutralise par securite) ;
   - ACCESS_TOKEN : PAT fine-grained (Settings > Developer settings >
     Fine-grained tokens > Generate new token) :
     * Resource owner : blassana280-ux ;
     * Repository access : Only select repositories ->
       omni-agents-framework (RIEN d autre) ;
     * Permissions : Secrets -> Read and write (RIEN d autre ;
       Metadata:read automatique et obligatoire) ;
     * Expiration : 30 jours recommandes.
     Le PAT n est injecte QUE dans l etape de stockage (jamais dans la
     verification ni l activation) et est efface apres usage.

## Lancer l acquisition

1. Ouvrir ce fichier sur GitHub (navigateur mobile), crayon,
   incrementer le compteur ci-dessous, commiter sur
   warships/android-build.

Derniere acquisition demandee : #0 (aucune)

2. Le workflow « Warships licence Unity (activation TOTP sans PC) » :
   - installe l arbre verrouille (npm ci, package-lock 67 paquets,
     integrite sha512) ;
   - genere le fichier de demande .alf (image unityci/editor
     2022.3.62f1-android) ;
   - l echange contre un .ulf via le binaire verrouille
     unity-license-activate 0.3.9 (seul site fonctionnel contacte :
     license.unity3d.com), sortie capturee et filtree, TOTP obligatoire ;
   - stocke le .ulf DIRECTEMENT dans le secret UNITY_LICENSE, verifie
     l horodatage (jamais la valeur), puis efface le PAT de la memoire.
3. Une fois le run vert : lancer le build APK via BUILD-TRIGGER.md.

## Domaines externes contactes par le workflow (exhaustif, T-013.4)

- registry.npmjs.org : les 67 paquets, verifies par integrite ;
- storage.googleapis.com : Chromium (script d installation de
  puppeteer 13.7.0, seul telechargement supplementaire documente) ;
- license.unity3d.com : formulaire d activation Unity ID ;
- api.github.com : stockage du secret UNITY_LICENSE (gh secret set/list) ;
- hub.docker.com : image unityci/editor (generation du .alf).

## Honnetete (aucune simulation)

- Statut : l activation manuelle Personal via license.unity3d.com n est
  PAS officiellement prise en charge par Unity (option masquee) ; l
  outil selectionne cette option masquee — l authentification complete
  (mot de passe + TOTP) reste TOUJOURS requise, aucune protection de
  compte n est contournee. Preuve = premiere execution reelle. Repli :
  Unity Hub sur un PC emprunte.
- Limites documentees : le parcours 2FA email est neutralise (arret
  propre) car l outil y afficherait une commande contenant les
  identifiants ; si Unity modifie son site, le flux peut casser ; les
  licences Personal expirent periodiquement (relancer ce fichier).
- Ne JAMAIS communiquer identifiants, secrets, PAT ou contenu de
  licence dans une conversation : tout passe par les secrets GitHub.
