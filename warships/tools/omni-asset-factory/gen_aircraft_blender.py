#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OMNI ASSET FACTORY — aéronefs embarqués (jet + hélicoptère).

1) ws-jet-01 : chasseur embarqué — fuselage profilé, ailes delta
   repliées, dérives inclinées, entrées d'air latérales, verrière
   verrière teintée, roulette de queue.
2) ws-helicopter-01 : hélicoptère naval — cabine, rotor 5 pales
   (pivot rotor_main animable), rotor de queue (pivot rotor_tail),
   trains, sonar treuillé (eslian nommé sonar_winch).

Statut : IMPLÉMENTÉE, NON EXÉCUTÉÉE ici (Blender absent du sandbox).

    blender --background --factory-startup --python gen_aircraft_blender.py -- --out ws-aircraft.fbx
"""
import math
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from omni_blender_common import (add_box, add_cylinder, add_cone, add_sphere,
                                 make_materials, assign, make_lods,
                                 export_fbx, report, clean_scene, parse_args_after_dashes)

import bpy

JET_LEN = 15.0
JET_SPAN = 10.0  (ailes repliées pour le park


def build_jet(mats):
    """Chasseur embarqué (ailes repliées au parking)."""
    # fuselage : cône proue + section + queue effilée
    nose = add_cone("jet-nose", 0.85, 0.1, 3.2, (0.0, JET_LEN * 0.36, 0.0),
                    rot=(math.radians(-90), 0.0, 0.0))
    assign(nose, mats["hull"])
    mid = add_cylinder("jet-fuselage", 0.85, 8.6, (0.0, JET_LEN * 0.08, 0.0),
                       rot=(math.radians(90), 0.0, 0.0))
    assign(mid, mats["hull"])
    aft = add_cone("jet-aft", 0.85, 4.8, (0.0, -JET_LEN * 0.30, 0.0),
                   rot=(math.radians(90), 0.0, 0.0))
    assign(aft, mats["hull"])
    # verrière
    canopy = add_sphere("jet-canopy", 0.78, (0.0, JET_LEN * 0.22, 0.55))
    canopy.scale = (0.75, 2.0, 0.7)
    assign(canopy, mats["glass"])
    # ailes delta repliées vers le haut (naval parking)
    for sx in (-1, 1):
        wing = add_box("jet-wing-" + ("p" if sx < 0 else "s"),
                       (4.2, 2.4, 0.22), (sx * 2.6, JET_LEN * 0.02, 0.0))
        assign(wing, mats["hull"])
        tip = add_box("jet-wingfold-" + ("p" if sx < 0 else "s"),
                      (1.6, 1.4, 0.2), (sx * 5.1, JET_LEN * 0.02, 0.9),
                      rot=(0.0, 0.0, sx * math.radians(35)))
        assign(tip, mats["hull"])
    # dérives inclinées + stabilisateurs
    for sx in (-1, 1):
        fin = add_box("jet-fin-" + ("p" if sx < 0 else "s"),
                      (0.22, 2.2, 2.6), (sx * 0.9, -JET_LEN * 0.32, 1.2),
                      rot=(0.0, 0.0, sx * math.radians(-18)))
        assign(fin, mats["hull"])
        stab = add_box("jet-stab-" + ("p" if sx < 0 else "s"),
                       (2.0, 1.2, 0.2), (sx * 1.4, -JET_LEN * 0.36, 0.0))
        assign(stab, mats["hull"])
    # entrées d'air + tuyère
    for sx in (-1, 1):
        intake = add_box("jet-intake-" + ("p" if sx < 0 else "s"),
                        (0.7, 2.0, 1.1), (sx * 1.1, JET_LEN * 0.12, -0.2))
        assign(intake, mats["dark"])
    nozzle = add_cylinder("jet-nozzle", 0.62, 1.2, (0.0, -JET_LEN * 0.52, 0.0),
                          rot=(math.radians(90), 0.0, 0.0))
    assign(nozzle, mats["metal"])
    # train avant tricycle
    gears = [("jet-gear-nose", (0.0, JET_LEN * 0.24, -1.3)),
             ("jet-gear-main-p", (-1.4, JET_LEN * 0.02, -1.3)),
             ("jet-gear-main-s", (1.4, JET_LEN * 0.02, -1.3))]
    for name, (gx, gy, gz) in gears:
        strut = add_cylinder(name + "-strut", 0.09, 1.3, (gx, gy, gz - 0.65),
                             rot=(0.0, 0.0, 0.0))
        assign(strut, mats["metal"])
        wheel = add_cylinder(name + "-wheel", 0.3, 0.22, (gx, gy, gz - 1.25),
                             rot=(0.0, 0.0, math.radians(90)))
        assign(wheel, mats["dark"])


def build_helicopter(mats):
    """Hélicoptère naval ASW (pivot rotor_main / rotor_tail animables)."""
    body = add_sphere("heli-body", 1.25, (0.0, 0.0, 0.0))
    body.scale = (1.0, 2.6, 1.0)
    assign(body, mats["hull"])
    nose = add_sphere("heli-nose", 0.9, (0.0, 2.8, -0.1))
    nose.scale = (0.9, 1.1, 0.85)
    assign(nose, mats["glass"])
    tailboom = add_cylinder("heli-tailboom", 0.32, 5.6, (0.0, -4.2, 0.25),
                            rot=(math.radians(90), 0.0, 0.0))
    assign(tailboom, mats["hull"])
    # rotor principal : pivot animable
    rotor_pivot = bpy.data.objects.new("rotor_main", None)
    rotor_pivot.empty_display_type = "PLAIN_AXES"
    rotor_pivot.location = (0.0, 0.4, 1.55)
    bpy.context.collection.objects.link(rotor_pivot)
    hub = add_cylinder("rotor_main-hub", 0.28, 0.4, (0.0, 0.0, 0.0))
    hub.parent = rotor_pivot
    assign(hub, mats["metal"])
    for k in range(5):
        a = (k / 5.0) * math.pi * 2.0
        blade = add_box("rotor_main-blade-" + str(k + 1), (0.32, 7.4, 0.1),
                        (math.sin(a) * 3.8, math.cos(a) * 3.8, 0.0),
                        rot=(0.0, -a, 0.0))
        blade.parent = rotor_pivot
        assign(blade, mats["dark"])
    # rotor de queue : pivot animable
    tailrotor_pivot = bpy.data.objects.new("rotor_tail", None)
    tailrotor_pivot.empty_display_type = "PLAIN_AXES"
    tailrotor_pivot.location = (0.35, -6.6, 0.75)
    bpy.context.collection.objects.link(tailrotor_pivot)
    for k in range(3):
        a = (k / 3.0) * math.pi * 2.0
        blade = add_box("rotor_tail-blade-" + str(k + 1), (0.08, 1.6, 0.22),
                        (0.0, math.sin(a) * 0.9, math.cos(a) * 0.9),
                        rot=(math.radians(90), 0.0, -a))
        blade.parent = tailrotor_pivot
        assign(blade, mats["dark"])
    fin = add_box("heli-fin", (0.14, 0.9, 1.1), (0.0, -6.4, 0.7))
    assign(fin, mats["hull"])
    # trains + treuil sonar
    for sx in (-1, 1):
        skid = add_cylinder("heli-skid-" + ("p" if sx < 0 else "s"), 0.07, 3.0,
                            (sx * 0.9, 0.2, -1.35), rot=(math.radians(90), 0.0, 0.0))
        assign(skid, mats["metal"])
        strut1 = add_cylinder("heli-strut-" + ("p" if sx < 0 else "s") + "-1", 0.06, 1.1, (sx * 0.9, 1.0, -0.85))
        strut2 = add_cylinder("heli-strut-" + ("p" if sx < 0 else "s") + "-2", 0.06, 1.1, (sx * 0.9, -0.6, -0.85))
        assign(strut1, mats["metal"])
        assign(strut2, mats["metal"])
    winch = add_cylinder("sonar_winch", 0.14, 0.9, (0.0, 1.2, -1.35), rot=(0.0, 0.0, 0.0))
    assign(winch, mats["metal"])
    # patins extrémités recourbés
    for sx in (-1, 1):
        tipf = add_cylinder("heli-skidtip-" + ("p" if sx < 0 else "s") + "-f", 0.07, 0.5,
                            (sx * 0.9, 1.9, -1.15), rot=(math.radians(-30), 0.0, 0.0))
        assign(tipf, mats["metal"])


def main():
    args = parse_args_after_dashes()
    clean_scene()
    mats = make_materials()
    build_jet(mats)
    build_helicopter(mats)
    everything = [o for o in bpy.context.scene.objects]
    all_meshes = [o for o in everything if o.type == "MESH"]
    make_lods(all_meshes)
    report([o for o in bpy.context.scene.objects if o.type == "MESH"])
    export_fbx([o for o in bpy.context.scene.objects], args.out)
    print("gen_aircraft_blender : FBX -> " + args.out)


if __name__ == "__main__":
    main()
