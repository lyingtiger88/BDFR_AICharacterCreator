"""BDFR Native Human: independent Maya morph authoring and local library.

No Blender, Human Generator, HG assets, or SMPL-X dependencies.
Uses an explicitly licensed base mesh supplied by the user or the existing
MakeHuman CC0 body loader. Does not claim pre-authored anatomy morphs.
"""
import json
from pathlib import Path
import maya.cmds as cmds
from maya.api import OpenMaya as om

HOME=Path.home()/"Documents"/"BDFR_AICharacterCreator"/"native_human"
LIBRARY=HOME/"morphs"
WINDOW="BDFRNativeHumanEditor"

def _mesh(node):
    if not cmds.objExists(node):
        raise ValueError("Mesh not found: "+node)
    shapes=cmds.listRelatives(node,shapes=True,noIntermediate=True,fullPath=True,type="mesh") or []
    if len(shapes)!=1:
        raise ValueError("Select a transform with exactly one polygon mesh")
    selection=om.MSelectionList()
    selection.add(shapes[0])
    return om.MFnMesh(selection.getDagPath(0))

def _points(node):
    fn=_mesh(node)
    return [(p.x,p.y,p.z) for p in fn.getPoints(om.MSpace.kObject)]

def _name(node):
    return node.split("|")[-1].split(":")[-1]

def _safe_name(s):
    import re
    s=re.sub(r"[^A-Za-z0-9_-]+","_",s.strip())
    return s[:64].strip("_") or "Morph"

def create_body():
    from bdfr_makehuman_auto import create_real_body
    result=create_real_body()
    bodies=[n for n in cmds.ls(type="transform",long=True) or []
            if _name(n)=="body" and cmds.listRelatives(n,shapes=True,type="mesh")]
    if not bodies:raise RuntimeError("Body import completed without a body transform")
    node=bodies[-1]
    cmds.select(node,replace=True)
    return node

def capture_morph(base,sculpt,name):
    """Store Maya-object-space deltas; reject topology mismatch.

    Deltas are tied to exact vertex indices; Maya scene units are saved.
    A separate topology check happens again when they are loaded.
    """
    if base==sculpt:raise ValueError("Base and sculpt must be different meshes")
    a=_points(base)
    b=_points(sculpt)
    if len(a)!=len(b):raise ValueError("Base/sculpt vertex count mismatch")
    deltas={}
    for i,(v,w) in enumerate(zip(a,b)):
        delta=[round(w[j]-v[j],8) for j in range(3)]
        if any(abs(x)>1e-7 for x in delta):deltas[str(i)]=delta
    if not deltas:raise ValueError("No vertex changes found. Sculpt the duplicate first.")
    LIBRARY.mkdir(parents=True,exist_ok=True)
    file=LIBRARY/(_safe_name(name)+".json")
    if file.exists():raise FileExistsError("Morph already exists; choose another name")
    # A cryptographic checksum of base coordinates prevents accidentally
    # binding to an incompatible base mesh with equal vertex count.
    import hashlib,struct
    def signature(points):
        digest=hashlib.sha256()
        for point in points:
            digest.update(struct.pack("<3d",*point))
        return digest.hexdigest()
    data={"schema":"BDFR_Native_Morph_1","name":name,
          "vertices":len(a),"basis_sha256":signature(a),
          "unit":cmds.currentUnit(q=True,linear=True),
          "delta_count":len(deltas),"deltas":deltas}
    file.write_text(json.dumps(data,separators=(",",":")),encoding="utf-8")
    return str(file)

def load_morph(base,path):
    import hashlib,struct
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema")!="BDFR_Native_Morph_1":raise ValueError("Unsupported morph schema")
    orig=_points(base)
    if len(orig)!=data["vertices"]:raise ValueError("Morph topology vertex count mismatch")
    signature=hashlib.sha256()
    for p in orig:signature.update(struct.pack("<3d",*p))
    if signature.hexdigest()!=data["basis_sha256"]:
        raise ValueError("Base vertex positions/order differ; load on the original base body before deformation.")
    if cmds.currentUnit(q=True,linear=True)!=data["unit"]:
        raise ValueError("Maya linear units differ from the authored morph file")
    duplicate=cmds.duplicate(base,returnRootsOnly=True,name="BDFR_Native_Morph_TEMP")[0]
    try:
        fn=_mesh(duplicate)
        target=list(fn.getPoints(om.MSpace.kObject))
        for idx,delta in data["deltas"].items():
            i=int(idx)
            if i<0 or i>=len(target):raise ValueError("Invalid morph vertex index")
            target[i]=om.MPoint(*(orig[i][j]+delta[j] for j in range(3)))
        fn.setPoints(target,om.MSpace.kObject)
        existing=cmds.listConnections(_mesh_shape(base)+".inMesh",source=True,destination=False,type="blendShape") or []
        if existing:
            blend=existing[0]
            used=cmds.getAttr(blend+".weight",multiIndices=True) or []
            index=max(used)+1 if used else 0
        else:
            blend=cmds.blendShape(base,frontOfChain=True,name="BDFR_Native_Human_BlendShape")[0]
            index=0
        cmds.blendShape(blend,e=True,target=(base,index,duplicate,1.0))
        alias=_safe_name(data["name"])
        cmds.aliasAttr(alias+"_"+str(index),blend+".weight["+str(index)+"]")
        cmds.setAttr(blend+".weight["+str(index)+"]",0)
        return blend,index,alias+"_"+str(index)
    finally:
        if cmds.objExists(duplicate):cmds.delete(duplicate)

