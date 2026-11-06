using System;
using System.Collections.Generic;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.Simulation
{
    /// <summary>
    /// Etat complet d'un navire pendant la bataille. La simulation n'est
    /// qu'une fonction de (etat, commandes) : deterministe et rejouable.
    /// </summary>
    public sealed class ShipState
    {
        public string Id;
        public ShipSpec Spec;
        public bool PlayerControlled;
        public bool Alive = true;

        public Vec2 Pos;         // metres
        public float HeadingDeg; // 0 = nord (+Y), sens horaire
        public float Speed;      // m/s positif = avance
        public float Rudder;    // -1..1 (positive = babord ? non : negatif = babord, positif = tribord)

        public Dictionary<string, CompartmentState> Compartments = new Dictionary<string, CompartmentState>();
        public Dictionary<string, WeaponState> Weapons = new Dictionary<string, WeaponState>();

        public float TotalHp { get; private set; }
        public float TotalHpMax { get; private set; }
        public float Buoyancy = 1f; // 1 = intact, 0 = coule

        public bool Sunk { get { return !Alive; } }

        public ShipState(ShipSpec spec, string id, bool playerControlled)
        {
            Id = id;
            Spec = spec;
            PlayerControlled = playerControlled;
            foreach (var c in spec.Compartments)
            {
                Compartments[c.Id] = new CompartmentState { Id = c.Id, Hp = c.Hp, HpMax = c.Hp, Flooding = 0f };
                TotalHpMax += c.Hp;
            }
            TotalHp = TotalHpMax;
            foreach (var w in spec.Weapons)
                Weapons[w.Id] = new WeaponState { Id = w.Id, Ammo = w.Ammo, CooldownS = 0f };
        }

        public float FractionHp { get { return TotalHpMax <= 0f ? 0f : TotalHp / TotalHpMax; } }

        public bool HasSystem(ShipSystemKind kind)
        {
            foreach (var c in Spec.Compartments)
            {
                CompartmentState cs;
                if (!Compartments.TryGetValue(c.Id, out cs)) continue;
                if (cs.Destroyed) continue;
                foreach (var s in c.Systems)
                    if (s == kind) return true;
            }
            return false;
        }

        public bool Flooded { get { return Buoyancy <= 0f; } }

        public float FloodingTotal
        {
            get
            {
                float f = 0f;
                foreach (var c in Compartments.Values) f += c.Flooding;
                return f;
            }
        }
    }
}
