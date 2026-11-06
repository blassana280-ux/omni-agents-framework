using System.Collections.Generic;
using OmniWarships.Core.Simulation;
using OmniWarships.Core.Spec;
using UnityEngine;

namespace OmniWarships.Unity
{
    /// <summary>
    /// HUD complet (OnGUI, aucune dependance a des assets UI) : vitesse, cap,
    /// sante par compartiment, voie d'eau, radar de contacts, armement avec
    /// munitions/rechargement, messages de bataille, FPS mesures, profils de
    /// qualite, ecran de victoire/defaite + rejouer.
    /// </summary>
    public sealed class HudController : MonoBehaviour
    {
        private BattleDirector _director;
        private Texture2D _white;
        private Texture2D _radarBg;
        private GUIStyle _label, _labelBig, _labelSmall, _boxStyle;
        private float _radarRangeM = 12000f;

        private readonly List<KeyValuePair<string, float>> _messages = new List<KeyValuePair<string, float>>();

        // FPS + adaptatif
        private int _frames;
        private float _fpsTimer;
        private int _fps;
        private float _avgFrameMs = 33f;
        private float _goodTime;
        private QualityProfile _adaptiveTarget = QualityProfile.Medium;

        public void Bind(BattleDirector director)
        {
            _director = director;

            _white = new Texture2D(1, 1);
            _white.SetPixel(0, 0, Color.white);
            _white.Apply();

            _radarBg = BuildRadarTexture(128);

            _label = new GUIStyle();
            _label.fontSize = 16;
            _label.normal.textColor = Color.white;
            _labelBig = new GUIStyle();
            _labelBig.fontSize = 34;
            _labelBig.fontStyle = FontStyle.Bold;
            _labelBig.alignment = TextAnchor.MiddleCenter;
            _labelBig.normal.textColor = Color.white;
            _labelSmall = new GUIStyle();
            _labelSmall.fontSize = 13;
            _labelSmall.normal.textColor = new Color(0.9f, 0.93f, 1f);
            _boxStyle = new GUIStyle();
        }

        private static Texture2D BuildRadarTexture(int size)
        {
            var t = new Texture2D(size, size, TextureFormat.RGBA32, false);
            float c = (size - 1) * 0.5f;
            for (int y = 0; y < size; y++)
            {
                for (int x = 0; x < size; x++)
                {
                    float d = Mathf.Sqrt((x - c) * (x - c) + (y - c) * (y - c)) / c;
                    Color col;
                    if (d > 1f) col = new Color(0f, 0f, 0f, 0f);
                    else if (d > 0.97f) col = new Color(0.35f, 0.9f, 0.5f, 0.9f);
                    else col = new Color(0.02f, 0.10f, 0.05f, 0.55f);
                    t.SetPixel(x, y, col);
                }
            }
            t.Apply();
            return t;
        }

        public void Message(string msg)
        {
            _messages.Add(new KeyValuePair<string, float>(msg, Time.time));
            while (_messages.Count > 6) _messages.RemoveAt(0);
        }

        private void Update()
        {
            _frames++;
            _fpsTimer += Time.unscaledDeltaTime;
            if (_fpsTimer >= 0.5f)
            {
                _fps = Mathf.RoundToInt(_frames / _fpsTimer);
                _fpsTimer = 0f;
                _frames = 0;
            }
            _avgFrameMs = Mathf.Lerp(_avgFrameMs, Time.unscaledDeltaTime * 1000f, 1f / 30f);

            if (QualityProfiles.Current == QualityProfile.Adaptive)
            {
                if (_avgFrameMs > 42f)
                {
                    if (_adaptiveTarget > QualityProfile.Low) _adaptiveTarget--;
                    _goodTime = 0f;
                }
                else if (_avgFrameMs < 23f)
                {
                    _goodTime += Time.unscaledDeltaTime;
                    if (_goodTime > 6f && _adaptiveTarget < QualityProfile.High)
                    {
                        _adaptiveTarget++;
                        _goodTime = 0f;
                    }
                }
                else _goodTime = 0f;
                QualityProfiles.ApplyAdaptiveTarget(_adaptiveTarget);
            }
        }

