using System;
using OmniWarships.Core.Common;

namespace OmniWarships.Core.Simulation
{
    /// <summary>
    /// Ocean de Gerstner (4 composantes) : fonction deterministe de (x, z, t)
    /// et de l'etat de mer. Identique en CI et dans Unity (flottabilite).
    /// </summary>
    public sealed class OceanModel
    {
        public const int ComponentCount = 4;

        public readonly int SeaState;
        public readonly float WindMs;
        private readonly float[] _amp = new float[ComponentCount];
        private readonly float[] _waveLen = new float[ComponentCount];
        private readonly float[] _dirDeg = new float[ComponentCount];
        private readonly float[] _phase = new float[ComponentCount];

        public OceanModel(int seaState, float windMs, int seed)
        {
            SeaState = Math.Max(0, Math.Min(9, seaState));
            WindMs = windMs;
            var rng = new Rng(seed);
            for (int i = 0; i < ComponentCount; i++)
            {
                // amplitude par composante croissant avec l'etat de mer
                _amp[i] = 0.22f * SeaState * (1f - 0.18f * i);
                _waveLen[i] = 45f + 30f * i + rng.NextFloat() * 25f;
                _dirDeg[i] = rng.NextRange(-25f, 25f);
                _phase[i] = rng.NextRange(0f, (float)(2 * Math.PI));
            }
        }

        public float MaxAmplitude
        {
            get
            {
                float s = 0f;
                for (int i = 0; i < ComponentCount; i++) s += _amp[i];
                return s;
            }
        }

        /// <summary>Hauteur de la houle (m) a la position (x, z) au temps t.</summary>
        public float HeightAt(float x, float z, float t)
        {
            float h = 0f;
            for (int i = 0; i < ComponentCount; i++)
            {
                Vec2 d = Vec2.FromHeadingDeg(_dirDeg[i]);
                float k = (float)(2 * Math.PI / _waveLen[i]);
                float phase = k * (d.X * x + d.Y * z) - k * (float)Math.Sqrt(6.25 * _waveLen[i]) * t + _phase[i];
                h += _amp[i] * (float)Math.Sin(phase);
            }
            return h;
        }

        /// <summary>Gite approximative (degres) sur l'axe traversier du navire.</summary>
        public float RollAt(Vec2 pos, float headingDeg, float beamM, float t)
        {
            Vec2 across = Vec2.FromHeadingDeg(headingDeg + 90f);
            float half = Math.Max(2f, beamM * 0.5f);
            float port = HeightAt((pos + across * half).X, (pos + across * half).Y, t);
            float star = HeightAt((pos - across * half).X, (pos - across * half).Y, t);
            float roll = (float)(Math.Atan2(port - star, 2 * half) * 180.0 / Math.PI);
            float cap = SeaState * 2.5f;
            if (roll > cap) roll = cap;
            if (roll < -cap) roll = -cap;
            return roll;
        }

        /// <summary>Tangage approximatif (degres) sur l'axe longitudinal.</summary>
        public float PitchAt(Vec2 pos, float headingDeg, float lengthM, float t)
        {
            Vec2 fwd = Vec2.FromHeadingDeg(headingDeg);
            float half = Math.Max(5f, lengthM * 0.4f);
            float bow = HeightAt((pos + fwd * half).X, (pos + fwd * half).Y, t);
            float stern = HeightAt((pos - fwd * half).X, (pos - fwd * half).Y, t);
            return (float)(Math.Atan2(bow - stern, 2 * half) * 180.0 / Math.PI);
        }
    }
}
