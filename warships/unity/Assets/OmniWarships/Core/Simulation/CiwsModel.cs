using System;
using System.Collections.Generic;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.Simulation
{
    /// <summary>
    /// CIWS (Phalanx-like, regle observable) : chaque navire equipe engage
    /// chaque missile ennemi a portee, un tir par menace et par tick.
    /// </summary>
    public static class CiwsModel
    {
        public const float EngageRangeM = 1800f;
        public const float KillRatePerS = 0.20f;

        public static void Update(BattleSim sim, List<Projectile> projectiles, float dt, Rng rng)
        {
            // pour chaque paire (defenseur, missile) : chance d'interception
            for (int i = projectiles.Count - 1; i >= 0; i--)
            {
                var p = projectiles[i];
                if (p.Kind != ProjectileKind.Missile) continue;

                ShipState owner;
                if (!sim.Ships.TryGetValue(p.OwnerId, out owner)) continue;

                foreach (var ship in sim.ShipList)
                {
                    if (!ship.Alive || ship.Id == p.OwnerId) continue;
                    if (owner.PlayerControlled == ship.PlayerControlled) continue; // allie : ne tire pas

                    WeaponState ws;
                    if (!ship.Weapons.TryGetValue("ciws-1", out ws)) continue;
                    if (ws.Ammo <= 0) continue;

                    float dist = Vec2.Distance(ship.Pos, p.Pos);
                    if (dist > EngageRangeM) continue;

                    // un tir par menace et par tick : spend = RoundsPerS * dt
                    const float RoundsPerS = 30f;
                    float spend = RoundsPerS * dt;
                    if (ws.Ammo < spend) continue;
                    ws.Ammo -= spend;

                    float killP = KillRatePerS * dt * (1f - dist / (EngageRangeM * 1.2f));
                    if (rng.NextFloat() < killP)
                    {
                        sim.Events.Add(new BattleEvent
                        {
                            Kind = BattleEventKind.Intercept,
                            Time = sim.Time,
                            Source = ship.Id,
                            Target = p.OwnerId,
                            Weapon = "ciws-1",
                            X = p.Pos.X,
                            Y = p.Pos.Y,
                            Detail = dist
                        });
                        projectiles.RemoveAt(i);
                        break;
                    }
                }
            }
        }
    }
}