        private void OnGUI()
        {
            if (_director == null || _director.Sim == null) return;
            ShipState player = _director.PlayerShip;
            if (player == null) return;

            DrawTopLeft();
            DrawTopCenter();
            DrawStatus(player);
            DrawRadar(player);
            DrawWeapons(player);
            DrawJoystick();
            DrawMessages();
            DrawOutcome();
        }

        private void DrawTopLeft()
        {
            Rect r = HudLayout.TopLeftRect;
            GUI.Box(r, "");
            GUI.Label(new Rect(r.x + 8, r.y + 4, 190, 22),
                "FPS " + _fps + "  |  " + QualityProfiles.Label(QualityProfiles.Current) +
                (QualityProfiles.Current == QualityProfile.Adaptive ?
                    " (" + QualityProfiles.Label(QualityProfiles.EffectiveProfile) + ")" : ""), _label);
            if (GUI.Button(HudLayout.QualityRect, "Profil : " + QualityProfiles.Label(QualityProfiles.Current)))
            {
                _director.CycleQualityProfile();
            }
        }

        private void DrawTopCenter()
        {
            float w = 260f;
            Rect r = new Rect(Screen.width * 0.5f - w * 0.5f, 10f, w, 30f);
            int total = Mathf.RoundToInt(_director.BattleTimeS);
            string s = string.Format("{0:00}:{1:00}  T+{2}", total / 60, total % 60, _director.Sim.TickIndex);
            GUI.Label(r, s, _label);
        }

        private void DrawStatus(ShipState player)
        {
            Rect r = HudLayout.StatusRect;
            GUI.Box(r, "");

            float kn = player.SpeedMs / 0.5144f;
            GUI.Label(new Rect(r.x + 10, r.y + 8, 180, 24),
                "Vitesse : " + kn.ToString("0.0") + " noeuds", _label);
            GUI.Label(new Rect(r.x + 10, r.y + 32, 180, 24),
                "Cap : " + player.HeadingDeg.ToString("0") + (char)176 + " (" + Cardinal(player.HeadingDeg) + ")", _label);

            // sante totale + compartiments
            float hp = 0f, hpMax = 0f;
            foreach (CompartmentState c in player.Compartments) { hp += c.Hp; hpMax += c.HpMax; }
            float frac = hpMax > 0f ? hp / hpMax : 0f;
            GUI.Label(new Rect(r.x + 10, r.y + 58, 180, 22), "Integrite : " + (frac * 100f).ToString("0") + " %", _label);
            DrawBar(new Rect(r.x + 10, r.y + 80, 180, 12), frac, Color.Lerp(Color.red, Color.green, frac));

            float y = r.y + 98;
            foreach (CompartmentState c in player.Compartments)
            {
                float cf = c.HpMax > 0f ? c.Hp / c.HpMax : 0f;
                Color col = c.Destroyed ? Color.red : (c.Breached ? new Color(1f, 0.55f, 0.1f) : new Color(0.4f, 0.75f, 1f));
                DrawBar(new Rect(r.x + 10, y, 180, 7), cf, col);
                if (c.Flooding > 0.01f)
                {
                    DrawBar(new Rect(r.x + 10, y + 7, 180, 4), c.Flooding, new Color(0.2f, 0.45f, 1f));
                }
                y += c.Breached ? 16 : 11;
            }

            float buoy = FloodingModel.LostBuoyancy(player);
            if (buoy > 0.01f)
            {
                GUI.Label(new Rect(r.x + 10, r.y + 186, 180, 20),
                    "VOIE D'EAU : " + (buoy * 100f).ToString("0") + " %", _labelSmall);
            }
        }

