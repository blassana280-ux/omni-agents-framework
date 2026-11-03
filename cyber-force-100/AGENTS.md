# AGENTS.md — Cyber Force 100

Règles de conduite pour tout agent (Vibe, OmniBrain, GitHub Copilot, humain
assisté) qui travaille sur ce dossier. Aligné sur l'AGENTS.md racine du dépôt
`omni-agents-framework` : en cas de conflit, la version racine gagne.

## Mission

Cyber Force 100 est une plateforme de cybersécurité **défensive** intégrée à
l'écosystème OmniBrain. Elle complète `omni-security` (relecteur sécurité
défensive) ; elle ne le remplace pas et n'est pas un orchestrateur concurrent
d'OmniBrain.

## Règles de travail sur ce dossier

1. **Jamais de commit direct sur `main`.** Branche
   `feature/cyber-force-100-<sujet>` + Pull Request. La fusion appartient à
   Lassana.
2. **Registre = source de vérité.** Tout agent ajouté/modifié doit passer les
   invariants de `cf100/agents/registry.py` (10 divisions, 10 agents par
   division, ids/noms uniques, outils en liste blanche, fallback valide).
   Lancer `python -m cf100 validate` avant tout commit.
3. **Tests = preuve.** `pytest` doit rester vert. Un test qui n'assert rien
   doit être supprimé. N'invente jamais un résultat de test.
4. **Défensif uniquement.** Pas d'exploit, pas d'attaque de tiers, pas de
   collecte de credentials — y compris dans les tests et la documentation.
5. **Secrets.** Aucun secret dans le code, les tests, les journaux ou les
   exemples. `cf100/security/secrets.py` bloque tout livrable contenant un
   secret détecté.
6. **Autonomie encadrée.** Toute action destructive (`merge_pr`,
   `delete_data`, `write_main`, `change_permissions`, `deploy_production`…)
   exige une validation humaine. Voir `registry/policies.json` et
   `docs/AUTONOMY.md`.
7. **Preuves.** Les opérations sensibles sont scellées dans le journal de
   preuves (`cf100/core/evidence.py`). Ne jamais réécrire ce journal.
8. **Honnêteté opérationnelle.** Un composant non câblé est documenté comme
   non implémenté. Ne jamais prétendre qu'un moteur tourne sans preuve
   fraîche.

## Commandes utiles

```bash
python -m cf100 validate      # invariants du registre
python -m cf100 audit         # auto-audit (registre, preuves, secrets)
python -m cf100 list CI       # agents d'une division
python -m cf100 export-omni   # export au format registry OmniBrain
pytest                        # suite complète
```
