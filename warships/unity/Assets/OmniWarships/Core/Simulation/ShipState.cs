using System;
using System.Collections.Generic;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.Simulation
{
    /// <summary>Commande de pilotage d'un navire pendant un tick.</summary>
    public sealed class ShipCommand
    {
        public float Throttle;   // -1..1 (marche arriere limitee)
        public float Rudder;    // -1..1 (negatif = babord)
        public List<FireRequest> Fires = new List<FireRequest>();

        public static ShipCommand Idle()
        {
            return new ShipCommand { Throttle = 0f, Rudder = 0f };
        }
    }

    public sealed class FireRequest
    {
        public string WeaponId;
        public string TargetShipId;
    }

    /// <summary>Contact detecte par un navire pendant la bataille.</summary>
    public sealed class Contact
    {
        public string ShipId;
        public float Quality;      // 0..1
        public int LastSeenTick;
        public Vec2 EstimatedPos;
    }

    /// <summary>Etat complet d'un navire pendant la bataille.</summary>
    public sealed class ShipState
    {
        public string Id;
        public string Team;
        public bool IsAi;
        public ShipSpec Spec;
        public Vec2 Pos;
        public float HeadingDeg;
        public float SpeedMs;          // signee : negative = marche arriere
        public float DepthM;           // sous-marins : 0 = surface
        public float PitchDeg, RollDeg;
        public bool Sunk;
        public float SunkAtS = -1f;

        public List<CompartmentState> Compartments = new List<CompartmentState>();
        public Dictionary<ShipSystemKind, float> SystemEff = new Dictionary<ShipSystemKind, float>();
        public Dictionary<string, WeaponState> Weapons = new Dictionary<string, WeaponState>();
        public Dictionary<string, Contact> Contacts = new Dictionary<string, Contact>();
        public List<string> DetectedBy = new List<string>();

        public float AgeS;

        public float Eff(ShipSystemKind k)
        {
            float v;
            return SystemEff.TryGetValue(k, out v) ? v : 0f;
        }

        public bool IsAlive { get { return !Sunk; } }
    }
}
