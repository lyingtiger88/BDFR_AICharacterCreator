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
    # Robust native primitives: reliable meshes independent of MFnMesh ring normals.
    def sphere(name, xyz, scale):
        obj=cmds.polySphere(name=name, radius=1, subdivisionsX=20,
                            subdivisionsY=16, constructionHistory=False)[0]
        cmds.parent(obj,group)
        cmds.setAttr(obj+".translate", *xyz, type="double3")
        cmds.setAttr(obj+".scale", *scale, type="double3")
        cmds.sets(obj, edit=True, forceElement=cmds.listConnections(
            skin,type="shadingEngine")[0])
        return obj

    def link(name, p1, p2, thickness):
        from maya.api import OpenMaya as om
        a=om.MVector(*p1); b=om.MVector(*p2)
        direction=b-a
        obj=cmds.polyCylinder(name=name, radius=1, height=1,
                              subdivisionsAxis=20, constructionHistory=False)[0]
        cmds.parent(obj,group)
        mid=(a+b)*0.5
        cmds.setAttr(obj+".translate",mid.x,mid.y,mid.z,type="double3")
        rot=om.MVector(0,1,0).rotateTo(direction.normal()).asEulerRotation()
        cmds.setAttr(obj+".rotate",math.degrees(rot.x),math.degrees(rot.y),
                     math.degrees(rot.z),type="double3")
        cmds.setAttr(obj+".scale",thickness,direction.length(),thickness,
                     type="double3")
        cmds.sets(obj,edit=True,forceElement=cmds.listConnections(
            skin,type="shadingEngine")[0])
        return obj

    required=[]
    for side,label in ((-1,"L"),(1,"R")):
        shoulder=(side*24*sw,142,0)
        elbow=(side*31*sw,110,0)
        wrist=(side*34*sw,84,3)
        hip=(side*11*hw,88,0)
        knee=(side*12*hw,50,1)
        ankle=(side*12*hw,11,0)
        required.extend([
            link(label+"_UpperArm",shoulder,elbow,6.8*m),
            sphere(label+"_Elbow",elbow,(5.4*m,5.4*m,5.4*m)),
            link(label+"_Forearm",elbow,wrist,4.8*m),
            sphere(label+"_Hand",(wrist[0],78,3),(4.2,7.5,2.8)),
            link(label+"_Thigh",hip,knee,9.2*hw*m),
            sphere(label+"_Knee",knee,(7.3,7.3,7.3)),
            link(label+"_Shin",knee,ankle,6.3*m),
            sphere(label+"_Foot",(ankle[0],5,8),(7,4.5,15)),
        ])
    if len(required)!=16 or not all(cmds.objExists(node) for node in required):
        raise RuntimeError("BDFR body generation incomplete: limbs missing")
    s=height/175.
    cmds.setAttr(group+".scale",s,s,s,type="double3")
    cmds.addAttr(root,longName="bdfrGenerator",dataType="string")
    cmds.setAttr(root+".bdfrGenerator","organic-proxy-v0.2.1",type="string")
    cmds.select(root,replace=True)
    cmds.viewFit()
    return root
