using System;
using OmniWarships.Core.Common;

namespace OmniWarships.Core.Simulation
{
    /// <summary>
    /// Ocean deterministe : houle de Gerstner parametree par l'etat de la
    /// mer, reproduite a l'identique dans le rendu (meme graine, memes
    /// amplitudes) pour que la flottabilite CPU corresponde aux vagues GPU.
    /// </summary>
    public sealed class OceanModel
    {
        public const float SeaWaterDensity = 1025f;

        public readonly int SeaState;
        public readonly float WindMs;
        public readonly float WaveHeight;
        public readonly float WaveLength;
        public readonly float WavePeriod;

        private readonly Rng _rng;
        private readonly GerstnerWave[] _waves;

        public OceanModel(int seaState, float windMs, int seed)
        {
            SeaState = Math.Max(0, Math.Min(9, seaState));
            WindMs = windMs;

            // echelle Douglas simplifiee : hauteur significative par etat de mer
            WaveHeight = SeaState switch
            {
                0 => 0.05f,
                1 => 0.3f,
                2 => 0.6f,
                3 => 1.0f,
                4 => 1.6f,
                5 => 2.5f,
                6 => 4.0f,
                7 => 6.0f,
                8 => 8.5f,
                _ => 11.0f
            };
            WaveLength = 40f + WindMs * 8f;
            WavePeriod = (float)Math.Sqrt(WaveLength / 1.56f); // vague en eau profonde

            _rng = new Rng(seed * 7 + 13);
            int count = 6;
            _waves = new GerstnerWave[count];
            for (int i = 0; i < count; i++)
            {
                float f = i / (float)count;
                _waves[i] = new GerstnerWave
                {
                    DirDeg = _rng.NextRange(f * 360f, (f + 1f) * 360f),
                    Amp = WaveHeight * (1f / (i + 1)) / 2f,
                    Len = WaveLength * _rng.NextRange(0.6f, 1.4f),
                    Phase = _rng.NextRange(0f, 360f)
                };
            }
        }

        public float HeightAt(Vec2 pos, float t)
        {
            float h = 0f;
            for (int i = 0; i < _waves.Length; i++)
            {
                var w = _waves[i];
                var dir = Vec2.FromHeadingDeg(w.DirDeg);
                float k = 2f * (float)Math.PI / w.Len;
                float x = Vec2.Dot(pos, dir) * k + w.Phase * Deg2Rad + t * SpeedOf(w.Len);
                h += w.Amp * (float)Math.Sin(x);
            }
            return h;
        }

        public float RollAt(Vec2 pos, float t, float beamM)
        {
            // pente locale : derivee de la houle, tangente, convertie en degres
            const float eps = 0.5f;
            float hL = HeightAt(pos + new Vec2(-eps, 0f), t);
            float hR = HeightAt(pos + new Vec2(eps, 0f), t);
            float slope = (hR - hL) / (2f * eps);
            return (float)(Math.Atan(slope * beamM * 0.5f) * 180.0 / Math.PI);
        }

        public float PitchAt(Vec2 pos, float t, float lengthM)
        {
            const float eps = 0.5f;
            float hF = HeightAt(pos + new Vec2(0f, eps), t);
            float hB = HeightAt(pos + new Vec2(0f, -eps), t);
            float slope = (hF - hB) / (2f * eps);
            return (float)(Math.Atan(slope * lengthM * 0.3f) * 180.0 / Math.PI);
        }

        private static float Deg2Rad { get { return (float)(Math.PI / 180.0); } }

        private static float SpeedOf(float len)
        {
            return 2f * (float)Math.PI / (float)Math.Sqrt(len / 1.56f);
        }

        private struct GerstnerWave
        {
            public float DirDeg;
            public float Amp;
            public float Len;
            public float Phase;
        }
    }
}
