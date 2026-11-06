#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OMNI ASSET FACTORY — sous-marin ws-submarine-01 DÉTAILLÉ.

Capsule de coque hydrodynamique (révolution), kiosque (sail) avec
hublots et périscope, ailerons de plongée (proue/kiosque/poupe),
gouvernail en croix, hélice (nominée propeller, pivot animable),
quillards d'échouage, matériaux procéduraux, UV, LOD 0/1/2.
Dimensions = spec ws-submarine-01 (78 m x 10 m).

Statut : IMPLÉMENTÉE, NON EXÉCUTÉE ici (Blender absent du sandbox).

    blender --background --factory-startup --python gen_submarine_blender.py -- --out ws-submarine-01.fbx
"""
import math
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from omni_blender_common import (add_box, add_cylinder, add_cone, add_sphere,
                                 make_materials, assign, make_lods,
                                 export_fbx, report, clean_scene, parse_args_after_dashes)

import bpy

HULL_LENGTH = 78.0
HULL_RADIUS = 5.0


def revolve_profile(name, length, radius, mat):
    """Coque de révolution : nez arrondi, cylindre, cône de poupe."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    verts, faces = [], []
    SEG = 24  # sections radiales
    RINGS = 18  # profils le long de l'axe
    for i in range(RINGS + 1):
        t = i / RINGS  # 0 = proue, 1 = poupe
        # rayon(t) : ogive proue, corps, cône + hérissement gouvernail
        if t < 0.22:
            r = radius * math.sin((t / 0.22) * math.pi / 2) ** 0.7
        elif t < 0.78:
            r = radius
        else:
            u = (t - 0.78) / 0.22
            r = radius * (1.0 - 0.72 * u)
        z = -length / 2.0 + t * length
        ring = []
        for j in range(SEG):
            a = (j / SEG) * math.pi * 2.0
            x = math.sin(a) * r
            y = math.cos(a) * r
            ring.append(len(verts))
            verts.append((x, z, y))
        if i > 0:
            for j in range(SEG):
                a, b = ring[j], ring[(j + 1) % SEG]
                faces.append((a, b, a - SEG, b - SEG))
    # fermer proue/poupe en éventail vers les centres
    for pole, center in ((0, len(verts)), (1, len(verts) + 1)):
        if pole == 0:
            verts.append((0.0, -length / 2.0, 0.0))
        else:
            verts.append((0.0, length / 2.0, 0.0))
        for j in range(SEG):
            base = pole * RINGS * SEG
            j0 = base + j
            j1 = base + (j + 1) % SEG
            if pole == 0:
                faces.append((center, j1, j0))
            else:
                faces.append((center, j0, j1))
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    assign(obj, mat)
    return obj


def main():
    args = parse_args_after_dashes()
    clean_scene()
    mats = make_materials()

    # coque de révolution + bandes anti-roulis
    hull = revolve_profile("ws-submarine-01", HULL_LENGTH, HULL_RADIUS, mats["hull"])
    for sx in (-1, 1):
        strake = add_box("strake-" + ("p" if sx < 0 else "s"),
                         (0.35, HULL_LENGTH * 0.5, 1.0),
                         (sx * (HULL_RADIUS * 0.86), 0.0, -HULL_RADIUS * 0.45))
        assign(strake, mats["dark"])

    # kiosque (sail) + périscope + hublots
    sail = add_box("sail", (2.6, 14.0, 7.5), (0.0, 6.0, HULL_RADIUS + 2.6))
    assign(sail, mats["super"])
    cap = add_cylinder("sail-cap", 1.6, 3.4, (0.0, 6.0, HULL_RADIUS + 6.4))
    assign(cap, mats["dark"])
    scope = add_cylinder("periscope", 0.22, 4.2, (0.0, 9.0, HULL_RADIUS + 7.0))
    assign(scope, mats["metal"])
    for k in range(3):
        p = add_box("sail-window-" + str(k + 1), (0.12, 1.3, 0.9),
                    (-1.32, 7.0 + k * 2.2, HULL_RADIUS + 4.4))
        assign(p, mats["glass"])
        ps = add_box("sail-window-s-" + str(k + 1), (0.12, 1.3, 0.9),
                     (1.32, 7.0 + k * 2.2, HULL_RADIUS + 4.4))
        assign(ps, mats["glass"])

    # ailerons de plongée proue + kiosque
    for name, (w, ch, x, y, z) in {
        "dive-plane-bow-p": (7.0, 2.0, -HULL_RADIUS * 0.62, HULL_LENGTH * 0.32, -1.0),
        "dive-plane-bow-s": (7.0, 2.0, HULL_RADIUS * 0.62, HULL_LENGTH * 0.32, -1.0),
        "dive-plane-sail-p": (5.0, 2.2, -1.6, 11.0, HULL_RADIUS + 2.2),
        "dive-plane-sail-s": (5.0, 2.2, 1.6, 11.0, HULL_RADIUS + 2.2),
    }.items():
        plane = add_box(name, (w, ch, 0.5), (x, y, z))
        assign(plane, mats["super"])

    # gouvernail en croix + hélice (pivot propeller animable)
    for name, (x, z) in (("rudder-top", (0.0, HULL_RADIUS * 0.55)),
                         ("rudder-bottom", (0.0, -HULL_RADIUS * 0.55)),
                         ("rudder-left", (-HULL_RADIUS * 0.55, 0.0)),
                         ("rudder-right", (HULL_RADIUS * 0.55, 0.0))):
        rud = add_box(name, (0.45, 6.5, 4.0), (x, HULL_LENGTH * 0.5, z))
        assign(rud, mats["super"])
    prop_pivot = bpy.data.objects.new("propeller", None)
    prop_pivot.empty_display_type = "PLAIN_AXES"
    prop_pivot.location = (0.0, HULL_LENGTH * 0.5 + 2.8, 0.0)
    bpy.context.collection.objects.link(prop_pivot)
    hub = add_sphere("propeller-hub", 0.9, (0.0, 0.0, 0.0))
    hub.parent = prop_pivot
    assign(hub, mats["metal"])
    for k in range(7):  # 7 pales
        angle = (k / 7.0) * math.pi * 2.0
        blade = add_box("propeller-blade-" + str(k + 1), (0.25, 1.7, 3.4),
                        (math.sin(angle) * 1.8, 0.25, math.cos(angle) * 1.8),
                        rot=(0.0, 0.5, angle))
        blade.parent = prop_pivot
        assign(blade, mats["metal"])

    # tubes lance-torpilles proue (grilles visibles)
    for k in range(4):
        ring = add_cylinder("bow-tube-" + str(k + 1), 0.55, 0.4,
                            (-1.8 + (k % 2) * 3.6, -HULL_LENGTH * 0.48, -1.5 + (k // 2) * 3.0),
                            rot=(math.radians(90), 0.0, 0.0))
        assign(ring, mats["dark"])

    everything = [o for o in bpy.context.scene.objects]
    all_meshes = [o for o in everything if o.type == "MESH"]
    make_lods(all_meshes)
    report([o for o in bpy.context.scene.objects if o.type == "MESH"])
    export_fbx([o for o in bpy.context.scene.objects], args.out)
    print("gen_submarine_blender : FBX -> " + args.out)


if __name__ == "__main__":
    main()
