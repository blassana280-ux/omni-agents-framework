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
- Couche Unity, assets 3D, APK : **en attente d'environnement Unity/Blender**
  (voir blocage ci-dessous).

## Hébergement (blocage documenté)

`create_repository` → 403 « Resource not accessible by integration »
(re-testé le 06/11/2026) : l'app GitHub n'a pas le scope Administration.
Le jeu vit donc **provisoirement** dans ce dépôt, isolé dans le dossier
`warships/` sur des branches `warships/*` — jamais dans main directement.
Procédure de migration vers le dépôt dédié `omni-warships` (à créer par
Lassana, un clic) : docs/ARCHITECTURE.md § Migration.

## Structure

```text
warships/
  core/OmniWarships.Core/        cœur de simulation C# (netstandard2.1)
  core/tests/                    tests xUnit (exécutés en CI)
  unity/                         projet Unity (URP) + scripts de couche
  docs/                          architecture, équipes, preuves, licences
  docs/fidelity/                 matrice de fidélité + sources
  tools/omni-fidelity-lab/        validation de la matrice (CI)
  tools/omni-asset-factory/       générateurs Blender + QC + licences
  tools/omni-battle-sandbox/      scénarios de simulation (validés en CI)
  tools/omni-replay-debug/        format de replay (enregistreur dans Core)
```

## Vérification

```bash
dotnet build warships/core/OmniWarships.Core/OmniWarships.Core.csproj -c Release
dotnet test  warships/core/tests/OmniWarships.Core.Tests.csproj
python3 warships/tools/omni-fidelity-lab/validate_matrix.py
python3 warships/tools/omni-battle-sandbox/validate_scenarios.py
```

Règles du studio : jamais de commit sur main, PR + CI, aucun secret, aucun
résultat simulé présenté comme réel, licences vérifiées avant toute
réutilisation, fusion = décision de Lassana.
