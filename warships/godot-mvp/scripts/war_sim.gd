extends RefCounted
# OW-APK-MVP-001 — noyau de simulation naval pur (aucune dependance au rendu).
# Les memes fonctions servent au jeu (main.gd) et aux tests headless
# deterministes (tests/test_core.gd). Convention : cap 0 = +Z, croissant
# en sens horaire vu du dessus.

const SHELL_SPEED := 85.0
const SHELL_GRAVITY := 9.8
const SHELL_MAX_RANGE := 740.0
const MAX_SPEED := 13.0
const ACCEL := 2.0
const MAX_TURN_RATE := 0.35

static func wrap_angle(a: float) -> float:
    while a > PI:
        a -= TAU
    while a < -PI:
        a += TAU
    return a

static func forward_of(heading: float) -> Vector3:
    return Vector3(sin(heading), 0.0, cos(heading))

static func step_ship(st: Dictionary, rudder: float, throttle: float, dt: float) -> Dictionary:
    var target: float = clampf(throttle, 0.0, 1.0) * MAX_SPEED
    var speed: float = float(st["speed"])
    if speed < target:
        speed = minf(speed + ACCEL * dt, target)
    else:
        speed = maxf(speed - ACCEL * dt, target)
    var turn: float = MAX_TURN_RATE * clampf(speed / 6.0, 0.1, 1.0) * clampf(rudder, -1.0, 1.0)
    var heading: float = wrap_angle(float(st["heading"]) + turn * dt)
    var pos: Vector3 = (st["pos"] as Vector3) + forward_of(heading) * speed * dt
    return {"pos": pos, "heading": heading, "speed": speed}

static func hit_test(point: Vector3, ship_pos: Vector3, heading: float, half_len: float, half_beam: float) -> bool:
    if point.y < -2.0 or point.y > 14.0:
        return false
    var dx: float = point.x - ship_pos.x
    var dz: float = point.z - ship_pos.z
    var lx: float = dx * cos(heading) - dz * sin(heading)
    var lz: float = dx * sin(heading) + dz * cos(heading)
    return absf(lx) <= half_beam and absf(lz) <= half_len

static func range_for_angle(theta: float, h0: float, v: float) -> float:
    var vx: float = v * cos(theta)
    var vy: float = v * sin(theta)
    var disc: float = vy * vy + 2.0 * SHELL_GRAVITY * h0
    if disc < 0.0:
        return 0.0
    var t: float = (vy + sqrt(disc)) / SHELL_GRAVITY
    return vx * t

static func ballistic_solution(from_pos: Vector3, aim_point: Vector3) -> Vector3:
    var dx: float = aim_point.x - from_pos.x
    var dz: float = aim_point.z - from_pos.z
    var d: float = sqrt(dx * dx + dz * dz)
    if d < 0.5 or d > SHELL_MAX_RANGE:
        return Vector3.ZERO
    var h0: float = maxf(from_pos.y, 0.0)
    var lo: float = 0.001
    var hi: float = 0.9
    if range_for_angle(hi, h0, SHELL_SPEED) < d:
        return Vector3.ZERO
    for i in range(28):
        var mid: float = (lo + hi) * 0.5
        if range_for_angle(mid, h0, SHELL_SPEED) < d:
            lo = mid
        else:
            hi = mid
    var theta: float = (lo + hi) * 0.5
    var dir: Vector3 = Vector3(dx, 0.0, dz) / d
    return dir * (SHELL_SPEED * cos(theta)) + Vector3.UP * (SHELL_SPEED * sin(theta))

static func step_shell(pos: Vector3, vel: Vector3, dt: float) -> Dictionary:
    var v: Vector3 = vel - Vector3.UP * (SHELL_GRAVITY * dt)
    var p: Vector3 = pos + v * dt
    return {"pos": p, "vel": v}

static func aim_lead(shooter_pos: Vector3, target_pos: Vector3, target_vel: Vector3, shell_speed: float) -> Vector3:
    var aim: Vector3 = target_pos
    for i in range(3):
        var d: float = Vector2(aim.x - shooter_pos.x, aim.z - shooter_pos.z).length()
        var t: float = d / shell_speed
        aim = target_pos + target_vel * t
    return Vector3(aim.x, 0.0, aim.z)

static func apply_damage(hp: float, dmg: float) -> float:
    return maxf(0.0, hp - dmg)

static func is_sunk(hp: float) -> bool:
    return hp <= 0.0

static func can_fire(shooter_pos: Vector3, shooter_heading: float, target_pos: Vector3, sector: float, max_dist: float) -> bool:
    var dx: float = target_pos.x - shooter_pos.x
    var dz: float = target_pos.z - shooter_pos.z
    var dist: float = sqrt(dx * dx + dz * dz)
    if dist > max_dist:
        return false
    var bearing: float = atan2(dx, dz)
    return absf(wrap_angle(bearing - shooter_heading)) <= sector

static func ai_command(self_pos: Vector3, self_heading: float, self_speed: float, target_pos: Vector3, target_speed: float, stand_off: float) -> Dictionary:
    var dx: float = target_pos.x - self_pos.x
    var dz: float = target_pos.z - self_pos.z
    var dist: float = sqrt(dx * dx + dz * dz)
    var bearing: float = atan2(dx, dz)
    var err: float = wrap_angle(bearing - self_heading)
    var rudder: float = 0.0
    var throttle: float = 1.0
    if dist > stand_off + 60.0:
        rudder = clampf(err * 2.0, -1.0, 1.0)
        throttle = 1.0
    elif dist < stand_off - 60.0:
        rudder = clampf((err + PI) * 0.5, -1.0, 1.0)
        throttle = 0.6
    else:
        rudder = clampf((err + 0.6) * 0.5, -1.0, 1.0)
        throttle = 0.8
    return {"rudder": rudder, "throttle": throttle}
