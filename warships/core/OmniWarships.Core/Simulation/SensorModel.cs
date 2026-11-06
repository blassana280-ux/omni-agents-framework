using System;

namespace OmniWarships.Core.Simulation
{
    /// <summary>
    /// Capteurs : radar (RCS, brouillard, brouillage) et sonar (signature
    /// acoustique, profondeur). La qualite du contact decroit avec la portee.
    /// </summary>
    public static class SensorModel
    {
        public const float FogRadarPenalty = 0.3f;
        public const float JammingPenalty = 0.4f;
        public const float DepthSonarPenalty = 0.6f;

        public static bool DetectRadar(SensorSpec s, ShipState target, float distance, float fog, float jamming, out float quality)
        {
            quality = 0f;
            if (target.DepthM > 5f) return false; // sous-marin plonge : RCS quasi nulle
            float rcsFactor = (float)Math.Sqrt(Math.Max(0.01f, target.Spec.RcsM2 / s.Ref));
            float rangeEff = s.RangeM * rcsFactor * (1f - FogRadarPenalty * fog) * (1f - JammingPenalty * jamming);
            if (distance > rangeEff) return false;
            quality = 1f - 0.2f * (distance / rangeEff);
            return true;
        }

        public static bool DetectSonar(SensorSpec s, ShipState target, float distance, out float quality)
        {
            quality = 0f;
            float depthFactor = target.DepthM / 150f;
            if (depthFactor > 1f) depthFactor = 1f;
            float acousticFactor = Math.Max(0.05f, target.Spec.Acoustic / s.Ref);
            float rangeEff = s.RangeM * acousticFactor * (1f - DepthSonarPenalty * depthFactor);
            if (distance > rangeEff) return false;
            quality = 1f - 0.2f * (distance / rangeEff);
            return true;
        }
    }
}
