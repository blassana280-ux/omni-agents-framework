using System;
using System.Collections.Generic;
using OmniWarships.Core.Spec;
using OmniWarships.Core.Simulation;
using OmniWarships.Core.Replay;
using UnityEngine;

namespace OmniWarships.Unity
{
    public enum BattleOutcome { InProgress, Victory, Defeat }

    /// <summary>
    /// Ordonnateur de la bataille : construit la simulation noyau, la fait
    /// avancer a pas fixe (FixedUpdate, 1/30 s), traduit les evenements du
    /// noyau en effets visuels, arbitre victoire/defaite et capture le
    /// replay deterministe. Toute la logique navale est dans OmniWarships.Core ;
    /// ce composant n'est que presentation + input + arbitrage.
    /// </summary>
    public sealed class BattleDirector : MonoBehaviour
    {
        public BattleSim Sim { get; private set; }
        public ShipState PlayerShip { get; private set; }
        public BattleOutcome Outcome { get; private set; }
        public string OutcomeMessage { get; private set; }
        public float BattleTimeS { get { return Sim == null ? 0f : Sim.TimeS; } }

        /// <summary>Emis apres chaque pas de simulation.</summary>
        public event Action OnSimTicked;

        private readonly List<ShipView> _views = new List<ShipView>();
        private List<ShipSpec> _specs;
        private ProjectileView _projectiles;
        private EffectsPool _effects;
        private TouchInputController _input;
        private HudController _hud;
        private OceanController _ocean;
        private WarshipCamera _camera;
        private ReplayData _replay;
        private int _eventCursor;

        public IReadOnlyList<ShipView> Views { get { return _views; } }
        public TouchInputController Input { get { return _input; } }
        public EffectsPool Effects { get { return _effects; } }
        public WarshipCamera Cam { get { return _camera; } }

        private void Start()
        {
            Time.fixedDeltaTime = BattleSim.FixedDt;
            _specs = SpecSource.LoadAll();
            SetupBattle();
        }

        private void SetupBattle()
        {
            _eventCursor = 0;
            Outcome = BattleOutcome.InProgress;
            OutcomeMessage = null;

            Sim = new BattleSim(BattleConfig.Seed, _specs,
                BattleConfig.SeaState, BattleConfig.Fog, BattleConfig.WindMs);
            _replay = ReplayRecorder.Capture(Sim);

            PlayerShip = Sim.AddShip(BattleConfig.PlayerSpecId, BattleConfig.PlayerTeam,
                BattleConfig.PlayerStartX, BattleConfig.PlayerStartZ, BattleConfig.PlayerHeadingDeg, false);
            Sim.AddShip(BattleConfig.EnemySpecId, BattleConfig.EnemyTeam,
                BattleConfig.EnemyStartX, BattleConfig.EnemyStartZ, BattleConfig.EnemyHeadingDeg, true);

            _ocean = GetOrCreate<OceanController>("OMNI Ocean");
            _effects = GetOrCreate<EffectsPool>("OMNI Effects");
            _projectiles = GetOrCreate<ProjectileView>("OMNI Projectiles");
            _camera = GetOrCreate<WarshipCamera>("OMNI Camera");
            _input = GetOrCreate<TouchInputController>("OMNI Input");
            _hud = GetOrCreate<HudController>("OMNI HUD");

            _ocean.Bind(Sim);
            _effects.Bind(this);
            _projectiles.Bind(this);
            _camera.Bind(this);
            _input.Bind(this);
            _hud.Bind(this);

            foreach (ShipView old in _views)
            {
                if (old != null) Destroy(old.gameObject);
            }
            _views.Clear();
            foreach (ShipState s in Sim.Ships) AddView(s);
        }

        private T GetOrCreate<T>(string name) where T : Component
        {
            T existing = FindFirstObjectByTypeLight<T>();
            if (existing != null) return existing;
            var go = new GameObject(name);
            return go.AddComponent<T>();
        }

        private static T FindFirstObjectByTypeLight<T>() where T : Component
        {
            return (T)Object.FindObjectOfType(typeof(T));
        }

        private void AddView(ShipState s)
        {
            var go = new GameObject("Ship " + s.Id + " (" + s.Spec.Id + ")");
            var view = go.AddComponent<ShipView>();
            view.Bind(s, this);
            _views.Add(view);
        }