def _mesh_shape(node):
    return cmds.listRelatives(node,shapes=True,noIntermediate=True,fullPath=True,type="mesh")[0]

def launch():
    if cmds.window(WINDOW,exists=True):cmds.deleteUI(WINDOW)
    window=cmds.window(WINDOW,title="BDFR Native Human | Maya Standalone Alpha",widthHeight=(570,460),sizeable=True)
    cmds.columnLayout(adjustableColumn=True,rowSpacing=8)
    cmds.text(label="BDFR NATIVE HUMAN — OFFLINE MAYA ALPHA",font="boldLabelFont",height=33)
    cmds.text(label="Uses only locally cached CC0 base geometry or your own licensed mesh. No Blender/HG required.",wordWrap=True)
    base=cmds.textFieldGrp(label="Base mesh",text="")
    sculpt=cmds.textFieldGrp(label="Sculpt mesh",text="")
    name=cmds.textFieldGrp(label="Morph name",text="CustomMorph")
    info=cmds.text(label="Load a base body, duplicate and sculpt it, then capture a reusable morph.",wordWrap=True,height=44)
    def set_selected(field):
        picked=cmds.ls(selection=True,long=True,type="transform") or []
        if len(picked)!=1:raise ValueError("Select exactly one mesh transform")
        _mesh(picked[0])
        cmds.textFieldGrp(field,e=True,text=picked[0])
    def safe(fn):
        def wrapped(*_):
            try:fn()
            except Exception as e:
                cmds.confirmDialog(title="BDFR Native Human",message=str(e)[-1500:],button=["OK"])
                cmds.warning(str(e))
        return wrapped
    cmds.button(label="CREATE BASE HUMAN (CC0, cached after first use)",height=36,
        command=safe(lambda:cmds.textFieldGrp(base,e=True,text=create_body())))
    cmds.button(label="USE SELECTED OBJECT AS BASE",command=safe(lambda:set_selected(base)))
    cmds.button(label="USE SELECTED OBJECT AS SCULPT TARGET",command=safe(lambda:set_selected(sculpt)))
    def duplicate():
        obj=cmds.textFieldGrp(base,q=True,text=True)
        _mesh(obj)
        dup=cmds.duplicate(obj,returnRootsOnly=True,name="BDFR_Human_Sculpt")[0]
        cmds.textFieldGrp(sculpt,e=True,text=dup)
        cmds.select(dup,replace=True)
        cmds.text(info,e=True,label="Sculpt the duplicate in Maya, then click SAVE MORPH.")
    cmds.button(label="DUPLICATE BASE FOR MAYA SCULPTING",height=33,command=safe(duplicate))
    def save():
        path=capture_morph(cmds.textFieldGrp(base,q=True,text=True),
            cmds.textFieldGrp(sculpt,q=True,text=True),
            cmds.textFieldGrp(name,q=True,text=True))
        cmds.text(info,e=True,label="Saved: "+path)
    cmds.button(label="SAVE SCULPT AS REUSABLE NATIVE MORPH",height=36,command=safe(save))
    def load():
        files=cmds.fileDialog2(fileMode=1,caption="Open BDFR native morph",
                               startingDirectory=str(LIBRARY),fileFilter="BDFR Morph (*.json)")
        if not files:return
        blend,index,alias=load_morph(cmds.textFieldGrp(base,q=True,text=True),files[0])
        cmds.floatSliderGrp(label=alias,field=True,minValue=0,maxValue=1,value=0,
             dragCommand=lambda val,*_:cmds.setAttr(blend+".weight["+str(index)+"]",float(val)),
             changeCommand=lambda val,*_:cmds.setAttr(blend+".weight["+str(index)+"]",float(val)))
        cmds.text(info,e=True,label="Native BlendShape loaded: "+alias)
    cmds.button(label="LOAD LOCAL MORPH AS LIVE MAYA BLENDSHAPE",height=36,command=safe(load))
    cmds.text(label="Alpha: morph authoring & reuse, not yet a complete anatomy/face/hair/rig system.",wordWrap=True)
    cmds.showWindow(window)
    return window
