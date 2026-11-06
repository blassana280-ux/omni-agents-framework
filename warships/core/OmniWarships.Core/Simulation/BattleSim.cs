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
        public int Tick;
        public BattleEventKind Kind;
        public string ShipId;
        public string TargetId;
        public string Detail;

        public static BattleEvent Launch(int tick, string ship, string weapon, string target)
        {
            return new BattleEvent { Tick = tick, Kind = BattleEventKind.Launch, ShipId = ship, TargetId = target, Detail = weapon };
        }
        public static BattleEvent Hit(int tick, string projectile, string target, float damage)
        {
            return new BattleEvent { Tick = tick, Kind = BattleEventKind.Hit, ShipId = projectile, TargetId = target, Detail = damage.ToString("0") };
        }
        public static BattleEvent Damage(int tick, string target, string compartment, bool destroyed)
        {
            return new BattleEvent { Tick = tick, Kind = BattleEventKind.Damage, ShipId = target, Detail = compartment + (destroyed ? ":detruit" : "") };
        }
        public static BattleEvent Intercept(int tick, string ship, string projectile, string source)
        {
            return new BattleEvent { Tick = tick, Kind = BattleEventKind.Intercept, ShipId = ship, TargetId = source, Detail = projectile };
        }
        public static BattleEvent Sunk(int tick, string ship)
        {
            return new BattleEvent { Tick = tick, Kind = BattleEventKind.Sunk, ShipId = ship };
        }
        public static BattleEvent Detection(int tick, string ship, string target)
        {
            return new BattleEvent { Tick = tick, Kind = BattleEventKind.Detection, ShipId = ship, TargetId = target };
        }
    }

    /// <summary>
    /// Moteur de bataille deterministe : pas fixe 1/30 s, RNG maison, tout
    /// l'etat est rejouable a l'identique depuis (graine, specs, placements,
    /// commandes joueur). Source unique du jeu, du sandbox et des replays.
    /// </summary>
    public sealed class BattleSim
    {
        public const float FixedDt = 1f / 30f;

        public int TickIndex;
        public float TimeS;
        public readonly int SeaState;
        public readonly float Fog;
        public readonly float WindMs;
        public readonly int Seed;
        public readonly OceanModel Ocean;
        public readonly Rng Rng;
        public readonly TacticalAI Ai = new TacticalAI();
        public readonly List<ShipState> Ships = new List<ShipState>();
        public readonly List<Projectile> Projectiles = new List<Projectile>();
        public readonly List<BattleEvent> Events = new List<BattleEvent>();

        private readonly Dictionary<string, ShipSpec> _specs = new Dictionary<string, ShipSpec>();
        private int _shipSerial;
        private int _projSerial;

        public BattleSim(int seed, IList<ShipSpec> specs, int seaState, float fog, float windMs)
        {
            Seed = seed;
            SeaState = seaState;
            Fog = fog;
            WindMs = windMs;
            Ocean = new OceanModel(seaState, windMs, seed);
            Rng = new Rng(seed);
            foreach (ShipSpec s in specs) _specs[s.Id] = s;
        }

        public ShipState AddShip(string specId, string team, float x, float z, float headingDeg, bool ai)
        {
            ShipSpec spec;
            if (!_specs.TryGetValue(specId, out spec))
            {
                throw new InvalidOperationException("spec inconnue: " + specId);
            }
            _shipSerial++;
            var s = new ShipState();
            s.Id = "s" + _shipSerial;
            s.Team = team;
            s.IsAi = ai;
            s.Spec = spec;
            s.Pos = new Vec2(x, z);
            s.HeadingDeg = headingDeg;
            foreach (CompartmentSpec c in spec.Compartments)
            {
                s.Compartments.Add(new CompartmentState { Id = c.Id, Hp = c.Hp, HpMax = c.Hp });
            }
            foreach (ShipSystemKind k in Enum.GetValues(typeof(ShipSystemKind)))
            {
                s.SystemEff[k] = 1f;
            }
            foreach (WeaponSpec w in spec.Weapons)
            {
                s.Weapons[w.Id] = new WeaponState { Id = w.Id, Ammo = w.Ammo, CooldownS = 0f };
            }
            Ships.Add(s);
            return s;
        }

        public ShipState Ship(string id)
        {
            foreach (ShipState s in Ships)
            {
                if (s.Id == id) return s;
            }
            return null;
        }

        public void Tick(IDictionary<string, ShipCommand> commands)
        {
            TickIndex++;
            TimeS += FixedDt;

            // 1. commandes : IA pour les navires IA, commandes joueur sinon
            var effective = new Dictionary<string, ShipCommand>();
            foreach (ShipState s in Ships)
            {
                ShipCommand cmd = null;
                if (s.IsAlive)
                {
                    if (s.IsAi) cmd = Ai.Decide(s, this);
                    else if (commands != null)
                    {
                        ShipCommand pc;
                        if (commands.TryGetValue(s.Id, out pc)) cmd = pc;
                    }
                }
                if (cmd == null) cmd = ShipCommand.Idle();
                effective[s.Id] = cmd;
            }

            // 2. mouvement + voie d'eau + naufrages
            foreach (ShipState s in Ships)
            {
                ShipCommand cmd;
                effective.TryGetValue(s.Id, out cmd);
                NavalMovementModel.Step(s, cmd ?? ShipCommand.Idle(), Ocean, FixedDt, TimeS);
                s.AgeS += FixedDt;
                bool wasSunk = s.Sunk;
                FloodingModel.Step(s, FixedDt, TimeS);
                if (s.Sunk && !wasSunk)
                {
                    Events.Add(BattleEvent.Sunk(TickIndex, s.Id));
                }
            }

            // 3. rechargement + tirs valides
            foreach (ShipState s in Ships)
            {
                foreach (WeaponState ws in s.Weapons.Values)
                {
                    if (ws.CooldownS > 0f) ws.CooldownS -= FixedDt;
                }
                if (s.Sunk) continue;
                ShipCommand cmd;
                if (!effective.TryGetValue(s.Id, out cmd)) continue;
                if (cmd.Fires == null || cmd.Fires.Count == 0) continue;
                foreach (FireRequest fr in cmd.Fires)
                {
                    TryFire(s, fr);
                }
            }

            // 4. projectiles en vol + impacts
            for (int i = Projectiles.Count - 1; i >= 0; i--)
            {
                Projectile p = Projectiles[i];
                ShipState hit = BallisticsModel.Step(p, Ships, FixedDt);
                if (hit != null)
                {
                    ApplyProjectileImpact(p, hit);
                }
                if (p.Dead) Projectiles.RemoveAt(i);
            }

            // 5. CIWS automatique
            foreach (ShipState s in Ships)
            {
                CiwsModel.Engage(s, Projectiles, FixedDt, Rng, Events, TickIndex);
            }
            for (int i = Projectiles.Count - 1; i >= 0; i--)
            {
                if (Projectiles[i].Dead) Projectiles.RemoveAt(i);
            }

            // 6. detections
            UpdateDetections();
        }

        private void TryFire(ShipState s, FireRequest fr)
        {
            WeaponState ws;
            if (!s.Weapons.TryGetValue(fr.WeaponId, out ws)) return;
            WeaponSpec spec = null;
            foreach (WeaponSpec w in s.Spec.Weapons)
            {
                if (w.Id == fr.WeaponId) { spec = w; break; }
            }
            if (spec == null) return;
            if (ws.CooldownS > 0f || ws.Ammo < 1) return;
            if (spec.Kind == WeaponKind.Ciws) return; // automatique

            ShipState target = Ship(fr.TargetShipId);
            if (target == null || target.Sunk) return;
            float dist = Vec2.Distance(s.Pos, target.Pos);
            if (dist > spec.RangeM * 1.05f) return;

            if (spec.Kind == WeaponKind.Gun && s.Eff(ShipSystemKind.Gunnery) < 0.3f) return;
            if ((spec.Kind == WeaponKind.Ssm || spec.Kind == WeaponKind.Sam) && s.Eff(ShipSystemKind.Missiles) < 0.3f) return;

            // un sous-marin profond ne tire ni canon ni missile
            if (s.DepthM > 15f && spec.Kind != WeaponKind.Torpedo) return;

            // les IA ne tirent que sur des contacts
            if (s.IsAi && !s.Contacts.ContainsKey(target.Id)) return;

            Vec2 aim;
            if (spec.Guidance == GuidanceKind.Pn)
            {
                aim = target.Pos;
            }
            else
            {
                aim = BallisticsModel.PredictIntercept(s.Pos, target.Pos,
                    Vec2.FromHeadingDeg(target.HeadingDeg) * target.SpeedMs, spec.SpeedMs);
            }

            int salvo = Math.Min(spec.Salvo, ws.Ammo);
            for (int i = 0; i < salvo; i++)
            {
                _projSerial++;
                Projectile p = BallisticsModel.Launch(s, spec, aim, target.Id, 1.5f, Rng, _projSerial);
                Projectiles.Add(p);
                Events.Add(BattleEvent.Launch(TickIndex, s.Id, spec.Id, target.Id));
            }
            ws.Ammo -= salvo;
            ws.CooldownS = spec.ReloadS;
        }

        private void ApplyProjectileImpact(Projectile p, ShipState hit)
        {
            float damage = p.Armed ? p.Damage : 0f;
            Events.Add(BattleEvent.Hit(TickIndex, p.Id, hit.Id, damage));
            if (damage <= 0f) return;
            DamageResult r = DamageModel.ApplyImpact(hit, p.Pos, p.DamageKind, damage);
            if (r.CompartmentId != null)
            {
                Events.Add(BattleEvent.Damage(TickIndex, hit.Id, r.CompartmentId, r.CompartmentDestroyed));
            }
        }

        private void UpdateDetections()
        {
            foreach (ShipState observer in Ships)
            {
                if (observer.Sunk) continue;
                float radarEff = observer.Eff(ShipSystemKind.Radar);
                float sonarEff = observer.Eff(ShipSystemKind.Sonar);
                foreach (ShipState target in Ships)
                {
                    if (target == observer || target.Team == observer.Team || target.Sunk) continue;
                    float dist = Vec2.Distance(observer.Pos, target.Pos);
                    bool detected = false;
                    float quality = 0f;
                    foreach (SensorSpec sensor in observer.Spec.Sensors)
                    {
                        bool d; float q;
                        if (sensor.Kind == SensorKind.Radar && radarEff > 0.3f)
                        {
                            d = SensorModel.DetectRadar(sensor, target, dist, Fog, 0f, out q);
                        }
                        else if (sensor.Kind == SensorKind.Sonar && sonarEff > 0.3f)
                        {
                            d = SensorModel.DetectSonar(sensor, target, dist, out q);
                        }
                        else
                        {
                            d = false; q = 0f;
                        }
                        if (d && q > quality) { quality = q; detected = true; }
                    }
                    if (detected)
                    {
                        bool isNew = !observer.Contacts.ContainsKey(target.Id);
                        observer.Contacts[target.Id] = new Contact
                        {
                            ShipId = target.Id,
                            Quality = quality,
                            LastSeenTick = TickIndex,
                            EstimatedPos = target.Pos
                        };
                        if (isNew)
                        {
                            Events.Add(BattleEvent.Detection(TickIndex, observer.Id, target.Id));
                        }
                    }
                }
            }
        }
    }
}
