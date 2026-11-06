using System;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.AI
{
    /// <summary>Tableau de menace : score de chaque contact pour la priorisation.</summary>
    public static class ThreatBoard
    {
        public static float ClassWeight(ShipClass c)
        {
            switch (c)
            {
                case ShipClass.Corvette: return 0.5f;
                case ShipClass.Frigate: return 1.0f;
                case ShipClass.Destroyer: return 1.3f;
                case ShipClass.Cruiser: return 1.6f;
                case ShipClass.Battleship: return 2.0f;
                case ShipClass.Carrier: return 1.2f;
                case ShipClass.Submarine: return 1.5f;
                default: return 1.0f;
            }
        }

        /// <summary>Menace : poids de classe x confiance du contact, decay avec la distance.</summary>
        public static float Score(ShipState self, Contact ct, ShipState target)
        {
            float dist = Vec2.Distance(self.Pos, ct.EstimatedPos);
            return ClassWeight(target.Spec.Class) * (0.5f + 0.5f * ct.Quality) / (1f + dist / 1000f);
        }
    }
}
