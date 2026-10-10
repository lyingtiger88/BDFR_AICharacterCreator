"""BDFR v0.2: ring-based organic proxy meshes for Autodesk Maya.
Geometry is procedural (not a scanned or AI-reconstructed human).
"""
import math
import maya.cmds as cmds
from maya.api import OpenMaya as om

ROOT = "BDFR_Character"


def _skin(name, color):
    if cmds.objExists(name):
        return name
    mat = cmds.shadingNode("lambert", asShader=True, name=name)
    cmds.setAttr(mat + ".color", *color, type="double3")
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name + "SG")
    cmds.connectAttr(mat + ".outColor", sg + ".surfaceShader", force=True)
    return mat


def _mesh(name, rings, parent, shader, sides=24, cap=True):
    """Smooth mesh from successive elliptical cross sections.
    Each ring: (center xyz, radii xyz); cross-section plane perpendicular to Y.
    """
    vertices = []
    for ((cx,cy,cz),(rx,_,rz)) in rings:
        for j in range(sides):
            a = 2.0 * math.pi * j / sides
            vertices.append(om.MPoint(cx + rx*math.cos(a), cy, cz + rz*math.sin(a)))
    counts, indices = [], []
    for i in range(len(rings)-1):
        for j in range(sides):
            k = (j+1)%sides
            indices.extend((i*sides+j, i*sides+k, (i+1)*sides+k, (i+1)*sides+j))
            counts.append(4)
    if cap:
        indices.extend(reversed(range(sides)))
        counts.append(sides)
        indices.extend((len(rings)-1)*sides+j for j in range(sides))
        counts.append(sides)
    fn = om.MFnMesh()
    obj = fn.create(vertices, counts, indices)
    shape = om.MFnDagNode(obj)
    transform = om.MFnDagNode(shape.parent(0))
    transform.setName(name)
    path = transform.fullPathName()
    path = cmds.parent(path, parent)[0]
    cmds.polySoftEdge(path, angle=180, constructionHistory=False)
    sg = cmds.listConnections(shader, type="shadingEngine") or []
    if sg:
        cmds.sets(path, edit=True, forceElement=sg[0])
    return path


def _outline(name, stations, parent, shader, sides=32):
    return _mesh(name, [((x,y,z),(rx,0,rz)) for y,x,z,rx,rz in stations],
                 parent, shader, sides)


def _limb(name, anchors, widths, parent, shader, sides=20):
    """Swept limbs: circular-ish sections remain horizontal; approximation only."""
    rings = []
    for (x,y,z), (rx,rz) in zip(anchors,widths):
        rings.append(((x,y,z),(rx,0,rz)))
    return _mesh(name,rings,parent,shader,sides)


def build(height=175., shoulders=1., waist=1., hips=1., muscle=1.,
          head=1., physique="Neutral"):
    """Build anatomically suggestive, editable independent surfaces in cm."""
    height=float(height)
    if not 120 <= height <= 230:
        raise ValueError("Height must be within 120..230 cm")
    for x in (shoulders,waist,hips,muscle,head):
        if not 0.5 <= float(x) <= 2.0:
            raise ValueError("Invalid morphology parameter")
    if cmds.objExists(ROOT):
        cmds.delete(ROOT)
    root=cmds.group(empty=True,name=ROOT)
    group=cmds.group(empty=True,name="Body_Surface_GRP",parent=root)
    skin=_skin("BDFR_v02_Skin", (0.57,0.34,0.24))
    eye=_skin("BDFR_v02_Eyes", (0.08,0.10,0.12))
    # Physique affects proportions, not a sex-specific anatomical assertion.
    profile={"Neutral":(1.,1.), "Broad":(1.12,0.95), "Curvy":(0.93,1.12)}
    sh,hi=profile.get(physique,profile["Neutral"])
    sw=shoulders*sh
    hw=hips*hi
    w=waist
    m=muscle
    _outline("Body_Torso",[
      (80,0,0,13*w,9*w),(85,0,0,17*hw,11*hw),
      (94,0,0,19*hw,12*hw),(101,0,0,16*w,10*w),
      (110,0,0,15*w,10*w),(120,0,0,18*sw,12*sw),
      (130,0,0,23*sw,13*sw),(138,0,0,24*sw,12*sw),
      (144,0,0,20*sw,10*sw),(150,0,0,9,7),
      (154,0,0,6,6)],group,skin)
    _outline("Head_Organic",[
      (151,0,0,5*head,5*head),(154,0,1,8*head,7*head),
      (158,0,1,9*head,8*head),(164,0,0,10*head,9*head),
      (170,0,-0.4,10.5*head,9.5*head),
      (176,0,-0.5,9*head,9*head),(179,0,-1,6*head,7*head),
      (180,0,-1,1*head,1*head)],group,skin)
    for side,label in ((-1,"L"),(1,"R")):
        _limb(label+"_Arm",[
          (side*21*sw,145,0),(side*25*sw,142,0),
          (side*28*sw,134,0),(side*30*sw,122,0),
          (side*32*sw,111,0),(side*33*sw,103,1),
          (side*34*sw,94,2),(side*34*sw,84,3),
          (side*34*sw,80,3)],
          [(6*m,6*m),(8*m,8*m),(8*m,8*m),(7*m,7*m),
           (5.4*m,5.4*m),(5.8*m,5.8*m),(5*m,5*m),
           (3.5*m,3.5*m),(2.4*m,2.4*m)],group,skin)
        _limb(label+"_Hand",[(side*34*sw,83,3),(side*34*sw,78,3),
                              (side*34*sw,73,3),(side*34*sw,70,3)],
              [(3.5,2.5),(4.5,2.8),(3.8,2.5),(1.,1.)],group,skin)
        lx=side*11*hw
        _limb(label+"_Leg",[(lx,91,0),(lx,84,0),(lx,73,0),
                             (lx,63,1),(lx,53,2),(lx,47,2),
                             (lx,37,1),(lx,25,0),(lx,12,0),(lx,8,0)],
              [(9.8*hw,9.4*hw),(10.8*hw*m,10.5*hw*m),
               (11*hw*m,10*hw*m),(9.2*hw,8.5*hw),(7.5,7.5),
               (7.3,7.6),(7.9*m,7.5*m),(6.4,6.1),(4.5,4.8),
               (4.0,4.5)],group,skin)
        # Distinct polygon foot, aligned toward +Z.
        _outline(label+"_Foot",[(0,lx,8,0.5,0.5),(3,lx,8,7,14),
                                 (7,lx,5,6.4,11),(11,lx,0,4.2,5)],
                 group,skin,sides=20)
        _outline(label+"_Eye",[(165,side*4.3*head,8*head,1.2,0.7),
                                (167,side*4.3*head,8.7*head,1.1,0.7)],
                 group,eye,sides=12)
    s=height/175.
    cmds.setAttr(group+".scale",s,s,s,type="double3")
    cmds.addAttr(root,longName="bdfrGenerator",dataType="string")
    cmds.setAttr(root+".bdfrGenerator","organic-proxy-v0.2",type="string")
    cmds.select(root,replace=True)
    cmds.viewFit()
    return root
