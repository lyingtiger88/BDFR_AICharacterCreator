"""Create an inspectable SMPL-X 22-body-joint guide in Maya.
The guide is NOT skinned and is not a production animation rig.
"""
import maya.cmds as cmds

NAMES=("pelvis","left_hip","right_hip","spine1","left_knee","right_knee",
       "spine2","left_ankle","right_ankle","spine3","left_foot","right_foot",
       "neck","left_collar","right_collar","head","left_shoulder",
       "right_shoulder","left_elbow","right_elbow","left_wrist","right_wrist")
PARENTS=(-1,0,0,0,1,2,3,4,5,6,7,8,9,9,9,12,13,14,16,17,18,19)
GROUP="BDFR_SMPLX_JointGuide"

def build(positions, target="BDFR_SMPLX_Character"):
    if len(positions)!=len(NAMES):
        raise ValueError("Expected 22 SMPL-X body joint positions")
    if not cmds.objExists(target):
        raise ValueError("SMPL-X character mesh missing")
    if cmds.objExists(GROUP):
        cmds.delete(GROUP)
    root=cmds.group(empty=True,name=GROUP)
    cmds.addAttr(root,longName="isGuideOnly",attributeType="bool",defaultValue=True)
    nodes=[]
    # world placement matches mesh scaled 100 and ground translation;
    # use target world transform rather than treating coordinates as world.
    world=cmds.xform(target,query=True,matrix=True,worldSpace=True)
    from maya.api import OpenMaya as om
    matrix=om.MMatrix(world)
    for i,(name,point) in enumerate(zip(NAMES,positions)):
        pos=om.MPoint(*point)*matrix
        cmds.select(clear=True)
        joint=cmds.joint(name="BDFR_"+name+"_JNT",position=(pos.x,pos.y,pos.z),radius=1.3)
        cmds.parent(joint,root if PARENTS[i]<0 else nodes[PARENTS[i]],absolute=True)
        nodes.append(joint)
    cmds.select(clear=True)
    return root

def show(value=True):
    if cmds.objExists(GROUP):
        cmds.setAttr(GROUP+".visibility",bool(value))
