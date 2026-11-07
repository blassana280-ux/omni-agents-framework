# DECLENCHEUR DE RELEASE DU CLI CORRIGE — OMNI WARSHIPS (T-013.9)

Ce fichier est le BOUTON DE PUBLICATION du CLI game-ci corrige
(securisation des identifiants Unity). Ne PAS le confondre avec
BUILD-TRIGGER.md (bouton de compilation APK) : ce fichier ne
declenchera JAMAIS le build Android.

## Publier / reconstruire l artefact corrige

1. Ouvrir ce fichier sur GitHub et cliquer sur le crayon (modifier).
2. Incrementer le compteur ci-dessous puis committer directement sur la
   branche warships/android-build.

Derniere release demandee : #1 (premiere demande de publication du CLI corrige)

3. Le workflow « Warships CLI corrige (build + release) » part
   automatiquement : source officielle game-ci/cli EPINGLEE au commit
   7da0cea2f31799a4cbd79c1d452c254023f4f678 + correctif minimal T-013.9
   (heritage ENV de UNITY_EMAIL/UNITY_PASSWORD et des autres identifiants
   sensibles : plus aucun secret dans la chaine de commande passee a
   sh -c, donc plus aucun secret dans l argv des processus du runner),
   tests automatiques a valeurs factices, compilation Bun 1.3.13,
   archive gameci-cli-secure-linux-x64.tar.gz + checksums.txt, release
   IMMUABLE (tag gameci-cli-secure-v0.1.72w1), empreinte ancree dans git
   (artifact-checksum.txt + BUILD-INFO.txt, commit du bot).

## En cas d echec

- Run rouge : lire l annotation du job (page du run GitHub) puis
  re-incrementer le compteur pour relancer.
- AUCUNE activation Unity, AUCUN secret reel dans ce workflow : il ne
  touche jamais Unity ni le build Android.
