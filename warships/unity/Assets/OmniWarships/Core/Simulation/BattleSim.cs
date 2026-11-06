using System;
using System.Collections.Generic;
using OmniWarships.Core.AI;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.Simulation
{
    public enum BattleEventKind { Launch, Hit, Damage, Intercept, Sunk, Detection }

    public sealed class BattleEvent
    {
        public BattleEventKind Kind;
        public float Time;          // s
        public string Source;       // navire tireur
        public string Target;       // navire cible
        public string Weapon;       // id arme
        public float X, Y;          // position evenement
        public float Detail;        // extra : degats, vitesse...
    }

    public sealed class FireRequest
    {
        public string WeaponId;
        public string TargetId;
    }

    public sealed class ShipCommand
    {
        public float Throttle;      // -1..1
        public float Rudder;        // -1..1
        public List<FireRequest> Fires = new List<FireRequest>();
    }

    /// <summary>
    /// Simulation de bataille navale deterministe. Tick fixe (pas de
    /// flottants accumules). Toutes les valeurs derivees de la matrice
    /// de donnees (ws-matrix.csv) validee par la CI.
    /// </summary>
    public sealed class BattleSim
    {
        public const float TickRate = 30f;
        public const float Dt = 1f / TickRate;

        private readonly Rng _rng;
        private readonly TacticalAI _ai = new TacticalAI();

        public readonly OceanModel Ocean;
        public float Time;
        public bool BattleOver;

        public Dictionary<string, ShipState> Ships = new Dictionary<string, ShipState>();
        public List<ShipState> ShipList = new List<ShipState>();
        public List<Projectile> Projectiles = new List<Projectile>();

        public List<BattleEvent> Events = new List<BattleEvent>();
        public List<DetectionInfo> Detections = new List<DetectionInfo>();

        private int _shipCounter;

        public BattleSim(int seed, List<ShipSpec> specs, int seaState = 3, float fog = 0f, float windMs = 5f)
        {
            _rng = new Rng(seed);
            Ocean = new OceanModel(seaState, windMs, seed);
            _specs = specs;
        }

        private readonly List<ShipSpec> _specs;

        public ShipState AddShip(string specId, Vec2 pos, float headingDeg, bool playerControlled)
        {
            ShipSpec spec = null;
            foreach (var s in _specs) if (s.Id == specId) { spec = s; break; }
            if (spec == null) throw new ArgumentException("spec inconnu : " + specId);
            _shipCounter++;
            var ship = new ShipState(spec, "s" + _shipCounter, playerControlled)
            {
                Pos = pos,
                HeadingDeg = headingDeg
            };
            Ships[ship.Id] = ship;
            ShipList.Add(ship);
            return ship;
        }

        public void Tick(IDictionary<string, ShipCommand> commands)
        {
            Time += Dt;

            // 1. mouvements
            foreach (var ship in ShipList)
            {
                ShipCommand cmd;
                if (!Alive(ship)) continue;
                if (ship.PlayerControlled)
                {
                    commands.TryGetValue(ship.Id, out cmd);
                }
                else
                {
                    cmd = _ai.Decide(ship, this);
                }
                if (cmd == null) continue;
                float effectiveTurn = ship.Spec.TurnDegS * (ship.Speed / ship.Spec.MaxSpeedMs);
                ship.Rudder = Clamp(cmd.Rudder, -1f, 1f);
                ship.HeadingDeg += ship.Rudder * effectiveTurn * Dt;
                if (ship.HeadingDeg >= 360f) ship.HeadingDeg -= 360f;
                if (ship.HeadingDeg < 0f) ship.HeadingDeg += 360f;
                NavalMovementModel.Update(ship, Clamp(cmd.Throttle, -1f, 1f), Dt);
            }

            // 2. detecteurs
            SensorModel.Update(this);

            // 3. armes : cooldowns + demandes de tir
            foreach (var ship in ShipList)
            {
                if (!Alive(ship)) continue;
                ShipCommand cmd;
                if (ship.PlayerControlled)
                {
                    commands.TryGetValue(ship.Id, out cmd);
                }
                else cmd = _ai.LastCommand;

                foreach (var w in ship.Weapons.Values)
                {
                    if (w.CooldownS > 0f) w.CooldownS = Math.Max(0f, w.CooldownS - Dt);
                }
                if (cmd == null) continue;
                foreach (var fire in cmd.Fires)
                {
                    WeaponState ws;
                    if (!ship.Weapons.TryGetValue(fire.WeaponId, out ws)) continue;
                    WeaponSpec wspec = null;
                    foreach (var w in ship.Spec.Weapons) if (w.Id == fire.WeaponId) { wspec = w; break; }
                    if (wspec == null) continue;
                    ShipState target;
                    if (!Ships.TryGetValue(fire.TargetId, out target)) continue;
                    if (!target.Alive) continue;
                    if (ws.Ammo <= 0 || ws.CooldownS > 0f) continue;

                    if (!ship.HasSystem(SystemKind(wspec.Kind))) continue;

                    ws.Ammo--;
                    ws.CooldownS = wspec.ReloadS;
                    Vec2 dir = target.Pos - ship.Pos;
                    float dist = dir.Length;
                    if (dist > wspec.RangeM) continue; // hors de portee : pas de tir

                    Vec2 launchPos = ship.Pos + Vec2.FromHeadingDeg(ship.HeadingDeg) * (ship.Spec.LengthM * 0.5f);
                    float spread = wspec.Kind == WeaponKind.Gun ? 1.2f : 0.4f;
                    float aimDeg = dir.HeadingDeg() + _rng.NextRange(-spread, spread);
                    float speed = wspec.SpeedMs;

                    var proj = new Projectile
                    {
                        Id = "p" + (_projCounter++),
                        Kind = wspec.Kind,
                        OwnerId = ship.Id,
                        TargetId = target.Id,
                        WeaponId = wspec.Id,
                        Pos = launchPos,
                        Dir = Vec2.FromHeadingDeg(aimDeg),
                        Speed = speed,
                        RemainingRange = wspec.RangeM,
                        Damage = wspec.Damage,
                        Guidance = wspec.Guidance,
                        TurnDegS = 25f,
                        Age = 0f,
                        FuelS = wspec.Kind == WeaponKind.Sam || wspec.Kind == WeaponKind.Ssm ? 60f : 0f
                    };
                    Projectiles.Add(proj);
                    Events.Add(new BattleEvent { Kind = BattleEventKind.Launch, Time = Time, Source = ship.Id, Target = target.Id, Weapon = wspec.Id, X = launchPos.X, Y = launchPos.Y, Detail = dist });
                }
            }

            // 4. ballistique + ciws
            BallisticsModel.Update(this, Projectiles, Dt, _rng);
            CiwsModel.Update(this, Projectiles, Dt, _rng);

            // 5. voies d'eau + flottabilite + coulage
            FloodingModel.Update(this, Dt, _rng);

            // 6. fin de bataille ?
            if (!BattleOver)
            {
                bool anyPlayer = false, anyAi = false;
                foreach (var s in ShipList)
                {
                    if (!Alive(s)) continue;
                    if (s.PlayerControlled) anyPlayer = true; else anyAi = true;
                }
                if (!anyPlayer || !anyAi) BattleOver = true;
            }
        }

        private int _projCounter;

        private static ShipSystemKind SystemKind(WeaponKind kind)
        {
            switch (kind)
            {
                case WeaponKind.Gun: return ShipSystemKind.Gunnery;
                case WeaponKind.Ssm:
                case WeaponKind.Sam:
                case WeaponKind.Torpedo:
                case WeaponKind.Rocket: return ShipSystemKind.Missiles;
                case WeaponKind.Ciws: return ShipSystemKind.Gunnery;
                default: return ShipSystemKind.Gunnery;
            }
        }

        private static bool Alive(ShipState s) { return s.Alive; }

        private static float Clamp(float v, float lo, float hi)
        {
            return v < lo ? lo : (v > hi ? hi : v);
        }
    }
}
