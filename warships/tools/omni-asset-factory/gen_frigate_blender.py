#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OMNI ASSET FACTORY — frégate ws-frigate-01 DETAILLÉE.

Coque paramétrique smooth, superstructure intégrée, passerelle vitrée,
mât avec radar rotatif (pivot radar_1), tourelle unique (turret_fwd),
VLS, 2 CIWS, sonar dôme de proue, hangar + helipont, matériaux
procéduraux, UV, LOD 0/1/2. Dimensions = spec ws-frigate-01 (135 m x 16 m).

Statut : IMPLÉMENTÉE, NON EXÉCUTÉE ici (Blender absent du sandbox).

    blender --background --factory-startup --python gen_frigate_blender.py -- --out ws-frigate-01.fbx
"""
import math
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from omni_blender_common import (build_hull, add_box, add_cylinder, add_cone,
                                 add_sphere, make_materials, assign, make_lods,
                                 export_fbx, report, clean_scene, parse_args_after_dashes)

import bpy

HULL_LENGTH = 135.0
HULL_BEAM = 16.0
DRAFT = 4.6
FREEBOARD = 7.0


def main():
    args = parse_args_after_dashes()
    clean_scene()
    mats = make_materials()

    hull = build_hull("ws-frigate-01", HULL_LENGTH, HULL_BEAM, DRAFT, FREEBOARD)
    assign(hull, mats["hull"])

    wl = add_box("waterline-belt", (HULL_BEAM * 1.02, HULL_LENGTH * 0.86, 0.45), (0.0, 0.0, 0.3))
    assign(wl, mats["waterline"])

    deck = add_box("main-deck", (HULL_BEAM * 0.94, HULL_LENGTH * 0.97, 0.4),
                   (0.0, 0.0, FREEBOARD))
    assign(deck, mats["deck"])

    # dôme sonar de proue (bulbe)
    bowdome = add_sphere("sonar-dome", 1.6, (0.0, HULL_LENGTH * 0.46, -DRAFT * 0.35))
    assign(bowdome, mats["dark"])

    # superstructure bloquée continue + passerelle
    sup = add_box("deckhouse", (9.0, 30.0, 7.0), (0.0, 10.0, FREEBOARD + 3.9))
    assign(sup, mats["super"])
    bridge = add_box("bridge", (7.4, 8.0, 3.6), (0.0, 18.0, FREEBOARD + 9.3))
    assign(bridge, mats["super"])
    glass = add_box("bridge-glass", (7.5, 7.0, 1.5), (0.0, 18.1, FREEBOARD + 9.8))
    assign(glass, mats["glass"])

    # mât pyramidal compact + radar (pivot)
    mast = add_cone("main-mast", 1.4, 0.35, 14.0, (0.0, 12.0, FREEBOARD + 16.0))
    assign(mast, mats["metal"])
    radar_pivot = bpy.data.objects.new("radar_1", None)
    radar_pivot.empty_display_type = "PLAIN_AXES"
    radar_pivot.location = (0.0, 12.0, FREEBOARD + 22.9)
    bpy.context.collection.objects.link(radar_pivot)
    bar = add_box("radar_1-bar", (4.8, 1.0, 0.5), (0.0, 0.0, 0.0))
    bar.parent = radar_pivot
    assign(bar, mats["dark"])

    # tourelle principale (pivot turret_fwd)
    pivot = bpy.data.objects.new("turret_fwd", None)
    pivot.empty_display_type = "PLAIN_AXES"
    pivot.location = (0.0, 32.0, FREEBOARD + 0.5)
    bpy.context.collection.objects.link(pivot)
    base = add_cylinder("turret_fwd-base", 2.9, 1.4, (0.0, 0.0, 0.0))
    base.parent = pivot
    assign(base, mats["super"])
    housing = add_box("turret_fwd-housing", (4.6, 6.2, 2.3), (0.0, 0.0, 1.8))
    housing.parent = pivot
    assign(housing, mats["super"])
    barrel = add_cylinder("turret_fwd-barrel", 0.26, 8.0, (0.0, 4.2, 2.0),
                          rot=(math.radians(90), 0.0, 0.0))
    barrel.parent = pivot
    assign(barrel, mats["metal"])

    # VLS 12 cellules + 2 x 4 SSM en élévation
    for i in range(12):
        gx = -2.7 + (i % 3) * 2.7
        gz = 26.0 - (i // 3) * 2.6
        cell = add_box("vls-cell-" + str(i + 1), (1.8, 1.8, 0.6), (gx, gz, FREEBOARD + 0.65))
        assign(cell, mats["dark"])
    for k in range(4):
        ssm = add_box("ssm-canister-" + str(k + 1), (1.2, 5.6, 1.2),
                      (-4.2 + k * 2.8, 2.0, FREEBOARD + 1.6), rot=(math.radians(-12), 0.0, 0.0))
        assign(ssm, mats["super"])

    # 2 CIWS
    for k, (cx, cz) in enumerate(((0.0, -12.0), (0.0, -48.0)), start=1):
        mount = add_cylinder("ciws_" + str(k) + "-mount", 1.3, 1.6, (cx, cz, FREEBOARD + 0.8))
        assign(mount, mats["super"])
        dome = add_sphere("ciws_" + str(k) + "-dome", 1.25, (cx, cz, FREEBOARD + 2.8))
        assign(dome, mats["metal"])

    # hangar + helipont + treuil
    hangar = add_box("hangar", (9.5, 17.0, 5.6), (0.0, -30.0, FREEBOARD + 3.2))
    assign(hangar, mats["super"])
    heli = add_box("helipad", (HULL_BEAM * 0.62, HULL_LENGTH * 0.15, 0.12),
                   (0.0, -HULL_LENGTH * 0.42, FREEBOARD + 0.5))
    assign(heli, mats["dark"])

    # cheminée unique inclinée
    funnel = add_cylinder("funnel-1", 1.8, 7.5, (0.0, -4.0, FREEBOARD + 7.7),
                          rot=(math.radians(-6), 0.0, 0.0))
    assign(funnel, mats["dark"])

    everything = [o for o in bpy.context.scene.objects]
    all_meshes = [o for o in everything if o.type == "MESH"]
    make_lods(all_meshes)
    report([o for o in bpy.context.scene.objects if o.type == "MESH"])
    export_fbx([o for o in bpy.context.scene.objects], args.out)
    print("gen_frigate_blender : FBX -> " + args.out)


if __name__ == "__main__":
    main()
