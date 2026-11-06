using System.Collections.Generic;
using OmniWarships.Core.Simulation;
using OmniWarships.Core.Spec;
using UnityEngine;

namespace OmniWarships.Unity
{
    /// <summary>Rects partages par l'input et le HUD (zones tactiles).</summary>
    public static class HudLayout
    {
        public static Vector2 JoystickCenter { get { return new Vector2(170f, Screen.height - 150f); } }
        public const float JoystickRadius = 115f;

        public static Rect JoystickRectGUI
        {
            get
            {
                Vector2 c = JoystickCenter;
                return new Rect(c.x - JoystickRadius, c.y - JoystickRadius,
                    JoystickRadius * 2f, JoystickRadius * 2f);
            }
        }

        public static Rect WeaponRect(int index)
        {
            return new Rect(Screen.width - 120 - index * 110, Screen.height - 100, 100, 70);
        }

        public static Rect TargetRect
        {
            get { return new Rect(Screen.width - 120, Screen.height - 170, 100, 50); }
        }

        public static Rect QualityRect
        {
            get { return new Rect(10f, 70f, 160f, 34f); }
        }

        public static Rect RadarRect
        {
            get { return new Rect(Screen.width - 220f, 70f, 200f, 200f); }
        }

        public static Rect StatusRect
        {
            get { return new Rect(10f, 110f, 200f, 210f); }
        }

        public static Rect TopLeftRect
        {
            get { return new Rect(10f, 10f, 200f, 56f); }
        }
    }

    /// <summary>
    /// Commandes tactiles Android (+ souris/clavier en edition) :
    /// joystick virtuel (gaz/barre), boutons d'armes, selection de cible,
    /// camera orbitale au glisser, zoom au pincer. Traduit l'input en
    /// ShipCommand du noyau a chaque pas fixe.
    /// </summary>
    public sealed class TouchInputController : MonoBehaviour
    {
        private BattleDirector _director;

        // joystick
        private bool _joyActive;
        private int _joyFinger = -1;
        private Vector2 _joyVec; // x : barre -1..1, y : gaz -1..1 (avant = +1)

        // camera
        private readonly Dictionary<int, Vector2> _camFingers = new Dictionary<int, Vector2>();
        private Vector2 _orbitAccum;
        private float _zoomAccum = 1f;
        private float _lastPinchDist = -1f;
        private Vector2 _mousePrev;

        // armes
        private readonly List<string> _pendingFires = new List<string>();
        private string _targetId;
        private int _targetIndex;

        public Vector2 JoystickVec { get { return _joyVec; } }
        public bool JoystickActive { get { return _joyActive; } }
        public string CurrentTargetId { get { return _targetId; } }

        public void Bind(BattleDirector director)
        {
            _director = director;
        }

        public Vector2 ConsumeOrbit()
        {
            Vector2 o = _orbitAccum;
            _orbitAccum = Vector2.zero;
            return o;
        }

        public float ConsumeZoom()
        {
            float z = _zoomAccum;
            _zoomAccum = 1f;
            return z;
        }

        /// <summary>Armes du joueur affichables (non-CIWS), 3 max, ordre stable.</summary>
        public static List<WeaponSpec> UsableWeapons(ShipState ship)
        {
            var list = new List<WeaponSpec>();
            if (ship == null) return list;
            int guns = 0, ssm = 0, torp = 0, other = 0;
            foreach (WeaponSpec w in ship.Spec.Weapons)
            {
                if (w.Kind == WeaponKind.Ciws) continue;
                bool take = false;
                if (w.Kind == WeaponKind.Gun && guns < 1) { guns++; take = true; }
                else if (w.Kind == WeaponKind.Ssm && ssm < 1) { ssm++; take = true; }
                else if (w.Kind == WeaponKind.Torpedo && torp < 1) { torp++; take = true; }
                else if (w.Kind == WeaponKind.Sam && other < 1) { other++; take = true; }
                if (take) list.Add(w);
                if (list.Count >= 3) break;
            }
            return list;
        }

