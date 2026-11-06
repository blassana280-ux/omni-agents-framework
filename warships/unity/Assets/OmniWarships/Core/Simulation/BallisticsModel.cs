using System;
using System.Collections.Generic;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.Simulation
{
    public enum ProjectileKind { Shell, Missile, Torpedo }

    public sealed class Projectile
    {
        public string Id;
        public ProjectileKind Kind;
        public string OwnerId;
        public string TargetId;
        public string WeaponId;
        public Vec2 Pos;
        public Vec2 Dir;
        public float Speed;
        public float RemainingRange;
        public float Damage;
        public GuidanceKind Guidance;
        public float TurnDegS;
        public float Age;
        public float FuelS;
    }

    /// <summary>
    /// Ballistique des projectiles : obus balistiques, missiles guides
    /// (navigation proportionnelle), torpilles droites. Deterministe.
    /// </summary>
    public static class BallisticsModel
    {
        public static void Update(BattleSim sim, List<Projectile> projectiles, float dt, Rng rng)
        {
            for (int i = projectiles.Count - 1; i >= 0; i--)
            {
                var p = projectiles[i];
                p.Age += dt;
                p.FuelS -= dt;

                // guidage
                if (p.Guidance == GuidanceKind.Pn)
                {
                    ShipState target;
                    if (sim.Ships.TryGetValue(p.TargetId, out target) && target.Alive)
                    {
                        Vec2 toTarget = target.Pos - p.Pos;
                        float want = toTarget.HeadingDeg();
                        float cur = p.Dir.HeadingDeg();
                        float diff = NormalizeAngle(want - cur);
                        float turn = p.TurnDegS * dt;
                        // NOTE : HeadingDeg (convention atan2(X, Y)) croit en sens horaire,
                        // alors que RotatedDeg tourne en sens antihoraire (+ = CCW).
                        // Pour converger vers le cap voulu, on applique donc RotatedDeg(-turn).
                        p.Dir = p.Dir.RotatedDeg(-turn).Normalized();
                    }
                }

                Vec2 move = p.Dir * (p.Speed * dt);
                p.Pos += move;
                p.RemainingRange -= move.Length;

                // impact ?
                bool remove = false;
                foreach (var ship in sim.ShipList)
                {
                    if (ship.Id == p.OwnerId || !ship.Alive) continue;
                    // torpille : ignore les navires en surface ? (simplification : tous navires de surface)
                    float hitRadius = ship.Spec.LengthM * 0.35f;
                    if (Vec2.Distance(p.Pos, ship.Pos) <= hitRadius)
                    {
                        float impactSpeed = p.Speed;
                        DamageModel.Apply(sim, ship, p, rng);
                        remove = true;
                        break;
                    }
                }

                if (p.FuelS < 0f && (p.Kind == ProjectileKind.Missile)) remove = true;
                if (p.RemainingRange <= 0f && p.Kind != ProjectileKind.Missile) remove = true;

                if (remove) projectiles.RemoveAt(i);
            }
        }

        private static float NormalizeAngle(float a)
        {
            while (a > 180f) a -= 360f;
            while (a < -180f) a += 360f;
            return a;
        }
    }
}
