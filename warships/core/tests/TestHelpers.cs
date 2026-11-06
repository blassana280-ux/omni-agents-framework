using System;
using System.Collections.Generic;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;
using OmniWarships.Core.Simulation;

namespace OmniWarships.Core.Tests
{
    public static class TestHelpers
    {
        public static List<ShipSpec> Specs() { return SpecLoader.LoadEmbedded(); }

        public static ShipSpec Find(List<ShipSpec> specs, string id)
        {
            foreach (ShipSpec s in specs) if (s.Id == id) return s;
            throw new InvalidOperationException("spec introuvable: " + id);
        }

        public static ShipState MakeShip(ShipSpec spec)
        {
            var s = new ShipState();
            s.Spec = spec;
            s.Team = "blue";
            s.Pos = Vec2.Zero;
            s.HeadingDeg = 0f;
            foreach (CompartmentSpec c in spec.Compartments)
                s.Compartments.Add(new CompartmentState { Id = c.Id, Hp = c.Hp, HpMax = c.Hp });
            foreach (ShipSystemKind k in Enum.GetValues(typeof(ShipSystemKind)))
                s.SystemEff[k] = 1f;
            foreach (WeaponSpec w in spec.Weapons)
                s.Weapons[w.Id] = new WeaponState { Id = w.Id, Ammo = w.Ammo, CooldownS = 0f };
            return s;
        }

        public static CompartmentState Compartment(ShipState s, string id)
        {
            foreach (CompartmentState c in s.Compartments) if (c.Id == id) return c;
            return null;
        }

        public static WeaponSpec Weapon(ShipSpec spec, string id)
        {
            foreach (WeaponSpec w in spec.Weapons) if (w.Id == id) return w;
            return null;
        }
    }
}