        public void CycleTarget()
        {
            ShipState player = _director == null ? null : _director.PlayerShip;
            if (player == null) return;
            List<string> ids = ContactIds(player);
            if (ids.Count == 0) { _targetId = null; _targetIndex = 0; return; }
            _targetIndex = (_targetIndex + 1) % ids.Count;
            _targetId = ids[_targetIndex];
        }

        private static List<string> ContactIds(ShipState player)
        {
            var ids = new List<string>();
            foreach (KeyValuePair<string, Contact> kv in player.Contacts)
            {
                ids.Add(kv.Key);
            }
            ids.Sort((a, b) => string.CompareOrdinal(a, b));
            return ids;
        }

        private void EnsureTarget()
        {
            ShipState player = _director == null ? null : _director.PlayerShip;
            if (player == null) return;
            if (_targetId != null && player.Contacts.ContainsKey(_targetId)) return;
            foreach (string id in ContactIds(player))
            {
                ShipState s = _director.Sim.Ship(id);
                if (s != null && !s.Sunk) { _targetId = id; _targetIndex = 0; return; }
            }
            _targetId = null;
        }

        private void Update()
        {
            bool keySteering = HandleKeys();
            HandleTouches();
            HandleMouse();

            // relachement : retour au neutre (ni touche, ni doigt sur le joystick)
            if (!keySteering && _joyFinger == -1)
            {
                _joyVec = Vector2.zero;
                _joyActive = false;
            }
        }

        private bool HandleKeys()
        {
            float throttle = 0f, rudder = 0f;
            if (Input.GetKey(KeyCode.UpArrow) || Input.GetKey(KeyCode.W)) throttle += 1f;
            if (Input.GetKey(KeyCode.DownArrow) || Input.GetKey(KeyCode.S)) throttle -= 1f;
            if (Input.GetKey(KeyCode.LeftArrow) || Input.GetKey(KeyCode.A)) rudder -= 1f;
            if (Input.GetKey(KeyCode.RightArrow) || Input.GetKey(KeyCode.D)) rudder += 1f;
            if (throttle != 0f || rudder != 0f)
            {
                _joyVec = new Vector2(rudder, throttle);
                _joyActive = true;
            }
            if (Input.GetKeyDown(KeyCode.Space)) QueueFireKeyByKind(WeaponKind.Gun);
            if (Input.GetKeyDown(KeyCode.X)) QueueFireKeyByKind(WeaponKind.Ssm);
            if (Input.GetKeyDown(KeyCode.C)) QueueFireKeyByKind(WeaponKind.Torpedo);
            if (Input.GetKeyDown(KeyCode.Tab)) CycleTarget();
            float wheel = Input.GetAxis("Mouse ScrollWheel");
            if (Mathf.Abs(wheel) > 0.001f) _zoomAccum *= 1f - wheel * 1.5f;
            return throttle != 0f || rudder != 0f;
        }

        private void HandleTouches()
        {
            Vector2 jc = HudLayout.JoystickCenter;
            for (int i = 0; i < Input.touchCount; i++)
            {
                Touch t = Input.GetTouch(i);
                Vector2 pos = ScreenToGui(t.position);

                if (t.phase == TouchPhase.Began)
                {
                    if (Vector2.Distance(pos, jc) <= HudLayout.JoystickRadius)
                    {
                        _joyActive = true;
                        _joyFinger = t.fingerId;
                    }
                    else if (HitWeaponButton(pos) == null)
                    {
                        if (HudLayout.TargetRect.Contains(pos)) CycleTarget();
                        else if (HudLayout.QualityRect.Contains(pos)) _director.CycleQualityProfile();
                        else _camFingers[t.fingerId] = t.position;
                    }
                }
                else if (t.phase == TouchPhase.Moved || t.phase == TouchPhase.Stationary)
                {
                    if (_joyActive && t.fingerId == _joyFinger)
                    {
                        Vector2 d = pos - jc;
                        if (d.magnitude > HudLayout.JoystickRadius) d = d.normalized * HudLayout.JoystickRadius;
                        _joyVec = new Vector2(d.x / HudLayout.JoystickRadius, -d.y / HudLayout.JoystickRadius);
                    }
                    else if (_camFingers.ContainsKey(t.fingerId))
                    {
                        Vector2 prev = _camFingers[t.fingerId];
                        _orbitAccum += new Vector2(t.position.x - prev.x, -(t.position.y - prev.y)) * 0.12f;
                        _camFingers[t.fingerId] = t.position;
                    }
                }
                else if (t.phase == TouchPhase.Ended || t.phase == TouchPhase.Canceled)
                {
                    if (t.fingerId == _joyFinger)
                    {
                        _joyActive = false;
                        _joyFinger = -1;
                        _joyVec = Vector2.zero;
                    }
                    _camFingers.Remove(t.fingerId);
                }
            }

            if (_camFingers.Count >= 2)
            {
                Vector2 p0 = Vector2.zero, p1 = Vector2.zero;
                int k = 0;
                foreach (KeyValuePair<int, Vector2> kv in _camFingers)
                {
                    if (k == 0) p0 = kv.Value; else if (k == 1) p1 = kv.Value;
                    k++;
                    if (k >= 2) break;
                }
                float dist = Vector2.Distance(p0, p1);
                if (_lastPinchDist > 0f && dist > 1f)
                {
                    _zoomAccum *= _lastPinchDist / dist;
                }
                _lastPinchDist = dist;
            }
            else
            {
                _lastPinchDist = -1f;
            }
        }

