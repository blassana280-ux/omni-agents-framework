# Autonomie encadrée — Cyber Force 100

## Niveaux d'autonomie

| Niveau | Signification | Risque `low` | Risque `medium` | Risque `high`/`critical` |
|---|---|---|---|---|
| `autonomous` | L'agent exécute sans solliciter | ✅ auto | ✅ auto | 🧑 validation humaine |
| `assisted` | L'agent exécute, l'humain informé | ✅ auto | ✅ auto (information) | 🧑 validation humaine |
| `supervised` | L'agent propose, l'humain tranche | ✅ auto | 🧑 validation humaine | 🧑 validation humaine |

Règles du moteur (`cf100/security/policy.py`) :

- **Toujours auto** : risque `low`.
- **Toujours humain** : risque `critical`, et toute action de la liste
  `dangerous_actions` (fusion, suppression, permissions, déploiement…),
  **quel que soit le niveau d'autonomie**.
- Entre les deux : plafond d'autonomie de l'agent (table ci-dessus).

## Validation humaine

```python
from cf100.security.policy import ApprovalLedger

ledger = ApprovalLedger(path="data/approvals.json")
decision = ledger.approve(decision_id, approver="Lassana Bah",
                          note="Raison de l'approbation")
```

- L'approbateur **ne peut pas** être un agent : les IDs d'agents sont
  rejetés (`ApprovalLedger` refuse `approver` ressemblant à un ID CF100).
- Chaque approbation est datée, motivée et stockée dans `data/approvals.json`.
- Le refus n'incrémente pas les compteurs d'échec d'un agent (un refus de
  politique n'est pas une panne).

## Classification des actions

Chaque action type a une classe de risque par défaut
(`registry/policies.json → action_risk`), surchargée par
`risk_rules` (combinaisons action×cible). Exemples :

- `low` : analyse de fichier local, lecture de registre, rapport.
- `medium` : scan réseau autorisé, patch de dépendance en branche dédiée.
- `high` : changement de configuration de défense, correction de code.
- `critical` : rotation de secret, suppression de données, fusion, déploiement.

## Apprentissage contrôlé

Le cycle `KnowledgeEvolution` :

```
propose → mark_tested → validate (HUMAIN UNIQUEMENT) → promote (mémoire collective)
```

- `DecisionEngine.learn()` ne modifie les poids que si
  `outcome["validated"] is True`.
- La mémoire collective n'accepte **que** des savoirs validés
  (`MemoryTiers.promote_validated`).
- Tout est journalisé (qui, quoi, quand) : traçabilité complète.

## Ce que l'autonomie ne couvrira jamais

Même en Phase 4+, CF100 n'auto-exécutera jamais sans humain :

- fusion de PR, écriture sur `main`, force-push, suppression de dépôt/branche ;
- rotation de secrets, changement de permissions, désactivation de protection ;
- suppression ou purge de données/preuves ;
- déploiement en production.
