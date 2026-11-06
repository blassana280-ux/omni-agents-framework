using System;
using OmniWarships.Core.Common;
using OmniWarships.Core.Simulation;
using Xunit;

namespace OmniWarships.Core.Tests
{
    /// <summary>Océan (déterminisme, bornes, réponse aux vagues).</summary>
    public class OceanTests
    {
        [Fact]
        public void OceanIsDeterministic()
        {
            var o1 = new OceanModel(4, 9f, 42);
            var o2 = new OceanModel(4, 9f, 42);
            Assert.Equal(o1.HeightAt(123.5f, -45.2f, 7.3f), o2.HeightAt(123.5f, -45.2f, 7.3f));
            Assert.Equal(o1.RollAt(new Vec2(10f, 20f), 45f, 16f, 3f), o2.RollAt(new Vec2(10f, 20f), 45f, 16f, 3f));
        }

        [Fact]
        public void AmplitudeBoundedBySeaState()
        {
            var calm = new OceanModel(0, 0f, 1);
            Assert.Equal(0f, calm.MaxAmplitude);
            var s4 = new OceanModel(4, 9f, 1);
            Assert.True(s4.MaxAmplitude >= 1f && s4.MaxAmplitude <= 4f, "amplitude mer 4 : " + s4.MaxAmplitude);
            var s9 = new OceanModel(9, 30f, 1);
            Assert.True(s9.MaxAmplitude <= 8f, "amplitude mer 9 bornée : " + s9.MaxAmplitude);
        }

        [Fact]
        public void RollBoundedSea4()
        {
            var o = new OceanModel(4, 9f, 5);
            var rng = new Rng(11);
            var pos = new Vec2(0f, 0f);
            float maxRoll = 0f;
            for (int i = 0; i < 400; i++)
            {
                pos = new Vec2(rng.NextRange(-2000f, 2000f), rng.NextRange(-2000f, 2000f));
                float roll = Math.Abs(o.RollAt(pos, rng.NextRange(0f, 360f), 16f, rng.NextRange(0f, 60f)));
                if (roll > maxRoll) maxRoll = roll;
            }
            Assert.True(maxRoll >= 0.5f && maxRoll <= 10.5f,
                "roulis max mer 4 : " + maxRoll + " degrés (bornes CI : 0.5-10.5, cible de rendu 2-6)");
        }

        [Fact]
        public void FlatCalmGivesZeroRoll()
        {
            var o = new OceanModel(0, 0f, 1);
            Assert.Equal(0f, o.RollAt(new Vec2(50f, -30f), 90f, 16f, 12f));
        }
    }
}
