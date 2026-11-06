using System;
using System.Collections.Generic;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.Simulation
{
    /// <summary>
    /// CIWS : defense rapprochee automatique contre les missiles entrants
    /// (taux d'interception probabiliste par seconde, munitions limitees).
    /// </summary>
    public static class CiwsModel
    {
        public const float KillRatePerS = 0.20f;
        public const float RoundsPerS = 80f;

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

                Projectile nearest = null;
                float best = float.MaxValue;
                foreach (Projectile p in projectiles)
                {
                    if (p.Dead || p.Team == ship.Team || p.Kind != WeaponKind.Ssm) continue;
                    float d = Vec2.Distance(p.Pos, ship.Pos);
                    if (d > spec.RangeM || d >= best) continue;
                    nearest = p; best = d;
                }
                if (nearest == null) continue;

                int spend = (int)(RoundsPerS * dt);
                if (spend < 1) spend = 1;
                ws.Ammo -= spend;
                if (ws.Ammo < 0) ws.Ammo = 0;

                if (rng.NextFloat() < KillRatePerS * dt)
                {
                    nearest.Dead = true;
                    nearest.Intercepted = true;
                    events.Add(BattleEvent.Intercept(tick, ship.Id, nearest.Id, nearest.SourceShipId));
                }
            }
        }
    }
}
