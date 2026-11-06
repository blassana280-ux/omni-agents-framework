# Politique de licences — OMNI WARSHIPS

1. **Originalité stricte** : aucun fichier, modèle, texture, son, nom ou
   code de Modern Warships (Cube Software / Artstorm) n'est copié. Le jeu
   s'en inspire au niveau des mécaniques observables (non protégées) avec
   des paramètres et implémentations originaux.
2. Code du jeu : licence à confirmer par Lassana (proposition : MIT pour
   le cœur, assets sous CC-BY-4.0 ; alternative : tous droits réservés).
3. Toute ressource tierce doit apparaître dans le journal
   tools/omni-asset-factory/LICENSE-LOG.csv avec : origine, auteur, licence
   SPDX, preuve de permission, date de vérification. Ressource sans ligne
   au journal = interdite d'import.
4. Licences acceptées pour les dépendances : MIT, Apache-2.0, BSD-2/3,
   CC0, CC-BY-4.0, OFL. Copyleft (GPL/LGPL) : interdit dans le code du jeu
   (distribution APK) sauf décision contraire de Lassana.
5. Aucun secret (clé API, jeton, mot de passe) dans le code, les commits,
   les workflows ou les logs. Vérifié par la CI (grep de motifs).
6. Politique d'exécution : le code externe indexé (registry/capabilities)
   n'est jamais exécuté aveuglément ; son utilisation passe par revue de
   licence + lecture + décision explicite.
