using System;
using UnityEngine;
using UnityEngine.Rendering;
#if UNITY_2022_3_OR_NEWER
using UnityEngine.Rendering.Universal;
#endif

namespace OmniWarships.Unity
{
    public enum QualityProfile { Ultra = 0, High = 1, Medium = 2, Low = 3, Adaptive = 4 }

    /// <summary>
    /// Profils graphiques Ultra / Eleve / Moyen / Faible / Adaptatif.
    /// Appareil de reference minimal : Tecno KN3 (Android 15, 4 Go RAM).
    /// Aucun FPS n'estdeclare : le HUD mesure et affiche les FPS reels.
    /// </summary>
    public static class QualityProfiles
    {
        public static QualityProfile Current = QualityProfile.High;

        public static event Action<QualityProfile> OnChanged;

        // ocean (segments du maillage), ombres, renderScale URP
        private static readonly int[] OceanSegments = { 128, 96, 64, 48, 64 };
        private static readonly ShadowQuality[] Shadows = {
            ShadowQuality.All, ShadowQuality.All, ShadowQuality.HardOnly, ShadowQuality.Disable, ShadowQuality.HardOnly
        };
        private static readonly float[] RenderScale = { 1.00f, 0.90f, 0.85f, 0.75f, 0.85f };
        private static readonly float[] ShadowDist = { 260f, 180f, 120f, 0f, 120f };

        public static int CurrentOceanSegments
        {
            get { return OceanSegments[(int)ProfileIndex(Current)]; }
        }

        public static bool EffectsEnabled
        {
            get { return ProfileIndex(Current) <= (int)QualityProfile.Medium; }
        }

        public static void Cycle()
        {
            int next = ((int)Current + 1) % 5;
            Apply((QualityProfile)next);
        }

        public static void Apply(QualityProfile p)
        {
            Current = p;
            int i = (int)ProfileIndex(p);
            QualitySettings.shadows = Shadows[i];
            QualitySettings.shadowDistance = ShadowDist[i];
            Application.targetFrameRate = 60;

#if UNITY_2022_3_OR_NEWER
            UniversalRenderPipelineAsset urp = UniversalRenderPipeline.asset as UniversalRenderPipelineAsset;
            if (urp != null) urp.renderScale = RenderScale[i];
#endif
            if (OnChanged != null) OnChanged(p);
        }

        /// <summary>Adaptatif suit le profil calcule par le HUD (mesure reelle).</summary>
        public static void ApplyAdaptiveTarget(QualityProfile target)
        {
            if (Current != QualityProfile.Adaptive) return;
            ApplyAdaptiveOnly(target);
        }

        private static void ApplyAdaptiveOnly(QualityProfile target)
        {
            int i = (int)ProfileIndex(target);
            QualitySettings.shadows = Shadows[i];
            QualitySettings.shadowDistance = ShadowDist[i];
#if UNITY_2022_3_OR_NEWER
            UniversalRenderPipelineAsset urp = UniversalRenderPipeline.asset as UniversalRenderPipelineAsset;
            if (urp != null) urp.renderScale = RenderScale[i];
#endif
            _effectiveAdaptive = target;
        }

        private static QualityProfile _effectiveAdaptive = QualityProfile.Medium;
        public static QualityProfile EffectiveProfile
        {
            get { return Current == QualityProfile.Adaptive ? _effectiveAdaptive : Current; }
        }

        private static int ProfileIndex(QualityProfile p)
        {
            if (p == QualityProfile.Adaptive) return (int)QualityProfile.Medium;
            return (int)p;
        }

        public static string Label(QualityProfile p)
        {
            switch (p)
            {
                case QualityProfile.Ultra: return "Ultra";
                case QualityProfile.High: return "Eleve";
                case QualityProfile.Medium: return "Moyen";
                case QualityProfile.Low: return "Faible";
                default: return "Adaptatif";
            }
        }
    }
}