        private void DrawRadar(ShipState player)
        {
            Rect r = HudLayout.RadarRect;
            GUI.DrawTexture(r, _radarBg, ScaleMode.StretchToFill, true);

            // nord en haut, navire du joueur au centre
            Vector2 c = r.center;
            float px = Mathf.Min(r.width, r.height) * 0.5f - 4f;

            // ligne de balayage
            float sweep = (Time.time * 90f) % 360f;
            Vector2 dir = DirFromHeading(sweep);
            DrawLine(c, c + dir * px, new Color(0.4f, 1f, 0.5f, 0.55f));

            // marqueur joueur (chevron vers le cap)
            DrawRect(new Rect(c.x - 3, c.y - 3, 6, 6), Color.cyan);

            foreach (KeyValuePair<string, Contact> kv in player.Contacts)
            {
                Contact ct = kv.Value;
                ShipState target = _director.Sim.Ship(ct.ShipId);
                if (target == null) continue;
                float dx = ct.EstimatedPos.X - player.Pos.X;
                float dz = ct.EstimatedPos.Y - player.Pos.Y;
                float scale = px / _radarRangeM;
                Vector2 p = new Vector2(c.x + dx * scale, c.y - dz * scale);
                if ((p - c).magnitude > px) continue;
                Color col = target.Sunk ? new Color(0.6f, 0.6f, 0.6f, 0.7f) :
                    new Color(1f, 0.35f, 0.3f, 0.4f + 0.6f * ct.Quality);
                DrawRect(new Rect(p.x - 3, p.y - 3, 6, 6), col);

                if (_director.Input != null && kv.Key == _director.Input.CurrentTargetId)
                {
                    DrawRect(new Rect(p.x - 6, p.y - 6, 12, 12), new Color(1f, 0.9f, 0.2f, 0.9f));
                }
            }
        }

        private static Vector2 DirFromHeading(float deg)
        {
            float rad = deg * Mathf.Deg2Rad;
            return new Vector2(Mathf.Sin(rad), Mathf.Cos(rad));
        }

        private void DrawWeapons(ShipState player)
        {
            List<WeaponSpec> weapons = TouchInputController.UsableWeapons(player);
            for (int i = 0; i < weapons.Count; i++)
            {
                WeaponSpec w = weapons[i];
                Rect r = HudLayout.WeaponRect(i);
                WeaponState ws;
                player.Weapons.TryGetValue(w.Id, out ws);

                string name = WeaponShortName(w.Kind);
                int ammo = ws == null ? 0 : ws.Ammo;
                GUI.Box(r, "");
                string txt = name + "\n" + ammo + " mun.";
                if (ws != null && ws.CooldownS > 0f)
                {
                    float cf = 1f - Mathf.Clamp01(ws.CooldownS / Mathf.Max(0.5f, w.ReloadS));
                    DrawBar(new Rect(r.x + 2, r.y + r.height - 8, r.width - 4, 6), cf, new Color(1f, 0.85f, 0.2f));
                    txt += "\nRECH " + ws.CooldownS.ToString("0.0") + "s";
                }
                GUI.Label(r, txt, _labelSmall);
            }

            string tgt = _director.Input == null ? null : _director.Input.CurrentTargetId;
            string tgtLabel = "CIBLE\n" + (string.IsNullOrEmpty(tgt) ? "—" : tgt);
            if (GUI.Button(HudLayout.TargetRect, tgtLabel, _labelSmall))
            {
                if (_director.Input != null) _director.Input.CycleTarget();
            }
        }

        private static string WeaponShortName(WeaponKind k)
        {
            switch (k)
            {
                case WeaponKind.Gun: return "CANON";
                case WeaponKind.Ssm: return "MISSILES";
                case WeaponKind.Sam: return "SAM";
                case WeaponKind.Torpedo: return "TORPILLES";
                default: return k.ToString().ToUpper();
            }
        }

        private void DrawJoystick()
        {
            Vector2 c = HudLayout.JoystickCenter;
            float rad = HudLayout.JoystickRadius;
            Color ring = new Color(1f, 1f, 1f, 0.25f);
            DrawRing(c, rad, ring);

            Vector2 knob = c + (_director.Input == null ? Vector2.zero :
                new Vector2(_director.Input.JoystickVec.x, -_director.Input.JoystickVec.y) * rad);
            GUI.DrawTexture(new Rect(knob.x - 22, knob.y - 22, 44, 44), _white, ScaleMode.StretchToFill, true, 0f,
                new Color(0.75f, 0.85f, 1f, 0.8f));
        }

