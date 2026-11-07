#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OmniWarships.Unity.EditorTools
{
    /// <summary>
    /// T-013.1 — garde-fou de la scene de bataille. Chemin UNIQUE partage
    /// par le menu editeur, la compilation locale (AndroidBuildConfig) et
    /// le build cloud GameCI (WarshipsBuildScript). La scene est :
    ///   1. creee automatiquement si elle manque (creation additive puis
    ///      fermeture : la scene ouverte par l utilisateur n est jamais
    ///      ecrasee) ;
    ///   2. enregistree dans les Build Settings ;
    ///   3. incluse EXPLICITEMENT dans BuildPlayerOptions.scenes.
    /// Un bootstrap runtime ne suffit PAS a produire un jeu : si aucune
    /// scene valide n est disponible, le build doit echouer clairement —
    /// jamais supposer que le runtime s en sortira seul.
    /// </summary>
    public static class BattleSceneGuard
    {
        public const string BattleScenePath = "Assets/OmniWarships/Battle.unity";

        /// <summary>Chemin absolu sur disque (le repertoire courant n est
        /// PAS garanti etre la racine du projet en mode batch).</summary>
        private static string BattleSceneAbsolutePath()
        {
            return Path.GetFullPath(Path.Combine(Application.dataPath, "..", BattleScenePath));
        }

        /// <summary>Vrai si la scene de bataille existe sur le disque.</summary>
        public static bool BattleSceneExists()
        {
            return File.Exists(BattleSceneAbsolutePath());
        }

        /// <summary>Cree la scene de bataille si elle manque. Ne modifie
        /// JAMAIS la scene courante de l editeur. Retourne vrai si la
        /// scene existe a la sortie.</summary>
        public static bool EnsureBattleScene()
        {
            if (BattleSceneExists())
            {
                return true;
            }
            var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Additive);
            bool ok = EditorSceneManager.SaveScene(scene, BattleScenePath);
            EditorSceneManager.CloseScene(scene, true);
            if (!ok)
            {
                Debug.LogError("OMNI WARSHIPS : creation impossible de la scene " + BattleScenePath + " — ABANDON.");
                return false;
            }
            AssetDatabase.SaveAssets();
            Debug.Log("OMNI WARSHIPS : scene de bataille creee automatiquement : " + BattleScenePath);
            return true;
        }

        /// <summary>Recree la scene (action manuelle explicite du menu)
        /// et l enregistre dans les Build Settings.</summary>
        public static bool RecreateBattleScene()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
            bool ok = EditorSceneManager.SaveScene(scene, BattleScenePath);
            if (!ok)
            {
                Debug.LogError("OMNI WARSHIPS : scene non sauvegardee (" + BattleScenePath + ").");
                return false;
            }
            AssetDatabase.SaveAssets();
            RegisterInBuildSettings();
            Debug.Log("OMNI WARSHIPS : scene sauvegardee " + BattleScenePath + " et ajoutee aux Build Settings.");
            return true;
        }

        /// <summary>Enregistre la scene (activee) dans les Build Settings
        /// — les builds via GameCI utilisent les scenes activees.</summary>
        public static void RegisterInBuildSettings()
        {
            EditorBuildSettings.scenes = new[]
            {
                new EditorBuildSettingsScene(BattleScenePath, true)
            };
        }

        /// <summary>
        /// Retourne les scenes a compiler (scene garantee existante et
        /// enregistree en Build Settings), ou NULL si aucune scene valide
        /// — le build doit alors refuser explicitement.
        /// </summary>
        public static string[] BuildScenesOrAbort()
        {
            if (!EnsureBattleScene() || !BattleSceneExists())
            {
                return null;
            }
            RegisterInBuildSettings();
            return new[] { BattleScenePath };
        }
    }
}
#endif
