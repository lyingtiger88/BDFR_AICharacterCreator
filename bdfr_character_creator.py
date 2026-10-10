"""BDFR AI Character Creator — Maya prototype v0.1.0.
Run in Maya Script Editor (Python):
import sys
sys.path.insert(0, r"C:/path/to/BDFR_AICharacterCreator")
from bdfr_character_creator import show
show()
"""
from __future__ import annotations

import maya.cmds as cmds

WINDOW = "BDFR_AICharacterCreator"
ROOT = "BDFR_Character"
VERSION = "0.2.2"


def _material(name, rgb):
    if cmds.objExists(name):
        return name
    shader = cmds.shadingNode("lambert", asShader=True, name=name)
    cmds.setAttr(shader + ".color", *rgb, type="double3")
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name + "_SG")
    cmds.connectAttr(shader + ".outColor", sg + ".surfaceShader", force=True)
    return shader


def _assign(mesh, shader):
    sgs = cmds.listConnections(shader, type="shadingEngine") or []
    if sgs:
        cmds.sets(mesh, edit=True, forceElement=sgs[0])


def _ellipsoid(name, position, scale, parent, shader):
    mesh = cmds.polySphere(name=name, radius=1.0, subdivisionsX=24, subdivisionsY=16)[0]
    cmds.parent(mesh, parent)
    cmds.xform(mesh, translation=position, objectSpace=True)
    cmds.setAttr(mesh + ".scale", *scale, type="double3")
    _assign(mesh, shader)
    return mesh


def _segment(name, start, end, radius1, radius2, parent, shader):
    """Create oriented tapered limb cylinder."""
    import math
    sx, sy, sz = start
    ex, ey, ez = end
    dx, dy, dz = ex - sx, ey - sy, ez - sz
    length = math.sqrt(dx*dx + dy*dy + dz*dz)
    mesh = cmds.polyCylinder(name=name, radius=1.0, height=1.0, subdivisionsAxis=18,
                             subdivisionsHeight=1)[0]
    cmds.parent(mesh, parent)
    cmds.xform(mesh, translation=((sx+ex)/2, (sy+ey)/2, (sz+ez)/2), objectSpace=True)
    # Maya cylinders are Y-aligned, aim the Y-axis along the segment.
    from maya.api import OpenMaya as om
    direction = om.MVector(dx, dy, dz).normal()
    quat = om.MVector(0, 1, 0).rotateTo(direction)
    rot = quat.asEulerRotation()
    cmds.setAttr(mesh + ".rotate", math.degrees(rot.x), math.degrees(rot.y),
                 math.degrees(rot.z), type="double3")
    cmds.setAttr(mesh + ".scale", radius1, length, radius2, type="double3")
    _assign(mesh, shader)
    return mesh


