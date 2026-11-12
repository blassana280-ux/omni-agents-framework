# OMNIBRAIN SUPREME — Spécification d’architecture

> **Statut :** proposition d’architecture validée pour revue — aucune implémentation de cette architecture n’est incluse dans ce commit.  
> **Date :** 2026-11-08  
> **Dépôt :** `blassana280-ux/omni-agents-framework`  
> **Branche de conception :** `omnibrain/supreme-design-v1`  
> **Base :** `main` — commit `41203f79880059a3ca2ffaa1b75c96eaeeb38c60`

## 1. Décision d’architecture

Faire évoluer OmniBrain vers un **orchestrateur multi-agents augmenté par un registre universel de compétences**, sans remplacer son moteur éprouvé et sans rendre les frameworks externes obligatoires.

L’architecture retenue est hybride et incrémentale :

1. conserver le noyau Python actuel et ses interfaces publiques ;
2. ajouter un catalogue de compétences versionné, auditable et interopérable ;
3. découvrir, importer, analyser et évaluer les skills avant toute activation ;
4. améliorer le routage par étapes, avec le routeur déterministe comme solution de repli ;
5. ajouter progressivement une fabrique d’agents, des adaptateurs de mémoire et une gouvernance de consentement ;
6. garder chaque intégration externe isolée derrière une interface et désactivée tant qu’elle n’a pas été vérifiée.

**Principe directeur :** OmniBrain doit savoir trouver une compétence, expliquer pourquoi elle convient, prouver son origine et ses contrôles, puis la sélectionner. La découverte d’une compétence ne doit jamais être interprétée comme une autorisation de l’exécuter.

## 2. État initial vérifié

Inspection effectuée sur la branche `main` au commit indiqué dans l’en-tête.

| Élément | État observé |
|---|---|
| Langage / runtime | Python 3.11 |
| Dépendances du noyau | Bibliothèque standard uniquement |
| Profils d’agents | 20 |
| Skills dans `registry/skills.json` | 30 |
| Spécialités routables | 18 |
| Fichiers de registre actuels | `agents.json`, `skills.json`, `routing.json`, `permissions.json` |
| Routage actuel | Déterministe, par mots-clés pondérés |
| Exécution parallèle | `ThreadPoolExecutor`, par vagues |
| Provider | `SubprocessProvider` ou `ManualProvider` honnête |
| Validation d’un run | 6 gates : completeness, evidence, execution, arbitration, secrets, trace |
| Mémoire et bus | Mémoire partagée avec rédaction / TTL et bus JSONL par run |
| Commandes existantes | `registry`, `skills`, `plan`, `run`, `providers`, `audit`, `overlays`, `selftest` |
| Vérification existante | `python3 -m unittest discover -s tests -t .` et `python3 -m omni registry` |

Les contrats existants à préserver sont notamment :

- `omni.models.Agent`, `Skill`, `Brief`, `Plan`, `ProviderResult` ;
- `Registry.load()`, `Registry.validate()`, `Registry.search_skills()` ;
- `Router.classify()`, `Router.select_agent()`, `Router.plan()` ;
- `Provider.available()` et `Provider.execute(brief)` ;
- les six gates de validation et le verdict `READY` impossible sans exécution réelle ;
- les protections GitOps : aucun commit sur `main`/`master`, aucun force-push et aucune fusion sans confirmation humaine.

Le dépôt possède déjà une PR ouverte #17 sur un chantier Warships. Cette spécification est isolée sur sa propre branche et ne doit pas retargeter, modifier ou bloquer cette PR.

## 3. Résultats attendus

### Objectifs fonctionnels

- Unifier les skills et agents découverts dans les dépôts du compte et dans des sources publiques sélectionnées.
- Retrouver une compétence à partir d’une demande, d’une spécialité, d’un outil, d’un langage ou d’un domaine.
- Conserver la provenance exacte : dépôt, chemin, commit, licence, propriétaire, date de collecte et empreinte de contenu.
- Distinguer clairement une source découverte, lue, analysée, évaluée, approuvée, activée ou mise en quarantaine.
- Expliquer chaque recommandation de skill et chaque décision de routage.
- Détecter les compétences absentes et proposer un agent spécialisé, sans l’activer automatiquement.
- Mesurer la qualité réelle avec des jeux de tests reproductibles, y compris hors ligne.
- Maintenir un mode local et gratuit : aucune dépendance à un service payant ni appel d’inférence payant implicite.

