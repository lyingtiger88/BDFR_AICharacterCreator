"""Download and import official CC0 MakeHuman base mesh directly into Maya.
No MakeHuman application or manual OBJ export is necessary.
"""
from pathlib import Path
import hashlib
import urllib.request
import maya.cmds as cmds

BASE_URL = "https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/3dobjs/base.obj"
CACHE = Path.home() / "Documents" / "BDFR_AICharacterCreator" / "assets" / "makehuman"
BASE_NAME = "makehuman_base.obj"

def ensure_base_mesh():
    CACHE.mkdir(parents=True, exist_ok=True)
    target=CACHE / BASE_NAME
    if target.exists() and target.stat().st_size > 100_000:
        return target
    tmp=target.with_suffix(".download")
    try:
        req=urllib.request.Request(BASE_URL,headers={"User-Agent":"BDFRCharacterCreator/0.3.1"})
        with urllib.request.urlopen(req,timeout=35) as response, open(tmp,"wb") as output:
            while True:
                chunk=response.read(1024*1024)
                if not chunk: break
                output.write(chunk)
        if tmp.stat().st_size < 100_000:
            raise RuntimeError("Downloaded OBJ is unexpectedly small.")
        with open(tmp,"rb") as f:
            prefix=f.read(2048).decode("utf-8",errors="replace")
        if not any(line.startswith(("v ","# ")) for line in prefix.splitlines()):
            raise RuntimeError("Download does not appear to be a Wavefront OBJ.")
        tmp.replace(target)
        return target
    finally:
        if tmp.exists():
            tmp.unlink()

def clean_imported_helpers(namespace="BDFRMakeHuman", smooth_level=2):
    """Remove OBJ reference-guide meshes, not actual Maya joints.
    Only touches named MakeHuman meshes in the specified namespace.
    """
    prefix=namespace+":"
    objects=cmds.ls(prefix+"*",type="transform",long=True) or []
    bodies=[]
    removed=[]
    for node in sorted(objects,key=lambda n:n.count("|"),reverse=True):
        if not cmds.objExists(node):
            continue
        short=node.split("|")[-1].split(":")[-1]
        shapes=cmds.listRelatives(node,shapes=True,type="mesh",fullPath=True) or []
        if not shapes:
            continue
        if short=="body":
            bodies.append(node)
        elif short.startswith(("helper_","joint_")):
            cmds.delete(node)
            removed.append(short)
    if not bodies:
        raise RuntimeError("The MakeHuman 'body' mesh was not found. Nothing else was modified.")
    for body in bodies:
        cmds.setAttr(body+".visibility",1)
        for shape in cmds.listRelatives(body,shapes=True,type="mesh",fullPath=True) or []:
            cmds.setAttr(shape+".displaySmoothMesh",2 if smooth_level else 0)
            cmds.setAttr(shape+".smoothLevel",max(0,min(int(smooth_level),3)))
            cmds.setAttr(shape+".renderSmoothLevel",max(0,min(int(smooth_level),3)))
    cmds.select(bodies,replace=True)
    cmds.viewFit()
    print("[BDFR] body-only cleanup:",len(removed),"reference helpers removed.")
    return {"bodies":bodies,"removed_helpers":removed,"smooth_preview":smooth_level,
            "anatomy":"unmodified base mesh; anatomical morph targets not yet applied"}


def create_real_body():
    """Import official base mesh and verify polygon counts. Maya may use scene units."""
    path=ensure_base_mesh()
    before=set(cmds.ls(type="mesh",long=True) or [])
    cmds.loadPlugin("objExport",quiet=True)
    namespace="BDFRMakeHuman"
    cmds.file(str(path),i=True,type="OBJ",ignoreVersion=True,
              mergeNamespacesOnClash=True,namespace=namespace,
              options="mo=1",preserveReferences=True)
    after=set(cmds.ls(type="mesh",long=True) or [])
    new_shapes=sorted(after-before)
    if not new_shapes:
        raise RuntimeError("OBJ was imported but no polygon meshes appeared.")
    total_vertices=sum(cmds.polyEvaluate(shape,vertex=True) for shape in new_shapes)
    total_faces=sum(cmds.polyEvaluate(shape,face=True) for shape in new_shapes)
    if total_vertices < 1000 or total_faces < 1000:
        raise RuntimeError("Imported geometry is unexpectedly incomplete.")
    transforms=list(dict.fromkeys(cmds.listRelatives(
        shape,parent=True,fullPath=True)[0] for shape in new_shapes))
    cleaned=clean_imported_helpers(namespace, smooth_level=2)
    result={"mesh_file":str(path),"meshes":len(new_shapes),
            "vertices":total_vertices,"faces":total_faces,
            "transforms":transforms}
    result["cleanup"]=cleaned
    print("[BDFR] MakeHuman CC0 body-only imported:",result)
    return result

def launch():
    window="BDFRRealBodyLoader"
    if cmds.window(window,exists=True):
        cmds.deleteUI(window)
    w=cmds.window(window,title="BDFR | Real MakeHuman Body v0.3.2",
                  widthHeight=(440,185),sizeable=True)
    cmds.columnLayout(adjustableColumn=True,rowSpacing=12)
    cmds.text(label="OFFICIAL MAKEHUMAN BASE BODY",font="boldLabelFont",height=32)
    cmds.text(label="First use downloads the CC0 base OBJ; later uses local cache.")
    def callback(*_):
        try:
            result=create_real_body()
            cmds.confirmDialog(title="MakeHuman body imported",
                message="Meshes: {meshes}\nVertices: {vertices}\nFaces: {faces}".format(**result),
                button=["OK"])
        except Exception as exc:
            cmds.confirmDialog(title="BDFR import failed",message=str(exc),button=["OK"])
            raise
    cmds.button(label="LOAD REAL FULL BODY (AUTOMATIC)",height=48,command=callback)
    cmds.text(label="Base mesh only. AI, morph controls and rigging are not yet connected.")
    cmds.showWindow(w)
    return w
