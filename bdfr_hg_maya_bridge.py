"""Maya adapter for Blender 4.4 / Human Generator 4.0.26 authored assets.

Only subprocesses Blender's public command-line export and imports FBX. The user
must have Human Generator installed/licensed and a saved .blend character scene.
"""
from pathlib import Path
import subprocess
import maya.cmds as cmds

WINDOW="BDFRHumanGeneratorBridge"
REPO=Path(__file__).resolve().parent

def _find_blender():
    paths=[
        Path(r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.4.3\blender.exe"),
    ]
    for p in paths:
        if p.is_file():return str(p)
    return "blender"

def export_human(blender,blend,fbx,collection=""):
    if not Path(blend).is_file():raise FileNotFoundError("Saved .blend scene not found")
    if Path(fbx).suffix.lower()!=".fbx":raise ValueError("Output path must end in .fbx")
    if not (REPO/"bdfr_hg_blender_bridge.py").is_file():
        raise FileNotFoundError("Blender-side bridge script missing")
    args=[blender,"-b",str(blend),"--python",str(REPO/"bdfr_hg_blender_bridge.py"),
          "--","--out",str(fbx)]
    if collection.strip():args+=["--collection",collection.strip()]
    result=subprocess.run(args,text=True,stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,timeout=360)
    if result.returncode!=0:
        raise RuntimeError("Blender export failed:\n"+result.stdout[-3000:])
    if not Path(fbx).is_file() or Path(fbx).stat().st_size<1024:
        raise RuntimeError("FBX export did not create a usable file:\n"+result.stdout[-1500:])
    return result.stdout

def import_human(fbx):
    if not Path(fbx).is_file():raise FileNotFoundError(fbx)
    if not cmds.pluginInfo("fbxmaya",q=True,loaded=True):
        cmds.loadPlugin("fbxmaya",quiet=True)
    # Use FBX import flags rather than opening a new Maya scene.
    cmds.file(str(fbx),i=True,type="FBX",ignoreVersion=True,
              mergeNamespacesOnClash=False,namespace="BDFRHumanGenerator",
              preserveReferences=True,options="fbx")
    return str(fbx)

def launch():
    if cmds.window(WINDOW,exists=True):cmds.deleteUI(WINDOW)
    w=cmds.window(WINDOW,title="BDFR | Human Generator Blender Bridge",
                  widthHeight=(590,335),sizeable=True)
    cmds.columnLayout(adjustableColumn=True,rowSpacing=10)
    cmds.text(label="HUMAN GENERATOR 4.0.26  |  BLENDER 4.4.3",font="boldLabelFont",height=38)
    cmds.text(label="Save your HG character in Blender first. Select its mesh + rig, or supply a collection.",wordWrap=True)
    blender=cmds.textFieldButtonGrp(label="Blender EXE",text=_find_blender(),buttonLabel="Browse",
                                   buttonCommand=lambda *_:choose_file(blender,1,"Blender executable"))
    blend=cmds.textFieldButtonGrp(label="Blender scene",text="",buttonLabel="Browse",
                                 buttonCommand=lambda *_:choose_file(blend,1,"Blender scene","*.blend"))
    out=cmds.textFieldButtonGrp(label="Output FBX",text=str(Path.home()/"Documents"/"BDFR_HG_Character.fbx"),
                               buttonLabel="Browse",
                               buttonCommand=lambda *_:choose_file(out,0,"FBX output","*.fbx"))
    collection=cmds.textFieldGrp(label="Collection (optional)",text="")
    def choose_file(control,mode,caption,mask="*"):
        chosen=cmds.fileDialog2(fileMode=mode,fileFilter=mask,caption=caption)
        if chosen:cmds.textFieldButtonGrp(control,e=True,text=chosen[0])
    def run(*_):
        exe=cmds.textFieldButtonGrp(blender,q=True,text=True).strip()
        source=cmds.textFieldButtonGrp(blend,q=True,text=True).strip()
        target=cmds.textFieldButtonGrp(out,q=True,text=True).strip()
        coll=cmds.textFieldGrp(collection,q=True,text=True).strip()
        try:
            cmds.waitCursor(state=True)
            log=export_human(exe,source,target,coll)
            print("[BDFR HG Bridge]",log[-1000:])
            import_human(target)
            cmds.confirmDialog(title="Human Generator bridge",message="Character FBX exported and imported into Maya.",button=["OK"])
        except Exception as exc:
            cmds.confirmDialog(title="Human Generator bridge error",message=str(exc)[-1800:],button=["OK"])
        finally:
            cmds.waitCursor(state=False)
    cmds.button(label="EXPORT FROM BLENDER + IMPORT INTO MAYA",height=43,command=run)
    cmds.text(label="Supports authored .blend characters; not live HG sliders or native HG generation in Maya.",wordWrap=True)
    cmds.showWindow(w)
    return w