### Non-objectifs de la première livraison

- Remplacer `omni/orchestrator.py` ou réécrire le moteur en Microsoft Agent Framework, OpenAI Agents SDK, CrewAI ou LangGraph.
- Installer automatiquement tous les dépôts trouvés.
- Copier intégralement des dépôts tiers dans OmniBrain.
- Exécuter des scripts provenant d’un skill au moment de la découverte ou de l’analyse.
- Lancer 1 000 processus agents en parallèle. Le nombre « 1 000+ » désigne une ambition de catalogue et de compétences référencées, pas un objectif de concurrence d’exécution.
- Autoriser un agent généré à modifier ses permissions, ses frontières ou ses propres critères d’évaluation.
- Fusionner automatiquement une PR ou effectuer une action irréversible.

## 4. Architecture cible

### 4.1 Vue d’ensemble

```
                         DEMANDE
                            |
                  Classifieur déterministe
                            |
              Décomposition / spécialités requises
                            |
                 Skill & Agent Resolver
                 /          |           \\
          Skill Catalog  Agent Registry  Provider Registry
                 \\          |           /
                  Score + explication + contraintes
                            |
                  Plan de tâches / vagues
                            |
                 Policy & Consent Gate
                            |
                 Provider réel disponible ?
                     /             \\
                   oui              non
                    |                |
              Exécution bornée   pending_human
                    |
             Evidence / Trace / QA
                    |
             6 gates + nouvelles
             gates de confiance skill
                    |
           Livrable + reçu d’audit
```

Les modules restent indépendants. Le résolveur peut proposer un skill ou un agent, mais seule la politique peut autoriser une action et seul un provider réel peut exécuter le travail.

### 4.2 Couches

| Couche | Responsabilité | Source de vérité |
|---|---|---|
| Discovery | Découvrir les dépôts et les fichiers skills | Sources autorisées |
| Ingestion | Lire, normaliser et figer une version | Commit + empreinte |
| Skill Catalog | Décrire capacités, limites et compatibilité | Registre versionné |
| Trust Pipeline | Contrôler provenance, licence, contenu et risques | Rapport d’audit |
| Skill Evaluation | Évaluer structure, déclenchement et qualité | Résultats reproductibles |
| Agent Factory | Proposer des profils d’agents manquants | Profil + tests + permissions |
| Adaptive Router | Classer et sélectionner sous contraintes | Décision explicable |
| Provider Registry | Décrire capacités et disponibilité réelles | Probe du provider |
| Policy & Consent | Autoriser ou refuser les actions | `permissions.json` + consentement |
| Memory Adapters | Uniformiser les backends de mémoire | Interface locale |
| Trace & Reports | Rejouer et auditer les décisions | JSON / JSONL existants |

## 5. Registre universel des skills

### 5.1 Compatibilité avec le registre actuel

Le format actuel de `registry/skills.json` est la base de compatibilité. Les champs déjà consommés (`id`, `title`, `source`, `specialties`, `verification`, `notes`) ne doivent pas disparaître ni changer de sens dans une mise à jour mineure.

Les métadonnées riches seront ajoutées de façon optionnelle et lues par un nouveau composant de catalogue. `Skill.from_dict()` et `Registry.load()` doivent continuer à lire les anciennes entrées. Une migration explicite et testée sera préférable à une conversion silencieuse au chargement.

Fichiers proposés :

- `registry/skills.json` — vue historique compatible et références de skills ;
- `registry/skill-sources.json` — sources admises, propriétaires, stratégies de mise à jour ;
- `registry/skills.lock.json` — commits et empreintes verrouillés ;
- `registry/skill-policy.json` — règles de licence, confiance, activation et quarantaine ;
- `.omni/skill-cache/` — instantanés locaux non versionnés, reconstruisibles depuis le lock.

### 5.2 Métadonnées normalisées

Chaque entrée enrichie devra pouvoir exprimer :

| Champ logique | Utilité |
|---|---|
| Identité | ID OmniBrain, nom canonique et description de déclenchement |
| Source | URL du dépôt, chemin précis, branche / tag et commit SHA |
| Provenance | Propriétaire, origine officielle / communautaire, date de récupération |
| Intégrité | SHA-256 du contenu normalisé et statut de signature amont si disponible |
| Licence | SPDX du dépôt et licence propre au skill lorsqu’elle diffère |
| Compatibilité | Harness, plateforme, runtime et contraintes système |
| Capacités | Spécialités, tâches prises en charge, langages et outils requis |
| Permissions | Outils demandés, accès réseau, fichiers et niveau d’autorité nécessaire |
| Risque | Indicateurs de scripts, instructions externes, accès secrets, opérations destructives |
| Évaluation | Tests, résultats, jeux de données, date et version du grader |
| État | Découvert, importé, analysé, évalué, approuvé, activé, suspendu ou révoqué |

