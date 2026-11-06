using UnityEngine;

namespace OmniWarships.Unity
{
    /// <summary>
    /// Pause et paramètres : fige le temps (timeScale 0) et désactive le
    /// directeur (FixedUpdate off = le noyau s'arrête proprement), menu
    /// tactile OnGUI : reprendre, les 5 profils graphiques, recommencer la
    /// bataille, quitter. Bouton système Android (retour) = pause.
    /// </summary>
    public sealed class PauseMenu : MonoBehaviour
    {
        public static bool IsPaused { get; private set; }

        private BattleDirector _director;
        private GUIStyle _style, _big;
        private Texture2D _white;

        public void Bind(BattleDirector director)
        {
            _director = director;
            _white = new Texture2D(1, 1);
            _white.SetPixel(0, 0, Color.white);
            _white.Apply();
        }

        private void Update()
        {
            if (_director == null) return;
            if (Input.GetKeyDown(KeyCode.Escape) || Input.GetKeyDown(KeyCode.P))
            {
                Toggle();
            }
        }

        public void Toggle()
        {
            if (_director == null) return;
            IsPaused = !IsPaused;
            Time.timeScale = IsPaused ? 0f : 1f;
            _director.enabled = !IsPaused; // FixedUpdate : le noyau s'arrête
            if (_director.Input != null) _director.Input.enabled = !IsPaused;
            if (_director.Cam != null) _director.Cam.enabled = !IsPaused;
        }

        private void OnGUI()
        {
            if (_director == null) return;
            if (_style == null)
            {
                _style = new GUIStyle();
                _style.fontSize = 19;
                _style.normal.textColor = Color.white;
                _style.alignment = TextAnchor.MiddleCenter;
                _big = new GUIStyle();
                _big.fontSize = 38;
                _big.fontStyle = FontStyle.Bold;
                _big.normal.textColor = Color.white;
                _big.alignment = TextAnchor.MiddleCenter;
            }

            if (!IsPaused)
            {
                if (GUI.Button(new Rect(Screen.width * 0.5f + 150f, 10f, 110f, 42f), "II  PAUSE"))
                {
                    Toggle();
                }
                return;
            }

            // voile sombre plein écran
            GUI.DrawTexture(new Rect(0f, 0f, Screen.width, Screen.height), _white,
                ScaleMode.StretchToFill, false, 0f, new Color(0f, 0f, 0f, 0.78f));

            float bx = Screen.width * 0.5f - 160f;
            float by = Screen.height * 0.20f;

            GUI.Box(new Rect(bx - 24f, by - 26f, 368f, 500f), "");
            GUI.Label(new Rect(bx, by, 320f, 46f), "PAUSE", _big);
            by += 58f;

            if (GUI.Button(new Rect(bx, by, 320f, 46f), "REPRENDRE")) Toggle();
            by += 58f;

            GUI.Label(new Rect(bx, by, 320f, 24f), "PROFILS GRAPHIQUES", _style);
            by += 30f;
            for (int i = 0; i < 5; i++)
            {
                QualityProfile p = (QualityProfile)i;
                string mark = QualityProfiles.Current == p ? "[x] " : "[  ] ";
                if (GUI.Button(new Rect(bx, by, 320f, 40f), mark + QualityProfiles.Label(p)))
                {
                    QualityProfiles.Apply(p);
                }
                by += 44f;
            }

            by += 8f;
            if (GUI.Button(new Rect(bx, by, 320f, 46f), "RECOMMENCER LA BATAILLE"))
            {
                _director.Restart();
                if (IsPaused) Toggle(); // relance + reprise du temps
            }
            by += 58f;
            if (GUI.Button(new Rect(bx, by, 320f, 46f), "QUITTER"))
            {
                Application.Quit();
            }
        }
    }
}
