namespace OmniWarships.Core.Spec
{
    public enum ShipClass { Corvette, Frigate, Destroyer, Cruiser, Battleship, Carrier, Submarine }

    public enum ShipSystemKind { Propulsion, Steering, Radar, Sonar, Gunnery, Missiles, Hangar, Comms }

    public enum WeaponKind { Gun, Ssm, Sam, Torpedo, Ciws, Rocket, DepthCharge }

    public enum SensorKind { Radar, Sonar }

    public enum GuidanceKind { None, Pn, Straight, Auto }

    public enum DamageKind { Shell, Missile, Torpedo, Collision }
}
