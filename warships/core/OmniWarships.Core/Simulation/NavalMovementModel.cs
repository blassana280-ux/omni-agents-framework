using System;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.Simulation
{
    /// <summary>
    /// Physique de navigation : inertie, poussee limitee, marche arriere
    /// reduite (25 % de la deceleration), virage proportionnel a la vitesse.
    /// Deterministe, pas a pas fixe.
    /// </summary>
    public static class NavalMovementModel
    {
        public const float ReverseThrustFactor = 0.25f;
        public const float TurnSpeedRef = 0.3f; // fraction de vitesse max pour le virage nominal

        public static void Step(ShipState s, ShipCommand cmd, OceanModel ocean, float dt, float t)
        {
            if (s.Sunk)
            {
                // un navire coule : il decelere et s'arrete
                s.SpeedMs *= 0.9f;
                s.Pos = s.Pos + Vec2.FromHeadingDeg(s.HeadingDeg) * (s.SpeedMs * dt);
                return;
            }

            float propEff = s.Eff(ShipSystemKind.Propulsion);
            float steerEff = s.Eff(ShipSystemKind.Steering);

            float maxSpeed = s.Spec.MaxSpeedMs * Math.Max(0.05f, propEff);
            float throttle = Math.Max(-1f, Math.Min(1f, cmd.Throttle));

            // vitesse cible et acceleration bornee
            float target;
            float accel;
            if (throttle >= 0f)
            {
                target = maxSpeed * throttle;
                accel = s.Spec.AccelMs2;
            }
            else
            {
                target = maxSpeed * throttle * 0.35f; // marche arriere lente
                accel = s.Spec.AccelMs2 * ReverseThrustFactor;
            }
            float dv = target - s.SpeedMs;
            float maxDv = accel * dt;
            if (dv > maxDv) dv = maxDv;
            if (dv < -maxDv) dv = -maxDv;
            s.SpeedMs += dv;

            // legere trainee quadratique quand on coupe la puissance
            if (Math.Abs(throttle) < 0.01f)
            {
                s.SpeedMs *= 1f - 0.02f * dt;
            }

            // virage : necessite de la vitesse, amplitude ∝ vitesse
            float speedFactor = Math.Abs(s.SpeedMs) / Math.Max(1f, s.Spec.MaxSpeedMs * TurnSpeedRef);
            if (speedFactor > 1f) speedFactor = 1f;
            float turnDegS = s.Spec.TurnDegS * speedFactor * steerEff;
            s.HeadingDeg += Math.Max(-1f, Math.Min(1f, cmd.Rudder)) * turnDegS * dt;
            if (s.HeadingDeg < 0f) s.HeadingDeg += 360f;
            if (s.HeadingDeg >= 360f) s.HeadingDeg -= 360f;

            s.Pos = s.Pos + Vec2.FromHeadingDeg(s.HeadingDeg) * (s.SpeedMs * dt);

            // reponse aux vagues
            s.RollDeg = ocean.RollAt(s.Pos, s.HeadingDeg, s.Spec.BeamM, t);
            s.PitchDeg = ocean.PitchAt(s.Pos, s.HeadingDeg, s.Spec.LengthM, t);
        }
    }
}
