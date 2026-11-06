# Architecture — OMNI WARSHIPS

## Principe directeur : un cœur déterministe, une couche présentation

Le gameplay est séparé en deux niveaux :

1. **OmniWarships.Core** (netstandard2.1, zéro dépendance, C# 8/9) : toute la
   simulation — mouvement naval, flottabilité, dégâts localisés, voie d'eau,
   balistique (obus/missiles/torpilles), capteurs (radar/sonar), IA tactique,
   océan Gerstner, replays. **Déterministe** : RNG maison (LCG), pas à pas
   fixe (1/30 s), floats uniquement. Compilable et testable hors Unity
   (dotnet test en CI) et consommable par Unity (netstandard2.1) et par les
   outils internes (sandbox, replay).
2. **Couche Unity (URP)** : rendu, entrées tactiles, audio, HUD — de simples
   adaptateurs qui interrogent le cœur. Aucune logique de gameplay dans
   MonoBehaviour : ils traduisent input → ShipCommand et état → visuel.

Bénéfices : le gameplay est testable automatiquement (CI), rejouable à
l'identique (replay = re-simulation), et l'optimisation Android ne touche
que la couche présentation.

## Modules (séparation imposée)

| Module | Contenu | Testé par |
|---|---|---|
| Core.Spec | specs navires/compartiments/armes/capteurs | xUnit (CI) |
| Core.Simulation | mouvement, océan, dégâts, voie d'eau, balistique, capteurs, BattleSim | xUnit (CI) |
| Core.AI | ThreatBoard, IA tactique, sélection de cibles | xUnit (CI) |
| Core.Replay | enregistreur/lecteur de replays | xUnit (CI) |
| Unity.Gameplay | ShipController, tourelles, HUD, océan visuel | PlayMode (à venir) |
| Unity.UI | menus, hangar, paramètres | PlayMode (à venir) |
| tools/* | Fidelity Lab, Asset Factory, Battle Sandbox, Replay & Debug | CI (données) |

## Déterminisme et replays

BattleSim est une machine à états à pas fixe : (graine, specs, commandes) →
états. Le replay n'enregistre PAS les états mais les commandes (+ graine) ;
rejouer = re-simuler. Un test CI prouve l'égalité bit à bit des états finaux
sur 200 ticks.

## Qualité graphique adaptative (cible Tecno KN3 : Android 15, 4 Go RAM)

5 profils (Ultra/Élevé/Moyen/Faible/Adaptatif) pilotés par un preset
URP + paramètres du cœur : distance de vue, LOD, ombres, particules,
fréquence de simulation des vagues lointaines. Le profil Adaptatif mesure
le temps de frame réel (Application.averageFrameTime lissé) et descend
d'un cran si FPS < 28 pendant 5 s, remonte si FPS > 55 pendant 30 s.
Objectifs : 30 FPS sur KN3, 60+ sur appareils puissants — **jamais déclarés
atteints sans mesure réelle sur appareil**.

## Aviation et sous-marins

Modélisés dans le cœur dès la conception (WeaponKind, surfaces aériennes
dans BattleSim sous forme d'unités à altitude, profondeur pour les
sous-marins avec détection sonar/visuelle selon la profondeur), pour que
la Phase 5 ne casse pas l'architecture.

## Migration vers le dépôt dédié omni-warships

Le dossier warships/ est auto-contenu. Quand Lassana crée le dépôt
omni-warships : (1) `git checkout warships/vertical-slice && git subtree
split -P warships -b warships-root` ; (2) push de warships-root comme main
du nouveau dépôt ; (3) CI warships-ci.yml déjà autonome. Aucune référence au
framework omni dans le code du jeu — la séparation est réelle dès aujourd'hui.
