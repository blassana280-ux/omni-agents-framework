# DECLENCHEUR D ACQUISITION DE LICENCE UNITY — OMNI WARSHIPS (T-013.2)

Ce fichier est le BOUTON D ACQUISITION DU .ULF de Lassana : obtenir la
licence Unity Personal SANS PC, SANS Unity Hub, depuis le telephone.

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
     par email que le workflow ne peut pas lire — l activation
     echouerait ;
   - ACCESS_TOKEN (recommande) : PAT fine-grained (Settings > Developer
     settings > Fine-grained tokens) limite a ce depot avec la
     permission « Secrets » en ecriture — permet au workflow de stocker
     le .ulf DIRECTEMENT dans le secret UNITY_LICENSE. Alternative sans
     PAT : le .ulf est publie en artefact prive « unity-ulf » et il faut
     copier TOUT son contenu dans le secret UNITY_LICENSE a la main.

## Lancer l acquisition

1. Ouvrir ce fichier sur GitHub (navigateur mobile), cliquer sur le
   crayon, incrementer le compteur ci-dessous, commiter sur
   warships/android-build.

Derniere acquisition demandee : #0 (aucune)

2. Le workflow « Warships licence Unity (acquisition .ulf sans PC) » :
   genere le fichier de demande .alf (image Docker unityci/editor
   2022.3.62f1-android), l echange contre un .ulf via l outil game-ci
   unity-license-activate (navigateur automatise sur license.unity3d.com),
   puis stocke ou publie le .ulf.
3. En cas d echec : artefact « screenshot-error » (capture du navigateur
   automatise) + consulter les logs du run.

## Honnetete (aucune simulation)

- La documentation officielle actuelle de game.ci recommande Unity Hub
  sur PC ; Lassana n a pas de PC. Ce flux utilise l outil maintenu
  game-ci/unity-license-activate (organisation game-ci) et le drapeau
  documente Unity -createManualActivationFile dans l image Docker
  officielle unityci/editor. Il ne sera PROUVE qu a sa premiere execution
  reelle — aucun statut n est pretendu avant.
- Ne JAMAIS communiquer identifiants, secrets ou contenu de licence dans
  une conversation : tout passe par les secrets GitHub.
