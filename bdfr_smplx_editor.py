"""BDFR v0.4 SMPL-X parametric editor for Maya.
Uses official SMPL-X weights via a separate Python process. Apply updates existing
mesh vertex positions in place (same topology), rather than importing duplicates.
"""
import json
import math
import subprocess
from pathlib import Path
import maya.cmds as cmds
from maya.api import OpenMaya as om
from bdfr_smplx_maya import DEFAULT_MODELS, DEFAULT_PYTHON, ROOT, OUTPUT, load_config, save_config

WINDOW="BDFRSMPLXEditor04"
TARGET="BDFR_SMPLX_Character"
STATE={"gender":None}

def _read_vertices(obj):
    result=[]
    with open(obj,"r",encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("v "):
                parts=line.split()
                if len(parts)>=4:
                    result.append(om.MPoint(float(parts[1]),float(parts[2]),float(parts[3])))
    if len(result)!=10475:
        raise RuntimeError("Expected 10475 SMPL-X vertices; got {}".format(len(result)))
    return result

def _shape(transform):
    shapes=cmds.listRelatives(transform,shapes=True,noIntermediate=True,fullPath=True,type="mesh") or []
    if len(shapes)!=1:
        raise RuntimeError("SMPL-X target needs exactly one active polygon mesh")
    selection=om.MSelectionList()
    selection.add(shapes[0])
    return om.MFnMesh(selection.getDagPath(0))

def evaluate(python_path, model_dir, gender, betas, shoulder, elbow, hand, smile):
    # Axis-angle pose angles in radians. No claim of anatomically correct muscle sliders.
    body=[0.0]*63
    # Standard SMPL-X body joints: shoulders 15,16; elbows 17,18.
    body[15*3+2]=math.radians(shoulder)
    body[16*3+2]=-math.radians(shoulder)
    body[17*3+1]=math.radians(elbow)
    body[18*3+1]=-math.radians(elbow)
    left=[0.0]*45
    right=[0.0]*45
    for i in range(0,45,3):
        left[i]=math.radians(hand)
        right[i]=math.radians(hand)
    expression=[smile]+[0.0]*9
    args=[str(python_path),str(ROOT/"smplx_export.py"),
          "--models",str(model_dir),"--out",str(OUTPUT),
          "--gender",gender,"--betas"]+[str(v) for v in betas]
    args+=["--body-pose"]+[str(v) for v in body]
    args+=["--left-hand"]+[str(v) for v in left]
    args+=["--right-hand"]+[str(v) for v in right]
    args+=["--expression"]+[str(v) for v in expression]
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    process=subprocess.run(args,capture_output=True,text=True,timeout=300)
    if process.returncode:
        raise RuntimeError("SMPL-X evaluation failed:\n"+(process.stderr or process.stdout)[-3500:])
    return _read_vertices(OUTPUT)

def apply(python_path, model_dir, gender, betas, shoulder=0,elbow=0,hand=0,smile=0):
    if not Path(python_path).is_file():
        raise FileNotFoundError("External Python not found; run setup_smplx_windows.ps1 first.")
    if not Path(model_dir).is_dir():
        raise FileNotFoundError("SMPL-X weights folder not found.")
    evaluate(python_path,model_dir,gender,betas,shoulder,elbow,hand,smile)
    return apply_exported(gender)

def apply_exported(gender):
    """Main-thread only; consume OBJ produced by a completed external evaluation."""
    verts=_read_vertices(OUTPUT)
    # Import through Maya only on the first evaluation; subsequent calls update mesh points.
    if cmds.objExists(TARGET):
        if STATE["gender"] not in (None,gender):
            raise RuntimeError("Changing gender requires removing current target; use New Character.")
        fn=_shape(TARGET)
        if fn.numVertices!=len(verts):
            raise RuntimeError("Topology mismatch: refusing to overwrite existing mesh.")
        fn.setPoints(verts,om.MSpace.kObject)
        cmds.setAttr(TARGET+".translateY",0)
        bbox=cmds.exactWorldBoundingBox(TARGET)
        cmds.move(0,-bbox[1],0,TARGET,relative=True,worldSpace=True)
        cmds.refresh(force=True)
    else:
        # Use the previously confirmed working OBJ import pipeline.
        cmds.loadPlugin("objExport",quiet=True)
        before=set(cmds.ls(type="mesh",long=True) or [])
        cmds.file(str(OUTPUT),i=True,type="OBJ",ignoreVersion=True,
                  namespace="BDFRSMPLX",mergeNamespacesOnClash=True,
                  options="mo=1",preserveReferences=True)
        added=list(set(cmds.ls(type="mesh",long=True) or [])-before)
        if len(added)!=1:
            raise RuntimeError("Expected exactly one SMPL-X mesh; found {}".format(len(added)))
        transform=cmds.listRelatives(added[0],parent=True,fullPath=True)[0]
        transform=cmds.rename(transform,TARGET)
        cmds.setAttr(transform+".scale",100,100,100,type="double3")
        bbox=cmds.exactWorldBoundingBox(transform)
        cmds.move(0,-bbox[1],0,transform,relative=True,worldSpace=True)
    STATE["gender"]=gender
    cmds.select(TARGET,replace=True)
    return TARGET

def launch():
    if cmds.window(WINDOW,exists=True):
        cmds.deleteUI(WINDOW)
    cfg=load_config()
    win=cmds.window(WINDOW,title="BDFR SMPL-X Parametric Editor v0.4 Live",
                    sizeable=True,widthHeight=(490,625))
    cmds.scrollLayout(childResizable=True)
    cmds.columnLayout(adjustableColumn=True,rowSpacing=7)
    cmds.text(label="SMPL-X | Body / Hands / Expression",font="boldLabelFont",height=36)
    cmds.text(label="Shape changes run asynchronously; last slider state wins.")
    py=cmds.textFieldGrp(label="Python",text=cfg.get("python") or str(DEFAULT_PYTHON))
    models=cmds.textFieldGrp(label="Model weights",text=cfg.get("models") or str(DEFAULT_MODELS))
    option=cmds.optionMenu(label="Body model")
    for label in ("neutral","male","female"):
        cmds.menuItem(label=label)
    cmds.separator(style="in")
    slider_labels=["Gender Characteristics","Body Fatness","Abdominal Volume","Body Stature","Body Build","Hip & Pelvis Shape","Lower Body Proportions","Upper Body Proportions","Waist-to-Hip Shape","Torso Contour"]
    sliders=[]
    for i in range(10):
        control=cmds.floatSliderGrp(label="%02d %s"%(i+1,slider_labels[i]),field=True,
                                    minValue=-3,maxValue=3,value=0)
        sliders.append(control)
    cmds.separator(style="in")
    shoulder=cmds.floatSliderGrp(label="Shoulder pose",field=True,minValue=-30,maxValue=30,value=0)
    elbow=cmds.floatSliderGrp(label="Elbow pose",field=True,minValue=-60,maxValue=60,value=0)
    hand=cmds.floatSliderGrp(label="Finger curl",field=True,minValue=0,maxValue=45,value=0)
    smile=cmds.floatSliderGrp(label="Expression coef 1",field=True,minValue=-2,maxValue=2,value=0)
    def values():
        return ([cmds.floatSliderGrp(s,q=True,value=True) for s in sliders],
                cmds.floatSliderGrp(shoulder,q=True,value=True),
                cmds.floatSliderGrp(elbow,q=True,value=True),
                cmds.floatSliderGrp(hand,q=True,value=True),
                cmds.floatSliderGrp(smile,q=True,value=True))
    def call(new=False):
        p=cmds.textFieldGrp(py,q=True,text=True)
        m=cmds.textFieldGrp(models,q=True,text=True)
        g=cmds.optionMenu(option,q=True,value=True)
        save_config(p,m)
        if new and cmds.objExists(TARGET):
            cmds.delete(TARGET)
            STATE["gender"]=None
        beta,s,e,h,ex=values()
        try:
            apply(p,m,g,beta,s,e,h,ex)
            print("[BDFR] SMPL-X parametric update succeeded:",g)
        except Exception as err:
            cmds.confirmDialog(title="BDFR SMPL-X error",message=str(err),button=["OK"])
            raise
    # QProcess worker: model evaluation never blocks Maya's UI thread.
    from bdfr_smplx_live import LiveController
    live=LiveController(WINDOW,
        lambda: {
            "python":cmds.textFieldGrp(py,q=True,text=True),
            "models":cmds.textFieldGrp(models,q=True,text=True),
            "gender":cmds.optionMenu(option,q=True,value=True),
            "betas":values()[0],
            "shoulder":values()[1],
            "elbow":values()[2],
            "hand":values()[3],
            "expression":values()[4]})
    STATE["live_controller"]=live
    for control in sliders+[shoulder,elbow,hand,smile]:
        cmds.floatSliderGrp(control,e=True,dragCommand=lambda *_:live.schedule(),
                            changeCommand=lambda *_:live.schedule())
    cmds.optionMenu(option,e=True,changeCommand=lambda *_:live.schedule())
    cmds.text(label="Live enabled: edits trigger a 200ms debounced asynchronous refresh.")
    cmds.button(label="APPLY TO EXISTING CHARACTER",height=42,command=lambda *_:call(False))
    cmds.button(label="NEW CHARACTER / CHANGE GENDER",height=34,command=lambda *_:call(True))
    cmds.text(label="10 shape coefficients are PCA dimensions, not labeled anatomical controls.")
    cmds.text(label="First expression coefficient is not guaranteed to be a smile.")
    cmds.text(label="Beta names are observed tendencies, not isolated anatomical controls.")
    cmds.showWindow(win)
    return win
