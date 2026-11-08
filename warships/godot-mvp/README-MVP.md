# OMNI WARSHIPS — MVP Android (Godot 4)

Mission OW-APK-MVP-001 : premier jeu 3D naval jouable, hors ligne, APK ARM64
pour Tecno KN3 (Android 15, 4 Go RAM). Projet autonome — le projet Unity
existant (warships/unity) n est ni modifie ni supprime.

## Decisions techniques (documentees)

- **Godot 4.7.2 + GDScript** : licence MIT, aucun compte, aucune activation,
  aucune dependance a une licence incertaine (contrairement a Unity Personal
  headless). Compilation APK 100 % gratuite et reproductible en CI.
- **Pipeline epingle** (pas d image Docker tierce) : binaire officiel
  godotengine/godot-builds 4.7.2-stable + JDK 17 + Android SDK
  (build-tools 35.0.1, platforms android-35 — exigences officielles Godot 4.7).
- **ARM64 uniquement** (architectures/arm64-v8a), APK leger, minSdk/Android 15 OK.
- **Signature release ephemere** generee dans le runner par keytool (variables
  GODOT_ANDROID_KEYSTORE_RELEASE_*) : aucun secret dans le depot, aucune
  configuration demandee. Limite : la cle change a chaque build — desinstaller
  l ancienne APK avant d installer une nouvelle (Android refuse le update
  signe differemment).
- **Aucun asset externe** : destroyer procedurale (primitives), ocean/ciel
  proceduraux. Aucune ressource piratee ou sans licence, aucun reseau, aucune
  publicite, aucun compte — 100 % hors ligne.
- Noyau de simulation pur (scripts/war_sim.gd) teste en CI par 10 tests
  headless deterministes (godot --headless -s tests/test_core.gd).

## Controles (ecran tactile)

- Glisser a GAUCHE de l ecran : barre (cap du destroyer).
- Bouton TIR (bas droite) : tire avec anticipation de la cible.
- Bouton AVANCE/STOP : regime moteur.
- Bouton II (haut) : pause. But : couler l ennemi avant d etre coule.

## Compilation (GitHub Actions)

Workflow : .github/workflows/warships-godot-mvp.yml (branche warships/android-mvp).
Chaque push sur warships/godot-mvp/** produit : import headless, tests,
export APK ARM64, verification reelle (taille, sha256, aapt dump badging :
arm64-v8a + targetSdk >= 24), artefact + release godot-mvp-v0.1.0.

## Installation sur Android (Tecno KN3)

1. Telecharger l APK depuis la release GitHub (godot-mvp-v0.1.0) ou l artefact
   de la derniere run CI, puis l ouvrir.
2. Autoriser l installation d applications inconnues pour le navigateur
   quand Android le demande (Parametres > Securite).
3. Installer. Si une version precedente (signature differente) existe deja :
   la DESINSTALLER d abord.
4. Jouer — aucune connexion requise a aucune etape.

## Limites connues (honetete)

- Aucun test sur appareil reel n a ete execute par les agents (aucun Tecno
  KN3 accessible) : l installation, le lancement, la fluidite 30 FPS et les
  commandes tactiles restent a verifier par Lassana sur le telephone.
- Visuels volontairement minimalistes (primitives 3D), pas de son.
- IA simple, un seul ennemi, pas de minimap (perimetre MVP).
- L APK est signee par une cle ephemere de CI : reservee au test, jamais
  publiee sur un store.