def create_character(height=175.0, build=1.0, head_ratio=1.0):
    """Create an intentionally stylized, editable proxy—not an AI photogrammetry result.
    Dimensions are centimetres; the meshes remain independent editable Maya objects.
    """
    height = float(height)
    build = float(build)
    head_ratio = float(head_ratio)
    if cmds.objExists(ROOT):
        cmds.delete(ROOT)
    root = cmds.group(empty=True, name=ROOT)
    skin = _material("BDFR_Skin_MAT", (0.68, 0.43, 0.31))
    dark = _material("BDFR_Dark_MAT", (0.09, 0.10, 0.13))
    clothing = _material("BDFR_Cloth_MAT", (0.12, 0.31, 0.42))
    s = height / 175.0
    w = build
    # All parts constructed at base 175cm and scaled together for stable overall height.
    rig = cmds.group(empty=True, name="BDFR_Body_GRP", parent=root)
    _ellipsoid("Pelvis", (0, 92, 0), (19*w, 13, 11*w), rig, clothing)
    _ellipsoid("Torso", (0, 122, 0), (24*w, 34, 13*w), rig, clothing)
    _ellipsoid("Neck", (0, 153, 0), (6, 8, 6), rig, skin)
    _ellipsoid("Head", (0, 165, 0), (10*head_ratio, 13*head_ratio, 9*head_ratio), rig, skin)
    # Forward is +Z
    for side, label in ((-1, "L"), (1, "R")):
        x = side
        _ellipsoid(label+"_Eye", (x*4*head_ratio, 167, 8*head_ratio),
                   (1.3, 1.3, 0.85), rig, dark)
        _ellipsoid(label+"_Ear", (x*10*head_ratio, 165, 0), (2, 3.5, 1.5), rig, skin)
        _segment(label+"_UpperArm", (x*24*w, 144, 0), (x*31*w, 112, 0),
                 7*w, 6*w, rig, skin)
        _ellipsoid(label+"_Elbow", (x*31*w, 112, 0), (5.5*w, 5.5, 5.5*w), rig, skin)
        _segment(label+"_Forearm", (x*31*w, 112, 0), (x*33*w, 87, 3),
                 5.5*w, 5*w, rig, skin)
        _ellipsoid(label+"_Hand", (x*33*w, 82, 3), (5*w, 8, 2.5*w), rig, skin)
        _segment(label+"_Thigh", (x*11*w, 86, 0), (x*12*w, 51, 1),
                 10*w, 9*w, rig, clothing)
        _ellipsoid(label+"_Knee", (x*12*w, 50, 1), (8*w, 8, 8*w), rig, clothing)
        _segment(label+"_Shin", (x*12*w, 48, 1), (x*12*w, 12, 0),
                 7*w, 6*w, rig, clothing)
        _ellipsoid(label+"_Foot", (x*12*w, 5, 8), (8*w, 5, 16*w), rig, dark)
    cmds.setAttr(rig + ".scale", s, s, s, type="double3")
    cmds.addAttr(root, longName="bdfrVersion", dataType="string")
    cmds.setAttr(root+".bdfrVersion", VERSION, type="string")
    cmds.select(root, replace=True)
    cmds.viewFit()
    return root


def _from_ui(*_):
    h = cmds.floatSliderGrp("bdfrHeight", q=True, value=True)
    b = cmds.floatSliderGrp("bdfrBuild", q=True, value=True)
    head = cmds.floatSliderGrp("bdfrHead", q=True, value=True)
    try:
        create_character(h, b, head)
        cmds.inViewMessage(amg="BDFR: proxy character created", pos="midCenter", fade=True)
    except Exception as exc:
        cmds.warning("BDFR character creation failed: {}".format(exc))
        raise


def export_obj(*_):
    path = cmds.fileDialog2(fileFilter="OBJ Files (*.obj)", dialogStyle=2, fileMode=0)
    if not path:
        return
    if not cmds.objExists(ROOT):
        cmds.warning("Create a character first.")
        return
    cmds.select(ROOT, replace=True)
    try:
        cmds.loadPlugin("objExport", quiet=True)
        cmds.file(path[0], force=True, options="groups=1;ptgroups=1;materials=1;smoothing=1;normals=1",
                  typ="OBJexport", preserveReferences=True, exportSelected=True)
    except Exception as exc:
        cmds.warning("OBJ export is unavailable in this Maya installation: {}".format(exc))
        raise


def export_fbx(*_):
    path = cmds.fileDialog2(fileFilter="FBX Files (*.fbx)", dialogStyle=2, fileMode=0)
    if not path:
        return
    if not cmds.objExists(ROOT):
        cmds.warning("Create a character first.")
        return
    cmds.select(ROOT, replace=True)
    try:
        cmds.loadPlugin("fbxmaya", quiet=True)
        cmds.file(path[0], force=True, typ="FBX export", preserveReferences=True,
                  exportSelected=True)
    except Exception as exc:
        cmds.warning("FBX export unavailable: {}".format(exc))
        raise


