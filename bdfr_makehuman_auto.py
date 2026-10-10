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
    cmds.select(transforms,replace=True)
    cmds.viewFit()
    result={"mesh_file":str(path),"meshes":len(new_shapes),
            "vertices":total_vertices,"faces":total_faces,
            "transforms":transforms}
    print("[BDFR] MakeHuman CC0 base imported:",result)
    return result

def launch():
    window="BDFRRealBodyLoader"
    if cmds.window(window,exists=True):
        cmds.deleteUI(window)
    w=cmds.window(window,title="BDFR | Real MakeHuman Body v0.3.1",
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
