extends Node3D
# OW-APK-MVP-001 — OMNI WARSHIPS MVP : combat naval jouable au tactile.
# Tout est construit en code : ocean, ciel, destroyer, IA ennemie, tir
# balistique, degats, victoire/defaite, HUD. Aucun asset externe, aucun
# reseau, 100 % hors ligne. Noyau pur : scripts/war_sim.gd (teste en CI).

const WarSim = preload("res://scripts/war_sim.gd")
const ShipView = preload("res://scripts/ship_view.gd")
const Hud = preload("res://scripts/hud.gd")
const TouchControls = preload("res://scripts/touch_controls.gd")

enum State { START, PLAYING, PAUSED, END }

const PLAYER_HP := 140.0
const ENEMY_HP := 100.0
const PLAYER_RELOAD := 3.0
const ENEMY_RELOAD := 4.8
const ENGAGE_DIST := 330.0
const PLAYER_SPREAD := 10.0
const ENEMY_SPREAD := 26.0

var state: int = State.START
var elapsed := 0.0
var time := 0.0
var cam: Camera3D
var hud: CanvasLayer
var controls: Control
var player := {}
var enemy := {}
var shells: Array = []
var fx: Array = []

func _ready() -> void:
    _build_world()
    cam = Camera3D.new()
    add_child(cam)
    hud = Hud.new()
    add_child(hud)
    controls = TouchControls.new()
    hud.add_child(controls)
    controls.fire_requested.connect(_on_fire_player)
    controls.pause_requested.connect(_on_pause)
    controls.any_touch.connect(_on_any_touch)
    player = _make_ship(Vector3(0.0, 0.0, 0.0), 0.0, PLAYER_HP, Color(0.30, 0.33, 0.38), true)
    enemy = _make_ship(Vector3(240.0, 0.0, 430.0), PI, ENEMY_HP, Color(0.45, 0.26, 0.22), false)
    _update_camera()

func _process(delta: float) -> void:
    var dt: float = minf(delta, 0.05)
    time += dt
    if state == State.PLAYING:
        elapsed += dt
        _step_play(dt)
    _step_fx(dt)
    _apply_visual()
    _update_camera()

func _step_play(dt: float) -> void:
    player["st"] = WarSim.step_ship(player["st"], controls.rudder, controls.throttle, dt)
    var ai := WarSim.ai_command(enemy["st"]["pos"], enemy["st"]["heading"], enemy["st"]["speed"], player["st"]["pos"], player["st"]["speed"], 170.0)
    enemy["st"] = WarSim.step_ship(enemy["st"], ai["rudder"], ai["throttle"], dt)
    player["reload_left"] = float(player["reload_left"]) - dt
    enemy["reload_left"] = float(enemy["reload_left"]) - dt
    if bool(enemy["alive"]) and float(enemy["reload_left"]) <= 0.0 and WarSim.can_fire(enemy["st"]["pos"], enemy["st"]["heading"], player["st"]["pos"], 0.6, ENGAGE_DIST):
        _fire(enemy, player, ENEMY_SPREAD)
    _step_shells(dt)
    _step_sinking(dt)
    hud.set_bars(float(player["hp"]), float(player["max_hp"]), float(enemy["hp"]), float(enemy["max_hp"]))
    hud.set_info(float(player["st"]["speed"]), _heading_deg(float(player["st"]["heading"])), _dist(player["st"]["pos"], enemy["st"]["pos"]))

func _fire(shooter: Dictionary, target: Dictionary, spread: float) -> void:
    if not bool(target["alive"]):
        return
    var st: Dictionary = shooter["st"]
    var tst: Dictionary = target["st"]
    var from_pos: Vector3 = st["pos"] + Vector3.UP * 4.6
    var tgt_vel: Vector3 = WarSim.forward_of(tst["heading"]) * float(tst["speed"])
    var aim: Vector3 = WarSim.aim_lead(from_pos, tst["pos"], tgt_vel, WarSim.SHELL_SPEED)
    aim.x += randf_range(-1.0, 1.0) * spread
    aim.z += randf_range(-1.0, 1.0) * spread
    var vel: Vector3 = WarSim.ballistic_solution(from_pos, aim)
    if vel == Vector3.ZERO:
        return
    var node := MeshInstance3D.new()
    var sph := SphereMesh.new()
    sph.radius = 0.45
    sph.height = 1.0
    node.mesh = sph
    node.material_override = _flat_mat(Color(0.08, 0.08, 0.09))
    add_child(node)
    shells.append({"pos": from_pos, "vel": vel, "node": node, "from_player": bool(shooter["is_player"]), "age": 0.0})
    shooter["reload_left"] = PLAYER_RELOAD if bool(shooter["is_player"]) else ENEMY_RELOAD