def show():
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    window = cmds.window(WINDOW, title="BDFR AI Character Creator | v"+VERSION,
                         widthHeight=(375, 340), sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=10)
    cmds.text(label="BDFR CHARACTER CREATOR", height=35, font="boldLabelFont")
    cmds.text(label="v0.1 — editable procedural body proxy (no photo-AI yet)",
              align="center")
    cmds.separator(style="in")
    cmds.floatSliderGrp("bdfrHeight", label="Height (cm)", field=True,
                        minValue=130, maxValue=220, value=175)
    cmds.floatSliderGrp("bdfrBuild", label="Body width", field=True,
                        minValue=0.65, maxValue=1.6, value=1.0)
    cmds.floatSliderGrp("bdfrHead", label="Head scale", field=True,
                        minValue=0.7, maxValue=1.3, value=1.0)
    cmds.button(label="CREATE / REBUILD CHARACTER", height=44, command=_from_ui)
    cmds.separator(style="in")
    cmds.button(label="Export OBJ", command=export_obj)
    cmds.button(label="Export FBX", command=export_fbx)
    cmds.text(label="EOS, image fitting, anatomical topology and rigs: planned",
              align="center")
    cmds.showWindow(window)
    return window


# ---- v0.2.2 corrected body UI ----

def _create_v02(*_):
    from bdfr_body_v02 import build
    profile = cmds.optionMenu("bdfrPhysiqueV02", q=True, value=True)
    values = [cmds.floatSliderGrp("bdfrV02_"+key, q=True, value=True)
              for key in ("height","shoulders","waist","hips","muscle","head")]
    try:
        result=build(*values,physique=profile)
        cmds.inViewMessage(amg="BDFR v0.2.2 body created: "+result,
                           pos="midCenter",fade=True)
    except Exception as exc:
        cmds.confirmDialog(title="BDFR build error", message=str(exc),
                           button=["OK"])
        raise


def _build_v02_ui():
    cmds.columnLayout(adjustableColumn=True,rowSpacing=8)
    cmds.text(label="BDFR AI CHARACTER CREATOR  |  v0.2.2",height=30,font="boldLabelFont")
    cmds.text(label="Procedural organic prototype — no photo fitting yet")
    cmds.separator(style="in")
    options=(("height","Height (cm)",130,220,175),
             ("shoulders","Shoulders",0.7,1.4,1),
             ("waist","Waist",0.7,1.4,1),
             ("hips","Hips",0.7,1.4,1),
             ("muscle","Muscle volume",0.7,1.4,1),
             ("head","Head proportion",0.7,1.3,1))
    for key,label,minimum,maximum,value in options:
        cmds.floatSliderGrp("bdfrV02_"+key,label=label,field=True,
                            minValue=minimum,maxValue=maximum,value=value)
    cmds.optionMenu("bdfrPhysiqueV02",label="Body preset")
    for entry in ("Neutral","Broad","Curvy"):
        cmds.menuItem(label=entry)
    cmds.button(label="GENERATE ORGANIC BODY",height=46,command=_create_v02)
    cmds.separator(style="in")
    cmds.button(label="Export OBJ",command=export_obj)
    cmds.button(label="Export FBX",command=export_fbx)
    cmds.text(label="Geometry only. No rig, AI photos, or EOS fitting yet.",
              align="center")


def show(dock=False):
    """Launch v0.2. dock=True uses Maya's dockable workspaceControl."""
    dockname="BDFRCharacterCreatorDock"
    if dock:
        if cmds.workspaceControl(dockname,exists=True):
            cmds.deleteUI(dockname)
        panel=cmds.workspaceControl(dockname,label="BDFR Character Creator",
                                    retain=False,initialWidth=400)
        cmds.setParent(panel)
        _build_v02_ui()
        return panel
    if cmds.window(WINDOW,exists=True):
        cmds.deleteUI(WINDOW)
    window=cmds.window(WINDOW,title="BDFR AI Character Creator | v0.2.2",
                       widthHeight=(405,480),sizeable=True)
    _build_v02_ui()
    cmds.showWindow(window)
    return window
