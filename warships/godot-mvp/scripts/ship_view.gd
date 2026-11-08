extends Node3D
# Vue 3D procedurale d un destroyer : aucun asset externe, aucune licence.
# Proue le long de -Z (convention Godot). Construite entierement en code,
# appelee par main.gd via build().

var _turrets: Array = []
var _wake: MeshInstance3D = null

func build(hull_color: Color, top_color: Color) -> void:
    _add_box(Vector3(9.0, 5.0, 66.0), Vector3(0.0, 0.5, 0.0), hull_color)
    _add_box(Vector3(8.0, 0.5, 60.0), Vector3(0.0, 3.2, 0.0), top_color)
    _add_box(Vector3(7.0, 3.0, 22.0), Vector3(0.0, 5.0, -2.0), top_color)
    _add_box(Vector3(5.5, 2.5, 9.0), Vector3(0.0, 7.8, 3.0), top_color)
    _add_cyl(1.6, 5.0, Vector3(0.0, 8.0, -8.0), Color(0.55, 0.56, 0.58))
    _add_cyl(0.35, 12.0, Vector3(0.0, 12.0, 4.0), Color(0.9, 0.9, 0.92))
    for zoff in [22.0, 13.0]:
        var tur := Node3D.new()
        tur.position = Vector3(0.0, 4.6, -zoff)
        add_child(tur)
        var box := MeshInstance3D.new()
        var bm := BoxMesh.new()
        bm.size = Vector3(3.4, 2.0, 4.2)
        box.mesh = bm
        box.material_override = _mat(hull_color)
        tur.add_child(box)
        var barrel := MeshInstance3D.new()
        var cyl := CylinderMesh.new()
        cyl.top_radius = 0.25
        cyl.bottom_radius = 0.35
        cyl.height = 6.5
        barrel.mesh = cyl
        barrel.material_override = _mat(Color(0.12, 0.12, 0.13))
        barrel.rotation_degrees = Vector3(90.0, 0.0, 0.0)
        barrel.position = Vector3(0.0, 0.6, -3.2)
        tur.add_child(barrel)
        _turrets.append(tur)
    var wake := MeshInstance3D.new()
    var quad := QuadMesh.new()
    quad.size = Vector2(7.0, 26.0)
    wake.mesh = quad
    var wm := StandardMaterial3D.new()
    wm.albedo_color = Color(1.0, 1.0, 1.0, 0.30)
    wm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    wm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    wake.material_override = wm
    wake.rotation_degrees = Vector3(-90.0, 0.0, 0.0)
    wake.position = Vector3(0.0, 0.15, 40.0)
    add_child(wake)
    _wake = wake

func aim_turrets(aim_point: Vector3) -> void:
    for tur in _turrets:
        var local: Vector3 = (tur as Node3D).to_local(aim_point)
        if Vector2(local.x, local.z).length() < 2.0:
            continue
        var yaw: float = atan2(-local.x, -local.z)
        yaw = clampf(yaw, -1.15, 1.15)
        (tur as Node3D).rotation = Vector3(0.0, yaw, 0.0)

func set_wake_scale(spd: float) -> void:
    if _wake != null:
        var k: float = clampf(spd / 13.0, 0.05, 1.0)
        _wake.scale = Vector3(0.6 + k * 0.7, 1.0, 0.3 + k * 0.9)

func _add_box(size: Vector3, pos: Vector3, color: Color) -> void:
    var m := MeshInstance3D.new()
    var b := BoxMesh.new()
    b.size = size
    m.mesh = b
    m.material_override = _mat(color)
    m.position = pos
    add_child(m)

func _add_cyl(radius: float, height: float, pos: Vector3, color: Color) -> void:
    var m := MeshInstance3D.new()
    var c := CylinderMesh.new()
    c.top_radius = radius
    c.bottom_radius = radius
    c.height = height
    m.mesh = c
    m.material_override = _mat(color)
    m.position = pos
    add_child(m)

func _mat(color: Color) -> StandardMaterial3D:
    var s := StandardMaterial3D.new()
    s.albedo_color = color
    s.roughness = 0.8
    return s
