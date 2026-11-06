using System;
using System.Collections.Generic;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.Simulation
{
    /// <summary>
    /// Voies d'eau : chaque compartiment perce prend l'eau selon sa
    /// profondeur (surface libre), reduisant la flottabilite.
    /// </summary>
    public static class FloodingModel
    {
        public const float MaxFloodRatePerS = 0.06f;

        public static void Update(BattleSim sim, float dt, Rng rng)
        {
            foreach (var ship in sim.ShipList)
            {
                if (!ship.Alive) continue;

                float buoy = 0f;
                float totalMax = 0f;
                foreach (var cs in ship.Compartments.Values)
                {
                    totalMax += cs.HpMax;
                    if (cs.Destroyed && !cs.Breached)
                    {
                        cs.Breached = true;
                        cs.Flooding = Math.Max(cs.Flooding, 0.3f);
                    }
                    if (cs.Breached)
                    {
                        cs.Flooding += MaxFloodRatePerS * dt * (1f + 0.5f * (1f - ship.FractionHp));
                        if (cs.Flooding >= 1f)
                        {
                            cs.Flooding = 1f;
                        }
                    }
                    buoy += cs.HpMax * (1f - cs.Flooding);
                }
                ship.Buoyancy = totalMax <= 0f ? 1f : buoy / totalMax;
                ship.LostBuoyancy = 1f - ship.Buoyancy;

                // flottabilite perdue : coule
                if (ship.Buoyancy <= 0.35f && ship.Alive)
                {
                    ship.Alive = false;
                    sim.Events.Add(new BattleEvent
                    {
                        Kind = BattleEventKind.Sunk,
                        Time = sim.Time,
                        Target = ship.Id,
                        X = ship.Pos.X,
                        Y = ship.Pos.Y,
                        Detail = ship.FloodingTotal
                    });
                }
            }
        }

        public static void StartFlooding(CompartmentState cs, float rate, Rng rng)
        {
            cs.Breached = true;
            cs.Flooding = Math.Max(cs.Flooding, 0.15f + 0.2f * rate);
        }
    }
}