Les champs doivent rester simples à sérialiser en JSON. Les champs inconnus ne doivent pas être inventés : ils restent inconnus et empêchent toute revendication de vérification correspondante.

### 5.3 Machine à états

```
discovered
    |
fetched + pinned
    |
metadata_validated
    |
static_scanned
    |
evaluated
    |
human_approved
    |
available
    |
active (par tâche, temporairement)
```

Tout contrôle bloquant peut envoyer le skill vers `quarantined`. Une source retirée, un commit changé sans nouvel audit ou une empreinte différente invalide l’approbation existante. Une révocation doit empêcher les prochaines activations sans effacer l’historique d’audit.

### 5.4 Provenance et mises à jour

- Épingler les sources par commit SHA, jamais uniquement par le nom d’une branche mouvante.
- Calculer une empreinte SHA-256 sur tous les fichiers pertinents du skill, avec un ordre de parcours déterministe.
- Enregistrer le chemin exact du skill et l’URL de sa source amont.
- Ne pas considérer un fork personnel comme une preuve de qualité ou de sécurité.
- Comparer les changements avant toute mise à jour ; un changement de contenu exige une nouvelle analyse et peut invalider les évaluations antérieures.
- Conserver les licences du dépôt et du répertoire du skill ; ne pas déduire que tous les répertoires d’un dépôt ont nécessairement la même licence.
- N’importer que les fichiers nécessaires au skill sélectionné ; ne pas copier les secrets, les données personnelles, les caches ni les répertoires de build.

## 6. Découverte et sources

### 6.1 Sources initiales à inventorier

**Sources officielles ou structurantes :**

