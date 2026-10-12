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
    if STATE.get("live_controller"):
        STATE["live_controller"].close()
        STATE["live_controller"]=None
    if cmds.window(WINDOW,exists=True):
        cmds.deleteUI(WINDOW)
    cfg=load_config()
    win=cmds.window(WINDOW,title="BDFR SMPL-X Parametric Editor v0.5.0 Skeleton Guide",
                    sizeable=True,widthHeight=(490,625))
    cmds.scrollLayout(childResizable=True)
    cmds.columnLayout(adjustableColumn=True,rowSpacing=7)
    cmds.text(label="SMPL-X | Body / Hands / Expression",font="boldLabelFont",height=36)
    cmds.text(label="STEP 1: Check Python and model weights below. STEP 2: Create your character.")
    create_button=cmds.button(label="CREATE SMPL-X CHARACTER IN MAYA",height=48)
    cmds.text(label="The character appears in the Maya viewport after generation.",
              wordWrap=True,align="center")
    cmds.text(label="Shape changes run asynchronously; last slider state wins.")
    py=cmds.textFieldGrp(label="Python",text=cfg.get("python") or str(DEFAULT_PYTHON))
    models=cmds.textFieldGrp(label="Model weights",text=cfg.get("models") or str(DEFAULT_MODELS))
    option=cmds.optionMenu(label="Body model")
    for label in ("neutral","male","female"):
        cmds.menuItem(label=label)
    cmds.separator(style="in")
    cmds.text(label="MAIN BODY CONTROLS",font="boldLabelFont")
    cmds.text(label="Sculpted morph targets only (no automatic balloon deformation)")
    cmds.text(label="Beta controls below are learned shape components, not isolated body measurements.",wordWrap=True)
    breast=cmds.floatSliderGrp(label="Breast Size",field=True,minValue=-1,maxValue=1,value=0)
    hips=cmds.floatSliderGrp(label="Hip Width",field=True,minValue=-1,maxValue=1,value=0)
    glutes=cmds.floatSliderGrp(label="Glute Size",field=True,minValue=-1,maxValue=1,value=0)
    cmds.separator(style="in")
    cmds.text(label="ADVANCED DETAILS  |  SMPL-X Shape Betas",font="boldLabelFont")
    # SMPL-X betas are learned PCA coefficients, NOT independent anatomical controls.
    slider_labels=["PCA Shape Component {}".format(i+1) for i in range(10)]
    sliders=[]
    for i in range(10):
        control=cmds.floatSliderGrp(label="%02d %s"%(i+1,slider_labels[i]),field=True,
                                    minValue=-3,maxValue=3,value=0)
        sliders.append(control)
    cmds.separator(style="in")
    shoulder=cmds.floatSliderGrp(label="Shoulder pose",field=True,minValue=-60,maxValue=60,value=0)
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
        # Manual commands use the SAME asynchronous pipeline as live editing.
        # Avoid the legacy OBJ path silently discarding sculpt morphs.
        p=cmds.textFieldGrp(py,q=True,text=True)
        m=cmds.textFieldGrp(models,q=True,text=True)
        if not Path(p).is_file() or not Path(m).is_dir():
            cmds.confirmDialog(title="SMPL-X setup required",
                message="Check Python and Model weights paths before creating a character.",
                button=["OK"])
            return
        save_config(p,m)
        print("[BDFR SMPL-X] Create requested: model={}, weights={}".format(
            cmds.optionMenu(option,q=True,value=True),m))
        if new and cmds.objExists(TARGET):
            cmds.delete(TARGET)
            STATE["gender"]=None
        STATE["live_controller"].schedule()
    # QProcess worker: model evaluation never blocks Maya's UI thread.
    from bdfr_smplx_persistent import PersistentController
    live=PersistentController(WINDOW,
        lambda: {
            "python":cmds.textFieldGrp(py,q=True,text=True),
            "models":cmds.textFieldGrp(models,q=True,text=True),
            "gender":cmds.optionMenu(option,q=True,value=True),
            "betas":values()[0],
            "shoulder":values()[1],
            "elbow":values()[2],
            "hand":values()[3],
            "expression":values()[4],
            "breast_size":cmds.floatSliderGrp(breast,q=True,value=True),
            "hip_width":cmds.floatSliderGrp(hips,q=True,value=True),
            "glute_size":cmds.floatSliderGrp(glutes,q=True,value=True)})
    STATE["live_controller"]=live
    cmds.button(create_button,e=True,command=lambda *_:call(new=True))
    # Sculpt workflow. Capture a base, duplicate and sculpt the mesh (same
    # topology); save the sculpt as a sparse morph for this exact shape/pose.
    morph_state={"base":None,"reference":None,"folder":None}
    def mesh_points(node):
        fn=_shape(node)
        return [(p.x,p.y,p.z) for p in fn.getPoints(om.MSpace.kObject)]
    def ref_key():
        return live._shape_key(live.settings())
    def capture_base(*_):
        if not cmds.objExists(TARGET):
            cmds.warning("[BDFR Morph] Generate a character first")
            return
        if any(abs(v)>1e-8 for v in (cmds.floatSliderGrp(breast,q=True,value=True),
                cmds.floatSliderGrp(hips,q=True,value=True),
                cmds.floatSliderGrp(glutes,q=True,value=True))):
            cmds.warning("[BDFR Morph] Set all three detail sliders to zero first")
            return
        morph_state["base"]=mesh_points(TARGET)
        morph_state["reference"]=ref_key()
        print("[BDFR Morph] Base captured. Duplicate mesh, sculpt the duplicate, then capture sculpt.")
    def capture_sculpt(*_):
        from bdfr_morph_targets import author,save,load_folder
        if morph_state["base"] is None:
            cmds.warning("[BDFR Morph] Capture base first")
            return
        if ref_key()!=morph_state["reference"]:
            cmds.warning("[BDFR Morph] Shape or pose changed since base capture")
            return
        selected=cmds.ls(selection=True,type="transform",long=True) or []
        if len(selected)!=1 or selected[0].split("|")[-1]==TARGET:
            cmds.warning("[BDFR Morph] Select one separate sculpted mesh, NOT the live body")
            return
        key=cmds.optionMenu(morph_key,q=True,value=True)
        direction=cmds.optionMenu(morph_direction,q=True,value=True)
        folder=morph_state["folder"]
        if not folder:
            paths=cmds.fileDialog2(fileMode=3,caption="Choose morph library folder")
            if not paths:return
            folder=paths[0]
        try:
            from pathlib import Path
            import json
            folder_path=Path(folder)
            profile=folder_path/"reference.json"
            expected=list(morph_state["reference"])
            if profile.exists():
                saved=json.loads(profile.read_text(encoding="utf-8"))
                if saved.get("shape_key")!=json.loads(json.dumps(expected)):
                    raise ValueError("Folder reference differs: choose another folder")
            morph=author(morph_state["base"],mesh_points(selected[0]),key,direction)
            save(folder_path/(key+"_"+direction+".json"),morph)
            if not profile.exists():
                profile.write_text(json.dumps({"shape_key":expected}),encoding="utf-8")
            morph_state["folder"]=folder
            live.install_library(load_folder(folder),morph_state["reference"])
            print("[BDFR Morph] Saved",key,direction,"vertices",len(morph["offsets"]))
        except Exception as exc:
            cmds.warning("[BDFR Morph] "+str(exc))
    def load_morphs(*_):
        from bdfr_morph_targets import load_folder
        import json
        from pathlib import Path
        paths=cmds.fileDialog2(fileMode=3,caption="Load sculpted morph library")
        if not paths:return
        folder=Path(paths[0])
        try:
            reference=json.loads((folder/"reference.json").read_text(encoding="utf-8"))["shape_key"]
            # JSON arrays need recursive tuple conversion.
            key=(reference[0],tuple(reference[1]),*reference[2:])
            if key!=ref_key():
                raise ValueError("Morph library reference does not match current shape / pose")
            library=load_folder(folder)
            live.install_library(library,key)
            morph_state["folder"]=str(folder)
            print("[BDFR Morph] Loaded",len(library),"sculpted targets")
        except Exception as exc:
            cmds.warning("[BDFR Morph] "+str(exc))
    cmds.text(label="MORPH AUTHORING  |  Artist sculpt required",font="boldLabelFont")
    cmds.rowLayout(numberOfColumns=2,adjustableColumn=1,columnWidth2=(235,235))
    cmds.button(label="1. CAPTURE BASE",command=capture_base)
    cmds.button(label="2. LOAD MORPH LIBRARY",command=load_morphs)
    cmds.setParent("..")
    morph_key=cmds.optionMenu(label="Sculpt channel")
    for name in ("breast_size","hip_width","glute_size"):
        cmds.menuItem(label=name)
    morph_direction=cmds.optionMenu(label="Sculpt direction")
    for name in ("positive","negative"):
        cmds.menuItem(label=name)
    cmds.button(label="3. CAPTURE SELECTED SCULPT",height=32,command=capture_sculpt)

    for control in [breast,hips,glutes]+sliders+[shoulder,elbow,hand,smile]:
        cmds.floatSliderGrp(control,e=True,dragCommand=lambda *_:live.schedule(),
                            changeCommand=lambda *_:live.schedule())
    cmds.optionMenu(option,e=True,changeCommand=lambda *_:live.schedule())
    # SMPL-X shoulder Z axis-axis-angle approximates an A-pose with
    # arms descending from the template position. Keep it editable.
    def apply_unreal_a_pose(*_):
        cmds.floatSliderGrp(shoulder,e=True,value=-35.0)
        cmds.floatSliderGrp(elbow,e=True,value=0.0)
        cmds.floatSliderGrp(hand,e=True,value=0.0)
        live.schedule()
        print("[BDFR] Unreal-style A-Pose requested: shoulders -35 degrees")
    def reset_pose(*_):
        cmds.floatSliderGrp(shoulder,e=True,value=0.0)
        cmds.floatSliderGrp(elbow,e=True,value=0.0)
        cmds.floatSliderGrp(hand,e=True,value=0.0)
        live.schedule()
        print("[BDFR] Rest pose requested")
    cmds.text(label="SKELETON  |  SMPL-X Body Joint Guide",font="boldLabelFont")
    def create_joint_guide(*_):
        from bdfr_smplx_skeleton import build
        if live.last_joints is None:
            cmds.warning("[BDFR] Change a slider or press Apply to evaluate SMPL-X joints first.")
            return
        try:
            group=build(live.last_joints,TARGET)
            print("[BDFR] SMPL-X joint guide created:",group)
        except Exception as exc:
            cmds.warning("[BDFR Skeleton] "+str(exc))
    def toggle_joint_guide(*_):
        from bdfr_smplx_skeleton import GROUP
        if cmds.objExists(GROUP):
            cmds.setAttr(GROUP+".visibility",not cmds.getAttr(GROUP+".visibility"))
    cmds.rowLayout(numberOfColumns=2,adjustableColumn=1,columnWidth2=(235,235))
    cmds.button(label="GENERATE SKELETON GUIDE",height=33,command=create_joint_guide)
    cmds.button(label="SHOW / HIDE SKELETON",height=33,command=toggle_joint_guide)
    cmds.setParent("..")
    cmds.text(label="POSE PRESETS  |  Unreal-style A-Pose (preview only)",font="boldLabelFont")
    cmds.rowLayout(numberOfColumns=2,adjustableColumn=1,columnWidth2=(235,235))
    cmds.button(label="UNREAL A-POSE",height=34,command=apply_unreal_a_pose)
    cmds.button(label="RESET REST POSE",height=34,command=reset_pose)
    cmds.setParent("..")

    def snapshot():
        betas,sh,el,ha,ex=values()
        return {"schema":1,"gender":cmds.optionMenu(option,q=True,value=True),
                "betas":betas,"shoulder":sh,"elbow":el,"hand":ha,
                "expression":ex,
                "breast_size":cmds.floatSliderGrp(breast,q=True,value=True),
                "hip_width":cmds.floatSliderGrp(hips,q=True,value=True),
                "glute_size":cmds.floatSliderGrp(glutes,q=True,value=True)}
    def save_preset(*_):
        from bdfr_character_presets import save
        paths=cmds.fileDialog2(fileMode=0,fileFilter="BDFR Character (*.json)",
                              caption="Save character parameters")
        if paths:
            try:
                save(paths[0],snapshot())
                print("[BDFR] Saved character preset:",paths[0])
            except Exception as exc:
                cmds.confirmDialog(title="Preset error",message=str(exc),button=["OK"])
    def load_preset(*_):
        from bdfr_character_presets import load
        paths=cmds.fileDialog2(fileMode=1,fileFilter="BDFR Character (*.json)",
                              caption="Load character parameters")
        if not paths:return
        try:
            data=load(paths[0])  # Fully validate before changing any control
            live.timer.stop()
            for control,key in ((breast,"breast_size"),(hips,"hip_width"),(glutes,"glute_size")):
                cmds.floatSliderGrp(control,e=True,value=data[key])
            for slider,value in zip(sliders,data["betas"]):
                cmds.floatSliderGrp(slider,e=True,value=value)
            for control,key in ((shoulder,"shoulder"),(elbow,"elbow"),
                                (hand,"hand"),(smile,"expression")):
                cmds.floatSliderGrp(control,e=True,value=data[key])
            cmds.optionMenu(option,e=True,value=data["gender"])
            live.schedule()
            print("[BDFR] Loaded preset:",paths[0])
        except Exception as exc:
            cmds.confirmDialog(title="Preset error",message=str(exc),button=["OK"])
    cmds.rowLayout(numberOfColumns=2,adjustableColumn=1,columnWidth2=(235,235))
    cmds.button(label="SAVE CHARACTER PRESET",command=save_preset,height=30)
    cmds.button(label="LOAD CHARACTER PRESET",command=load_preset,height=30)
    cmds.setParent("..")
    cmds.text(label="Live enabled: edits trigger a 90ms debounce; SMPL-X weights stay loaded in external Python.")
    cmds.button(label="APPLY TO EXISTING CHARACTER",height=42,command=lambda *_:call(False))
    cmds.button(label="NEW CHARACTER / CHANGE GENDER",height=34,command=lambda *_:call(True))
    cmds.text(label="Detail sliders require matching artist-sculpted morphs; otherwise no-op.")
    cmds.text(label="10 shape coefficients are PCA dimensions, not labeled anatomical controls.")
    cmds.text(label="First expression coefficient is not guaranteed to be a smile.")
    cmds.text(label="Use CREATE SMPL-X CHARACTER above to generate the initial mesh.")
    cmds.showWindow(win)
    return win
