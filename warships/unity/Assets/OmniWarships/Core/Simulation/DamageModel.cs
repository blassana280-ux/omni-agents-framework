using System;
using System.Collections.Generic;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.Simulation
{
    /// <summary>
    /// Degats : penetration d'armure par compartiment, destruction des
    /// systemes, voies d'eau. Baseline observable : un obus de 127 mm
    /// perce ~25 mm d'acier (a bout portant) ; reference BRL obsolte.
    /// </summary>
    public static class DamageModel
    {
        public static void Apply(BattleSim sim, ShipState ship, Projectile p, Rng rng)
        {
            float baseDamage = p.Damage;

            // compartiment touche : impact le long de l'axe du navire
            float impactHeading = p.Dir.HeadingDeg();
            Vec2 rel = p.Pos - ship.Pos;
            Vec2 fwd = Vec2.FromHeadingDeg(ship.HeadingDeg);
            float along = Vec2.Dot(rel, fwd) / Math.Max(1f, ship.Spec.LengthM) + 0.5f; // 0 = proue, 1 = poupe
            if (along < 0f) along = 0f;
            if (along > 1f) along = 1f;

            CompartmentSpec hit = null;
            foreach (var c in ship.Spec.Compartments)
                if (c.Covers(along)) { hit = c; break; }
            if (hit == null) hit = ship.Spec.Compartments[ship.Spec.Compartments.Count / 2];

            CompartmentState cs;
            if (!ship.Compartments.TryGetValue(hit.Id, out cs)) return;

            float armorFactor = hit.Armor > 0f ? 1f / hit.Armor : 1f;
            float dmg = baseDamage * armorFactor;

            // angle d'impact : les obus frappant perpendiculairement touchent plus fort
            float cos = Math.Abs(Vec2.Dot(p.Dir, Vec2.FromHeadingDeg(ship.HeadingDeg + 90f)));
            dmg *= 0.7f + 0.3f * cos;

            cs.Hp -= dmg;
            ship.TotalHp -= dmg;

            sim.Events.Add(new BattleEvent
            {
                Kind = BattleEventKind.Damage,
                Time = sim.Time,
                Source = p.OwnerId,
                Target = ship.Id,
                Weapon = p.WeaponId,
                X = p.Pos.X,
                Y = p.Pos.Y,
                Detail = dmg
            });

            // voie d'eau : chance selon degats et type
            float floodChance = 0f;
            if (p.Kind == ProjectileKind.Torpedo) floodChance = 0.8f;
            else if (p.Kind == ProjectileKind.Missile) floodChance = 0.3f;
            else floodChance = 0.08f;
            if (cs.Hp <= 0f) floodChance = Math.Max(floodChance, 0.5f);

            if (rng.NextFloat() < floodChance)
            {
                cs.Breached = true;
                FloodingModel.StartFlooding(cs, floodChance * 0.5f, rng);
            }

            if (cs.Hp <= 0f) cs.Destroyed = true;
            if (ship.TotalHp <= 0f)
            {
                sim.Events.Add(new BattleEvent
                {
                    Kind = BattleEventKind.Sunk,
                    Time = sim.Time,
                    Source = p.OwnerId,
                    Target = ship.Id,
                    X = ship.Pos.X,
                    Y = ship.Pos.Y
                });
                ship.Alive = false;
            }
        }
    }
}
