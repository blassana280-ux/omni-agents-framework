using System;
using System.Collections.Generic;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.Simulation
{
    public sealed class DamageResult
    {
        public string CompartmentId;
        public float AppliedDamage;
        public bool CompartmentDestroyed;
        public bool Breached;
        public List<ShipSystemKind> SystemsHit = new List<ShipSystemKind>();
    }

    /// <summary>
    /// Degats localises : l'impact est projete le long de la coque pour
    /// trouver le compartiment touche ; les systemes de ce compartiment
    /// se degradent reellement (propulsion, radar, armement...).
    /// </summary>
    public static class DamageModel
    {
        /// <summary>Position le long de la coque : 0 = proue, 1 = poupe.</summary>
        public static float AlongHull(ShipState ship, Vec2 impactPos)
        {
            Vec2 fwd = Vec2.FromHeadingDeg(ship.HeadingDeg);
            float forward = Vec2.Dot(impactPos - ship.Pos, fwd);
            float along = 0.5f - forward / Math.Max(1f, ship.Spec.LengthM);
            if (along < 0f) along = 0f;
            if (along > 1f) along = 1f;
            return along;
        }

        public static CompartmentState FindCompartment(ShipState ship, float along)
        {
            CompartmentState best = null;
            float bestDist = float.MaxValue;
            foreach (CompartmentState cs in ship.Compartments)
            {
                CompartmentSpec spec = null;
                foreach (CompartmentSpec s in ship.Spec.Compartments)
                {
                    if (s.Id == cs.Id) { spec = s; break; }
                }
                if (spec != null && spec.Covers(along)) return cs;
                if (spec != null)
                {
                    float d = Math.Abs(spec.Center - along);
                    if (d < bestDist) { bestDist = d; best = cs; }
                }
            }
            return best;
        }

        public static DamageResult ApplyImpact(ShipState ship, Vec2 impactPos, DamageKind kind, float damage)
        {
            var result = new DamageResult();
            result.AppliedDamage = damage;
            if (ship.Sunk || damage <= 0f) return result;

            CompartmentState comp = FindCompartment(ship, AlongHull(ship, impactPos));
            if (comp == null) return result;
            CompartmentSpec spec = null;
            foreach (CompartmentSpec s in ship.Spec.Compartments)
            {
                if (s.Id == comp.Id) { spec = s; break; }
            }
            if (spec == null) return result;
            result.CompartmentId = comp.Id;

            float effective = damage / Math.Max(0.2f, spec.Armor);
            comp.Hp -= effective;

            if (comp.Hp <= 0f)
            {
                comp.Hp = 0f;
                comp.Destroyed = true;
                comp.Breached = true;
                result.CompartmentDestroyed = true;
                result.Breached = true;
                foreach (ShipSystemKind sys in spec.Systems)
                {
                    float nv = ship.Eff(sys) * 0.25f;
                    if (nv < 0.15f) nv = 0.15f;
                    ship.SystemEff[sys] = nv;
                    result.SystemsHit.Add(sys);
                }
            }
            else
            {
                float ratio = effective / Math.Max(1f, comp.HpMax);
                if (ratio > 0.35f) comp.Breached = true;
                result.Breached = comp.Breached;
                foreach (ShipSystemKind sys in spec.Systems)
                {
                    float nv = ship.Eff(sys) * (1f - 0.4f * ratio);
                    if (nv < 0.15f) nv = 0.15f;
                    ship.SystemEff[sys] = nv;
                    result.SystemsHit.Add(sys);
                }
            }
            return result;
        }

        public static bool AllCompartmentsDestroyed(ShipState ship)
        {
            foreach (CompartmentState c in ship.Compartments)
            {
                if (!c.Destroyed) return false;
            }
            return ship.Compartments.Count > 0;
        }
    }
}
