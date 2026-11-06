using System.Collections.Generic;

namespace OmniWarships.Core.Spec
{
    public sealed class WeaponSpec
    {
        public string Id;
        public WeaponKind Kind;
        public float Damage;
        public float RangeM;
        public float SpeedMs;
        public float ReloadS;
        public int Salvo;
        public int Ammo;
        public GuidanceKind Guidance;
    }

    public sealed class WeaponState
    {
        public string Id;
        public int Ammo;
        public float CooldownS;
    }

    public sealed class SensorSpec
    {
        public string Id;
        public SensorKind Kind;
        public float RangeM;
        public float Ref; // radar : RCS de reference (m2) ; sonar : signature acoustique de reference
    }
}
