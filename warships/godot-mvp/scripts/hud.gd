extends CanvasLayer
# HUD : barres de vie joueur/ennemi, vitesse/cap/distance, overlays
# (demarrage, pause, fin). Dessin 100 % code, coordonnees 1280x720.

var _p_fill: ColorRect
var _e_fill: ColorRect
var _p_label: Label
var _e_label: Label
var _info: Label
var _overlay: ColorRect
var _big: Label
var _sub: Label

func _ready() -> void:
    layer = 5
    _panel(Rect2(16.0, 12.0, 300.0, 74.0))
    _p_label = _label(Vector2(26.0, 18.0), "JOUEUR  100%", 20)
    _p_fill = _bar(Vector2(26.0, 48.0), 280.0, Color(0.2, 0.8, 0.3))
    _panel(Rect2(964.0, 12.0, 300.0, 74.0))
    _e_label = _label(Vector2(974.0, 18.0), "ENNEMI  100%", 20)
    _e_fill = _bar(Vector2(974.0, 48.0), 280.0, Color(0.9, 0.3, 0.2))
    _info = _label(Vector2(534.0, 696.0), "", 20)
    _overlay = ColorRect.new()
    _overlay.color = Color(0.0, 0.0, 0.05, 0.66)
    _overlay.size = Vector2(1280.0, 720.0)
    _overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
    add_child(_overlay)
    _big = _label(Vector2(330.0, 230.0), "OMNI WARSHIPS", 64)
    _sub = _label(Vector2(380.0, 330.0), "", 26)
    show_start()

func show_start() -> void:
    _big.add_theme_color_override("font_color", Color(1.0, 1.0, 1.0))
    _overlay.visible = true
    _big.visible = true
    _sub.visible = true
    _big.text = "OMNI WARSHIPS"
    _big.position = Vector2(330.0, 230.0)
    _sub.text = "MVP 0.1 — touchez l ecran pour jouer"

func show_pause() -> void:
    _overlay.visible = true
    _big.visible = true
    _sub.visible = true
    _big.text = "PAUSE"
    _sub.text = "Touchez le bouton II pour reprendre"

func show_end(victory: bool, elapsed: float) -> void:
    _overlay.visible = true
    _big.visible = true
    _sub.visible = true
    if victory:
        _big.text = "VICTOIRE"
        _big.add_theme_color_override("font_color", Color(0.3, 1.0, 0.4))
    else:
        _big.text = "DEFAITE"
        _big.add_theme_color_override("font_color", Color(1.0, 0.3, 0.25))
    _sub.text = "Duree : %d s — touchez pour rejouer" % int(elapsed)

func hide_overlays() -> void:
    _overlay.visible = false
    _big.visible = false
    _sub.visible = false

func set_bars(p_hp: float, p_max: float, e_hp: float, e_max: float) -> void:
    var pf: float = clampf(p_hp / p_max, 0.0, 1.0)
    var ef: float = clampf(e_hp / e_max, 0.0, 1.0)
    _p_fill.size = Vector2(280.0 * pf, 14.0)
    _e_fill.size = Vector2(280.0 * ef, 14.0)
    _p_label.text = "JOUEUR  %d%%" % int(round(pf * 100.0))
    _e_label.text = "ENNEMI  %d%%" % int(round(ef * 100.0))

func set_info(spd: float, heading_deg: float, dist: float) -> void:
    _info.text = "Vitesse %d m/s   Cap %d   Distance ennemi %d m" % [int(round(spd)), int(round(heading_deg)), int(round(dist))]

func _panel(r: Rect2) -> void:
    var p := ColorRect.new()
    p.position = r.position
    p.size = r.size
    p.color = Color(0.05, 0.08, 0.10, 0.55)
    p.mouse_filter = Control.MOUSE_FILTER_IGNORE
    add_child(p)

func _label(pos: Vector2, text: String, size: int) -> Label:
    var l := Label.new()
    l.text = text
    l.position = pos
    l.add_theme_font_size_override("font_size", size)
    l.add_theme_color_override("font_color", Color(1.0, 1.0, 1.0))
    add_child(l)
    return l

func _bar(pos: Vector2, width: float, color: Color) -> ColorRect:
    var bg := ColorRect.new()
    bg.position = pos
    bg.size = Vector2(width, 14.0)
    bg.color = Color(0.12, 0.14, 0.16, 0.8)
    bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
    add_child(bg)
    var f := ColorRect.new()
    f.position = pos
    f.size = Vector2(width, 14.0)
    f.color = color
    f.mouse_filter = Control.MOUSE_FILTER_IGNORE
    add_child(f)
    return f
