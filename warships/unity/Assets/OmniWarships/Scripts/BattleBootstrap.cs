using OmniWarships.Core.Simulation;
using UnityEngine;

namespace OmniWarships.Unity
{
    /// <summary>Configuration de la premiere bataille jouable (modifiable ici).</summary>
    public static class BattleConfig
    {
        public const int Seed = 20261106;      // determinisme : meme graine = meme bataille
        public const int SeaState = 4;
        public const float Fog = 0.10f;
        public const float WindMs = 8f;

        public const string PlayerSpecId = "ws-destroyer-01";
        public const string PlayerTeam = "blue";
        public const float PlayerStartX = 0f;
        public const float PlayerStartZ = 0f;
        public const float PlayerHeadingDeg = 0f;

        public const string EnemySpecId = "ws-frigate-01";
        public const string EnemyTeam = "red";
        public const float EnemyStartX = 6000f;
        public const float EnemyStartZ = 6000f;
        public const float EnemyHeadingDeg = 225f;
    }

    /// <summary>
    /// Point d'entree : auto-construit toute la bataille au lancement
    /// (edition ET build), meme depuis une scene vide, via
    /// [RuntimeInitializeOnLoadMethod]. Aucune scene asset n'est requise ;
    /// l'entree est reproductible et auditable.
    /// </summary>
    public static class BattleBootstrap
    {
        public static BattleDirector Director { get; private set; }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Run()
        {
            if (Director != null) return; // deja lance (domain reload off)
            if (Object.FindObjectOfType<BattleDirector>() != null) return;

            QualityProfiles.Apply(QualityProfiles.Current);

            var go = new GameObject("OMNI Battle Director");
            Director = go.AddComponent<BattleDirector>();

#if UNITY_ANDROID && !UNITY_EDITOR
            Screen.orientation = ScreenOrientation.LandscapeLeft;
#endif
        }
    }
}