func _step_shells(dt: float) -> void:
    var i: int = shells.size() - 1
    while i >= 0:
        var sh: Dictionary = shells[i]
        var out: Dictionary = WarSim.step_shell(sh["pos"], sh["vel"], dt)
        sh["pos"] = out["pos"]
        sh["vel"] = out["vel"]
        sh["age"] = float(sh["age"]) + dt
        var pos: Vector3 = sh["pos"]
        var target: Dictionary = player if bool(sh["from_player"]) else enemy
        var hit: bool = bool(target["alive"]) and WarSim.hit_test(pos, target["st"]["pos"], float(target["st"]["heading"]), 36.0, 6.5)
        if hit:
            var dmg: float = 16.0 + randf() * 10.0
            target["hp"] = WarSim.apply_damage(float(target["hp"]), dmg)
            _explosion(pos)
            if WarSim.is_sunk(float(target["hp"])):
                target["alive"] = false
                target["sink_t"] = 0.0
            _kill_shell(i)
        elif pos.y <= 0.0:
            _splash(pos)
            _kill_shell(i)
        elif float(sh["age"]) > 12.0:
            _kill_shell(i)
        else:
            (sh["node"] as Node3D).position = pos
        i -= 1

func _kill_shell(i: int) -> void:
    (shells[i]["node"] as Node3D).queue_free()
    shells.remove_at(i)

func _step_sinking(dt: float) -> void:
    for ship in [player, enemy]:
        if float(ship["sink_t"]) >= 0.0:
            ship["sink_t"] = float(ship["sink_t"]) + dt
            if float(ship["sink_t"]) >= 1.5 and state == State.PLAYING:
                _end(ship == enemy)

func _apply_visual() -> void:
    for ship in [player, enemy]:
        var st: Dictionary = ship["st"]
        var view: Node3D = ship["view"]
        var phase: float = 0.0 if bool(ship["is_player"]) else 2.1
        var y: float = -0.35 + sin(time * 1.25 + phase) * 0.12
        var roll: float = sin(time * 0.85 + phase) * 0.03
        var pitch: float = sin(time * 0.6 + phase * 0.5) * 0.015
        var sink_t: float = float(ship["sink_t"])
        if sink_t >= 0.0:
            y -= sink_t * 1.6
            roll += sink_t * 0.22
        view.position = Vector3(st["pos"].x, y, st["pos"].z)
        view.rotation = Vector3(pitch, float(st["heading"]) + PI, roll)
        view.set_wake_scale(float(st["speed"]))
        var tgt: Dictionary = enemy if bool(ship["is_player"]) else player
        if bool(tgt["alive"]):
            view.aim_turrets(tgt["st"]["pos"] + Vector3.UP * 5.0)

func _update_camera() -> void:
    var st: Dictionary = player["st"]
    var fw: Vector3 = WarSim.forward_of(float(st["heading"]))
    var p: Vector3 = st["pos"]
    cam.position = p - fw * 80.0 + Vector3(0.0, 34.0, 0.0)
    cam.look_at(p + fw * 55.0, Vector3.UP)

func _step_fx(dt: float) -> void:
    var i: int = fx.size() - 1
    while i >= 0:
        var e: Dictionary = fx[i]
        e["age"] = float(e["age"]) + dt
        var t: float = float(e["age"]) / float(e["life"])
        if t >= 1.0:
            (e["node"] as Node3D).queue_free()
            fx.remove_at(i)
        else:
            var node: Node3D = e["node"]
            var s: float = 0.4 + t * float(e["grow"])
            node.scale = Vector3(s, s * float(e["flat"]), s)
            var mat: StandardMaterial3D = node.material_override
            var c: Color = mat.albedo_color
            c.a = (1.0 - t) * float(e["alpha"])
            mat.albedo_color = c
        i -= 1

