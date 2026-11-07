#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace OmniWarships.Unity.EditorTools
{
    /// <summary>
    /// T-013 / T-013.1 — preparation et compilation Android pour le
    /// Tecno KN3 (Android 15, 4 Go RAM). S execute dans l editeur Unity
    /// 2022.3 : menu « OMNI WARSHIPS ». La scene de bataille est
    /// garantee par BattleSceneGuard (creee si absente, enregistree en
    /// Build Settings, incluse EXPLICITEMENT dans
    /// BuildPlayerOptions.scenes, echec clair sinon — le bootstrap
    /// runtime ne suffit jamais a produire un jeu sans scene incluse).
    /// Aucune permission Android (jeu hors ligne complet).
    /// </summary>
    public static class AndroidBuildConfig
    {
        private const string ApkName = "omni-warships-v0.1.0.apk";

        [MenuItem("OMNI WARSHIPS/Android/1. Preparer le build KN3 (ARM64, IL2CPP)")]
        public static void Configure()
        {
            PlayerSettings.companyName = "Lassana Bah";
            PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android, "ml.bah.omniwarships");
            PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel24;
            if (PlayerSettings.Android.bundleVersionCode < 1)
            {
                PlayerSettings.Android.bundleVersionCode = 1;
            }
            PlayerSettings.defaultInterfaceOrientation = UIOrientation.LandscapeLeft;
            PlayerSettings.allowedAutorotateToLandscapeLeft = true;
            PlayerSettings.allowedAutorotateToLandscapeRight = true;
            PlayerSettings.allowedAutorotateToPortrait = false;
            PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;
            PlayerSettings.stripEngineCode = true;
            EditorUserBuildSettings.androidBuildSystem = AndroidBuildSystem.Gradle;
            EditorUserBuildSettings.buildAppBundle = false; // APK (pas AAB)
            QualitySettings.vSyncCount = 0;
            Application.targetFrameRate = 60;
            AssetDatabase.SaveAssets();
            Debug.Log("OMNI WARSHIPS : projet configure pour Android ARM64 IL2CPP, "
                + "paysage verrouille, Gradle/APK, cible Tecno KN3 (Android 15, 4 Go).");
        }

        [MenuItem("OMNI WARSHIPS/Android/2. Compiler l APK (Builds/)")]
        public static void BuildApk()
        {
            Configure();

            string[] scenes = BattleSceneGuard.BuildScenesOrAbort();
            if (scenes == null)
            {
                Debug.LogError("OMNI WARSHIPS : ABANDON du build Android — aucune scene de bataille valide (BattleSceneGuard).");
                return;
            }

            string projectDir = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            string apk = Path.Combine(projectDir, "Builds", ApkName);
            Directory.CreateDirectory(Path.Combine(projectDir, "Builds"));

            Debug.Log("OMNI WARSHIPS : build Android en cours — scene incluse : " + scenes[0]);

            var opts = new BuildPlayerOptions
            {
                target = BuildTarget.Android,
                locationPathName = apk,
                scenes = scenes,
                options = BuildOptions.None
            };

            BuildReport report = BuildPipeline.BuildPlayer(opts);
            if (report.summary.result == BuildResult.Succeeded)
            {
                Debug.Log("OMNI WARSHIPS : APK OK -> " + apk
                    + " (" + report.summary.totalSize + " octets, "
                    + report.summary.totalErrors + " erreur)");
            }
            else
            {
                Debug.LogError("OMNI WARSHIPS : echec du build Android ("
                    + report.summary.result + ", " + report.summary.totalErrors + " erreurs)");
            }
        }
    }
}
#endif
