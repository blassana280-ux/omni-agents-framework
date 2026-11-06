#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OMNI ASSET FACTORY — porte-avions ws-carrier-01 DÉTAILLÉ.

Coque massive (265 m), pont continu, pont oblique d'appontage, îlot
superstructure avec passerelle vitrée et mâts radars (pivots radar_1/2),
4 ascenseurs d'appontage, 4 CIWS, catapultes marquées, spots d'appontage,
matériaux procéduraux, UV, LOD 0/1/2. Dimensions = spec ws-carrier-01.

Statut : IMPLÉMENTÉE, NON EXÉCUTÉE ici (Blender absent du sandbox).

    blender --background --factory-startup --python gen_carrier_blender.py -- --out ws-carrier-01.fbx
"""
import math
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from omni_blender_common import (build_hull, add_box, add_cylinder, add_cone,
                                 add_sphere, make_materials, assign, make_lods,
                                 export_fbx, report, clean_scene, parse_args_after_dashes)

import bpy

HULL_LENGTH = 265.0
HULL_BEAM = 32.0
DRAFT = 10.5
FREEBOARD = 18.0  # pont d'envol élevé


def main():
    args = parse_args_after_dashes()
    clean_scene()
    mats = make_materials()

    hull = build_hull("ws-carrier-01", HULL_LENGTH, HULL_BEAM * 0.62, DRAFT, FREEBOARD * 0.55)
    assign(hull, mats["hull"])

    # caisson latéral (sponson) élargissant le flanc au niveau du pont
    for sx in (-1, 1):
        sponson = add_box("sponson-" + ("p" if sx < 0 else "s"),
                          (HULL_BEAM * 0.20, HULL_LENGTH * 0.72, 3.0),
                          (sx * HULL_BEAM * 0.40, 0.0, FREEBOARD - 2.2))
        assign(sponson, mats["hull"])

    # pont d'envol : bande longitudinale + pont oblique (angled deck)
    deck = add_box("flight-deck", (HULL_BEAM, HULL_LENGTH * 0.985, 0.5),
                   (0.0, 0.0, FREEBOARD))
    assign(deck, mats["deck"])
    angled = add_box("angled-deck", (HULL_BEAM * 0.92, 108.0, 0.55),
                     (2.5, -38.0, FREEBOARD + 0.28), rot=(0.0, 0.0, math.radians(-9)))
    assign(angled, mats["deck"])

    # bandes de sécurité + catapultes (marquages peints en matériau accent)
    for k in range(2):
        cat = add_box("catapult-" + str(k + 1), (0.7, 92.0, 0.06),
                      (-6.5 + k * 8.0, 62.0, FREEBOARD + 0.58))
        assign(cat, mats["accent"])
    landing = add_box("landing-line", (0.7, 105.0, 0.06),
                      (3.2, -40.0, FREEBOARD + 0.62), rot=(0.0, 0.0, math.radians(-9)))
    assign(landing, mats["accent"])

    # 4 ascenseurs d'appontage (bords visibles)
    for k, (ex, ez) in enumerate(((-13.5, 42.0), (13.5, 42.0), (-13.5, -22.0), (13.5, -22.0))):
        lift = add_box("deck-lift-" + str(k + 1), (2.2, 20.0, 0.5), (ex, ez, FREEBOARD + 0.30))
        assign(lift, mats["metal"])

    # îlot superstructure (tribord) + passerelle vitrée
    island = add_box("island", (9.0, 46.0, 16.0), (HULL_BEAM * 0.31, 18.0, FREEBOARD + 8.3))
    assign(island, mats["super"])
    bridge = add_box("island-bridge", (8.2, 12.0, 4.2), (HULL_BEAM * 0.31, 26.0, FREEBOARD + 17.2))
    assign(bridge, mats["super"])
    glass = add_box("island-glass", (8.3, 11.0, 1.6), (HULL_BEAM * 0.31, 26.2, FREEBOARD + 18.0))
    assign(glass, mats["glass"])

    # mâts radars : 2 pivots rotatifs
    for k, mz in enumerate((30.0, 12.0), start=1):
        mast = add_cone("island-mast-" + str(k), 1.5, 0.35, 15.0,
                        (HULL_BEAM * 0.31, mz, FREEBOARD + 27.0))
        assign(mast, mats["metal"])
        pivot = bpy.data.objects.new("radar_" + str(k), None)
        pivot.empty_display_type = "PLAIN_AXES"
        pivot.location = (HULL_BEAM * 0.31, mz, FREEBOARD + 34.6)
        bpy.context.collection.objects.link(pivot)
        bar = add_box("radar_" + str(k) + "-bar", (6.0, 1.0, 0.5), (0.0, 0.0, 0.0))
        bar.parent = pivot
        assign(bar, mats["dark"])

    # 4 CIWS répartis + 2 SAM
    for k, (cx, cz) in enumerate(((-14.0, 88.0), (14.0, 74.0), (-14.0, -95.0), (14.0, -108.0)), start=1):
        mount = add_cylinder("ciws_" + str(k) + "-mount", 1.6, 2.0, (cx, cz, FREEBOARD - 1.0))
        assign(mount, mats["super"])
        dome = add_sphere("ciws_" + str(k) + "-dome", 1.5, (cx, cz, FREEBOARD + 0.6))
        assign(dome, mats["metal"])
    for k, (sx, sz) in enumerate(((10.0, -60.0), (10.0, 55.0)), start=1):
        sam = add_box("sam-launcher-" + str(k), (3.2, 5.0, 2.0), (sx, sz, FREEBOARD + 0.4))
        assign(sam, mats["dark"])

    everything = [o for o in bpy.context.scene.objects]
    all_meshes = [o for o in everything if o.type == "MESH"]
    make_lods(all_meshes)
    report([o for o in bpy.context.scene.objects if o.type == "MESH"])
    export_fbx([o for o in bpy.context.scene.objects], args.out)
    print("gen_carrier_blender : FBX -> " + args.out)


if __name__ == "__main__":
    main()
