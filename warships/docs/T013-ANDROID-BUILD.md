# T-013 — Première APK Android réellement jouable : audit, production d'assets, chemins de compilation

Date : 06/11/2026. Branche : warships/android-build (empilée sur warships/unity-3d), PR #16.

## 1. Audit des PR #13 / #14 / #15 (réel, lecture croisée du code)

Méthode : chaque référence croisée des scripts T-012 a été vérifiée contre le
code réellement présent dans le dépôt (lecture des fichiers, pas de mémoire).

Conclusions :
- **API confirmées conformes** : BattleDirector (Sim, PlayerShip, Views,
  ViewOf, Input, Effects, Cam, Restart, OnSimTicked, Outcome), EffectsPool
  (Explosion/Splash/MuzzleFlash/Smoke/QuadMesh), ShipView (State, Spec,
  BowWorldPos, MarkDamage, BeginSink, MakeFlashMaterial), QualityProfiles,
  TouchInputController (BuildCommand, CurrentTargetId), noyau (Projectile,
  CompartmentState, WeaponKind.Rocket, OceanModel.HeightAt, Intercept).
- **1 bug critique trouvé et corrigé** : parse_args_after_dashes() avait un
  parseur argparse VIDE — args.out aurait levé AttributeError et fait
  échouer les générateurs au premier appel réel (commit 784e613e).
- **1 bug réel corrigé grâce à l'exécution CI** : gen_aircraft_blender.py
  appelait add_cone sans l'argument r2 (TypeError) — révélé par le
  traceback CI, corrigé (commit 7e1aa424). Le validateur (py_compile) ne
  pouvait pas l'attraper : preuve que le validateur n'est pas une compilation.
- Limite cosmétique (non bloquante) : le bouton PAUSE peut démarrer une
  orbite caméra d'un frame.

## 2. Production RÉELLE des FBX — FAITE (Blender 4.2.3 LTS en CI)

Workflow .github/workflows/warships-blender-fbx.yml. Historique honnête des
runs (chaque échec corrigé puis re-testé) :
1. ref checkout invalide (backslash parasite) — corrigé (bb8ed144) ;
2. chemins relatifs faux + blender renvoie exit 0 malgré une erreur
   Python — corrigés (1a3427a9) ;
3. apt-get install blender > 20 min sur l'image Ubuntu 26 (timeout 25 min)
   — remplacé par Blender portable 4.2.3 LTS téléchargé directement
   (0b2288d7) ;
4. traceback du générateur aéronefs révélé par l'annotation CI — corrigé
   (7e1aa424) ;
5. **RUN VERT (38 s)** : run 42282487303 — les 6 générateurs exécutés,
   FBX vérifiés (tailles réelles), committés par le bot (9c1db33a) et
   publiés en artefact omni-warships-fbx (FBX + logs).

FBX réellement produits (tailles vérifiées dans le dépôt, commit 9c1db33a) :

| Fichier | Taille (octets) |
|---|---|
| ws-destroyer-01.fbx | 2 404 572 |
| ws-frigate-01.fbx | 2 278 988 |
| ws-carrier-01.fbx | 2 255 020 |
| ws-submarine-01.fbx | 343 676 |
| ws-aircraft.fbx | 502 428 |
| ws-equipment.fbx | 354 524 |
| **Total** | **8 139 208 (≈ 8,1 Mo)** |

Intégration : warships/unity/Assets/OmniWarships/Resources/Models/ — chargés
au runtime par ShipModelLibrary (LOD 0/1/2 nommés _LOD1/_LOD2, pivots
tourelles/radars/rotors exportés comme EMPTY).

## 3. Mission « première bataille jouable » — correspondance code réel

| Exigence | Implémentation (déjà en place, audité) |
|---|---|
| Destroyer contrôlable | BattleBootstrap/BattleConfig : joueur = ws-destroyer-01, équipe blue |
| Ennemi IA | ws-frigate-01, équipe red, IsAi=true (TacticalAI décide à chaque tick) |
| Océan 3D + environnement | OceanController + shader OmniOcean (même formule Gerstner/graine que le noyau) ; WeatherDirector (jour/nuit, météo, pluie, éclairs) |
| Radar et ciblage | SensorModel (noyau) + HUD radar + TouchInputController.CycleTarget |
| Canons + missiles fonctionnels | BuildCommand → BattleSim.TryFire (obus balistique exact, SSM guidage PN, torpilles armées) |
| Impacts et dégâts visibles | Explosion + MarkDamage + ShipDamageVisuals (fumées, écume voie d'eau) |
| Destruction et naufrage | Sunk → BeginSink + Explosion |
| Victoire / défaite | BattleDirector.UpdateOutcome + messages HUD |
| Pause et reprise | PauseMenu (timeScale 0 + noyau arrêté proprement) |
| Commandes tactiles Android | TouchInputController (joystick, boutons d'armes, orbite, pincer) |
| Solo hors ligne | Aucune dépendance réseau ; specs embarquées Resources/Ships |

## 4. Optimisation Android (Tecno KN3, 4 Go RAM)

5 profils (QualityProfiles) : Ultra / Élevé / Moyen / Faible / Adaptatif
(segments océan 128→48, ombres, renderScale 1.00→0.75, effets on/off).
Mesures FPS : exigent l'APK + l'appareil réel. **Aucun chiffre FPS n'est
annoncé sans mesure.**

## 5. Compilation Unity et APK — deux chemins prêts, un blocage : la licence

- **Chemin A (local, gratuit)** : Lassana ouvre warships/unity dans
  Unity 2022.3 (licence personnelle gratuite), menu « OMNI WARSHIPS →
  Android → 1. Preparer le build KN3 » puis « 2. Compiler l'APK »
  (AndroidBuildConfig.cs : identifiant ml.bah.omniwarships, ARM64, IL2CPP,
  paysage verrouillé, Gradle APK, minSdk 24). L'APK sort dans
  Builds/omni-warships-v0.1.0.apk.
- **Chemin B (cloud, GameCI)** : .github/workflows/warships-gameci.yml —
  activation manuelle (workflow_dispatch). Prérequis : secrets
  UNITY_LICENSE / UNITY_EMAIL / UNITY_PASSWORD (licence Unity — l'activation
  exigée par Unity est la seule étape impossible à faire à la place de
  Lassana). Produit l'artefact APK + une release GitHub en brouillon.
- Permissions Android du jeu : **aucune** (hors ligne complet).

## 6. Blocages documentés (honnêtes)

- Aucun Unity/SDK Android dans l'environnement assistant : la compilation
  Unity et l'APK ne peuvent pas être produites ici. Les FBX, eux, sont
  réellement produits en CI (Blender GPL, section 2).
- Licence Unity : indispensable pour tout build (locale ou cloud).
  Décision et activation = Lassana (un clic en local + 3 secrets pour GameCI).
- FPS Tecno KN3 : à mesurer après installation de l'APK réelle.
