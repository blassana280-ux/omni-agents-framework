using System;
using System.Collections.Generic;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.Simulation
{
    /// <summary>
    /// CIWS : defense rapprochee automatique contre les missiles entrants.
    /// Engage CHAQUE missile ennemi a portee (rafale par menace), avec un
    /// taux d'interception probabiliste par seconde et des munitions limitees.
    /// Matrice de fidelite : 55-85% d'une salve subsonique a 1.5 km.
    /// </summary>
    public static class CiwsModel
    {
        public const float KillRatePerS = 0.20f;
        public const float RoundsPerS = 30f; // 1800 coups/min ; 1 tir par menace et par pas

        public static void Engage(ShipState ship, List<Projectile> projectiles, float dt, Rng rng, List<BattleEvent> events, int tick)
        {
            if (ship.Sunk) return;
            foreach (KeyValuePair<string, WeaponState> kv in ship.Weapons)
            {
                WeaponState ws = kv.Value;
                WeaponSpec spec = null;
                foreach (WeaponSpec w in ship.Spec.Weapons)
                {
                    if (w.Id == ws.Id) { spec = w; break; }
                }
                if (spec == null || spec.Kind != WeaponKind.Ciws || ws.Ammo <= 0) continue;

                int spend = (int)(RoundsPerS * dt);
                if (spend < 1) spend = 1;
                foreach (Projectile p in projectiles)
                {
                    if (p.Dead || p.Team == ship.Team || p.Kind != WeaponKind.Ssm) continue;
                    float d = Vec2.Distance(p.Pos, ship.Pos);
                    if (d > spec.RangeM) continue;
                    if (ws.Ammo < spend) break; // a court de munitions : plus d'engagement
                    ws.Ammo -= spend;
                    if (rng.NextFloat() < KillRatePerS * dt)
                    {
                        p.Dead = true;
                        p.Intercepted = true;
                        events.Add(BattleEvent.Intercept(tick, ship.Id, p.Id, p.SourceShipId));
                    }
                }
            }
        }
    }
}