        private void DrawRing(Vector2 c, float radius, Color col)
        {
            // cercle approxime par segments
            int segs = 36;
            Vector2 prev = c + new Vector2(radius, 0f);
            for (int i = 1; i <= segs; i++)
            {
                float a = 2f * Mathf.PI * i / segs;
                Vector2 p = c + new Vector2(Mathf.Cos(a) * radius, Mathf.Sin(a) * radius);
                DrawLine(prev, p, col);
                prev = p;
            }
        }

        private void DrawLine(Vector2 a, Vector2 b, Color col)
        {
            Vector2 mid = (a + b) * 0.5f;
            Vector2 delta = b - a;
            float len = delta.magnitude;
            if (len < 0.5f) return;
            float ang = Mathf.Atan2(delta.y, delta.x) * Mathf.Rad2Deg;
            Matrix4x4 saved = GUI.matrix;
            GUIUtility.RotateAroundPivot(ang, mid);
            GUI.DrawTexture(new Rect(mid.x - len * 0.5f, mid.y - 0.5f, len, 1.5f), _white,
                ScaleMode.StretchToFill, true, 0f, col);
            GUI.matrix = saved;
        }

        private void DrawRect(Rect r, Color col)
        {
            GUI.DrawTexture(r, _white, ScaleMode.StretchToFill, true, 0f, col);
        }

        private void DrawBar(Rect r, float frac, Color col)
        {
            DrawRect(r, new Color(0.1f, 0.12f, 0.15f, 0.9f));
            if (frac > 0.001f)
            {
                Rect f = new Rect(r.x, r.y, r.width * Mathf.Clamp01(frac), r.height);
                DrawRect(f, col);
            }
        }

        private void DrawMessages()
        {
            float y = Screen.height - 140f;
            for (int i = _messages.Count - 1; i >= 0; i--)
            {
                float age = Time.time - _messages[i].Value;
                if (age > 7f) { _messages.RemoveAt(i); continue; }
                float alpha = age > 5f ? 1f - (age - 5f) / 2f : 1f;
                Color c = new Color(1f, 0.95f, 0.8f, alpha);
                Rect r = new Rect(Screen.width * 0.5f - 240f, y - (i * 20f), 480f, 20f);
                var style = new GUIStyle(_labelSmall);
                style.alignment = TextAnchor.MiddleCenter;
                style.normal.textColor = c;
                GUI.Label(r, _messages[i].Key, style);
            }
        }

        private void DrawOutcome()
        {
            if (_director.Outcome == BattleOutcome.InProgress) return;
            Color overlay = new Color(0f, 0f, 0f, 0.55f);
            GUI.DrawTexture(new Rect(0, 0, Screen.width, Screen.height), _white,
                ScaleMode.StretchToFill, false, 0f, overlay);

            string title = _director.Outcome == BattleOutcome.Victory ? "VICTOIRE" : "DEFAITE";
            Color col = _director.Outcome == BattleOutcome.Victory ?
                new Color(0.55f, 1f, 0.6f) : new Color(1f, 0.4f, 0.35f);
            var style = new GUIStyle(_labelBig);
            style.fontSize = 56;
            style.normal.textColor = col;
            GUI.Label(new Rect(0, Screen.height * 0.3f, Screen.width, 70), title, style);
            if (_director.OutcomeMessage != null)
            {
                GUI.Label(new Rect(0, Screen.height * 0.3f + 80, Screen.width, 30), _director.OutcomeMessage, _label);
            }
            Rect b = new Rect(Screen.width * 0.5f - 110, Screen.height * 0.55f, 220, 50);
            if (GUI.Button(b, "REJOUER"))
            {
                _director.Restart();
            }
        }

        private static string Cardinal(float headingDeg)
        {
            string[] names = { "N", "NE", "E", "SE", "S", "SO", "O", "NO" };
            int i = Mathf.RoundToInt(headingDeg / 45f) % 8;
            return names[i];
        }
    }
}
