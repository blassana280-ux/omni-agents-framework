#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OMNI ASSET FACTORY — generateur Blender parametrique : destroyer ws-destroyer-01.

Construit une coque parametrique (bmesh, sections le long de la longueur),
superstructure, tourelles, VLS, mats et cheminee — formes 100% originales,
aucune donnee proprietaire. Dimensions = spec ws-destroyer-01 du depot
(155 m x 20 m) : la geometrie suit la donnee, pas l'inverse.

Statut honnete : IMPLMENTEE, NON EXECUTEE ici (Blender absent de
l'environnement d'execution de l'assistant). Execution locale :

    blender --background --factory-startup \
        --python gen_destroyer_blender.py -- --out ws-destroyer-01.fbx

Sortie : FBX (metres) a importer dans Unity (axe avant = -Z apres conversion
FBX/Unity ; coque construite le long de +Y en coordonnees Blender).
"""
import argparse
import math
import sys

try:
    import bpy
    import bmesh
    from mathutils import Matrix
except ImportError:
    sys.exit("Erreur : bpy indisponible. Executer ce script DANS Blender >= 3.0 "
             "(blender --background --python gen_destroyer_blender.py -- --out out.fbx)")

# Dimensions : spec ws-destroyer-01 (warships/data/ships/ws-destroyer-01.ship.txt)
HULL_LENGTH = 155.0
HULL_BEAM = 20.0
DRAFT = 6.1
FREEBOARD_MID = 8.0

SECTIONS = 40       # stations le long de la coque
RING_POINTS = 7     # points par demi-section (quille -> pont)
BOW_POWER = 1.9     # pincement de la proue
SECTION_POWER = 0.62  # forme en U/V des sections


def half_beam(t):
    """Demi-largeur normalisee (1 = maximum) a la position t in [0=poupe, 1=proue]."""
    if t < 0.35:
        return 0.82 + 0.18 * (t / 0.35)          # tranche poupe -> mi-navire
    if t < 0.75:
        return 1.0                                // plein bordeaux
    return max(0.04, 1.0 - ((t - 0.75) / 0.25) ** BOW_POWER)


def deck_height(t):
    """Tonture : pont legerement plus haut a la proue et la poupe."""
    return FREEBOARD_MID + 2.2 * (t - 0.5) ** 2 * 4.0 + 0.8 * t


def keel_depth(t):
    """Talon : remonte vers la proue (avant du talon)."""
    return -DRAFT + DRAFT * 0.55 * max(0.0, (t - 0.6) / 0.4) ** 2


def section_ring(t):
    """Points fermes d'une section (quille -> etoile -> pont -> port -> quille)."""
    b = half_beam(t) * HULL_BEAM * 0.5
    yd = deck_height(t)
    yk = keel_depth(t)
    ring = []
    for j in range(RING_POINTS + 1):
        u = j / RING_POINTS
        x = b * u ** SECTION_POWER
        y = yk + (yd - yk) * u
        ring.append((x, y))
    ring.append((-b, yd))
    for j in range(RING_POINTS + 1):
        u = 1.0 - j / RING_POINTS
        x = -b * u ** SECTION_POWER
        y = yk + (yd - yk) * u
        ring.append((x, y))
    return ring


def build_hull():
    """Coque par skinning de sections (bmesh), fond a la poupe (tranche)."""
    mesh = bpy.data.meshes.new("ws-destroyer-hull")
    obj = bpy.data.objects.new("ws-destroyer-hull", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    rings = []
    for s in range(SECTIONS + 1):
        t = s / SECTIONS
        z = (t - 0.5) * HULL_LENGTH  # +Y = proue (Blender)
        ring = section_ring(t)
        verts = [bm.verts.new((x, z, y)) for (x, y) in ring]
        rings.append(verts)

    n = len(rings[0])
    for s in range(SECTIONS):
        for i in range(n):
            a, b, c, d = rings[s][i], rings[s][(i + 1) % n], rings[s + 1][(i + 1) % n], rings[s + 1][i]
            bm.faces.new((a, b, c, d))

    # tranche (poupe) : polygone plein
    bm.faces.new(reversed(rings[0]))
    # proue : eventail vers un point
    bow = bm.verts.new((0.0, HULL_LENGTH * 0.5 + 0.35, deck_height(1.0) - 0.9))
    for v in rings[SECTIONS]:
        pass
    bm.verts.ensure_lookup_table()
    ring_last = rings[SECTIONS]
    for i in range(len(ring_last) - 1):
        bm.faces.new((bow, ring_last[i], ring_last[i + 1]))

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    return obj


def add_box(name, size, location, collection_obj=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(scale=True)
    return obj


def add_cylinder(name, radius, depth, location):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=location)
    obj = bpy.context.active_object
    obj.name = name
    return obj


def build_superstructure():
    objs = []
    # bloc passerelle principal
    objs.append(add_box("deckhouse-main", (10.0, 34.0, 8.0), (0.0, 12.0, FREEBOARD_MID + 4.0)))
    # passerelle elevee (vue)
    objs.append(add_box("bridge", (8.0, 10.0, 4.5), (0.0, 22.0, FREEBOARD_MID + 10.2)))
    # hangar helico
    objs.append(add_box("hangar", (11.0, 22.0, 6.5), (0.0, -38.0, FREEBOARD_MID + 3.2)))
    # mat principal (pyramide simplifiee)
    bpy.ops.mesh.primitive_cone_add(radius1=1.6, radius2=0.35, depth=18.0, location=(0.0, 16.0, FREEBOARD_MID + 17.0))
    mast = bpy.context.active_object
    mast.name = "main-mast"
    objs.append(mast)
    # cheminees
    objs.append(add_cylinder("funnel-1", 2.1, 9.0, (0.0, -2.0, FREEBOARD_MID + 8.5)))
    objs.append(add_cylinder("funnel-2", 1.7, 7.0, (0.0, -10.0, FREEBOARD_MID + 7.5)))
    return objs


def build_turrets():
    objs = []
    for name, z in (("turret-fwd", 38.0), ("turret-aft", -52.0)):
        base = add_cylinder(name + "-base", 3.4, 2.2, (0.0, z, FREEBOARD_MID + 2.0))
        objs.append(base)
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, z + 1.6, FREEBOARD_MID + 3.3))
        housing = bpy.context.active_object
        housing.name = name + "-housing"
        housing.scale = (5.2, 7.0, 2.4)
        bpy.ops.object.transform_apply(scale=True)
        objs.append(housing)
        barrel = add_cylinder(name + "-barrel", 0.32, 9.5, (0.0, z + 6.6, FREEBOARD_MID + 3.4))
        barrel.rotation_euler = (math.radians(90) * 0.0, 0.0, 0.0)
        barrel.rotation_euler[1] = 0.0  # le canon pointe vers +Y par construction (axe cylindre = Z)
        barrel.rotation_mode = "XYZ"
        barrel.rotation_euler = (math.radians(90), 0.0, 0.0)
        objs.append(barrel)
    return objs


