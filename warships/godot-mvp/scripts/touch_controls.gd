extends Control
# Commandes tactiles plein ecran : barre a babord (glisser), boutons TIR et
# AVANCE a tribord, pause en haut. Traite les evenements bruts, dessin en code.
# Coordonnees logiques 1280x720 (stretch canvas_items).

signal fire_requested
signal pause_requested
signal any_touch

var rudder := 0.0
var throttle := 0.0

var _steering := false
var _steer_idx := -1
var _steer_origin := Vector2.ZERO

const FIRE_CENTER := Vector2(1160.0, 600.0)
const FIRE_RADIUS := 82.0
const THROTTLE_RECT := Rect2(930.0, 540.0, 140.0, 140.0)
const PAUSE_RECT := Rect2(600.0, 16.0, 80.0, 44.0)
const STEER_MAX_X := 520.0

func _ready() -> void:
    set_anchors_preset(Control.PRESET_FULL_RECT)
    mouse_filter = Control.MOUSE_FILTER_IGNORE

func _input(ev: InputEvent) -> void:
    if ev is InputEventScreenTouch:
        if ev.pressed:
            _press(ev.index, ev.position)
        else:
            _release(ev.index)
    elif ev is InputEventScreenDrag and _steering and ev.index == _steer_idx:
        rudder = clampf((ev.position.x - _steer_origin.x) / 170.0, -1.0, 1.0)
        queue_redraw()

func _press(idx: int, p: Vector2) -> void:
    any_touch.emit()
    if PAUSE_RECT.has_point(p):
        pause_requested.emit()
        return
    if p.distance_to(FIRE_CENTER) <= FIRE_RADIUS:
        fire_requested.emit()
        return
    if THROTTLE_RECT.has_point(p):
        throttle = 0.0 if throttle > 0.0 else 1.0
        queue_redraw()
        return
    if p.x < STEER_MAX_X:
        _steering = true
        _steer_idx = idx
        _steer_origin = p
        rudder = 0.0
        queue_redraw()

func _release(idx: int) -> void:
    if _steering and idx == _steer_idx:
        _steering = false
        _steer_idx = -1
        rudder = 0.0
        queue_redraw()

func _draw() -> void:
    draw_circle(FIRE_CENTER, FIRE_RADIUS, Color(0.85, 0.20, 0.15, 0.75))
    draw_circle(FIRE_CENTER, FIRE_RADIUS - 6.0, Color(0.95, 0.35, 0.25, 0.9))
    draw_string(ThemeDB.fallback_font, FIRE_CENTER + Vector2(-34.0, 12.0), "TIR", HORIZONTAL_ALIGNMENT_LEFT, -1, 34, Color(1, 1, 1))
    draw_rect(THROTTLE_RECT, Color(0.10, 0.45, 0.20, 0.75))
    var tlabel := "STOP" if throttle > 0.0 else "AVANCE"
    draw_string(ThemeDB.fallback_font, THROTTLE_RECT.position + Vector2(20.0, 80.0), tlabel, HORIZONTAL_ALIGNMENT_LEFT, -1, 26, Color(1, 1, 1))
    draw_rect(PAUSE_RECT, Color(1.0, 1.0, 1.0, 0.25))
    draw_string(ThemeDB.fallback_font, PAUSE_RECT.position + Vector2(14.0, 30.0), "II", HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color(1, 1, 1))
    var base := Vector2(120.0, 660.0)
    draw_line(base - Vector2(90.0, 0.0), base + Vector2(90.0, 0.0), Color(1, 1, 1, 0.35), 3.0)
    draw_circle(base + Vector2(rudder * 90.0, 0.0), 10.0, Color(1, 1, 1, 0.8))
