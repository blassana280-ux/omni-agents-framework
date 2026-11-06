#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OMNI ASSET FACTORY — équipements navals MODULAIRES (pivots animables).

Chaque équipement est autonome (base + parties mobiles parentées à un
EMPTY pivot) pour instanciation Unity : rotation tourelle (pivot
turret_yaw), élévation canon (pivot gun_pitch), radar rotatif (pivot
radar_spin), VLS (grille de cellules), CIWS (pivot ciws_yaw + dôme).

Statut : IMPLÉMENTÉ, NON EXÉCUTÉÉE ici (Blender absent du sandbox).

    blender --background --factory-startup --python gen_equipment_blender.py -- --out ws-equipment.fbx
"""
import math
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from omni_blender_common import (add_box, add_cylinder, add_cone, add_sphere,
                                 make_materials, assign, make_lods,
                                 export_fbx, report, clean_scene, parse_args_after_dashes)

import bpy


def new_pivot(name, location):
    pivot = bpy.data.objects.new(name, None)
    pivot.empty_display_type = "PLAIN_AXES"
    pivot.location = location
    bpy.context.collection.objects.link(pivot)
    return pivot


def build_turret(mats, xoff):
    """Tourelle double canon : pivot turret_yaw + pivot gun_pitch."""
    yaw = new_pivot("turret_yaw", (xoff, 0.0, 0.0))
    base = add_cylinder("turret-base", 2.9, 1.4, (0.0, 0.0, 0.0))
    base.parent = yaw
    assign(base, mats["super"])
    housing = add_box("turret-housing", (5.0, 6.6, 2.4), (0.0, 0.0, 1.9))
    housing.parent = yaw
    assign(housing, mats["super"])
    pitch = new_pivot("gun_pitch", (xoff, 2.6, 3.2))
    pitch.parent = yaw
    for k, dy in enumerate((-0.9, 0.9), start=1):
        barrel = add_cylinder("turret-barrel-" + str(k), 0.28, 9.0, (dy, 4.4, 0.0),
                              rot=(math.radians(90), 0.0, 0.0))
        barrel.parent = pitch
        assign(barrel, mats["metal"])
        mantlet = add_box("turret-mantlet-" + str(k), (1.4, 1.6, 1.2), (dy, 1.4, 0.0))
        mantlet.parent = pitch
        assign(mantlet, mats["dark"])


def build_radar(mats, xoff):
    """Radar rotatif : pivot radar_spin + barre + radôme agile."""
    spin = new_pivot("radar_spin", (xoff, 0.0, 6.0))
    mast = add_cylinder("radar-mast", 0.6, 5.6, (0.0, 0.0, -2.8))
    mast.parent = spin
    assign(mast, mats["metal"])
    bar = add_box("radar-bar", (6.4, 1.0, 0.5), (0.0, 0.0, 0.6))
    bar.parent = spin
    assign(bar, mats["dark"])
    dome = add_sphere("radar-dome", 0.9, (0.0, 0.0, 1.9))
    dome.scale = (1.0, 1.0, 0.6)
    dome.parent = spin
    assign(dome, mats["metal"])


def build_vls(mats, xoff):
    """VLS : grille de cellules + capots."""
    grid = new_pivot("vls_grid", (xoff, 0.0, 0.0))
    frame = add_box("vls-frame", (8.4, 8.4, 0.9), (0.0, 0.0, 0.0))
    frame.parent = grid
    assign(frame, mats["super"])
    for i in range(16):
        gx = -3.15 + (i % 4) * 2.1
        gz = -3.15 + (i // 4) * 2.1
        cell = add_box("vls-cell-" + str(i + 1), (1.75, 1.75, 0.5), (gx, gz, 0.6))
        cell.parent = grid
        assign(cell, mats["dark"])


def build_ciws(mats, xoff):
    """CIWS : pivot ciws_yaw + bloc canon + dôme radar."""
    yaw = new_pivot("ciws_yaw", (xoff, 0.0, 0.0))
    mount = add_cylinder("ciws-mount", 1.4, 1.7, (0.0, 0.0, 0.0))
    mount.parent = yaw
    assign(mount, mats["super"])
    dome = add_sphere("ciws-rdome", 1.15, (0.0, 0.4, 1.7))
    dome.scale = (1.0, 1.3, 1.0)
    dome.parent = yaw
    assign(dome, mats["metal"])
    gun = add_box("ciws-gun", (0.8, 2.8, 0.7), (0.0, -1.9, 1.5))
    gun.parent = yaw
    assign(gun, mats["dark"])
    barrel = add_cylinder("ciws-barrel", 0.14, 2.0, (0.0, -3.2, 1.5),
                          rot=(math.radians(90), 0.0, 0.0))
    barrel.parent = yaw
    assign(barrel, mats["metal"])


def build_launcher(mats, xoff):
    """Lanceur SSM incliné 4 canisters."""
    base = new_pivot("ssm_launcher", (xoff, 0.0, 0.0))
    cradle = add_box("ssm-cradle", (4.2, 6.6, 1.0), (0.0, 0.0, 0.5),
                     rot=(math.radians(-15), 0.0, 0.0))
    cradle.parent = base
    assign(cradle, mats["super"])
    for k in range(4):
        can = add_box("ssm-canister-" + str(k + 1), (1.1, 5.6, 1.1),
                      (-1.65 + k * 1.1, 0.3, 1.8), rot=(math.radians(-15), 0.0, 0.0))
        can.parent = base
        assign(can, mats["dark"])


def main():
    args = parse_args_after_dashes()
    clean_scene()
    mats = make_materials()
    # espacement : chaque module tous les 20 m sur l'axe X pour lecture claire
    build_turret(mats, 0.0)
    build_radar(mats, -20.0)
    build_vls(mats, 20.0)
    build_ciws(mats, -40.0)
    build_launcher(mats, 40.0)
    everything = [o for o in bpy.context.scene.objects]
    all_meshes = [o for o in everything if o.type == "MESH"]
    make_lods(all_meshes)
    report([o for o in bpy.context.scene.objects if o.type == "MESH"])
    export_fbx([o for o in bpy.context.scene.objects], args.out)
    print("gen_equipment_blender : FBX -> " + args.out)


if __name__ == "__main__":
    main()
