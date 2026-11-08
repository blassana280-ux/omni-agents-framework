extends SceneTree
# Tests headless deterministes du noyau naval (OW-APK-MVP-001).
# CI : godot --headless -s tests/test_core.gd — code de sortie non nul si echec.

const WarSim = preload("res://scripts/war_sim.gd")

var fails := 0
var total := 0

func _init() -> void:
    _test_step_ship_straight()
    _test_step_ship_turn()
    _test_wrap_angle()
    _test_ballistic_exact()
    _test_shell_flight_lands_on_target()
    _test_aim_lead()
    _test_hit_test()
    _test_damage()
    _test_ai_far_approach()
    _test_can_fire_sector()
    if fails == 0:
        print("[TEST] all passed (%d tests)" % total)
    else:
        print("[TEST] FAILED %d / %d" % [fails, total])
    quit(1 if fails > 0 else 0)

func _check(name: String, ok: bool) -> void:
    total += 1
    if ok:
        print("[TEST] PASS %s" % name)
    else:
        fails += 1
        print("[TEST] FAIL %s" % name)

func _test_step_ship_straight() -> void:
    var st := {"pos": Vector3(0, 0, 0), "heading": 0.0, "speed": 5.0}
    var out := WarSim.step_ship(st, 0.0, 1.0, 1.0)
    _check("step_ship accelere tout droit", absf(float(out["speed"]) - 7.0) < 0.01 and absf(float(out["pos"].z) - 7.0) < 0.01 and absf(float(out["pos"].x)) < 0.001)

func _test_step_ship_turn() -> void:
    var st := {"pos": Vector3(0, 0, 0), "heading": 0.0, "speed": 13.0}
    var out := WarSim.step_ship(st, 1.0, 1.0, 1.0)
    _check("step_ship vire avec la barre", float(out["heading"]) > 0.3 and float(out["heading"]) < 0.4)

func _test_wrap_angle() -> void:
    _check("wrap_angle ramene dans [-PI, PI]", absf(WarSim.wrap_angle(3.0 * PI) - PI) < 0.001 and absf(WarSim.wrap_angle(-3.0 * PI) + PI) < 0.001)

func _test_ballistic_exact() -> void:
    var from := Vector3(0.0, 4.6, 0.0)
    var aim := Vector3(0.0, 0.0, 200.0)
    var vel := WarSim.ballistic_solution(from, aim)
    var ok := vel != Vector3.ZERO
    if ok:
        ok = absf(vel.x) < 0.001 and vel.z > 80.0 and vel.y > 8.0
    _check("ballistic_solution arc bas vers 200 m", ok)

func _test_shell_flight_lands_on_target() -> void:
    var from := Vector3(0.0, 4.6, 0.0)
    var aim := Vector3(35.0, 0.0, 210.0)
    var vel := WarSim.ballistic_solution(from, aim)
    var pos := from
    var t := 0.0
    var landed := false
    var dist := 999.0
    while t < 12.0:
        var out := WarSim.step_shell(pos, vel, 0.02)
        pos = out["pos"]
        vel = out["vel"]
        t += 0.02
        if pos.y <= 0.0:
            landed = true
            break
    if landed:
        dist = Vector2(pos.x - aim.x, pos.z - aim.z).length()
    _check("tir simule tombe sur la cible (< 3 m)", landed and dist < 3.0)

func _test_aim_lead() -> void:
    var from := Vector3(0.0, 4.6, 0.0)
    var tgt := Vector3(0.0, 0.0, 300.0)
    var vel := Vector3(5.0, 0.0, 0.0)
    var aim := WarSim.aim_lead(from, tgt, vel, 85.0)
    _check("aim_lead anticipe la cible en mouvement", aim.x > 12.0 and aim.x < 25.0 and absf(aim.z - 300.0) < 0.001)

func _test_hit_test() -> void:
    var ship_pos := Vector3(0.0, 0.0, 0.0)
    var h := PI / 2.0
    var hit_mid := WarSim.hit_test(Vector3(0.0, 1.0, 3.0), ship_pos, h, 35.0, 6.0)
    var miss_bow := not WarSim.hit_test(Vector3(40.0, 1.0, 0.0), ship_pos, h, 35.0, 6.0)
    var miss_side := not WarSim.hit_test(Vector3(0.0, 1.0, 10.0), ship_pos, h, 35.0, 6.0)
    var miss_high := not WarSim.hit_test(Vector3(0.0, 20.0, 0.0), ship_pos, h, 35.0, 6.0)
    _check("hit_test boite orientee + hauteur", hit_mid and miss_bow and miss_side and miss_high)

func _test_damage() -> void:
    _check("degats et naufrage", absf(WarSim.apply_damage(100.0, 30.0) - 70.0) < 0.001 and WarSim.apply_damage(5.0, 30.0) == 0.0 and WarSim.is_sunk(0.0) and not WarSim.is_sunk(1.0))

func _test_ai_far_approach() -> void:
    var cmd := WarSim.ai_command(Vector3(0.0, 0.0, 0.0), 0.0, 8.0, Vector3(300.0, 0.0, 300.0), 5.0, 160.0)
    _check("IA approche a pleine puissance quand loin", float(cmd["throttle"]) == 1.0 and float(cmd["rudder"]) > 0.0)

func _test_can_fire_sector() -> void:
    var ok := WarSim.can_fire(Vector3.ZERO, 0.0, Vector3(30.0, 0.0, 100.0), 0.5, 330.0)
    var ko := WarSim.can_fire(Vector3.ZERO, 0.0, Vector3(60.0, 0.0, -50.0), 0.5, 330.0)
    _check("secteur de tir respecte", ok and not ko)
