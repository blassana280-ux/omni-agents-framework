using System;
using System.Collections.Generic;

namespace OmniWarships.Core.Spec
{
    public sealed class ShipSpec
    {
        public const float KnotsToMs = 0.5144f;

        public string Id;
        public string Name;
        public ShipClass Class;
        public float LengthM, BeamM, DraftM, DisplacementT;
        public float MaxSpeedKn, AccelMs2, TurnDegS, RcsM2, Acoustic;

        public List<CompartmentSpec> Compartments = new List<CompartmentSpec>();
        public List<WeaponSpec> Weapons = new List<WeaponSpec>();
        public List<SensorSpec> Sensors = new List<SensorSpec>();

        public float MaxSpeedMs { get { return MaxSpeedKn * KnotsToMs; } }
        public float TotalHp { get { float s = 0f; foreach (var c in Compartments) s += c.Hp; return s; } }
    }
}
