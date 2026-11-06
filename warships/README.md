# OMNI WARSHIPS — studio de développement naval Android

Jeu naval militaire Android, original, inspiré du niveau de qualité de Modern
Warships (Cube Software / Artstorm) **sans jamais copier ses fichiers, modèles,
textures, sons ou code**. Étude de fidélité : docs/fidelity/FIDELITY_MATRIX.md.

## État réel (preuves, jamais d'annonces)

Voir docs/PROOF_STATUS.md — chaque fonctionnalité porte un statut parmi :
prévue / en développement / implémentée / testée / tests réussis / compilée /
APK produite / installée / testée sur appareil réel / validée.

- Cœur de simulation C# (netstandard2.1, zéro dépendance) : **compilé et testé
  en CI** (dotnet build + dotnet test — workflow warships-ci.yml).
- Matrice de fidélité + scénarios : **validés en CI** (validateur Python).
- Couche Unity (URP 2022.3 : contrôleurs, HUD, océan, tactile) : **code écrit,
  structure et copies octet par octet du noyau validées en CI**
  (tools/omni-unity-bridge/validate_unity_layer.py).
- Couche 3D T-012 (environnement jour/nuit + météo, écume, combat visuel relié
  aux événements du noyau, dégâts progressifs, pause + profils, chargement FBX
  + LOD) : **code écrit, structure validée en CI, compilation Unity requise**.
- Générateurs 3D Blender détaillés (destroyer, frégate, porte-avions,
  sous-marin, aéronefs, équipements ; UV, matériaux, LOD, pivots animables) :
  **scripts écrits + syntaxe validée en CI, non exécutés** (Blender absent de
  l'environnement — aucun FBX prétendu produit).
- Pipeline GameCI Android : **préparé, inactif** (exemple hors
  .github/workflows — activation liée à la décision de licence de Lassana).
- Compilation Unity, APK, mesures FPS : **en attente d'environnement**
  (voir blocage ci-dessous).

## Hébergement (blocage documenté)

Création de dépôt via l'app GitHub impossible : `create_repository` → 403
« Resource not accessible by integration » (re-testé le 06/11/2026). Le jeu vit
donc **provisoirement** dans ce dépôt, isolé dans le dossier `warships/` sur des
branches `warships/*` — jamais dans main directement. Procédure de migration vers
le dépôt dédié `omni-warships` (à créer par Lassana, un clic) :
docs/ARCHITECTURE.md § Migration.

## Structure

```text
warships/
  core/OmniWarships.Core/        cœur de simulation C# (netstandard2.1, replay déterministe intégré)
  core/tests/                    tests xUnit (exécutés en CI)
  unity/                         projet Unity 2022.3 URP (Assets/OmniWarships : couche de jeu + copies
                                 octet par octet du noyau + specs embarquées Resources/Ships)
  unity/ci/                      pipeline GameCI PRÉPARÉ (exemple inactif, hors .github/workflows)
  docs/                          architecture, équipes, preuves, licences
  docs/fidelity/                 matrice de fidélité + sources
  tools/omni-fidelity-lab/        validation de la matrice (CI)
  tools/omni-asset-factory/       générateurs Blender détaillés (7 scripts : coques paramétriques,
                                 UV, matériaux procéduraux, LOD, pivots animables) + QC + licences
  tools/omni-battle-sandbox/      scénarios de simulation (validés en CI)
  tools/omni-unity-bridge/        validateur couche Unity + synchronisation noyau (CI)
```

## Vérification

```bash
dotnet build warships/core/OmniWarships.Core/OmniWarships.Core.csproj -c Release
dotnet test  warships/core/tests/OmniWarships.Core.Tests.csproj
python3 warships/tools/omni-fidelity-lab/validate_matrix.py
python3 warships/tools/omni-battle-sandbox/validate_scenarios.py
python3 warships/tools/omni-unity-bridge/validate_unity_layer.py
```

Règles du studio : jamais de commit sur main, PR + CI, aucun secret, aucun
résultat simulé présenté comme réel, licences vérifiées avant toute
réutilisation, fusion = décision de Lassana.