        public ShipView ViewOf(string shipId)
        {
            foreach (ShipView v in _views)
            {
                if (v != null && v.State != null && v.State.Id == shipId) return v;
            }
            return null;
        }

        private void FixedUpdate()
        {
            if (Sim == null) return;
            if (Outcome != BattleOutcome.InProgress) return;

            var cmds = new Dictionary<string, ShipCommand>();
            if (PlayerShip != null && !PlayerShip.Sunk)
            {
                cmds[PlayerShip.Id] = _input.BuildCommand();
            }
            ReplayRecorder.RecordPlayerCommands(_replay, cmds);
            Sim.Tick(cmds);

            DrainEvents();
            UpdateOutcome();
            if (OnSimTicked != null) OnSimTicked();
        }

        private void DrainEvents()
        {
            for (int i = _eventCursor; i < Sim.Events.Count; i++)
            {
                BattleEvent e = Sim.Events[i];
                switch (e.Kind)
                {
                    case BattleEventKind.Launch:
                        {
                            ShipView src = ViewOf(e.ShipId);
                            if (src != null) _effects.MuzzleFlash(src.BowWorldPos());
                            _hud.Message("Tir : " + e.Detail + " (" + e.ShipId + " > " + e.TargetId + ")");
                            break;
                        }
                    case BattleEventKind.Hit:
                        {
                            ShipView target = ViewOf(e.TargetId);
                            float dmg = ParseFloat(e.Detail);
                            if (target != null && dmg > 0f)
                            {
                                _effects.Explosion(target.transform.position, Mathf.Lerp(6f, 18f, dmg / 2600f));
                                if (e.TargetId == PlayerShip.Id) _camera.Shake(0.8f);
                            }
                            _hud.Message("Impact " + e.Detail + " sur " + e.TargetId);
                            break;
                        }
                    case BattleEventKind.Damage:
                        {
                            bool destroyed = e.Detail.EndsWith(":detruit");
                            string comp = e.Detail.Replace(":detruit", "");
                            ShipView target = ViewOf(e.ShipId);
                            if (target != null) target.MarkDamage(comp, destroyed);
                            _hud.Message((destroyed ? "COMPARTIMENT DETRUIT : " : "Degats : ") + comp + " (" + e.ShipId + ")");
                            break;
                        }
                    case BattleEventKind.Intercept:
                        _hud.Message("CIWS " + e.ShipId + " : missile " + e.Detail + " intercepte");
                        break;
                    case BattleEventKind.Sunk:
                        {
                            ShipView v = ViewOf(e.ShipId);
                            if (v != null)
                            {
                                v.BeginSink();
                                _effects.Explosion(v.transform.position, 30f);
                            }
                            _hud.Message(e.ShipId + " A COULE");
                            if (e.ShipId == PlayerShip.Id) _camera.Shake(1.2f);
                            break;
                        }
                    case BattleEventKind.Detection:
                        _hud.Message("Contact detecte : " + e.TargetId);
                        break;
                }
            }
            _eventCursor = Sim.Events.Count;
        }

        private void UpdateOutcome()
        {
            bool playerSunk = PlayerShip.Sunk;
            bool enemiesAlive = false;
            foreach (ShipState s in Sim.Ships)
            {
                if (s.Team != PlayerShip.Team && !s.Sunk) { enemiesAlive = true; break; }
            }
            if (playerSunk)
            {
                Outcome = BattleOutcome.Defeat;
                OutcomeMessage = "DEFAITE — navire coule. Le noyau ne ment jamais.";
            }
            else if (!enemiesAlive)
            {
                Outcome = BattleOutcome.Victory;
                OutcomeMessage = "VICTOIRE — ennemi envoye par le fond.";
            }
        }

        /// <summary>Relance la meme bataille (meme graine) : le replay reste deterministe.</summary>
        public void Restart()
        {
            SetupBattle();
        }

        public void CycleQualityProfile()
        {
            QualityProfiles.Cycle();
        }

        public IReadOnlyList<ShipView> AllViews() { return _views; }

        private static float ParseFloat(string s)
        {
            float v;
            if (float.TryParse(s, System.Globalization.NumberStyles.Any,
                System.Globalization.CultureInfo.InvariantCulture, out v)) return v;
            return 0f;
        }
    }
}
