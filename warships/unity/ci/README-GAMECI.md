# Pipeline de compilation Unity (GameCI) — PRÉPARÉ, INACTIF

Statut honnête : **préparé, non activé**. Ce pipeline ne s'exécute pas tant
que Lassana n'a pas décidé de la licence Unity (GameCI utilise la licence
personnelle/protégée Unity pour les builders). Le fichier `gameci-example.yml`
de ce dossier est un EXEMPLE : il n'est PAS dans .github/workflows/, donc
GitHub Actions ne le déclenche jamais.

## Ce qu'il ferait une fois activé

1. Copier `gameci-example.yml` vers `.github/workflows/warships-gameci.yml`.
2. Renseigner les secrets du dépôt : UNITY_LICENSE (contenu du fichier
   .ulf), UNITY_EMAIL, UNITY_PASSWORD (ou un Personal Access Token).
3. Le job build-android :
   - image unityci/editor:2022.3.62f1-android3-1 ;
   - test du projet (compilation C# + scripts de test) ;
   - build Android (ARM64, IL2CPP, cible API 34) -> artefact APK ;
   - upload de l'APK en artefact téléchargeable sur la PR.
4. Les jobs existants (data, core, couche Unity) restent inchangés.

## Ce que ce pipeline NE fait PAS

- Il ne mesure pas les FPS sur Tecno KN3 (aucun appareil réel branché) ;
- il ne remplace pas la validation manuelle sur appareil ;
- il n'est pas compté comme « compilée » tant que le run n'est pas vert.

## Pourquoi l'inactivité

La licence Unity personnelle gratuite couvre ce dépôt, mais son activation
dans une CI publique exige des secrets et une acceptation explicite de
Lassana. Rien n'est activé sans son accord — règle du projet.
