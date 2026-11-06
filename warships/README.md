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
- Compilation Unity, assets 3D Blender, APK : **en attente d'environnement
  Unity/Blender** (voir blocage ci-dessous).

## Hébergement (blocage documenté)

`create_repository@@/CODE403@@ → 403 « Resource not accessible by integration »
(re-testé le 06/11/2026) : l'app GitHub n'a pas le scope Administration.
Le jeu vit donc **provisoirement** dans ce dépôt, isolé dans le dossier
`warships/@@/CODE403@@ sur des branches `warships/*@@/CODE403@@ — jamais dans main directement.
Procédure de migration vers le dépôt dédié `omni-warships@@/CODE403@@ (à créer par
Lassana, un clic) : docs/ARCHITECTURE.md § Migration.

## Structure

```text
warships/
  core/OmniWarships.Core/        cœur de simulation C# (netstandard2.1, replay déterministe intégré)
  core/tests/                    tests xUnit (exécutés en CI)
  unity/                         projet Unity 2022.3 URP (Assets/OmniWarships : couche de jeu + copies
                                 octet par octet du noyau + specs embarquées Resources/Ships)
  docs/                          architecture, équipes, preuves, licences
  docs/fidelity/                 matrice de fidélité + sources
  tools/omni-fidelity-lab/        validation de la matrice (CI)
  tools/omni-asset-factory/       générateurs Blender + QC + licences
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
