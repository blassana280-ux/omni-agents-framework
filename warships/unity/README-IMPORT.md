# OMNI WARSHIPS — projet Unity (URP) : premiere bataille jouable 3D

Projet Unity **reel** : couche de presentation reliee au noyau deterministe
` warships/core/OmniWarships.Core` (copie exacte, verifiee octet par octet en CI).
La logique de jeu (mouvement, balistique, degats, capteurs, IA, naufrages)
vit dans le noyau C# ; ce projet n'est que du rendu, de l'audio-visuel et de l'input.

## Statut honnete (l'assistant n'a ni Unity ni SDK Android dans son bac a sable)

| Element | Statut |
|---|---|
| Fichiers du projet Unity (scripts, shaders, asmdef, configs) | implémentés (code écrit, poussés sur la branche) |
| Validateurs CI (structure + copies exactes noyau/specs) | exécutés en CI a chaque push |
| Compilation Unity des scripts/shaders | NON verifiee ici — requiere Unity 2022.3 LTS |
| APK / AAB | NON produit ici — see Build Android ci-dessous |
| FPS sur Tecno KN3 | NON mesure — aucun appareil reel disponible ici |

## Ouverture du projet

1. Installer **Unity 2022.3 LTS** (2022.3.62f1 ou plus recent) + modules Android Build Support (SDK/NDK) + OpenJDK.
2. Ouvrir le dossier ` warships/unity` comme projet Unity (Unity Hub > Add > Open).
3. Attendre l'import (premiere fois : generation des .meta et Library/).
4. Menu **Omni Warships > Configurer le pipeline URP** (cree et assigne l'asset URP + le renderer).
   En cas d'echec : Assets > Create > Rendering > URP Asset (with Universal Renderer), puis
   Project Settings > Graphics > assigner l'asset cree.
5. Menu **Omni Warships > Creer la scene Bataille** (cree Assets/OmniWarships/Battle.unity).
6. **Play** : la bataille s'auto-construit (destroyer joueur vs frégate IA), meme depuis une scene vide.

Controles : tactile (joystick bas-gauche, boutons d'armes bas-droite, glisser = camera,
pincer = zoom) ; clavier en edition (Z/S ou fleches = gaz/derapage, Q/D = barre,
Espace = canon, X = missiles, C = torpilles, Tab = changer de cible).

## Build Android

1. File > Build Settings > Android > Switch Platform.
2. Texture compression : ASTC. Resolution : 1920x1080 ou moins.
3. Player Settings : orientation Landscape, Minimum API 24, Target API 35 (Android 15),
   Scripting Backend IL2CPP, ARM64 seul (Tecno KN3).
4. Build (APK ou AAB). Puis installer et mesurer les FPS reels (le HUD affiche les FPS).
   Aucune licence payante n'est requise pour ce flux (Unity Personal inclut Android).

## Architecture

```
Assets/OmniWarships/
  OmniWarships.Core.asmdef      noyau deterministe, zero reference Unity
  Core/                         copie EXACTE de warships/core/OmniWarships.Core (CI la verifie)
  OmniWarships.Unity.asmdef     couche presentation
  Scripts/                      BattleBootstrap (auto-construction), BattleDirector (pas fixe 1/30),
                                ShipView (coque parametrique), OceanController (Gerstner shader),
                                WarshipCamera, TouchInputController, HudController (OnGUI),
                                ProjectileView, EffectsPool, QualityProfiles, SpecSource
  Shaders/                      OmniOcean (houle Gerstner 4 composantes + ecume + speculaire),
                                OmniFlash (additif explosions), OmniSmoke (fumee alpha)
  Editor/                       menu Omni Warships (URP, scene, verification specs)
  Resources/Ships/              copie EXACTE des 7 specs .ship.txt (CI la verifie)
```

Convention de passage noyau > monde : position noyau (X, Y) = monde Unity (X, Z) ;
cap 0 deg = +Z (nord) ; rotation = Quaternion.Euler(0, cap, 0). Les vagues C++
et le shader utilisent la MEME formule (OceanModel.HeightAt dupliquee dans le
shader pour le GPU ; la flottabilite des navires reste au CPU, source unique).

## Qualite graphique

Profils in-game (bouton HUD haut-gauche) : Ultra / Eleve / Moyen / Faible / Adaptatif
(resolution ocean 128-48 segments, ombres, renderScale URP, effets). Adaptatif
surveille le temps de frame et descend/monte automatiquement. Le HUD affiche
les FPS mesures sur l'appareil — aucune performance n'estdeclaree sans mesure.

## Mode hors ligne

Aucune dependance reseau : specs embarquees (Resources), simulation locale,
pas d'API distante, pas d'analytique. Replay deterministe JSONL via le noyau
(ReplayRecorder) — bataille rejouable a l'identique.

## CI

Le job ` Couche Unity` (workflow warships-ci.yml) execute
` python3 warships/tools/omni-unity-bridge/validate_unity_layer.py` :
presence des fichiers requis, validite JSON (manifest/asmdef), references
d'assemblies, egalite OCTET PAR OCTET des copies noyau et specs, equilibre
des accolades C#, absence de secrets. La COMPILATION Unity reste hors CI
(Unity non installe sur les runners ; game-ci possible en Phase 8 si Lassana
l'autorise — necessite une licence Unity).
