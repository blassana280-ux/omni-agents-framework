# DECLENCHEUR DE VERIFICATION DES SECRETS UNITY — OMNI WARSHIPS (T-013.7)

Ce fichier est le BOUTON DE VERIFICATION de Lassana : verifier que les
secrets de la methode personal sont prets, SANS PC, depuis le telephone.

IMPORTANT (T-013.7) : ce workflow ne declenche AUCUNE activation et ne
produit AUCUN fichier de licence. Unity a supprime l activation
manuelle des licences Personal (le portail d activation hors-ligne est
reserve aux sieges Enterprise et Industry) : l ancien flux d
acquisition de fichier de licence (.alf puis .ulf, T-013.2 a T-013.5,
avec outillage npm et navigateur de 2022) est RETIRE du depot. Methode
actuelle : le build lui-meme (BUILD-TRIGGER.md) demande un siege
Personal PAR IDENTIFIANTS dans son conteneur (unity-builder v4) — le
siege est obtenu et rendu automatiquement pendant le build.

## Prerequis (une seule fois)

1. Compte Unity GRATUIT Personal (id.unity.com) — aucune carte
   bancaire. Compte DEDIE au CI recommande (jamais le compte
   principal).
2. DESACTIVER la 2FA sur ce compte : id.unity.com > Security >
   Two-Factor Authentication. L activation headless ne peut repondre
   a AUCUN defi 2FA ni verification d appareil — avec la 2FA activee,
   le build echouera proprement.
3. Secrets du depot (Settings > Secrets and variables > Actions) :
   - UNITY_EMAIL : adresse du compte Unity ;
   - UNITY_PASSWORD : mot de passe du compte Unity.
   Ce sont les DEUX seuls secrets requis (plus de fichier de licence,
   plus de TOTP, plus de PAT).

## Lancer la verification

1. Ouvrir ce fichier sur GitHub (navigateur mobile), crayon,
   incrementer le compteur ci-dessous, commiter sur
   warships/android-build.

Derniere verification demandee : #0 (aucune)

2. Le workflow « Warships licence Unity (verification des secrets,
   aucune activation) » verifie que les secrets sont presents et
   propres (sans espaces parasites autour), SANS jamais les afficher,
   SANS contacter Unity, SANS produire le moindre fichier ; nettoyage
   du runner toujours execute (if: always()).
3. Une fois le run vert : lancer le build APK via BUILD-TRIGGER.md —
   c est le build qui obtient le siege Personal (methode personal par
   identifiants, dans son conteneur) puis le rend a la fin.

## Honnetete (aucune simulation)

- Le mecanisme (siege Personal par identifiants, sans PC, sans fichier
  de licence) est prouve par le code source des scripts d activation
  game-ci et leurs mesures publiques (Unity 2022.3.62f3, voisin de
  notre 2022.3.62f1) ; l obtention REELLE ne sera prouvee que par le
  premier run reel du build avec vos identifiants.
- Un siege Personal est TENU jusqu a restitution : le build le rend
  automatiquement a la fin (meme en cas d echec). En cas de message
  « no available seats », patienter (sieges limites) puis relancer.
- Ne JAMAIS communiquer identifiants ou contenu de licence dans une
  conversation : tout passe par les secrets GitHub. La licence MIT de
  game-ci n est pas une licence Unity.
