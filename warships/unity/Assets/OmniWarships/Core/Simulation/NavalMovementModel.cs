using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.Simulation
{
    /// <summary>
    /// Physique navale simplifiee mais realiste : acceleration, frottement,
    /// influence de l'etat de la mer et des degats de propulsion.
    /// </summary>
    public static class NavalMovementModel
    {
        public static void Update(ShipState s, float throttle, float dt)
        {
            float maxMs = s.Spec.MaxSpeedMs;
            float accel = s.Spec.AccelMs2;

            // propulsion endommagee : reduit accel et vitesse max
            bool propOk = s.HasSystem(ShipSystemKind.Propulsion);
            bool steerOk = s.HasSystem(ShipSystemKind.Steering);
            float hpFactor = 0.5f + 0.5f * s.FractionHp;
            if (!propOk) hpFactor *= 0.4f;
            accel *= hpFactor;
            maxMs *= hpFactor;

            float target = throttle * maxMs;
            if (throttle < 0f) target = throttle * maxMs * 0.35f; // marche arriere lente

            // trainee : converge vers la cible
            s.Speed += (target - s.Speed) * Math.Min(1f, accel * dt / Math.Max(1f, Math.Abs(target - s.Speed)));
            s.Speed = Clamp(s.Speed, -maxMs * 0.35f, maxMs);

            // offrande a la mer : la vague ralentit le navire
            float waveDrag = 1f - 0.08f * OceanAt(s);
            s.Speed *= waveDrag;

            Vec2 fwd = Vec2.FromHeadingDeg(s.HeadingDeg);
            s.Pos += fwd * (s.Speed * dt);

            // derive du vent
            s.Pos += Vec2.FromHeadingDeg(90f) * (WindAt(s) * 0.02f * dt);
        }

        private static float OceanAt(ShipState s)
        {
            // approximation locale : mer module 3 par defaut
            return 0.5f;
        }

        private static float WindAt(ShipState s)
        {
            return 2f;
        }

        private static float Clamp(float v, float lo, float hi)
        {
            return v < lo ? lo : (v > hi ? hi : v);
        }
    }
}
