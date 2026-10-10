"""BDFR Character Creator 0.2.2 - reliable Maya native geometry body.
All geometry is generated via maya.cmds, without OpenMaya mesh constructors.
This is a procedural mannequin, not a photo-realistic anatomical reconstruction.
"""
import math
import maya.cmds as cmds

ROOT = "BDFR_Character"
VERSION = "0.2.2"
EXPECTED = ("Torso","Pelvis","Neck","Head",
            "L_UpperArm","L_Elbow","L_Forearm","L_Hand",
            "L_Thigh","L_Knee","L_Shin","L_Foot",
            "R_UpperArm","R_Elbow","R_Forearm","R_Hand",
            "R_Thigh","R_Knee","R_Shin","R_Foot")


def _material():
    name="BDFR_Skin_022"
    if not cmds.objExists(name):
        shader=cmds.shadingNode("lambert",asShader=True,name=name)
        cmds.setAttr(shader+".color",0.60,0.39,0.29,type="double3")
        group=cmds.sets(renderable=True,noSurfaceShader=True,empty=True,name=name+"SG")
        cmds.connectAttr(shader+".outColor",group+".surfaceShader",force=True)
    return cmds.listConnections(name+".outColor",type="shadingEngine")[0]


def build(height=175., shoulders=1., waist=1., hips=1., muscle=1.,
          head=1., physique="Neutral"):
    """Return generated root after asserting every named limb exists."""
    vals=(height,shoulders,waist,hips,muscle,head)
    if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in vals):
        raise ValueError("BDFR: parameters must be finite numbers")
    if not 130 <= height <= 220 or any(not 0.5 <= x <= 2 for x in vals[1:]):
        raise ValueError("BDFR: parameter outside supported range")
    preset={"Neutral":(1.,1.),"Broad":(1.12,0.96),"Curvy":(0.94,1.12)}
    sh,hi=preset.get(physique,(1.,1.))
    shoulder=shoulders*sh
    hip=hips*hi
    if cmds.objExists(ROOT):
        cmds.delete(ROOT)
    root=cmds.group(em=True,name=ROOT)
    mesh_group=cmds.group(em=True,name="BDFR_Meshes",parent=root)
    material=_material()
    made={}

    def ellipsoid(label,center,radii):
        obj=cmds.polySphere(name="BDFR_"+label,radius=1,
                            subdivisionsX=24,subdivisionsY=18,
                            constructionHistory=False)[0]
        obj=cmds.parent(obj,mesh_group)[0]
        cmds.xform(obj,objectSpace=True,translation=center)
        cmds.setAttr(obj+".scale",*radii,type="double3")
        cmds.sets(obj,e=True,forceElement=material)
        made[label]=obj
        return obj

    def bone(label,start,finish,radius):
        # Stable cylinder alignment via Maya's native aimConstraint.
        dx=finish[0]-start[0];dy=finish[1]-start[1];dz=finish[2]-start[2]
        length=math.sqrt(dx*dx+dy*dy+dz*dz)
        if length < 1e-5:
            raise ValueError("Zero-length limb: "+label)
        obj=cmds.polyCylinder(name="BDFR_"+label,radius=radius,
                              height=length,subdivisionsAxis=20,
                              constructionHistory=False)[0]
        obj=cmds.parent(obj,mesh_group)[0]
        center=tuple((start[i]+finish[i])/2 for i in range(3))
        cmds.xform(obj,worldSpace=True,translation=center)
        # Rotate local +Y towards the limb using the Maya API quaternion;
        # all meshes themselves remain cmds primitives.
        from maya.api import OpenMaya as om
        q=om.MVector(0,1,0).rotateTo(om.MVector(dx,dy,dz).normal())
        e=q.asEulerRotation()
        cmds.setAttr(obj+".rotate",*[math.degrees(v) for v in (e.x,e.y,e.z)],
                     type="double3")
        cmds.sets(obj,e=True,forceElement=material)
        made[label]=obj
        return obj

    try:
        ellipsoid("Pelvis",(0,91,0),(18*hip,14,12*hip))
        ellipsoid("Torso",(0,123,0),(23*shoulder,31,13*waist))
        ellipsoid("Neck",(0,151,0),(6,8,6))
        ellipsoid("Head",(0,167,0),(10*head,13*head,9*head))
        for sign,side in ((-1,"L"),(1,"R")):
            shoulder_joint=(sign*23*shoulder,141,0)
            elbow=(sign*31*shoulder,112,0)
            wrist=(sign*34*shoulder,88,2)
            h=(sign*11*hip,87,0)
            knee=(sign*12*hip,49,1)
            ankle=(sign*12*hip,11,0)
            bone(side+"_UpperArm",shoulder_joint,elbow,6.6*muscle)
            ellipsoid(side+"_Elbow",elbow,(5.2,5.2,5.2))
            bone(side+"_Forearm",elbow,wrist,4.7*muscle)
            ellipsoid(side+"_Hand",(wrist[0],82,2),(4,8,3))
            bone(side+"_Thigh",h,knee,9*hip*muscle)
            ellipsoid(side+"_Knee",knee,(7.5,7.5,7.5))
            bone(side+"_Shin",knee,ankle,6.2*muscle)
            ellipsoid(side+"_Foot",(ankle[0],5,9),(7,5,15))
        missing=[name for name in EXPECTED
                 if name not in made or not cmds.objExists(made[name])]
        if missing:
            raise RuntimeError("Missing mesh members: "+", ".join(missing))
        # Check each member is within our character hierarchy and has a mesh shape.
        for label,obj in made.items():
            if not cmds.listRelatives(obj,shapes=True,type="mesh"):
                raise RuntimeError("No polygon mesh for: "+label)
            parent=cmds.listRelatives(obj,parent=True,fullPath=True) or []
            if not parent or not parent[0].endswith("|BDFR_Meshes"):
                raise RuntimeError("Unexpected mesh hierarchy: "+label)
        scale=float(height)/175.
        cmds.setAttr(mesh_group+".scale",scale,scale,scale,type="double3")
        cmds.addAttr(root,longName="bdfrGeneratorVersion",dataType="string")
        cmds.setAttr(root+".bdfrGeneratorVersion",VERSION,type="string")
        cmds.select(root,r=True)
        cmds.viewFit()
        cmds.inViewMessage(amg="BDFR v0.2.2: <hl>20 parts generated</hl>",
                           pos="midCenter",fade=True)
        print("[BDFR] PASS - generated {} required body parts, v{}".format(
              len(EXPECTED),VERSION))
        return root
    except Exception:
        print("[BDFR] FAILED - body generator stopped; see Python traceback.")
        if cmds.objExists(root):
            cmds.delete(root)
        raise


def diagnose():
    """A quick command-line report after clicking Generate."""
    found=cmds.ls("BDFR_*",type="transform",long=True) or []
    missing=[s for s in EXPECTED if not cmds.objExists("BDFR_"+s)]
    result={"version":VERSION,"required":len(EXPECTED),
            "missing":missing,"found":len(found)}
    print("[BDFR] Diagnostic:",result)
    return result