def build_vls():
    objs = []
    for i in range(8):
        objs.append(add_box("vls-cell-" + str(i + 1), (1.7, 1.7, 1.0),
                             (-3.0 + (i % 4) * 2.0, 30.0 - (i // 4) * 2.4, FREEBOARD_MID + 0.5)))
    return objs


def main():
    parser = argparse.ArgumentParser(description="Generateur destroyer (Omni Asset Factory)")
    parser.add_argument("--out", required=True, help="chemin du FBX de sortie")
    parser.add_argument("--scale", type=float, default=1.0, help="echelle d'export (defaut 1.0 = metres)")
    args, _ = parser.parse_known_args(sys.argv[sys.argv.index("--") + 1:]) if "--" in sys.argv else (None, None)
    if args is None:
        parser.print_help()
        sys.exit("Erreur : utiliser -- pour separer les arguments de Blender (voir docstring).")

    # scene propre
    bpy.ops.wm.read_factory_settings(use_empty=True)

    hull = build_hull()
    objs = [hull] + build_superstructure() + build_turrets() + build_vls()

    mat = bpy.data.materials.new("omni-hull-grey")
    mat.diffuse_color = (0.55, 0.57, 0.60, 1.0)
    for o in objs:
        if o.type == "MESH":
            if o.data.materials:
                o.data.materials[0] = mat
            else:
                o.data.materials.append(mat)

    bpy.ops.export_scene.fbx(filepath=args.out,
                              use_selection=False,
                              object_types={"MESH"},
                              apply_scale_options="FBX_SCALE_UNITS",
                              global_scale=args.scale,
                              add_leaf_bones=False)

    verts = sum(len(o.data.vertices) for o in objs if o.type == "MESH")
    print("gen_destroyer_blender : " + str(len(objs)) + " objets, " + str(verts)
          + " sommets, FBX -> " + args.out)


if __name__ == "__main__":
    main()
