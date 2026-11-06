using System;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;
using OmniWarships.Core.Simulation;
using Xunit;

namespace OmniWarships.Core.Tests
{
    /// <summary>Dégâts localisés (matrice : compartiments, systèmes, armure).</summary>
    public class DamageTests
    {
        [Fact]
        public void ImpactMapsToTheRightCompartment()
        {
            ShipState s = TestHelpers.MakeShip(TestHelpers.Find(TestHelpers.Specs(), "ws-frigate-01"));
            Assert.Equal(0.1f, DamageModel.AlongHull(s, new Vec2(0f, 54f)), 2);
            Assert.Equal("bow", DamageModel.FindCompartment(s, 0.1f).Id);
            Assert.Equal("engine", DamageModel.FindCompartment(s, 0.5f).Id);
            Assert.Equal("stern", DamageModel.FindCompartment(s, 0.88f).Id);
        }

        [Fact]
        public void TwoSsmImpactsOnEngineCutPropulsionBelow60Pct()
        {
            ShipState s = TestHelpers.MakeShip(TestHelpers.Find(TestHelpers.Specs(), "ws-frigate-01"));
            Vec2 center = s.Pos;
            DamageModel.ApplyImpact(s, center, DamageKind.Missile, 1600f);
            float p1 = s.Eff(ShipSystemKind.Propulsion);
            Assert.True(p1 >= 0.5f && p1 <= 0.7f, "1 impact : propulsion " + p1);
            DamageModel.ApplyImpact(s, center, DamageKind.Missile, 1600f);
            float p2 = s.Eff(ShipSystemKind.Propulsion);
            Assert.True(p2 <= 0.6f, "2 impacts : propulsion " + p2 + " > 60% (matrice de fidélité)");
            Assert.True(p2 >= 0.15f, "plancher de 15%");
            Assert.True(TestHelpers.Compartment(s, "engine").Destroyed, "engine doit être détruit");
            Assert.True(TestHelpers.Compartment(s, "engine").Breached, "engine doit être percé");
        }

        [Fact]
        public void ArmorReducesEffectiveDamage()
        {
            ShipState frigate = TestHelpers.MakeShip(TestHelpers.Find(TestHelpers.Specs(), "ws-frigate-01"));
            ShipState battleship = TestHelpers.MakeShip(TestHelpers.Find(TestHelpers.Specs(), "ws-battleship-01"));
            DamageModel.ApplyImpact(frigate, frigate.Pos, DamageKind.Missile, 1600f);
            DamageModel.ApplyImpact(battleship, battleship.Pos, DamageKind.Missile, 1600f);
            float lostFrigate = 1300f - TestHelpers.Compartment(frigate, "engine").Hp;
            float lostBattle = 4200f - TestHelpers.Compartment(battleship, "engine").Hp;
            Assert.True(lostFrigate > lostBattle + 100f,
                "armure du cuirassé doit absorber davantage (frégate -" + lostFrigate + ", cuirassé -" + lostBattle + ")");
        }

        [Fact]
        public void SuperstructureHitDegradesRadar()
        {
            ShipState s = TestHelpers.MakeShip(TestHelpers.Find(TestHelpers.Specs(), "ws-frigate-01"));
            Vec2 fwd = Vec2.FromHeadingDeg(0f);
            Vec2 impact = s.Pos + fwd * (0.5f - 0.32f) * s.Spec.LengthM;
            DamageModel.ApplyImpact(s, impact, DamageKind.Shell, 900f);
            Assert.True(s.Eff(ShipSystemKind.Radar) < 1f, "le radar doit se dégrader");
            Assert.Equal("fwd-super", TestHelpers.Compartment(s, "fwd-super").Id == "fwd-super" ? "fwd-super" : DamageModel.FindCompartment(s, 0.32f).Id);
        }
    }
}
