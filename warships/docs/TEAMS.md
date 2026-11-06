# Organisation du studio — agents mobilisés

OmniBrain SUPREME = directeur du studio (routage, briefing, vérification).
Mistral = partenaire de raisonnement et d'exécution dans GitHub.
Arena = exécutant principal (branches, commits, PR via omni/gitops).

## Équipes et affectations (toutes réellement mobilisées)

| Équipe | Agents mobilisés | Mission concrète | Livrable vérifiable |
|---|---|---|---|
| Direction | **omnibrain**, **omni-architect** + profil engineering-software-architect | architecture cœur/présentation, décisions | docs/ARCHITECTURE.md + CI verte |
| Simulation | **omni-ai** + profil game-designer | mouvement, dégâts, voie d'eau, balistique | OmniWarships.Core (dotnet test CI) |
| Combat | profil game-designer + **omni-qa** | capteurs radar/sonar, contre-mesures, ciblage | Core.Simulation + tests |
| IA de jeu | **omni-ai** + profil game-designer | ThreatBoard, tactiques, niveaux de difficulté | Core.AI + tests |
| 3D / Assets | profil technical-artist + profil gis-3d-scene-developer | générateurs Blender, LOD, QC | tools/omni-asset-factory |
| Graphismes | profil technical-artist | océan Gerstner, effets, 5 profils qualité | Core océan + presets URP |
| Contenu | profils level-designer + economy-designer | scénarios, équilibrage, progression | tools/omni-battle-sandbox |
| Android | **omni-android** + profil engineering-mobile-release-engineer | packaging, optimisation mémoire | à venir (Unity requis) |
| Qualité | **omni-qa**, **omni-reviewer** + profils testing-test-automation-engineer, testing-reality-checker | tests xUnit, validation données, revue adverse | CI warships-ci.yml |
| Performance | **omni-perf** + profil testing-performance-benchmarker | profils adaptatifs, mesures | à venir (appareil réel) |
| UI/UX | **omni-designer** + profils design-ux-architect, design-ui-designer | HUD, hangar, contrôles tactiles | à venir (Unity requis) |
| Production | **omni-gitops**, **omni-devops** + profil project-management-studio-producer | branches, PR, CI, traçabilité | PR + CI + docs |

## Honnêteté sur la mobilisation

Les agents sont des **profils d'expertise** (registre omni + dépôt
agency-agents) : ils structurent le travail, les livrables et les revues —
l'exécution matérielle est faite par l'assistant (Mistral/Arena) qui incarne
le profil, et la preuve d'exécution est toujours externe et vérifiable
(CI GitHub Actions). Aucun agent n'est déclaré « au travail » sans livrable
poussé et vérifié. Les agents omni-* sont ceux du registre du framework
(registry/agents.json) ; les profils nommés sans préfixe viennent du dépôt
forké blassana280-ux/agency-agents (divisions Game Development, Engineering,
Testing, Project Management, Design, GIS).
