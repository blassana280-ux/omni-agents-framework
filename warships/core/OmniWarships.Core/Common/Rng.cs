namespace OmniWarships.Core.Common
{
    /// <summary>LCG deterministe : memes resultats sur .NET, Mono et Unity.</summary>
    public sealed class Rng
    {
        private uint _state;

        public Rng(int seed)
        {
            // evite l'etat 0 et les graines faibles
            _state = (uint)seed * 2654435761u + 1u;
            for (int i = 0; i < 4; i++) NextFloat();
        }

        public float NextFloat()
        {
            _state = _state * 1664525u + 1013904223u;
            return (_state >> 8) / 16777216f; // [0, 1)
        }

        public float NextRange(float lo, float hi)
        {
            return lo + (hi - lo) * NextFloat();
        }

        public int NextInt(int max)
        {
            return (int)(NextFloat() * max);
        }
    }
}