        private void HandleMouse()
        {
            if (Input.GetMouseButtonDown(0))
            {
                Vector2 p = ScreenToGui(Input.mousePosition);
                bool hudHit = HitWeaponButton(p) != null
                    || HudLayout.TargetRect.Contains(p)
                    || HudLayout.QualityRect.Contains(p);
                bool joy = HudLayout.JoystickRectGUI.Contains(p);
                if (!hudHit && !joy) _mousePrev = Input.mousePosition;
            }
            if (Input.GetMouseButton(0) && _mousePrev != Vector2.zero)
            {
                Vector2 delta = (Vector2)Input.mousePosition - _mousePrev;
                _orbitAccum += new Vector2(delta.x, -delta.y) * 0.12f;
                _mousePrev = Input.mousePosition;
            }
            if (Input.GetMouseButtonUp(0)) _mousePrev = Vector2.zero;
        }

        private static Vector2 ScreenToGui(Vector3 p)
        {
            return new Vector2(p.x, Screen.height - p.y);
        }

        /// <summary>Teste les boutons d'armes ; declenche le tir si presse.</summary>
        private WeaponSpec HitWeaponButton(Vector2 guiPos)
        {
            ShipState player = _director == null ? null : _director.PlayerShip;
            if (player == null) return null;
            List<WeaponSpec> weapons = UsableWeapons(player);
            for (int i = 0; i < weapons.Count; i++)
            {
                if (HudLayout.WeaponRect(i).Contains(guiPos))
                {
                    QueueFire(weapons[i].Id);
                    return weapons[i];
                }
            }
            return null;
        }

        private void QueueFire(string weaponId)
        {
            EnsureTarget();
            if (_pendingFires.Count < 8 && !_pendingFires.Contains(weaponId))
            {
                _pendingFires.Add(weaponId);
            }
        }

        private void QueueFireKeyByKind(WeaponKind kind)
        {
            ShipState player = _director == null ? null : _director.PlayerShip;
            if (player == null) return;
            foreach (WeaponSpec w in player.Spec.Weapons)
            {
                if (w.Kind == kind) { QueueFire(w.Id); return; }
            }
        }

        /// <summary>Commande du noyau pour ce pas fixe.</summary>
        public ShipCommand BuildCommand()
        {
            var cmd = new ShipCommand();
            cmd.Throttle = Mathf.Clamp(_joyVec.y, -1f, 1f);
            cmd.Rudder = Mathf.Clamp(_joyVec.x, -1f, 1f);

            EnsureTarget();
            if (_targetId != null && _pendingFires.Count > 0)
            {
                foreach (string weaponId in _pendingFires)
                {
                    cmd.Fires.Add(new FireRequest { WeaponId = weaponId, TargetShipId = _targetId });
                }
            }
            _pendingFires.Clear();
            return cmd;
        }
    }
}
