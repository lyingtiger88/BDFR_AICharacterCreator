"""BDFR AI Character Creator — unified Maya entry point.

Default: native editor. Optional legacy engines live under Advanced Tools.
No external imports happen until the corresponding button is pressed.
"""
import maya.cmds as cmds

WINDOW = "BDFRCharacterCreatorEngineSelect"

def _open(module_name, window):
    import importlib
    try:
        module = importlib.import_module(module_name)
        module.launch()
    except Exception as exc:
        cmds.confirmDialog(title="BDFR — Unable to open tool",
                           message=str(exc)[-1500:], button=["OK"])
        cmds.warning("[BDFR] "+str(exc))
        return
    if cmds.window(window, exists=True):
        cmds.deleteUI(window)

def launch():
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    win = cmds.window(WINDOW,title="BDFR AI Character Creator",
                      widthHeight=(540,400),sizeable=True)
    cmds.columnLayout(adjustableColumn=True,rowSpacing=12)
    cmds.text(label="BDFR AI CHARACTER CREATOR",
              font="boldLabelFont",height=48,align="center")
    cmds.text(label="Create and edit characters in Maya",
              align="center",height=22)
    cmds.separator(style="in")
    cmds.button(label="CREATE CHARACTER",height=54,
                annotation="Open BDFR Native Human editor",
                command=lambda *_:_open("bdfr_native_human",win))
    def open_existing(*_):
        # Maya scene import/open uses native file picker; do not overwrite
        # the current scene or silently discard unsaved work.
        try:
            files=cmds.fileDialog2(fileMode=1,caption="Open Character Maya Scene",
                                   fileFilter="Maya Files (*.ma *.mb)")
            if not files:return
            cmds.file(files[0],open=True,force=False,prompt=True)
        except Exception as exc:
            cmds.confirmDialog(title="Open Character",message=str(exc)[-1500:],button=["OK"])
    cmds.button(label="OPEN CHARACTER SCENE",height=48,command=open_existing)
    cmds.separator(style="in")
    cmds.frameLayout(label="ADVANCED / DEVELOPMENT TOOLS",
                     collapsable=True,collapse=True,marginHeight=10,marginWidth=10)
    cmds.columnLayout(adjustableColumn=True,rowSpacing=7)
    cmds.button(label="SMPL-X Parametric Editor",
                command=lambda *_:_open("bdfr_smplx_editor",win))
    cmds.button(label="Game Character / MakeHuman Base Loader",
                command=lambda *_:_open("bdfr_makehuman_auto",win))
    cmds.button(label="Human Generator — Blender Bridge",
                command=lambda *_:_open("bdfr_hg_maya_bridge",win))
    cmds.button(label="BDFR Native Human Morph Lab",
                command=lambda *_:_open("bdfr_native_human",win))
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.text(label="Native editor is an early alpha. Full character authoring features are in development.",
              wordWrap=True,align="center",height=38)
    cmds.showWindow(win)
    return win
