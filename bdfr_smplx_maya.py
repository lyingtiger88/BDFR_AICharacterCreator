"""Maya front-end to the official SMPL-X implementation, with persistent paths.
Does not redistribute licensed model weights.
"""
import json
import os
import subprocess
import sys
import shutil
from pathlib import Path
import maya.cmds as cmds

ROOT=Path(__file__).resolve().parent
CONFIG=Path.home()/ "Documents"/"BDFR_AICharacterCreator"/"smplx_settings.json"
DEFAULT_MODELS=ROOT/"models"/"smplx"
DEFAULT_PYTHON=ROOT/".venv_smplx"/"Scripts"/"python.exe"
OUTPUT=Path.home()/ "Documents"/"BDFR_AICharacterCreator"/"generated"/"smplx_character.obj"

def load_config():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (ValueError,OSError):
        return {"python":str(DEFAULT_PYTHON) if DEFAULT_PYTHON.is_file() else (shutil.which("python") or ""), "models":str(DEFAULT_MODELS)}

def save_config(python_path, model_path):
    CONFIG.parent.mkdir(parents=True,exist_ok=True)
    CONFIG.write_text(json.dumps({"python":python_path,"models":model_path},
                                 indent=2),encoding="utf-8")

def run(python_path, model_path, gender="neutral", betas=None):
    interpreter=Path(python_path).expanduser()
    model_dir=Path(model_path).expanduser()
    if not model_dir.is_dir() and DEFAULT_MODELS.is_dir():
        model_dir=DEFAULT_MODELS
    if not interpreter.is_file():
        raise FileNotFoundError("Choose the external Python executable with torch and smplx installed.")
    if not model_dir.is_dir():
        raise FileNotFoundError("Choose folder with your licensed SMPL-X model files.")
    filename="SMPLX_"+gender.upper()
    weights=list(model_dir.rglob(filename+".npz"))+list(model_dir.rglob(filename+".pkl"))
    if gender=="neutral":
        weights+=list(model_dir.rglob("SMPLX_NEUTRAL_2020.npz"))
    if not weights:
        raise FileNotFoundError(filename+" model not found in the configured folder.")
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    command=[str(interpreter),str(ROOT/"smplx_export.py"),"--models",str(model_dir),
             "--out",str(OUTPUT),"--gender",gender]
    if betas:
        command+=["--betas"]+[str(float(x)) for x in betas]
    p=subprocess.run(command,text=True,capture_output=True,timeout=300)
    if p.returncode:
        raise RuntimeError("SMPL-X export failed:\n"+(p.stderr or p.stdout)[-2500:])
    before=set(cmds.ls(type="mesh",long=True) or [])
    cmds.loadPlugin("objExport",quiet=True)
    cmds.file(str(OUTPUT),i=True,type="OBJ",ignoreVersion=True,
              namespace="BDFRSMPLX",mergeNamespacesOnClash=True,
              options="mo=1",preserveReferences=True)
    after=set(cmds.ls(type="mesh",long=True) or [])
    new_shapes=list(after-before)
    if not new_shapes:
        raise RuntimeError("SMPL-X exported an OBJ but Maya imported no mesh.")
    transforms=list({cmds.listRelatives(s,parent=True,fullPath=True)[0] for s in new_shapes})
    for node in transforms:
        # SMPL-X uses meters, Maya default is centimeters.
        cmds.setAttr(node+".scale",100,100,100,type="double3")
    # Align the lowest point of the character with Maya's ground plane.
    # OBJ imports and source shapes may have varying vertical offsets.
    bounds=[cmds.exactWorldBoundingBox(node) for node in transforms]
    lowest_y=min(b[1] for b in bounds)
    for node in transforms:
        cmds.move(0.0,-lowest_y,0.0,node,relative=True,worldSpace=True)
    print("[BDFR SMPL-X] Ground aligned; previous minimum Y =",lowest_y)
    cmds.select(transforms,r=True)
    cmds.viewFit()
    return {"meshes":transforms,"output":str(OUTPUT)}

def launch():
    cfg=load_config()
    win="BDFRSMPLXWindow"
    if cmds.window(win,exists=True):cmds.deleteUI(win)
    window=cmds.window(win,title="BDFR SMPL-X Engine v0.3.5",widthHeight=(500,310))
    cmds.columnLayout(adjustableColumn=True,rowSpacing=10)
    cmds.text(label="SMPL-X | Full Body, Face & Hands",height=34,font="boldLabelFont")
    python_field=cmds.textFieldButtonGrp(label="External Python",text=cfg.get("python",""),
                                         buttonLabel="Browse",adjustableColumn=2)
    models_field=cmds.textFieldButtonGrp(label="Licensed weights",text=cfg.get("models","") or str(DEFAULT_MODELS),
                                         buttonLabel="Browse",adjustableColumn=2)
    def browse_python(*_):
        f=cmds.fileDialog2(fileMode=1,caption="Choose Python executable")
        if f:cmds.textFieldButtonGrp(python_field,e=True,text=f[0])
    def browse_models(*_):
        f=cmds.fileDialog2(fileMode=3,caption="Choose licensed SMPL-X model folder")
        if f:cmds.textFieldButtonGrp(models_field,e=True,text=f[0])
    cmds.textFieldButtonGrp(python_field,e=True,buttonCommand=browse_python)
    cmds.textFieldButtonGrp(models_field,e=True,buttonCommand=browse_models)
    gender=cmds.optionMenu(label="SMPL-X base model")
    for n in ("neutral","female","male"):cmds.menuItem(label=n)
    def generate(*_):
        py=cmds.textFieldButtonGrp(python_field,q=True,text=True)
        models=cmds.textFieldButtonGrp(models_field,q=True,text=True)
        save_config(py,models)
        try:
            result=run(py,models,cmds.optionMenu(gender,q=True,value=True))
            cmds.confirmDialog(title="SMPL-X ready",message="Imported: "+str(result["meshes"]),
                               button=["OK"])
        except Exception as e:
            cmds.confirmDialog(title="SMPL-X error",message=str(e),button=["OK"])
            raise
    cmds.button(label="GENERATE REAL SMPL-X BODY",height=45,command=generate)
    cmds.text(label="The first setup needs your licensed model files; paths are saved.",align="center")
    cmds.text(label="This exports a neutral pose mesh; rigging and photo fitting are not yet connected.")
    cmds.showWindow(window)
    return window
