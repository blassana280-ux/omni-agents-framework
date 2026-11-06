using System;
using System.Collections.Generic;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.Simulation
{
    /// <summary>Projectile en vol (obus, missile, torpille).</summary>
    public sealed class Projectile
    {
        public string Id;
        public string Team;
        public string SourceShipId;
        public WeaponKind Kind;
        public DamageKind DamageKind;
        public float Damage;
        public Vec2 Pos;
        public float Altitude;
        public Vec2 Vel;
        public float Vz;
        public float Speed;
        public string TargetShipId;
        public GuidanceKind Guidance;
        public float AgeS;
        public float MaxAgeS;
        public float TraveledM;
        public float ArmDistM;
        public bool Armed = true;
        public bool Dead;
        public bool Intercepted;
    }

    /// <summary>
    /// Balistique : trajectoire d'obus (gravite, arc bas, solution exacte
    /// de tir + integration parabolique exacte par pas), guidage missile
    /// par rotation bornee, course droite des torpilles avec armement.
    /// </summary>
    public static class BallisticsModel
    {
        public const float Gravity = 9.81f;
        public const float SsmMaxTurnDegS = 20f;
        public const float SamMaxTurnDegS = 35f;
        public const float TorpedoArmDistM = 300f;
        public const float TorpedoDepthM = 4f;

        /// <summary>Point de visee sur cible a vitesse constante.</summary>
        public static Vec2 PredictIntercept(Vec2 shooterPos, Vec2 targetPos, Vec2 targetVel, float projectileSpeed)
        {
            float d = Vec2.Distance(shooterPos, targetPos);
            float t = d / Math.Max(1f, projectileSpeed);
            Vec2 aim = targetPos + targetVel * t;
            for (int i = 0; i < 3; i++)
            {
                d = Vec2.Distance(shooterPos, aim);
                t = d / Math.Max(1f, projectileSpeed);
                aim = targetPos + targetVel * t;
            }
            return aim;
        }

        public static Projectile Launch(ShipState shooter, WeaponSpec w, Vec2 aim, string targetId, float spreadDeg, Rng rng, int serial)
        {
            var p = new Projectile();
            p.Id = "p" + serial;
            p.Team = shooter.Team;
            p.SourceShipId = shooter.Id;
            p.Kind = w.Kind;
            p.Damage = w.Damage;
            p.Speed = w.SpeedMs;
            p.TargetShipId = targetId;
            p.Guidance = w.Guidance;
            p.TraveledM = 0f;
            switch (w.Kind)
            {
                case WeaponKind.Gun:
                    {
                        p.DamageKind = DamageKind.Shell;
                        p.Pos = shooter.Pos;
                        p.Altitude = 12f;
                        float dx = Vec2.Distance(shooter.Pos, aim);
                        // denivele cible - tir : le point vise (~3 m) est 9 m sous le pont (12 m)
                        float y0 = -9f;
                        double v = w.SpeedMs;
                        double disc = v * v * v * v - Gravity * (Gravity * dx * dx + 2.0 * y0 * v * v);
                        if (disc < 0.0) disc = 0.0;
                        double tanTheta = (dx < 1f) ? 0.0 : (v * v - Math.Sqrt(disc)) / (Gravity * dx);
                        double theta = Math.Atan(tanTheta);
                        Vec2 dir = (aim - shooter.Pos).Normalized();
                        dir = dir.RotatedDeg(rng.NextRange(-spreadDeg, spreadDeg));
                        p.Vel = dir * ((float)(v * Math.Cos(theta)));
                        p.Vz = (float)(v * Math.Sin(theta));
                        p.Armed = true;
                        p.MaxAgeS = 60f;
                        break;
                    }
                case WeaponKind.Ssm:
                case WeaponKind.Sam:
                    {
                        p.DamageKind = DamageKind.Missile;
                        p.Pos = shooter.Pos;
                        p.Altitude = 12f;
                        Vec2 dir = (aim - shooter.Pos).Normalized();
                        dir = dir.RotatedDeg(rng.NextRange(-spreadDeg, spreadDeg));
                        p.Vel = dir * w.SpeedMs;
                        p.Vz = 0f;
                        p.Armed = true;
                        p.MaxAgeS = (w.RangeM / Math.Max(1f, w.SpeedMs)) + 6f;
                        break;
                    }
                case WeaponKind.Torpedo:
                    {
                        p.DamageKind = DamageKind.Torpedo;
                        p.Pos = shooter.Pos;
                        p.Altitude = -TorpedoDepthM;
                        Vec2 dir = (aim - shooter.Pos).Normalized();
                        dir = dir.RotatedDeg(rng.NextRange(-spreadDeg, spreadDeg));
                        p.Vel = dir * w.SpeedMs;
                        p.Vz = 0f;
                        p.Armed = false;
                        p.ArmDistM = TorpedoArmDistM;
                        p.MaxAgeS = (w.RangeM / Math.Max(1f, w.SpeedMs)) + 10f;
                        break;
                    }
                default:
                    {
                        p.DamageKind = DamageKind.Missile;
                        p.Pos = shooter.Pos;
                        p.Altitude = 12f;
                        p.Vel = (aim - shooter.Pos).Normalized() * w.SpeedMs;
                        p.MaxAgeS = 30f;
                        break;
                    }
            }
            return p;
        }

        /// <summary>Un pas de vol. Renvoie le navire touche, sinon null.</summary>
        public static ShipState Step(Projectile p, List<ShipState> ships, float dt)
        {
            if (p.Dead) return null;
            p.AgeS += dt;

            if (p.Kind == WeaponKind.Gun)
            {
                Vec2 prevPos = p.Pos;
                float prevAlt = p.Altitude;
                p.Pos = p.Pos + p.Vel * dt;
                // integration exacte de la gravite sur le pas (parabole)
                p.Altitude = p.Altitude + p.Vz * dt - 0.5f * Gravity * dt * dt;
                p.Vz -= Gravity * dt;
                p.TraveledM += p.Speed * dt;
                // franchissement de la silhouette du navire (0..22 m)
                if (p.Altitude <= 22f)
                {
                    ShipState hit = HitCheck(p, ships, 25f);
                    if (hit != null) { p.Dead = true; return hit; }
                }
                // impact a la surface : point interpole (precision de la solution de tir)
                if (p.Altitude <= 0.5f && prevAlt > p.Altitude)
                {
                    float denom = prevAlt - p.Altitude;
                    float frac = denom > 0.0001f ? (prevAlt - 0.5f) / denom : 1f;
                    p.Pos = prevPos + p.Vel * (frac * dt);
                    p.Dead = true;
                    return HitCheck(p, ships, 25f);
                }
                if (p.AgeS > p.MaxAgeS) p.Dead = true;
                return null;
            }

            if (p.Kind == WeaponKind.Ssm || p.Kind == WeaponKind.Sam)
            {
                ShipState target = null;
                foreach (ShipState s in ships)
                {
                    if (s.Id == p.TargetShipId) { target = s; break; }
                }
                if (target != null && !target.Sunk)
                {
                    Vec2 desired = (target.Pos - p.Pos).Normalized();
                    Vec2 cur = p.Vel.Normalized();
                    float maxTurn = (p.Kind == WeaponKind.Sam ? SamMaxTurnDegS : SsmMaxTurnDegS) * dt;
                    float diff = HeadingDiff(cur.HeadingDeg(), desired.HeadingDeg());
                    float turn = Math.Max(-maxTurn, Math.Min(maxTurn, diff));
                    p.Vel = cur.RotatedDeg(turn) * p.Speed;
                }
                p.Pos = p.Pos + p.Vel * dt;
                p.TraveledM += p.Speed * dt;
                ShipState hit = HitCheck(p, ships, 2f);
                if (hit != null) { p.Dead = true; return hit; }
                if (p.AgeS > p.MaxAgeS) p.Dead = true;
                return null;
            }

            if (p.Kind == WeaponKind.Torpedo)
            {
                p.Pos = p.Pos + p.Vel * dt;
                p.TraveledM += p.Speed * dt;
                if (!p.Armed && p.TraveledM >= p.ArmDistM) p.Armed = true;
                if (p.Altitude <= 0f)
                {
                    ShipState hit = HitCheck(p, ships, 2f);
                    if (hit != null)
                    {
                        p.Dead = true;
                        if (p.Armed) return hit; // frappe non armee : aucun degat
                        return null;
                    }
                }
                if (p.AgeS > p.MaxAgeS) p.Dead = true;
                return null;
            }

            p.Pos = p.Pos + p.Vel * dt;
            return null;
        }

        private static ShipState HitCheck(Projectile p, List<ShipState> ships, float extraRadiusM)
        {
            foreach (ShipState s in ships)
            {
                if (s.Team == p.Team || s.Sunk) continue;
                float radius = s.Spec.BeamM * 0.5f + extraRadiusM;
                if (Vec2.Distance(p.Pos, s.Pos) > radius) continue;
                bool depthOk = (p.Kind == WeaponKind.Torpedo) ? (s.DepthM <= 15f) : (s.DepthM < 15f);
                if (!depthOk) continue;
                if (p.Kind == WeaponKind.Gun)
                {
                    if (p.Altitude < -2f || p.Altitude > 22f) continue;
                }
                else if (p.Altitude > 20f) continue;
                return s;
            }
            return null;
        }

        private static float HeadingDiff(float from, float to)
        {
            float d = to - from;
            while (d > 180f) d -= 360f;
            while (d < -180f) d += 360f;
            return d;
        }
    }
}
