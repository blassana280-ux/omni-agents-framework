#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OMNI ASSET FACTORY — socle commun des generateurs Blender.

Fonctions partagees par tous les gen_*_blender.py :
  - coque parametrique detaillee (sections 12 pts, tonture, talon avant,
    bulwark, smooth shading + subsurf) ;
  - materiaux Principled BSDF avec textures procedurales (peinture coque,
    pont antiderrapant, vitres, caoutchouc, metal, bandes) — ZERO image
    externe, tout genere par nodes ;
  - UV : smart project par objet ;
  - LOD : decimate 50 % / 25 %, nommage <mesh>_LOD1/2 (convention Unity
    LODGroup) ;
  - export FBX en metres + rapport de production (verts/tris par LOD).

Execution (Blender >= 3.0, teste CI GitHub Actions, licence GPL) :
    blender --background --factory-startup --python gen_destroyer_blender.py -- --out out.fbx
"""
import math
import sys

try:
    import bpy
    import bmesh
    from mathutils import Vector, Matrix
except ImportError:
    sys.exit("Erreur : bpy indisponible. Executer DANS Blender >= 3.0.")

SUBSURF_LEVEL = 2
HULL_SECTIONS = 48
HULL_RING = 12  # points par demi-section


# ------------------------------------------------------------------ coque

def half_beam(t):
    """Demi-largeur normalisee ; t in [0 (poupe), 1 (proue)]."""
    if t < 0.30:
        return 0.80 + 0.20 * (t / 0.30)
    if t < 0.72:
        return 1.0
    return max(0.05, 1.0 - ((t - 0.72) / 0.28) ** 1.8)


def section_ring(t, length, beam, draft, freeboard):
    """Points fermes d'une section : quille -> etoile -> pont -> port -> quille."""
    b = half_beam(t) * beam * 0.5
    yd = freeboard * (1.0 + 0.22 * (t - 0.5) ** 2 * 8.0 + 0.06 * t)  # tonture
    yk = -draft + draft * 0.5 * max(0.0, (t - 0.55) / 0.45) ** 2        # talon avant
    ring = []
    for j in range(HULL_RING + 1):
        u = j / HULL_RING
        ring.append((b * u ** 0.62, yk + (yd - yk) * u))
    ring.append((-b, yd))
    for j in range(HULL_RING + 1):
        u = 1.0 - j / HULL_RING
        ring.append((-b * u ** 0.62, yk + (yd - yk) * u))
    return ring


