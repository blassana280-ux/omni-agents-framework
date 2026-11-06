#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEngine;

namespace OmniWarships.Unity.EditorTools
{
    /// <summary>
    /// T-013 — preparation et compilation Android pour le Tecno KN3
    /// (Android 15, 4 Go RAM). S'execute dans l'editeur Unity 2022.3 :
    /// menu « OMNI WARSHIPS ». Aucune scene requise (bootstrap runtime),
    /// aucune permission Android specifique (jeu hors ligne complet).
    /// </summary>
    public static class AndroidBuildConfig
    {
        private const string ApkPath = "Builds/omni-warships-v0.1.0.apk";

        [MenuItem("OMNI WARSHIPS/Android/1. Preparer le build KN3 (ARM64, IL2CPP)")]
        public static void Configure()
        {
            PlayerSettings.companyName = "Lassana Bah";
            PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android, "ml.bah.omniwarships");
            PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel24;
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

        [MenuItem("OMNI WARSHIPS/Android/2. Compiler l'APK (Builds/)")]
        public static void BuildApk()
        {
            Configure();

            var opts = new BuildPlayerOptions
            {
                target = BuildTarget.Android,
                locationPathName = ApkPath,
                options = BuildOptions.None
            };

            // la scene Battle creee par le menu editeur (facultative) :
            // le bootstrap runtime construit tout meme depuis une scene vide.
            if (File.Exists("Assets/Scenes/Battle.unity"))
            {
                opts.scenes = new[] { "Assets/Scenes/Battle.unity" };
            }

            Directory.CreateDirectory("Builds");
            BuildReport report = BuildPipeline.BuildPlayer(opts);
            if (report.summary.result == BuildResult.Succeeded)
            {
                Debug.Log("OMNI WARSHIPS : APK OK -> " + ApkPath
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
