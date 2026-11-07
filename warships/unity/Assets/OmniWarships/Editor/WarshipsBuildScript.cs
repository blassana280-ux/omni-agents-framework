#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace OmniWarships.Unity.EditorTools
{
    /// <summary>
    /// T-013.1 — methode de build GameCI (input buildMethod de
    /// game-ci/unity-builder@v4, workflow warships-gameci.yml).
    /// Configure le projet Android (ARM64, IL2CPP, minSdk 24, paysage,
    /// APK), garantit la scene de bataille via BattleSceneGuard, puis
    /// compile AVEC scene explicite dans BuildPlayerOptions.scenes.
    /// Tout echec sort avec le code 1 (EditorApplication.Exit) :
    /// GameCI ne peut pas interpreter un echec comme un succes.
    /// </summary>
    public static class WarshipsBuildScript
    {
        public static void BuildAndroid()
        {
            AndroidBuildConfig.Configure();

            string[] scenes = BattleSceneGuard.BuildScenesOrAbort();
            if (scenes == null)
            {
                Fail("ABANDON du build Android : aucune scene de bataille valide (BattleSceneGuard).");
                return;
            }

            string projectDir = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            string apk = Path.Combine(projectDir, "Builds", "omni-warships-v0.1.0.apk");
            Directory.CreateDirectory(Path.GetDirectoryName(apk));

            Debug.Log("OMNI WARSHIPS : build Android en cours — scene incluse : " + scenes[0]);

            BuildReport report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                target = BuildTarget.Android,
                locationPathName = apk,
                scenes = scenes,
                options = BuildOptions.None
            });

            if (report.summary.result != BuildResult.Succeeded)
            {
                Fail("echec du build Android (" + report.summary.result + ", "
                    + report.summary.totalErrors + " erreurs).");
                return;
            }

            Debug.Log("OMNI WARSHIPS : APK OK -> " + apk + " (" + report.summary.totalSize
                + " octets, scene incluse : " + scenes[0] + ")");
        }

        private static void Fail(string message)
        {
            Debug.LogError("OMNI WARSHIPS : " + message);
            EditorApplication.Exit(1);
        }
    }
}
#endif