def build_hull(name, length, beam, draft, freeboard, bulwark=0.9):
    """Coque parametrique : retourne l'objet coque (LOD0, smooth, subsurf)."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    rings = []
    for s in range(HULL_SECTIONS + 1):
        t = s / HULL_SECTIONS
        z = (t - 0.5) * length  # +Y = proue
        ring = section_ring(t, length, beam, draft, freeboard)
        rings.append([bm.verts.new((x, z, y)) for (x, y) in ring])

    n = len(rings[0])
    for s in range(HULL_SECTIONS):
        for i in range(n):
            a = rings[s][i]
            b2 = rings[s][(i + 1) % n]
            c = rings[s + 1][(i + 1) % n]
            d = rings[s + 1][i]
            bm.faces.new((a, b2, c, d))
    bm.faces.new(list(reversed(rings[0])))          # tranche poupe
    bow = bm.verts.new((0.0, length * 0.5 + 0.4, freeboard * 1.18 - 1.0))
    last = rings[HULL_SECTIONS]
    for i in range(len(last) - 1):
        bm.faces.new((bow, last[i], last[i + 1]))   # proue

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    # lissage + subsurf : coque reelle, pas un empilement de primitives
    for poly in mesh.polygons:
        poly.use_smooth = True
    mod = obj.modifiers.new("Subsurf", "SUBSURF")
    mod.levels = SUBSURF_LEVEL
    mod.render_levels = SUBSURF_LEVEL
    smart_uv(obj)
    return obj


def add_box(name, size, location, rot=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(scale=True)
    smart_uv(obj)
    return obj


def add_cylinder(name, radius, depth, location, rot=(0.0, 0.0, 0.0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth,
                                        location=location, rotation=rot, vertices=verts)
    obj = bpy.context.active_object
    obj.name = name
    smart_uv(obj)
    return obj


def add_cone(name, r1, r2, depth, location, rot=(0.0, 0.0, 0.0), verts=24):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=depth,
                                     location=location, rotation=rot, vertices=verts)
    obj = bpy.context.active_object
    obj.name = name
    smart_uv(obj)
    return obj


def add_sphere(name, radius, location):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=location, segments=24, ring_count=16)
    obj = bpy.context.active_object
    obj.name = name
    for poly in obj.data.polygons:
        poly.use_smooth = True
    smart_uv(obj)
    return obj


def add_railing(parent_deck_y, x_from, x_to, z_from, z_to, name, height=1.05):
    """Ligne de garde simplifiee : main courante fine sur montants epares."""
    objs = []
    rail = add_box(name, ((x_to - x_from), 0.12, 0.12),
                   ((x_from + x_to) * 0.5, parent_deck_y + height, (z_from + z_to) * 0.5))
    objs.append(rail)
    steps = max(2, int(abs(z_to - z_from) / 4.0) + 1)
    for i in range(steps + 1):
        z = z_from + (z_to - z_from) * i / steps
        post = add_box(name + "-post", (0.09, height, 0.09), (x_from if x_to == x_from else (x_from + (x_to - x_from) * i / steps), parent_deck_y + height * 0.5, z if x_to == x_from else (z_from + z_to) * 0.5))
        objs.append(post)
    return objs


# ------------------------------------------------------------- materiaux

def make_materials():
    """Materiaux proceduraux (nodes) — aucun fichier image externe."""
    def base(name, color, rough=0.55, metallic=0.15):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metallic
        return mat

    mats = {}
    mats["hull"] = base("omni-hull-haze", (0.52, 0.54, 0.56))
    # bande de flottabilite (rouge oxide sombre)
    mats["waterline"] = base("omni-waterline", (0.42, 0.11, 0.09), rough=0.7)
    # pont : gris fonce + bump antiderrapant par bruit
    deck = base("omni-deck", (0.28, 0.29, 0.31), rough=0.9)
    _noise_bump(deck, scale=180.0, strength=0.35)
    mats["deck"] = deck
    mats["super"] = base("omni-superstructure", (0.68, 0.71, 0.74), rough=0.5)
    mats["dark"] = base("omni-dark-rubber", (0.05, 0.05, 0.06), rough=0.95)
    glass = base("omni-glass", (0.10, 0.14, 0.18), rough=0.08, metallic=0.6)
    mats["glass"] = glass
    mats["metal"] = base("omni-metal", (0.55, 0.57, 0.60), rough=0.3, metallic=0.85)
    mats["accent"] = base("omni-accent-orange", (0.75, 0.35, 0.08))
    return mats


def _noise_bump(mat, scale, strength):
    """Bump procedurale (bruit) branchee sur le Principled BSDF."""
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Detail"].default_value = 8.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


def assign(obj, mat):
    if obj.type == "MESH":
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)


# ------------------------------------------------------------------- UV

def smart_uv(obj):
    if obj is None or obj.type != "MESH":
        return
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0),
                             island_margin=0.02, correct_aspect=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)


# ------------------------------------------------------------------ LOD

def make_lods(objects, ratios=(0.5, 0.25)):
    """LOD1/LOD2 par decimate ; nomme <mesh>_LOD1/2 (convention LODGroup)."""
    lods = []
    for obj in objects:
        if obj is None or obj.type != "MESH":
            continue
        for k, ratio in enumerate(ratios, start=1):
            lod = obj.copy()
            lod.data = obj.data.copy()
            lod.name = obj.name + "_LOD" + str(k)
            bpy.context.collection.objects.link(lod)
            mod = lod.modifiers.new("Decimate", "DECIMATE")
            mod.ratio = ratio
            mod.use_collapse_triangulate = True
            lods.append(lod)
    return lods


def export_fbx(objects, filepath, scale=1.0):
    for o in bpy.context.scene.objects:
        o.select_set(o in objects)
    bpy.ops.export_scene.fbx(filepath=filepath,
                             use_selection=True,
                             object_types={"MESH", "EMPTY"},
                             apply_scale_options="FBX_SCALE_UNITS",
                             global_scale=scale,
                             add_leaf_bones=False,
                             use_mesh_modifiers=True)


def report(objects):
    total_v = total_t = 0
    lines = []
    for o in objects:
        if o.type != "MESH":
            continue
        v = len(o.data.vertices)
        t = len(o.data.polygons)
        total_v += v
        total_t += t
        lines.append("  " + o.name + " : " + str(v) + " verts, " + str(t) + " tris")
    print("RAPPORT ASSET (" + str(len(objects)) + " objets) :")
    for l in lines:
        print(l)
    print("TOTAL : " + str(total_v) + " verts / " + str(total_t) + " tris")
    return total_v, total_t


def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def parse_args_after_dashes():
    """Arguments apres le -- de la ligne Blender.

    FIX T-013 (audit du 06/11/2026) : l'ancien parseur etait VIDE, donc
    args.out levait AttributeError et faisait echouer les 7 generateurs
    des le premier appel reel. --out est desormais declare.
    """
    import argparse
    if "--" not in sys.argv:
        sys.exit("Erreur : separer les arguments par -- (blender --python script.py -- --out f.fbx)")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True,
                        help="chemin du FBX a produire (ex: ws-destroyer-01.fbx)")
    return parser.parse_known_args(sys.argv[sys.argv.index("--") + 1:])[0]
