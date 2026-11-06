# T-013 — Première APK Android réellement jouable : audit, production d'assets, chemins de compilation

Date : 06/11/2026. Branche : `warships/android-build` (empilée sur `warships/unity-3d`), PR #16.

## 1. Audit des PR #13 / #14 / #15 (réel, lecture croisée du code)

Méthode : chaque référence croisée des nouveaux scripts T-012 a été
vérifiée contre le code réellement présent dans le dépôt (lecture des
fichiers, pas de mémoire).

Conclusions :
- **API confirmées conformes** : BattleDirector (Sim, PlayerShip, Views,
  ViewOf, Input, Effects, Cam, Restart, OnSimTicked, Outcome), EffectsPool
  (Explosion/Splash/MuzzleFlash/Smoke/QuadMesh), ShipView (State, Spec,
  BowWorldPos, MarkDamage, BeginSink, MakeFlashMaterial(Color,float)),
  QualityProfiles (Apply/Current/Label/EffectsEnabled), TouchInputController
  (BuildCommand, CurrentTargetId, JoystickVec), noyau (Projectile.Id/Pos/
  Altitude/Kind, CompartmentState.Breached/Flooding/Destroyed, WeaponKind.Rocket,
  OceanModel.HeightAt, BattleEventKind.Intercept avec Detail=projectile).
- **1 bug critique trouvé et corrigé** : `parse_args_after_dashes()`
  construisait un parseur argparse VIDE, donc `args.out` aurait levé
  AttributeError et fait échouer **les 7 générateurs Blender** au premier
  appel réel (commit 784e613e : `--out` désormais déclaré). Ce bug
  était invisible pour le validateur (py_compile valide la syntaxe, pas
  les attributs) — c'est exactement pourquoi le validateur n'est pas une
  compilation.
- Limite connue (cosmétique, non bloquante) : appuyer sur le bouton
  PAUSE peut aussi démarrer une orbite caméra d'un frame (le tactile HUD
  traite tout le reste de l'écran comme un drag caméra).
- Le validateur structurel n'est PAS une compilation Unity : les seules
  preuves de compilation possibles sont (a) un build local Unity par
  Lassana, (b) un run GameCI vert.

## 2. Production RÉELLE des FBX (Blender en CI, licence GPL = zéro blocage)

Workflow `.github/workflows/warships-blender-fbx.yml` : installe
Blender sur le runner GitHub Actions (apt, GPL, aucune licence), exécute
les 7 générateurs, vérifie la taille réelle de chaque FBX (échec si vide
ou < 2 000 octets), puis :
- **commite les FBX dans `Resources/Models/`** → chargés au runtime
  par ShipModelLibrary (LOD 0/1/2, tourelles/radars animés) ;
- publie l'artefact téléchargeable `omni-warships-fbx`.

Échelle de preuve : FBX générés = produire la liste avec tailles réelles
(issue du run CI). Aucun FBX n'est déclaré sans run vert.

## 3. Mission « première bataille jouable » — correspondance code réel

| Exigence | Implémentation (déjà en place, audité) |
|---|---|
| Destroyer contrôlable | BattleBootstrap/BattleConfig : joueur = ws-destroyer-01, équipe blue |
| Ennemi IA | ws-frigate-01, équipe red, IsAi=true (TacticalAI décide à chaque tick) |
| Océan 3D + environnement | OceanController + shader OmniOcean = même formule Gerstner/graine que le noyau ; WeatherDirector (jour/nuit, météo, pluie, éclairs) |
| Radar et ciblage | SensorModel (noyau) + HUD radar + TouchInputController.CycleTarget |
| Canons + missiles fonctionnels | BuildCommand → BattleSim.TryFire (obus balistique exact, SSM guidage PN, torpilles armées) |
| Impacts et dégâts visibles | Explosion + MarkDamage (feux) + ShipDamageVisuals (fumées, écume voie d'eau) |
| Destruction et naufrage | Sunk → BeginSink (animation de naufrage) + Explosion |
| Victoire / défaite | BattleDirector.UpdateOutcome + messages HUD |
| Pause et reprise | PauseMenu (timeScale 0 + noyau arrêté proprement) |
| Commandes tactiles Android | TouchInputController (joystick, boutons d'armes, orbite, pincer) |
| Solo hors ligne | Aucune dépendance réseau ; specs embarquées Resources/Ships |

## 4. Optimisation Android (Tecno KN3, 4 Go RAM)

5 profils (QualityProfiles) : Ultra / Élevé / Moyen / Faible / Adaptatif
(segments océan 128→48, ombres, renderScale 1.00→0.75, effets on/off).
Mesures FPS : exigent l'APK + l'appareil réel (le HUD mesure les FPS
réels). **Aucun chiffre FPS n'est annoncé sans mesure.**

## 5. Compilation Unity et APK — deux chemins, un seul blocage : la licence

- **Chemin A (local, gratuit)** : Lassana ouvre `warships/unity` dans
  Unity 2022.3.62f1 (licence personnelle gratuite), menu
  « OMNI WARSHIPS → Android → 1. Preparer le build KN3 » puis
  « 2. Compiler l'APK » (AndroidBuildConfig.cs : identifiant
  ml.bah.omniwarships, ARM64, IL2CPP, paysage verrouillé, Gradle APK,
  minSdk 24). L'APK sort dans `Builds/omni-warships-v0.1.0.apk`.
- **Chemin B (cloud, GameCI)** : workflow
  `.github/workflows/warships-gameci.yml` — **activation manuelle
  unique** (workflow_dispatch). Prérequis : secrets UNITY_LICENSE /
  UNITY_EMAIL / UNITY_PASSWORD (licence Unity personnelle — l'activation
  exigée par Unity est la seule étape impossible à faire à la place de
  Lassana). Produit l'artefact APK + une release GitHub en brouillon.
- Permissions Android du jeu : **aucune** (hors ligne complet — ni
  INTERNET, ni stockage externe).

## 6. Blocages documentés (honnêtes)

- Aucun Unity/Blender/SDK Android dans l'environnement assistant :
  la compilation Unity et l'APK ne peuvent pas être produites ici.
  Le Blender CI ci-dessus est exécuté sur les runners GitHub (réel).
- Licence Unity : indispensable pour tout build (locale ou cloud).
  Décision et activation = Lassana (un clic + 3 secrets pour GameCI).
- FPS Tecno KN3 : à mesurer après installation de l'APK réelle.
