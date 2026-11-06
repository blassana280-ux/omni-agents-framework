using System;
using System.Collections.Generic;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;
using OmniWarships.Core.Simulation;
using Xunit;

namespace OmniWarships.Core.Tests
{
    /// <summary>Balistique (matrice : solution de tir <= 10 m, PN <= 15 m, torpille non armée = 0).</summary>
    public class BallisticsTests
    {
        private const float Dt = 1f / 30f;

        [Fact]
        public void ShellSolutionLandsWithin10mOfAim()
        {
            ShipSpec frigateSpec = TestHelpers.Find(TestHelpers.Specs(), "ws-frigate-01");
            ShipState shooter = TestHelpers.MakeShip(frigateSpec);
            Vec2 targetPos = new Vec2(4000f, 3000f);
            Vec2 targetVel = new Vec2(8f, 0f);
            Vec2 aim = BallisticsModel.PredictIntercept(shooter.Pos, targetPos, targetVel, 800f);
            WeaponSpec gun = TestHelpers.Weapon(frigateSpec, "main-gun");
            Projectile p = BallisticsModel.Launch(shooter, gun, aim, "s2", 0f, new Rng(1), 1);
            var empty = new List<ShipState>();
            Vec2 impact = Vec2.Zero;
            bool landed = false;
            float prevAlt = p.Altitude;
            Vec2 prevPos = p.Pos;
            while (!p.Dead)
            {
                BallisticsModel.Step(p, empty, Dt);
                if (!landed && prevAlt > 3f && p.Altitude <= 3f)
                {
                    float denom = prevAlt - p.Altitude;
                    float frac = denom > 0.0001f ? (prevAlt - 3f) / denom : 1f;
                    impact = prevPos + p.Vel * (frac * Dt);
                    landed = true;
                }
                prevAlt = p.Altitude;
                prevPos = p.Pos;
            }
            Assert.True(landed, "l'obus doit franchir l'altitude cible");
            float err = Vec2.Distance(impact, aim);
            Assert.True(err <= 10f, "impact à " + err + " m du point visé (matrice : <= 10 m)");
        }

        [Fact]
        public void ProportionalNavConvergesWithin15m()
        {
            ShipSpec frigateSpec = TestHelpers.Find(TestHelpers.Specs(), "ws-frigate-01");
            ShipState shooter = TestHelpers.MakeShip(frigateSpec);
            ShipSpec destroyerSpec = TestHelpers.Find(TestHelpers.Specs(), "ws-destroyer-01");
            ShipState target = TestHelpers.MakeShip(destroyerSpec);
            target.Id = "s2"; // le missile cherche sa cible par identifiant
            target.Team = "red";
            target.Pos = new Vec2(0f, 4000f);
            var ships = new List<ShipState> { target };
            WeaponSpec ssm = TestHelpers.Weapon(frigateSpec, "ssm-x8");
            Projectile p = BallisticsModel.Launch(shooter, ssm, target.Pos, "s2", 0f, new Rng(2), 1);
            float dt = 1f / 120f;
            Vec2 flee = new Vec2(1f, 0f) * 8f; // cible qui fuit latéralement
            float minDist = float.MaxValue;
            ShipState hit = null;
            int guard = 0;
            while (!p.Dead && guard < 20000)
            {
                minDist = Math.Min(minDist, Vec2.Distance(p.Pos, target.Pos));
                target.Pos = target.Pos + flee * dt;
                hit = BallisticsModel.Step(p, ships, dt);
                guard++;
            }
            Assert.NotNull(hit);
            Assert.True(minDist <= 15f,
                "distance minimale de guidage " + minDist + " m (matrice : <= 15 m)");
        }

        [Fact]
        public void UnarmedTorpedoDealsZeroDamage()
        {
            ShipSpec frigateSpec = TestHelpers.Find(TestHelpers.Specs(), "ws-frigate-01");
            ShipState shooter = TestHelpers.MakeShip(frigateSpec);
            ShipState target = TestHelpers.MakeShip(TestHelpers.Find(TestHelpers.Specs(), "ws-destroyer-01"));
            target.Team = "red";
            target.Pos = new Vec2(0f, 250f); // plus proche que la distance d'armement
            var ships = new List<ShipState> { target };
            WeaponSpec torp = TestHelpers.Weapon(frigateSpec, "torp-x2");
            Projectile p = BallisticsModel.Launch(shooter, torp, target.Pos, "s2", 0f, new Rng(3), 1);
            ShipState hit = null;
            int guard = 0;
            while (!p.Dead && guard < 20000)
            {
                hit = BallisticsModel.Step(p, ships, Dt);
                guard++;
            }
            Assert.True(p.Dead, "la torpille doit se terminer");
            Assert.Null(hit); // frappe non armée : aucun dégât
            float hp = 0f;
            foreach (var c in target.Compartments) hp += c.Hp;
            Assert.Equal(7550f, hp, 1); // structure intacte

            // version armée : cible au-delà de la distance d'armement
            target.Pos = new Vec2(0f, 400f);
            Projectile p2 = BallisticsModel.Launch(shooter, torp, target.Pos, "s2", 0f, new Rng(3), 2);
            ShipState hit2 = null;
            guard = 0;
            while (!p2.Dead && guard < 20000)
            {
                hit2 = BallisticsModel.Step(p2, ships, Dt);
                guard++;
            }
            Assert.NotNull(hit2); // armée : elle frappe
        }
    }
}
