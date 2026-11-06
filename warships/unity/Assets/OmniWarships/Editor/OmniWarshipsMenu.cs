using System.Collections.Generic;
using OmniWarships.Core.Spec;
using OmniWarships.Unity;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace OmniWarships.Unity.EditorTools
{
    /// <summary>
    /// Menu d'outils d'edition : configuration URP, creation de la scene de
    /// bataille, verification des specs embarquees. Chaque action logge
    /// clairement son resultat — aucun echec silencieux.
    /// </summary>
    public static class OmniWarshipsMenu
    {
        private const string AssetDir = "Assets/OmniWarships";

        [MenuItem("Omni Warships/1. Configurer le pipeline URP")]
        public static void ConfigureUrp()
        {
            try
            {
                var rendererData = ScriptableObject.CreateInstance<UniversalRendererData>();
                var pipelineAsset = ScriptableObject.CreateInstance<UniversalRenderPipelineAsset>();

                var so = new SerializedObject(pipelineAsset);
                so.Update();
                var list = so.FindProperty("m_RendererDataList");
                if (list == null)
                {
                    Debug.LogError("OMNI WARSHIPS : propriete m_RendererDataList introuvable (version URP inattendue). " +
                        "Creation manuelle : Assets > Create > Rendering > URP Asset (with Universal Renderer), " +
                        "puis Project Settings > Graphics > Scriptable Render Pipeline Settings.");
                    return;
                }
                list.arraySize = 1;
                list.GetArrayElementAtIndex(0).objectReferenceValue = rendererData;
                so.ApplyModifiedProperties();

                AssetDatabase.CreateAsset(rendererData, AssetDir + "/URP_Renderer.asset");
                AssetDatabase.CreateAsset(pipelineAsset, AssetDir + "/URP_Settings.asset");
                AssetDatabase.SaveAssets();

                GraphicsSettings.defaultRenderPipeline = pipelineAsset;
                Debug.Log("OMNI WARSHIPS : URP configure (" + AssetDir + "/URP_Settings.asset). " +
                    "Ombres et HDR sont activables dans l'asset URP.");
            }
            catch (System.Exception ex)
            {
                Debug.LogError("OMNI WARSHIPS : echec de la configuration URP automatique (" + ex.Message + "). " +
                    "Fallback manuel : Assets > Create > Rendering > URP Asset (with Universal Renderer), " +
                    "puis Project Settings > Graphics > assigner l'asset.");
            }
        }

        [MenuItem("Omni Warships/2. Creer la scene Bataille")]
        public static void CreateBattleScene()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
            // la bataille s'auto-construit au Play via BattleBootstrap ; la scene
            // n'a besoin d'aucun objet specifique.
            bool ok = EditorSceneManager.SaveScene(scene, AssetDir + "/Battle.unity");
            if (ok) Debug.Log("OMNI WARSHIPS : scene sauvegardee " + AssetDir + "/Battle.unity — appuyer sur Play.");
            else Debug.LogError("OMNI WARSHIPS : scene non sauvegardee (dossier " + AssetDir + " absent ?)");
        }

        [MenuItem("Omni Warships/3. Verifier les specs embarquees")]
        public static void VerifySpecs()
        {
            List<ShipSpec> specs = SpecSource.LoadAll();
            if (specs.Count == 0)
            {
                Debug.LogError("OMNI WARSHIPS : AUCUNE spec dans Resources/Ships — verifier Assets/OmniWarships/Resources/Ships/");
                return;
            }
            foreach (ShipSpec s in specs)
            {
                Debug.Log("OMNI WARSHIPS spec OK : " + s.Id + " (" + s.Class + ", " +
                    s.Weapons.Count + " armes, " + s.Compartments.Count + " compartiments)");
            }
            Debug.Log("OMNI WARSHIPS : " + specs.Count + " specs chargees et validees (parse reussi).");
        }
    }
}
