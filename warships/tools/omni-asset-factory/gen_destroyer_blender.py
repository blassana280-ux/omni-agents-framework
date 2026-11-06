#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OMNI ASSET FACTORY — destroyer ws-destroyer-01 DETAILLE.

Coque parametrique smooth (subsurf), superstructure, passerelle vitree,
mat avec radar rotatif (pivot nomme radar_1), 2 tourelles nommees
turret_fwd / turret_aft (pivots pour animation Unity), VLS, 2 CIWS,
cheminees, helipont, lignes de garde, materiaux proceduraux, UV, LOD 0/1/2.

Dimensions = spec ws-destroyer-01 (155 m x 20 m). Formes 100% originales.
Statut : IMPLEMENTE, NON EXECUTE ici (Blender absent du sandbox).

    blender --background --factory-startup --python gen_destroyer_blender.py -- --out ws-destroyer-01.fbx
"""
import math
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from omni_blender_common import (build_hull, add_box, add_cylinder, add_cone,
                                 add_sphere, make_materials, assign, make_lods,
                                 export_fbx, report, clean_scene, parse_args_after_dashes)

import bpy

HULL_LENGTH = 155.0
HULL_BEAM = 20.0
DRAFT = 6.1
FREEBOARD = 8.0


def main():
    args = parse_args_after_dashes()
    clean_scene()
    mats = make_materials()

    hull = build_hull("ws-destroyer-01", HULL_LENGTH, HULL_BEAM, DRAFT, FREEBOARD)
    assign(hull, mats["hull"])

    # bande de flottabilite : ceinture fine au niveau de l'eau
    wl = add_box("waterline-belt", (HULL_BEAM * 1.02, HULL_LENGTH * 0.86, 0.55),
                 (0.0, 0.0, 0.4))
    assign(wl, mats["waterline"])

    # pont principal + helipont
    deck = add_box("main-deck", (HULL_BEAM * 0.94, HULL_LENGTH * 0.97, 0.45),
                   (0.0, 0.0, FREEBOARD))
    assign(deck, mats["deck"])
    heli = add_box("helipad", (HULL_BEAM * 0.62, HULL_LENGTH * 0.16, 0.12),
                   (0.0, -HULL_LENGTH * 0.40, FREEBOARD + 0.55))
    assign(heli, mats["dark"])

    # superstructure : bloc principal + passerelle a vitres + ailes
    sup = add_box("deckhouse", (10.5, 34.0, 8.0), (0.0, 12.0, FREEBOARD + 4.3))
    assign(sup, mats["super"])
    bridge = add_box("bridge", (8.6, 10.5, 4.4), (0.0, 22.5, FREEBOARD + 10.6))
    assign(bridge, mats["super"])
    glass = add_box("bridge-glass", (8.7, 9.2, 1.7), (0.0, 22.6, FREEBOARD + 11.2))
    assign(glass, mats["glass"])
    for sx in (-1, 1):  # ailes de passerelle
        wing = add_box("bridge-wing-" + ("p" if sx < 0 else "s"),
                       (3.2, 2.6, 0.35), (sx * 6.8, 22.5, FREEBOARD + 10.6))
        assign(wing, mats["super"])

    # mat principal pyramidal + barre radar rotative (pivot anime Unity)
    mast = add_cone("main-mast", 1.7, 0.4, 17.0, (0.0, 15.0, FREEBOARD + 19.0))
    assign(mast, mats["metal"])
    radar_pivot = bpy.data.objects.new("radar_1", None)  # EMPTY = pivot
    radar_pivot.empty_display_type = "PLAIN_AXES"
    radar_pivot.location = (0.0, 15.0, FREEBOARD + 27.6)
    bpy.context.collection.objects.link(radar_pivot)
    bar = add_box("radar_1-bar", (5.6, 1.1, 0.55), (0.0, 0.0, 0.0))
    bar.parent = radar_pivot
    assign(bar, mats["dark"])
    yard = add_box("mast-yard", (7.5, 0.5, 0.5), (0.0, 15.0, FREEBOARD + 22.5))
    assign(yard, mats["metal"])

    # tourelles principales : pivots turret_fwd / turret_aft (animation Unity)
    for name, zoff in (("turret_fwd", 38.0), ("turret_aft", -52.0)):
        pivot = bpy.data.objects.new(name, None)
        pivot.empty_display_type = "PLAIN_AXES"
        pivot.location = (0.0, zoff, FREEBOARD + 0.55)
        bpy.context.collection.objects.link(pivot)
        base = add_cylinder(name + "-base", 3.5, 1.6, (0.0, 0.0, 0.0))
        base.parent = pivot
        assign(base, mats["super"])
        housing = add_box(name + "-housing", (5.4, 7.2, 2.6), (0.0, 0.0, 2.0))
        housing.parent = pivot
        assign(housing, mats["super"])
        for dy in (-0.9, 0.9):  # double canon 127 mm
            barrel = add_cylinder(name + "-barrel-" + ("l" if dy < 0 else "r"),
                                  0.30, 9.2, (dy, 4.8, 2.2), rot=(math.radians(90), 0.0, 0.0))
            barrel.parent = pivot
            assign(barrel, mats["metal"])
        shroud = add_box(name + "-shroud", (3.4, 4.6, 1.4), (0.0, 4.2, 2.9))
        shroud.parent = pivot
        assign(shroud, mats["dark"])

    # VLS (2 x 8 cellules) + lanceurs SSM en elevation
    for i in range(16):
        gx = -3.6 + (i % 4) * 2.4
        gz = 28.0 - (i // 4) * 2.8
        cell = add_box("vls-cell-" + str(i + 1), (1.9, 1.9, 0.7), (gx, gz, FREEBOARD + 0.75))
        assign(cell, mats["dark"])
    for k in range(4):
        ssm = add_box("ssm-canister-" + str(k + 1), (1.4, 6.2, 1.4),
                      (-4.5 + k * 3.0, -6.0, FREEBOARD + 1.9), rot=(math.radians(-14), 0.0, 0.0))
        assign(ssm, mats["super"])

    # 2 CIWS (dome + bloc) nommes ciws_1 / ciws_2
    for k, (cx, cz) in enumerate(((0.0, -18.0), (0.0, -46.0)), start=1):
        mount = add_cylinder("ciws_" + str(k) + "-mount", 1.5, 1.8, (cx, cz, FREEBOARD + 0.9))
        assign(mount, mats["super"])
        dome = add_sphere("ciws_" + str(k) + "-dome", 1.45, (cx, cz, FREEBOARD + 3.1))
        assign(dome, mats["metal"])
        blk = add_box("ciws_" + str(k) + "-gun", (1.1, 2.6, 0.9), (cx, cz - 1.9, FREEBOARD + 2.6))
        assign(blk, mats["dark"])

    # cheminees + entree d'air
    for k, (fz, fr) in enumerate(((-2.0, 2.1), (-10.5, 1.75)), start=1):
        funnel = add_cylinder("funnel-" + str(k), fr, 8.5, (0.0, fz, FREEBOARD + 8.9))
        assign(funnel, mats["dark"])
        cap = add_cylinder("funnel-" + str(k) + "-cap", fr * 1.12, 0.8, (0.0, fz, FREEBOARD + 13.2))
        assign(cap, mats["metal"])
    intake = add_box("engine-intake", (2.8, 5.0, 2.2), (0.0, -6.5, FREEBOARD + 5.4))
    assign(intake, mats["dark"])

    # hangar helico
    hangar = add_box("hangar", (11.0, 20.0, 6.4), (0.0, -36.0, FREEBOARD + 3.6))
    assign(hangar, mats["super"])

    everything = [o for o in bpy.context.scene.objects]
    all_meshes = [o for o in everything if o.type == "MESH"]
    make_lods(all_meshes)
    report([o for o in bpy.context.scene.objects if o.type == "MESH"])
    export_fbx([o for o in bpy.context.scene.objects], args.out)
    print("gen_destroyer_blender : FBX -> " + args.out)


if __name__ == "__main__":
    main()
