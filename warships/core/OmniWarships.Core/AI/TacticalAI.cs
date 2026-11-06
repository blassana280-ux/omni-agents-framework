using System;
using System.Collections.Generic;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.AI
{
    /// <summary>
    /// IA tactique embarquee : priorite aux menaces, tenue de distance par
    /// classe, esquive des torpilles, tir des armes dans leur portee apres
    /// un temps de reaction. Deterministe (aucun aleatoire propre).
    /// </summary>
    public sealed class TacticalAI
    {
        public const float ReactionTimeS = 1.0f;

        private readonly Dictionary<string, int> _firstSeenTick = new Dictionary<string, int>();

        public ShipCommand Decide(ShipState s, BattleSim sim)
        {
            var cmd = new ShipCommand();
            if (s.Sunk) return cmd;

            // 1. torpille entrante : esquive perpendiculaire pleine vitesse
            Projectile torp = null; float torpDist = float.MaxValue;
            foreach (Projectile p in sim.Projectiles)
            {
                if (p.Dead || p.Team == s.Team || p.Kind != WeaponKind.Torpedo) continue;
                float d = Vec2.Distance(p.Pos, s.Pos);
                if (d < 2500f && d < torpDist) { torp = p; torpDist = d; }
            }
            if (torp != null)
            {
                cmd.Throttle = 1f;
                float away = (s.Pos - torp.Pos).HeadingDeg();
                float side = HeadingDelta(s.HeadingDeg, away) >= 0f ? 90f : -90f;
                Steer(cmd, s, away + side);
                return cmd;
            }

            // 2. cible : contact au meilleur score de menace
            ShipState target = null; float best = 0f;
            foreach (KeyValuePair<string, Contact> kv in s.Contacts)
            {
                ShipState t = sim.Ship(kv.Value.ShipId);
                if (t == null || t.Sunk) continue;
                float score = ThreatBoard.Score(s, kv.Value, t);
                if (score > best) { best = score; target = t; }
            }

            if (target == null)
            {
                cmd.Throttle = 0.4f; // patrouille lente
                cmd.Rudder = 0.1f;
                return cmd;
            }

            float dist = Vec2.Distance(s.Pos, target.Pos);
            float pref = PreferredRangeM(s.Spec.Class);
            float bearing = (target.Pos - s.Pos).HeadingDeg();

            if (dist > pref * 1.15f)
            {
                cmd.Throttle = 1f;
                Steer(cmd, s, bearing);
            }
            else if (dist < pref * 0.7f)
            {
                cmd.Throttle = 1f;
                Steer(cmd, s, bearing + 180f);
            }
            else
            {
                cmd.Throttle = 0.6f;
                Steer(cmd, s, bearing + 45f);
            }

            // 3. armes apres temps de reaction
            string key = s.Id + ">" + target.Id;
            int firstSeen;
            if (!_firstSeenTick.TryGetValue(key, out firstSeen))
            {
                firstSeen = sim.TickIndex;
                _firstSeenTick[key] = firstSeen;
            }
            if (sim.TickIndex - firstSeen < (int)(ReactionTimeS / BattleSim.FixedDt)) return cmd;

            foreach (WeaponSpec w in s.Spec.Weapons)
            {
                WeaponState ws;
                if (!s.Weapons.TryGetValue(w.Id, out ws)) continue;
                if (ws.CooldownS > 0f || ws.Ammo < 1) continue;
                bool use = false;
                if (w.Kind == WeaponKind.Gun && dist <= w.RangeM * 0.9f && s.Eff(ShipSystemKind.Gunnery) > 0.3f) use = true;
                if (w.Kind == WeaponKind.Ssm && dist <= w.RangeM * 0.85f && dist > 1500f && s.Eff(ShipSystemKind.Missiles) > 0.3f) use = true;
                if (w.Kind == WeaponKind.Torpedo && dist <= w.RangeM * 0.5f) use = true;
                if (use) cmd.Fires.Add(new FireRequest { WeaponId = w.Id, TargetShipId = target.Id });
            }
            return cmd;
        }

        private static void Steer(ShipCommand cmd, ShipState s, float bearing)
        {
            float diff = HeadingDelta(s.HeadingDeg, bearing);
            float r = diff / 30f;
            if (r > 1f) r = 1f;
            if (r < -1f) r = -1f;
            cmd.Rudder = r;
        }

        public static float HeadingDelta(float from, float to)
        {
            float d = to - from;
            while (d > 180f) d -= 360f;
            while (d < -180f) d += 360f;
            return d;
        }

        public static float PreferredRangeM(ShipClass c)
        {
            switch (c)
            {
                case ShipClass.Corvette: return 4000f;
                case ShipClass.Frigate: return 7000f;
                case ShipClass.Destroyer: return 6000f;
                case ShipClass.Cruiser: return 10000f;
                case ShipClass.Battleship: return 13000f;
                case ShipClass.Carrier: return 20000f;
                case ShipClass.Submarine: return 3000f;
                default: return 7000f;
            }
        }
    }
}