func _splash(pos: Vector3) -> void:
    var node := MeshInstance3D.new()
    var sph := SphereMesh.new()
    sph.radius = 1.0
    sph.height = 0.6
    node.mesh = sph
    node.position = Vector3(pos.x, 0.25, pos.z)
    node.material_override = _flat_mat(Color(0.93, 0.96, 1.0, 0.7))
    add_child(node)
    fx.append({"node": node, "age": 0.0, "life": 0.8, "grow": 7.0, "flat": 0.3, "alpha": 0.7})

func _explosion(pos: Vector3) -> void:
    var node := MeshInstance3D.new()
    var sph := SphereMesh.new()
    sph.radius = 1.4
    sph.height = 2.4
    node.mesh = sph
    node.position = pos
    node.material_override = _flat_mat(Color(1.0, 0.55, 0.16, 0.95))
    add_child(node)
    fx.append({"node": node, "age": 0.0, "life": 0.55, "grow": 5.0, "flat": 1.0, "alpha": 0.95})

func _flat_mat(color: Color) -> StandardMaterial3D:
    var m := StandardMaterial3D.new()
    m.albedo_color = color
    m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    return m

func _make_ship(pos: Vector3, heading: float, hp: float, color: Color, is_player: bool) -> Dictionary:
    var view = ShipView.new()
    view.build(color, Color(0.85, 0.86, 0.88))
    add_child(view)
    return {"view": view, "st": {"pos": pos, "heading": heading, "speed": 4.0}, "hp": hp, "max_hp": hp, "reload_left": 1.2, "is_player": is_player, "alive": true, "sink_t": -1.0}

func _build_world() -> void:
    var sky_mat := ProceduralSkyMaterial.new()
    sky_mat.sky_top_color = Color(0.22, 0.45, 0.80)
    sky_mat.sky_horizon_color = Color(0.75, 0.82, 0.90)
    sky_mat.ground_bottom_color = Color(0.10, 0.20, 0.30)
    sky_mat.ground_horizon_color = Color(0.55, 0.62, 0.70)
    var sky := Sky.new()
    sky.sky_material = sky_mat
    var env := Environment.new()
    env.background_mode = Environment.BG_SKY
    env.sky = sky
    env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
    env.ambient_light_energy = 1.0
    env.fog_enabled = true
    env.fog_light_color = Color(0.75, 0.82, 0.90)
    env.fog_density = 0.0025
    var we := WorldEnvironment.new()
    we.environment = env
    add_child(we)
    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-52.0, 35.0, 0.0)
    sun.light_energy = 1.15
    add_child(sun)
    var ocean := MeshInstance3D.new()
    var plane := PlaneMesh.new()
    plane.size = Vector2(6000.0, 6000.0)
    ocean.mesh = plane
    var om := StandardMaterial3D.new()
    om.albedo_color = Color(0.05, 0.20, 0.32)
    om.roughness = 0.15
    ocean.material_override = om
    add_child(ocean)

func _heading_deg(h: float) -> float:
    return fposmod(rad_to_deg(h), 360.0)

func _dist(a: Vector3, b: Vector3) -> float:
    return Vector2(a.x - b.x, a.z - b.z).length()

func _on_fire_player() -> void:
    if state == State.PLAYING and float(player["reload_left"]) <= 0.0 and bool(enemy["alive"]):
        _fire(player, enemy, PLAYER_SPREAD)

func _on_pause() -> void:
    if state == State.PLAYING:
        state = State.PAUSED
        hud.show_pause()
    elif state == State.PAUSED:
        state = State.PLAYING
        hud.hide_overlays()

func _on_any_touch() -> void:
    if state == State.START:
        state = State.PLAYING
        hud.hide_overlays()
    elif state == State.END:
        get_tree().call_deferred("reload_current_scene")

func _end(victory: bool) -> void:
    state = State.END
    hud.show_end(victory, elapsed)
