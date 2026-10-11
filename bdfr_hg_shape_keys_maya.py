"""Maya panel for Blender-native shape keys in installed HG scenes."""
import json, subprocess, tempfile
from pathlib import Path
import maya.cmds as cmds

WINDOW="BDFRHGShapeKeys"
SCRIPT=Path(__file__).resolve().parent/"bdfr_hg_shape_keys_blender.py"

def inspect(blender,blend):
    if not Path(blend).is_file():raise FileNotFoundError(blend)
    with tempfile.TemporaryDirectory() as folder:
        report=Path(folder)/"shape_keys.json"
        proc=subprocess.run([blender,"-b",blend,"--python",str(SCRIPT),"--",
                             "--list",str(report)],capture_output=True,text=True,timeout=180)
        if proc.returncode or not report.exists():
            raise RuntimeError((proc.stdout+"\n"+proc.stderr)[-2500:])
        return json.loads(report.read_text(encoding="utf-8"))["meshes"]

def export(blender,blend,changes,output):
    if not str(output).lower().endswith(".fbx"):raise ValueError("FBX path required")
    with tempfile.TemporaryDirectory() as folder:
        changes_path=Path(folder)/"changes.json"
        report=Path(folder)/"report.json"
        changes_path.write_text(json.dumps(changes),encoding="utf-8")
        proc=subprocess.run([blender,"-b",blend,"--python",str(SCRIPT),"--",
             "--list",str(report),"--changes",str(changes_path),"--out",output],
             capture_output=True,text=True,timeout=360)
        if proc.returncode or not Path(output).is_file():
            raise RuntimeError((proc.stdout+"\n"+proc.stderr)[-2500:])
    return output

def launch(blender="",blend=""):
    from bdfr_hg_maya_bridge import _find_blender
    if cmds.window(WINDOW,exists=True):cmds.deleteUI(WINDOW)
    win=cmds.window(WINDOW,title="Human Generator | Blender Shape Key Controls",
                    widthHeight=(570,630),sizeable=True)
    cmds.columnLayout(adjustableColumn=True,rowSpacing=7)
    cmds.text(label="NATIVE BLENDER SHAPE KEYS — OPTIONAL HG CONTROLS",
              font="boldLabelFont",height=35)
    cmds.text(label="Scan, then BIND to HG_Body to activate realtime Maya blendShape sliders.",
              align="center",wordWrap=True)
    exe=cmds.textFieldGrp(label="Blender",text=blender or _find_blender())
    source=cmds.textFieldGrp(label="Blend file",text=blend)
    output=cmds.textFieldGrp(label="Export FBX",
         text=str(Path.home()/"Documents"/"BDFR_HG_ShapeKey_Preview.fbx"))
    status=cmds.text(label="Inspect a saved Blender character to discover shape keys.")
    scroll=cmds.scrollLayout(childResizable=True,height=360)
    content=cmds.columnLayout(adjustableColumn=True)
    controls={}
    native={}
    def update_maya(obj,key,slider):
        binding=native.get((obj,key))
        if not binding:return
        node,alias,low,high=binding
        if not cmds.objExists(node):return
        value=cmds.floatSliderGrp(slider,q=True,value=True)
        cmds.setAttr(node+"."+alias,max(low,min(high,value)))
    def read(*_):
        for child in cmds.columnLayout(content,q=True,childArray=True) or []:
            cmds.deleteUI(child)
        controls.clear()
        try:
            data=inspect(cmds.textFieldGrp(exe,q=True,text=True),
                         cmds.textFieldGrp(source,q=True,text=True))
            cmds.setParent(content)
            for obj,keys in data.items():
                cmds.text(label=obj,font="boldLabelFont",align="left")
                for item in keys:
                    slider=cmds.floatSliderGrp(label=item["name"],field=True,
                            minValue=item["min"],maxValue=item["max"],
                            fieldMinValue=item["min"],fieldMaxValue=item["max"],
                            value=item["value"])
                    controls[(obj,item["name"])]=slider
            for (obj,key),slider in controls.items():
                cmds.floatSliderGrp(slider,e=True,
                    dragCommand=lambda *_,o=obj,k=key,c=slider:update_maya(o,k,c),
                    changeCommand=lambda *_,o=obj,k=key,c=slider:update_maya(o,k,c))
            cmds.text(status,e=True,label="Found {} Blender shape keys. Bind to Maya to enable Live changes.".format(len(controls)))
        except Exception as err:
            cmds.warning("[BDFR HG ShapeKeys] "+str(err))
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.button(label="SCAN SHAPE KEYS IN SAVED BLEND FILE",height=34,command=read)
    def apply(*_):
        if not controls:
            cmds.warning("[BDFR] No Blender shape keys detected")
            return
        changes={}
        for (obj,key),slider in controls.items():
            changes.setdefault(obj,{})[key]=cmds.floatSliderGrp(slider,q=True,value=True)
        try:
            target=export(cmds.textFieldGrp(exe,q=True,text=True),
                          cmds.textFieldGrp(source,q=True,text=True),
                          changes,cmds.textFieldGrp(output,q=True,text=True))
            cmds.confirmDialog(title="FBX exported",message="Updated mesh exported to:\n"+
              target+"\nUse a NEW Maya scene to import the FBX; existing Maya mesh is unchanged.",
              button=["OK"])
        except Exception as err:
            cmds.confirmDialog(title="ShapeKey error",message=str(err)[-2000:],button=["OK"])
    def bind_live(*_):
        import bdfr_hg_maya_blendshapes
        try:
            found=bdfr_hg_maya_blendshapes.bind(
                cmds.textFieldGrp(exe,q=True,text=True).strip(),
                cmds.textFieldGrp(source,q=True,text=True).strip())
            native.clear()
            native.update(found)
            cmds.text(status,e=True,label="LIVE MAYA BLENDSHAPES: {} controls connected".format(len(found)))
            print("[BDFR HG] Bound {} live shape keys to HG_Body".format(len(found)))
            for (obj,key),control in controls.items():
                update_maya(obj,key,control)
        except Exception as err:
            cmds.confirmDialog(title="Maya BlendShape binding failed",
                message=str(err)[-2000:],button=["OK"])
            raise
    cmds.button(label="BIND SHAPE KEYS TO EXISTING MAYA HG_BODY (LIVE)",
                height=43,command=bind_live)
    cmds.button(label="EXPORT UPDATED SHAPE KEY MESH TO FBX",height=38,command=apply)
    cmds.showWindow(win)
    return win
