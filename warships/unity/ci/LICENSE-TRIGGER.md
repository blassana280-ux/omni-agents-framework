# DECLENCHEUR D ACQUISITION DE LICENCE UNITY — OMNI WARSHIPS (T-013.3)

Ce fichier est le BOUTON D ACQUISITION DU .ULF de Lassana : obtenir la
licence Unity Personal SANS PC, SANS Unity Hub, depuis le telephone.

SECURITE (depot public) : le .ulf n est JAMAIS publie — ni artefact,
ni release, ni commit, ni capture. Il va UNIQUEMENT dans le secret
UNITY_LICENSE via l API GitHub. Aucune valeur n est affichee dans les
logs.

## Prerequis (une seule fois)

1. Creer un compte Unity gratuit (id.unity.com) depuis le navigateur —
   aucune carte bancaire.
2. Secrets du depot (Settings > Secrets and variables > Actions) :
   - UNITY_EMAIL : adresse du compte Unity ;
   - UNITY_PASSWORD : mot de passe du compte Unity ;
   - UNITY_TOTP_KEY (fortement recommande) : cle authenticator TOTP
     (id.unity.com > Security > Two-Factor Authentication > App
     d authentification > « Impossible de scanner le code ? » ->
     sauvegarder la cle). Sans TOTP, Unity peut exiger un code envoye
     par email que le workflow ne peut pas lire — l acquisition
     echouerait ;
   - ACCESS_TOKEN (OBLIGATOIRE — T-013.3) : PAT fine-grained
     (Settings > Developer settings > Fine-grained tokens > Generate
     new token) :
     * Resource owner : blassana280-ux ;
     * Repository access : Only select repositories ->
       omni-agents-framework (RIEN d autre) ;
     * Permissions : Secrets -> Read and write (RIEN d autre ;
       Metadata:read est automatique et obligatoire) ;
     * Expiration : 30 jours recommandes (renouvelable en 2 clics).
     Le PAT n est injecte QUE dans l etape de stockage du secret —
     absent de l etape d activation, qui ne voit que les identifiants
     Unity. Sans ACCESS_TOKEN : arret explicite du workflow, AUCUN
     repli par artefact (un .ulf en artefact n est jamais prive sur un
     depot public).

## Lancer l acquisition

1. Ouvrir ce fichier sur GitHub (navigateur mobile), cliquer sur le
   crayon, incrementer le compteur ci-dessous, commiter sur
   warships/android-build.

Derniere acquisition demandee : #0 (aucune)

2. Le workflow « Warships licence Unity (acquisition .ulf sans PC) » :
   genere le fichier de demande .alf (image Docker unityci/editor
   2022.3.62f1-android), l echange contre un .ulf via l outil EPINGLE
   unity-license-activate@0.3.9 (organisation game-ci, code audite :
   seul domaine contacte = license.unity3d.com), puis stocke le .ulf
   DIRECTEMENT dans le secret UNITY_LICENSE et verifie la mise a jour
   (horodatage, jamais la valeur).
3. Une fois le run vert : lancer le build APK en editant
   BUILD-TRIGGER.md.

## Honnetete (aucune simulation)

- Statut de la methode : l activation manuelle Personal via
  license.unity3d.com n est PAS officiellement prise en charge par
  Unity (l option y est masquee) ; l outil selectionne cette option
  masquee — l authentification complete (mot de passe + TOTP) reste
  TOUJOURS requise, aucune protection de compte n est contournee.
  Preuve = premiere execution reelle. Si Unity change son site ou
  bloque le flux, repli : Unity Hub sur n importe quel PC emprunte.
- Outil epingle unity-license-activate@0.3.9, integrite verifiee par
  npm a l installation, aucun script d installation dans le package ;
  limite documentee : les dependances transitives (puppeteer,
  crypto-js) sont resolues par npm et non figees.
- Ne JAMAIS communiquer identifiants, secrets, PAT ou contenu de
  licence dans une conversation : tout passe par les secrets GitHub.
