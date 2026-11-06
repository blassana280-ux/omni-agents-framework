using System;
using System.Collections.Generic;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.Simulation
{
    /// <summary>
    /// Voie d'eau : chaque compartiment breach prend l'eau ; le navire
    /// coule quand la flottabilite perdue depasse le seuil. Un seul
    /// compartiment breached ne coule pas un navire cloisonne ; la
    /// gravite vient du nombre de breches.
    /// </summary>
    public static class FloodingModel
    {
        public const float RatePerS = 0.012f;
        public const float DestroyedRateFactor = 1.5f;
        public const float SinkThreshold = 0.9f;

        /// <summary>Fraction de flottabilite perdue (0..1).</summary>
        public static float LostBuoyancy(ShipState ship)
        {
            float lost = 0f, share = 0f;
            foreach (CompartmentState c in ship.Compartments)
            {
                CompartmentSpec spec = null;
                foreach (CompartmentSpec cs in ship.Spec.Compartments)
                {
                    if (cs.Id == c.Id) { spec = cs; break; }
                }
                float w = spec == null ? 0.1f : spec.Half;
                share += w;
                lost += c.Flooding * w;
            }
            return share <= 0f ? 0f : lost / share;
        }

        public static void Step(ShipState ship, float dt, float timeS)
        {
            if (ship.Sunk) return;
            foreach (CompartmentState c in ship.Compartments)
            {
                if (c.Breached)
                {
                    float rate = RatePerS * (c.Destroyed ? DestroyedRateFactor : 1f);
                    c.Flooding += rate * dt;
                    if (c.Flooding > 1f) c.Flooding = 1f;
                }
            }
            if (LostBuoyancy(ship) >= SinkThreshold || DamageModel.AllCompartmentsDestroyed(ship))
            {
                ship.Sunk = true;
                ship.SunkAtS = timeS;
            }
        }
    }
}