- [Agent Skills — Anthropic](https://github.com/anthropics/skills) : exemples de skills et référence de formats.
- [OpenAI Skills](https://github.com/openai/skills) : catalogue de skills Codex.
- [Google Skills](https://github.com/google/skills) : skills Google et Cloud.
- [NVIDIA Skills](https://github.com/NVIDIA/skills) : catalogue NVIDIA et modèle de fiche de confiance.
- [Vercel Skills CLI](https://github.com/vercel-labs/skills) : découverte et installation multi-harness.
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) : patterns d’orchestration et d’intégration, à étudier comme adaptateur éventuel.
- [Microsoft Agent Governance Toolkit](https://github.com/microsoft/agent-governance-toolkit) : gouvernance, identité, sandbox et audit.

**Collections transversales :**

- [wshobson/agents](https://github.com/wshobson/agents) : collection multi-harness d’agents, de skills et de commandes.
- [obra/superpowers](https://github.com/obra/superpowers) : méthodologie de travail et skills de développement.
- [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) : workflows d’ingénierie.
- [github/awesome-copilot](https://github.com/github/awesome-copilot) : agents, instructions, skills et plugins.
- [AlexZio00/sovereign-skills](https://github.com/AlexZio00/sovereign-skills) : audits, qualité, gestion de session et gouvernance.
- [agentic-design-patterns-skills](https://github.com/albertoclemente/agentic-design-patterns-skills) : patterns d’agents et routeur de patterns.
- [agent-consent-patterns](https://github.com/mrchaarlie/agent-consent-patterns) : patterns de consentement, approbation et reçus d’action.
- [adaptive-task-routing](https://github.com/zyzdev/adaptive-task-routing) : référence de routage sensible au contexte et au coût de changement.

Cette liste est une liste de départ, pas une approbation globale. Chaque skill doit être examiné individuellement.

### 6.2 Réutilisation des dépôts déjà présents dans le compte

La découverte doit commencer par l’inventaire des dépôts du compte, notamment les forks existants :

- `skills` (Anthropic), `skills-open-IA` (OpenAI), `skills-open-agents` (Vercel), `skills-Google-` (Google) ;
- `awesome-agent-skills`, `agency-agents`, `skills-collection`, `agent-skills-3`, `awesome-claude-code-toolkit` ;
- `Open-Agents`, `openai-agents-python`, `agents`, `agents-voice` ;
- `mem0`, `cognee`, `hindsight`, `OpenViking` ;
- `security-audit-skill`, `knowledge-work-plugins` et les collections spécialisées.

Le catalogue doit détecter les doublons par URL canonique, dépôt parent, chemin et empreinte. Un dépôt déjà forké sera réutilisé comme miroir ou référence ; on ne créera pas un second fork du même upstream.

### 6.3 Politique de fork

Un fork est un choix de maintenance, pas un mécanisme de découverte obligatoire.

Créer un nouveau fork uniquement lorsque l’un des besoins suivants est démontré : maintenir un correctif local, contribuer en upstream avec un workflow dédié, figer un snapshot maintenable ou construire un adaptateur spécifique. Les index de skills, listes de liens et petits exemples n’ont pas besoin d’être forkés par défaut.

Avant un fork futur : vérifier l’absence de fork existant, la licence, l’activité, la taille, la pertinence et les droits d’écriture. La fonction de fork n’étant pas exposée dans l’intégration GitHub utilisée pendant cet audit, aucun nouveau fork ne doit être revendiqué ou lancé par un fallback non vérifié.

## 7. Vérification de confiance et sécurité des skills

### 7.1 Niveaux de confiance

| Niveau | Signification | Peut être activé ? |
|---|---|---|
| `unverified` | URL ou nom seulement | Non |
| `source_verified` | Dépôt et chemin lus | Non |
| `metadata_validated` | Métadonnées conformes | Non |
| `scanned` | Analyse statique terminée sans blocage | Pas encore |
| `evaluated` | Tests de qualité exécutés | Après approbation |
| `approved` | Approbation humaine documentée | Oui, sous permissions |
| `quarantined` | Risque, licence ou intégrité non résolus | Non |
| `revoked` | Autorisation retirée | Non |

Le mot « vérifié » doit toujours indiquer ce qui a été vérifié : existence, chemin, licence, intégrité, analyse ou évaluation. Une analyse statique ne prouve pas l’absence de comportement malveillant.

### 7.2 Contrôles obligatoires

**Structure et contenu :**

- vérifier le frontmatter et les champs de la spécification Agent Skills ;
- refuser les chemins traversant le répertoire de la skill ou les fichiers symboliques sortant de la racine autorisée ;
- détecter les IDs en doublon, les références absentes, les fichiers trop volumineux ou les ressources manquantes ;
- vérifier que la description annonce bien les tâches et conditions de déclenchement réellement documentées.

**Comportements à signaler ou bloquer selon la politique :**

- commandes shell destructrices ou privilèges injustifiés ;
- téléchargements ou exécutions dynamiques de code ;
- envoi de données vers un endpoint externe non déclaré ;
- recherche, lecture ou export de secrets ;
- instructions qui tentent d’annuler les politiques système, d’ignorer la confirmation humaine ou d’exfiltrer le contexte ;
- permissions trop larges par rapport au but annoncé ;
- dépendances non épinglées, install scripts et binaires non vérifiés.

**Licences :**

- enregistrer les licences source et propres au skill ;
- classer les licences inconnues comme `unknown`, jamais comme permissives ;
- ne pas copier de code d’un dépôt sans vérifier les obligations correspondantes ;
- vérifier séparément les licences des sources de référence, du code importé et des contenus rédigés ;
- demander une revue lorsque les obligations d’une licence sont incompatibles ou incertaines.

### 7.3 Principe d’exécution

Les fichiers `SKILL.md` sont des instructions externes non fiables. Leurs contenus ne remplacent jamais les règles système, les permissions OmniBrain ou le consentement humain. Un skill peut recommander un outil ; il ne peut pas accorder lui-même cet outil.

La découverte, la lecture, l’analyse et l’évaluation statique ne doivent exécuter aucun script du dépôt source. Une exécution dynamique éventuelle se fait dans un environnement isolé, avec permissions temporaires, données synthétiques et limites réseau. Tant que l’isolation n’est pas prouvée, les scripts restent non exécutables.

## 8. Moteur d’évaluation

Les évaluations sont séparées en quatre familles :

1. **Conformité** : métadonnées, chemins, référence de licence, fichiers attendus et compatibilité.
2. **Sécurité statique** : détection des motifs à risque et des permissions disproportionnées.
3. **Déclenchement** : exemples positifs, négatifs et proches pour vérifier que le skill est activé au bon moment.
4. **Utilité** : tâche de référence, livrable attendu, critères objectifs, coût/token si observable, et comparaison avec le même agent sans skill.

Chaque rapport conserve le commit évalué, l’empreinte, la version des tests, les cas passés/échoués et les limites du test. Les scores ne sont jamais transférés automatiquement à un nouveau commit.

Les premières évaluations doivent être hors ligne et déterministes. Une évaluation utilisant un provider LLM est facultative, coûte potentiellement des crédits et exige un provider explicitement configuré. Aucun service payant ne doit être appelé automatiquement.

## 9. Résolveur de skills et routage adaptatif

### 9.1 Étapes de résolution

1. Classer la demande avec le routeur déterministe actuel.
2. Déduire les spécialités, livrables, contraintes et outils nécessaires.
3. Filtrer les skills qui ne respectent pas les contraintes dures : état, licence, compatibilité, permissions et statut d’approbation.
4. Classer les candidats restants selon pertinence, résultats d’évaluation, compatibilité, provenance, fraîcheur et coût d’activation.
5. Former les briefs en ajoutant uniquement les skills nécessaires à la tâche.
6. Expliquer les choix, les exclusions et les incertitudes.
7. Si aucun candidat acceptable n’existe, signaler le manque au lieu d’inventer une capacité.

Un score de pertinence ne peut jamais annuler un filtre de sécurité ou une interdiction de politique.

### 9.2 Séparation entre routage et sélection de modèle

Le choix du spécialiste, le choix du skill et le choix du provider/modèle sont trois décisions liées mais séparées.

Le provider doit prouver sa disponibilité avec le mécanisme existant `available()`. Le registre pourra décrire ses capacités, limites, latence et coût connus. Une donnée inconnue doit être présentée comme inconnue. Un modèle prétendument disponible ne peut pas être sélectionné sur la seule base de son nom.

Le routeur adaptatif doit considérer :

- difficulté, ambiguïté et coût d’une erreur ;
- spécialité, compétences et résultats vérifiés de l’agent ;
- capacités réellement déclarées du provider ;
- budget et limites configurés ;
- latence et parallélisme disponibles ;
- continuité du contexte et coût d’un changement de modèle ;
- besoin d’une revue indépendante.

Le routeur actuel reste le fallback déterministe obligatoire. En cas de panne, de coût inconnu ou de données de capacité manquantes, il doit conserver un comportement sûr et expliquer la dégradation.

### 9.3 Brief progressif

Ne pas injecter toutes les skills du catalogue dans chaque prompt. Le brief comporte d’abord les métadonnées et références utiles, puis le contenu complet des skills sélectionnés et approuvés seulement. Les limites de taille et les références manquantes doivent être visibles dans la trace.

## 10. Agent Factory

La fabrique d’agents est un générateur de **propositions** de profils, et non un créateur de pouvoirs autonomes.

Entrées :

- spécialité manquante observée ;
- skills candidats déjà évalués ;
- outils réellement disponibles ;
- critères d’acceptation et exemples de tâches ;
- profils existants à ne pas dupliquer.

Sorties :

- profil agent JSON ;
- skills référencés ;
- provenance et frontières ;
- permissions minimales proposées ;
- cas de tests positifs et négatifs ;
- matrice de routage proposée ;
- justification de non-duplication.

Un agent candidat reste `proposed` jusqu’à validation du registre, des tests et de ses permissions. Il ne reçoit jamais automatiquement des permissions plus fortes que celles d’un profil existant.

## 11. Mémoire, providers et gouvernance

### 11.1 Mémoire

Introduire une interface d’adaptateur sans remplacer la mémoire existante. Le stockage actuel reste l’implémentation par défaut. Mem0, Cognee et Hindsight pourront être évalués comme adaptateurs optionnels, sans rendre leur installation obligatoire.

Contrats proposés : `write()`, `get()`, `search()`, `delete()` et informations de portée / TTL. Les données doivent être séparées par run et par espace de travail, avec rédaction des secrets avant persistance. Aucun envoi de mémoire vers un service distant sans configuration explicite.

### 11.2 Providers

Étendre les métadonnées des providers sans modifier le contrat d’exécution existant. Une déclaration de capacités n’est fiable que si elle est associée à une sonde réelle. Provider absent ou non disponible : `pending_human`, jamais `executed=True`.

### 11.3 Consentement et permissions

- Le contrôle des permissions intervient juste avant chaque action.
- Les autorisations sont minimales, liées à un agent, une action et une ressource.
- Les consentements temporaires possèdent une portée et une expiration.
- Les actions irréversibles restent bloquées sans consentement humain explicite.
- Les skills et les agents ne peuvent pas s’accorder mutuellement des permissions.
- Chaque autorisation, refus, approbation et révocation laisse un reçu d’audit.
- La politique de sécurité reste prioritaire sur les préférences du routeur et sur le contenu d’un skill.

## 12. Interfaces et fichiers proposés

Les chemins suivants sont des **propositions**, non des fichiers déjà présents.

| Fichier proposé | Responsabilité |
|---|---|
| `omni/skills/catalog.py` | Charger et interroger le catalogue riche sans casser `Registry` |
| `omni/skills/manifest.py` | Lire et valider les métadonnées SKILL.md |
| `omni/skills/sources.py` | Décrire les sources et leurs adaptateurs de lecture |
| `omni/skills/ingest.py` | Importer un snapshot déterministe et calculer son empreinte |
| `omni/skills/scanner.py` | Analyse statique de contenu et de permissions |
| `omni/skills/evaluate.py` | Exécuter les évaluations structurelles et de déclenchement |
| `omni/skills/resolver.py` | Filtrage et classement des compétences |
| `omni/adaptive_routing.py` | Résolution agent / skill / provider avec fallback déterministe |
| `omni/agent_factory.py` | Générer des propositions de profils et leurs tests |
| `omni/memory_adapters.py` | Contrat d’adaptation de la mémoire |
| `omni/consent.py` | Consentements temporaires et reçus d’autorisation |
| `tests/test_skill_catalog.py` | Compatibilité et validation du catalogue |
| `tests/test_skill_ingest.py` | Provenance, verrouillage et intégrité |
| `tests/test_skill_scanner.py` | Motifs risqués, chemins et quarantaine |
| `tests/test_skill_evaluation.py` | Cas d’évaluation déterministes |
| `tests/test_skill_resolver.py` | Filtrage dur, classement et explications |
| `tests/test_adaptive_routing.py` | Fallbacks et disponibilité réelle |
| `tests/test_agent_factory.py` | Non-duplication, registre et permissions |
| `tests/test_consent.py` | Approbation, portée, expiration et révocation |

Les nouveaux modules sont ajoutés par petites unités. `omni/routing.py`, `omni/orchestrator.py`, `omni/registry.py` et les fichiers de registre existants ne doivent pas subir de refonte générale sans nécessité démontrée.

## 13. CLI cible

Les commandes suivantes sont des propositions d’interface :

| Commande | Comportement attendu |
|---|---|
| `python3 -m omni sources list` | Liste les sources configurées et leur statut |
| `python3 -m omni sources scan` | Découverte en lecture seule |
| `python3 -m omni sources sync --dry-run` | Compare les commits et affiche les changements sans importer |
| `python3 -m omni skills search <termes>` | Recherche avec explication du classement |
| `python3 -m omni skills inspect <id>` | Affiche provenance, licence, capacités et confiance |
| `python3 -m omni skills audit <id>` | Lance les contrôles statiques |
| `python3 -m omni skills evaluate <id>` | Lance les évaluations sans provider par défaut |
| `python3 -m omni skills approve <id>` | Enregistre une approbation humaine |
| `python3 -m omni skills quarantine <id>` | Suspend l’activation |
| `python3 -m omni routes explain <demande>` | Explique spécialités, agents, skills et provider proposé |
| `python3 -m omni agents propose <spécialité>` | Produit un profil candidat, sans l’activer |

Les opérations réseau sont explicites, identifiables dans les logs et limitées aux sources configurées. Toute commande qui modifie le registre exige un mode d’écriture explicite ; les commandes de scan et de plan restent en lecture seule.

## 14. Plan de livraison par étapes

### Étape 0 — Inventaire fiable

- [ ] Extraire les 30 entrées de skills actuelles, les 20 profils et les 18 spécialités.
- [ ] Identifier les doublons, les sources non accessibles et les chemins non vérifiés.
- [ ] Relier chaque source à son upstream canonique et à son éventuel fork déjà présent.
- [ ] Conserver un rapport de référence et une copie des registres avant migration.

**Gate :** aucun nombre, parent, chemin ou statut non vérifié n’est présenté comme établi.

### Étape 1 — Contrat de catalogue rétrocompatible

- [ ] Définir les métadonnées optionnelles et les nouveaux fichiers JSON.
- [ ] Ajouter le chargeur riche sans supprimer les interfaces historiques.
- [ ] Ajouter les validations d’ID, de chemins, de références et de champs de provenance.
- [ ] Tester les anciennes entrées inchangées et les nouvelles entrées enrichies.

**Gate :** les tests actuels et `python3 -m omni registry` restent verts.

### Étape 2 — Découverte, import et verrouillage

- [ ] Implémenter des adaptateurs en lecture seule pour les sources autorisées.
- [ ] Détecter upstreams, forks locaux, doublons et commits.
- [ ] Importer uniquement le répertoire d’un skill sélectionné.
- [ ] Produire le lock de commit SHA et d’empreinte SHA-256.
- [ ] Comparer les mises à jour en mode dry-run avant toute modification.

**Gate :** même source + même commit = même empreinte ; changement de contenu = nouvelle révision.

### Étape 3 — Scanner et évaluateur de confiance

- [ ] Implémenter les contrôles de structure, licence, chemins et intégrité.
- [ ] Détecter les instructions à risque et les demandes de permissions anormales.
- [ ] Placer les cas ambigus ou bloquants en quarantaine.
- [ ] Ajouter jeux de tests positifs, négatifs et adversariaux.
- [ ] Enregistrer les résultats par commit, empreinte et version d’évaluateur.

**Gate :** aucune skill non approuvée/quarantinée ne peut être activée ; aucun script amont n’est exécuté durant scan/evaluate.

### Étape 4 — Résolveur et activation progressive

- [ ] Ajouter les filtres d’éligibilité et le score explicable.
- [ ] Ajouter les tests de confusion entre descriptions similaires.
- [ ] Ajouter le chargement progressif des skills approuvées.
- [ ] Tracer les compétences choisies et écartées avec leurs raisons.

**Gate :** les décisions de sécurité dominent toujours le classement de pertinence.

### Étape 5 — Routage adaptatif

- [ ] Combiner spécialité, skill, agent et disponibilité provider.
- [ ] Ajouter limites de budget, latence, concurrence et continuité de contexte.
- [ ] Conserver `Router` déterministe comme fallback systématique.
- [ ] Vérifier les providers au moment de la sélection et de l’exécution.

**Gate :** aucun provider absent ou modèle non configuré ne peut être annoncé comme opérationnel.

### Étape 6 — Agent Factory et mémoire

- [ ] Générer des profils candidats à partir des lacunes mesurées.
- [ ] Valider leurs références, tests et permissions minimales.
- [ ] Ajouter les adaptateurs de mémoire derrière le contrat stable.
- [ ] Tester suppression, TTL, cloisonnement et rédaction des secrets.

**Gate :** aucun agent généré ne devient actif sans approbation et registre cohérent.

### Étape 7 — Gouvernance et durcissement

- [ ] Ajouter le consentement temporaire par action et ressource.
- [ ] Enregistrer reçus, refus, approbations et révocations.
- [ ] Vérifier les frontières entre instructions de skill et politique système.
- [ ] Ajouter tests de prompt injection, secret exposure et opérations irréversibles.

**Gate :** les opérations dangereuses restent refusées sans consentement explicite et vérifiable.

## 15. Stratégie de tests et définition de « prêt »

### Vérification à chaque étape

Commandes de base existantes :

```bash
python3 -m unittest discover -s tests -t .
python3 -m omni registry
python3 -m omni providers
python3 -m omni selftest
```

Les tests du registre et du catalogue ne doivent pas exiger Internet. Les tests de connecteurs utilisent des réponses HTTP figées. Les tests de providers payants sont désactivés en CI par défaut et doivent être explicitement sélectionnés.

### Cas obligatoires

- anciennes entrées de `skills.json` lisibles ;
- ID dupliqué, référence manquante, chemin traversant et lien symbolique interdit ;
- commit ou empreinte modifiés après approbation ;
- licence inconnue, licence propre au répertoire différente de celle du dépôt ;
- instructions qui tentent de contourner les règles, exfiltrer des secrets ou élargir les permissions ;
- skill pertinent mais non approuvé, qui doit être rejeté ;
- deux skills de descriptions proches, avec sélection déterministe et justification ;
- skill retiré ou révoqué, non activable ;
- provider absent ou défaillant, avec résultat `pending_human`/échec honnête ;
- agent candidat avec permission non déclarée, rejeté ;
- approbation limitée à une action/ressource expirée ou révoquée ;
- aucune modification de `main` et aucune fusion dans les tests GitOps.

### Définition d’un jalon prêt

Un jalon est prêt uniquement si :

1. tests ciblés verts ;
2. tests de régression verts ;
3. validation du registre verte ;
4. preuves ou logs conservés ;
5. licences et provenance documentées ;
6. aucune dépendance ou capacité non déclarée ;
7. revue indépendante des changements ;
8. PR isolée et non fusionnée jusqu’à décision humaine.

## 16. Risques et mesures

| Risque | Mesure de réduction |
|---|---|
| Volume énorme de skills et de dépôts | Découverte large, import sélectif, déduplication |
| Prompt injection dans un skill | Traitement comme donnée non fiable, scan, permissions externes au skill |
| Licence inconnue ou composite | Quarantaine et revue avant copie |
| Régression de l’orchestrateur | Interfaces historiques conservées et tests de compatibilité |
| Mauvaise sélection / descriptions proches | Cas négatifs, explications, fallback déterministe |
| Score de confiance trompeur | États précis, preuves par commit, aucun label « sûr » absolu |
| Dépendance à une API ou un modèle payant | Core sans dépendance, coût par défaut nul, providers explicites |
| Compétences obsolètes | Pinning, diff de contenu, revalidation lors d’une mise à jour |
| Agent trop privilégié | Permissions minimales, consentement humain et reçus d’audit |
| Catalogue corrompu ou indisponible | Cache local verrouillé et dernier registre valide conservé |

## 17. Références techniques consultées

- [Agent Skills specification](https://agentskills.io/) — format portable de skills.
- [Microsoft Learn — Agent Skills](https://learn.microsoft.com/en-us/agent-framework/agents/skills) — champs de métadonnées et compatibilité.
- [NVIDIA — NVIDIA-Verified Agent Skills](https://docs.nvidia.com/skills) — provenance, vérification et gouvernance des capacités.
- [NVIDIA — Capability Governance](https://developer.nvidia.com/blog/nvidia-verified-agent-skills-provide-capability-governance-for-ai-agents/) — catalogage, scan, évaluation, fiche de confiance et signature.
- [Vercel — Skills CLI](https://github.com/vercel-labs/skills) — découverte et installation multi-harness.
- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents/sdk) — référence pour handoffs, guardrails, résultats et observabilité ; pas une dépendance du noyau.
- [OpenAI Agents — tracing](https://developers.openai.com/api/docs/guides/agents/integrations-observability) — références de traçabilité.
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) et [Agent Governance Toolkit](https://github.com/microsoft/agent-governance-toolkit) — références de workflows, gouvernance et contrôle.
- [Agent Consent Patterns](https://github.com/mrchaarlie/agent-consent-patterns) — référence de portée, approbation et audit.
- Les dépôts source listés à la section 6, à examiner skill par skill avant toute adoption.

## 18. Décisions restant ouvertes avant implémentation

Ces points ne bloquent pas la rédaction de la spécification, mais devront être explicités dans le plan d’implémentation ou validés avant qu’un comportement externe soit rendu visible :

1. **Sources autorisées :** catalogue public seulement au premier jalon, ou également les dépôts privés accessibles au compte.
2. **Politique de licence :** liste exacte des licences autorisées pour référencer, importer ou redistribuer un skill ; ces trois actions n’ont pas les mêmes implications.
3. **Approbation :** approbation manuelle individuelle par skill ou approbation par source avec ré-audit de chaque nouvelle version.
4. **Synchronisation :** commande manuelle au départ ; cadence automatique uniquement après choix explicite et contrôles de notification.
5. **Persistance de la mémoire :** rester strictement local dans les premiers jalons ou autoriser un adaptateur distant après configuration.
6. **Budget de provider :** conserver le comportement sans provider par défaut ; aucun coût d’inférence externe sans configuration et approbation explicites.
7. **Politique de fork :** fork uniquement des frameworks réellement adaptés et maintenus, plutôt que des index et catalogues de liens.

## 19. Hors périmètre de cette spécification

Ce document définit le design et les gates. Il ne prétend pas que le registre universel, le scanner, l’Agent Factory, la mémoire multi-backend ou le routeur adaptatif sont déjà implémentés. Leur réalisation commencera après revue et approbation de cette spécification, dans des branches et PR séparées.

---

**Critère final :** OmniBrain SUPREME doit augmenter la capacité de son réseau sans sacrifier la vérité d’exécution, la provenance, les licences, la sécurité, la réversibilité ni le contrôle humain.
