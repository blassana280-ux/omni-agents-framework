using System.Collections.Generic;
using OmniWarships.Core.Simulation;
using OmniWarships.Core.Spec;
using UnityEngine;

namespace OmniWarships.Unity
{
    /// <summary>
    /// Effets de combat reliés aux événements RÉELS du noyau : traînées de
    /// fumée des missiles en vol, bulles de torpilles, tracers + flak de la
    /// défense antiaérienne sur chaque événement Intercept. Le noyau reste la
    /// seule source de vérité ; ce composant ne fait que de la présentation.
    /// </summary>
    public sealed class CombatEffects : MonoBehaviour
    {
        private BattleDirector _director;
        private BattleSim _lastSim;
        private int _eventCursor;
        private readonly Dictionary<string, Vector3> _lastPos = new Dictionary<string, Vector3>();
        private readonly Dictionary<string, float> _nextTrailS = new Dictionary<string, float>();

        public void Bind(BattleDirector director)
        {
            _director = director;
            director.OnSimTicked += OnSimTicked;
        }

        private void OnSimTicked()
        {
            if (_director == null || _director.Sim == null) return;

            // Restart -> nouvelle sim : curseurs et mémoire remis à zéro
            if (_director.Sim != _lastSim)
            {
                _lastSim = _director.Sim;
                _eventCursor = 0;
                _lastPos.Clear();
                _nextTrailS.Clear();
            }

            if (QualityProfiles.EffectsEnabled) TrailProjectiles();
            DrainIntercepts();
        }

        private void TrailProjectiles()
        {
            foreach (Projectile p in _director.Sim.Projectiles)
            {
                Vector3 pos = new Vector3(p.Pos.X, p.Altitude, p.Pos.Y);
                _lastPos[p.Id] = pos;

                float next;
                if (!_nextTrailS.TryGetValue(p.Id, out next)) next = 0f;

                if (p.Kind == WeaponKind.Ssm || p.Kind == WeaponKind.Sam || p.Kind == WeaponKind.Rocket)
                {
                    // traînée de propulsion du missile
                    if (Time.time >= next)
                    {
                        _director.Effects.Smoke(pos - new Vector3(0f, 0.6f, 0f), 2.6f);
                        _nextTrailS[p.Id] = Time.time + 0.12f;
                    }
                }
                else if (p.Kind == WeaponKind.Torpedo)
                {
                    // bulles du lanceur/torpille : remontée à la surface
                    if (Time.time >= next)
                    {
                        float surfY = _director.Sim.Ocean.HeightAt(p.Pos.X, p.Pos.Y, _director.Sim.TimeS);
                        _director.Effects.Smoke(new Vector3(p.Pos.X, surfY, p.Pos.Y), 1.5f);
                        _nextTrailS[p.Id] = Time.time + 0.22f;
                    }
                }
            }
        }

        private void DrainIntercepts()
        {
            var events = _director.Sim.Events;
            for (int i = _eventCursor; i < events.Count; i++)
            {
                BattleEvent e = events[i];
                if (e.Kind != BattleEventKind.Intercept) continue;

                ShipView defender = _director.ViewOf(e.ShipId);
                Vector3 projPos;
                if (defender == null || !_lastPos.TryGetValue(e.Detail, out projPos)) continue;

                // tracers AA : points de flash entre le défenseur et le missile
                Vector3 from = defender.transform.position + Vector3.up * 14f;
                for (int k = 1; k <= 4; k++)
                {
                    _director.Effects.MuzzleFlash(Vector3.Lerp(from, projPos, k / 4f));
                }
                // flak : le missile intercepté explose en vol
                _director.Effects.Explosion(projPos, 5.5f);
            }
            _eventCursor = events.Count;
        }
    }
}
