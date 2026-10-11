"""BDFR AI Character Creator — select modeling engine (restored).

Four development modeling engines remain separate; this is the familiar
selection menu, not the experimental unified Create/Open home screen.
"""
import maya.cmds as cmds

WINDOW = "BDFRCharacterCreatorEngineSelect"

ENGINES = (
    ("SMPL-X", "bdfr_smplx_editor",
     "SMPL-X parametric modeling and joint guide."),
    ("Game Character (MakeHuman)", "bdfr_makehuman_auto",
     "MakeHuman-based CC0 game character base mesh."),
    ("Human Generator (Blender Bridge)", "bdfr_hg_maya_bridge",
     "Human Generator Blender-to-Maya character bridge."),
    ("BDFR Native Human (Standalone Alpha)", "bdfr_native_human",
     "Experimental standalone Maya mesh and Morph authoring."),
)

def launch():
    if cmds.window(WINDOW,exists=True):
        cmds.deleteUI(WINDOW)
    win=cmds.window(WINDOW,title="BDFR AI Character Creator | Modeling Engines",
                    sizeable=True,widthHeight=(620,450))
    cmds.columnLayout(adjustableColumn=True,rowSpacing=10)
    cmds.text(label="SELECT MODELING ENGINE",
              font="boldLabelFont",align="center",height=38)
    cmds.text(label="Choose which character modeling workflow to open.",
              align="center",height=25)
    cmds.separator(style="in")
    collection=cmds.radioCollection()
    buttons=[]
    for index,(label,_,description) in enumerate(ENGINES):
        buttons.append(cmds.radioButton(label=label,select=index==0))
    note=cmds.text(label=ENGINES[0][2],align="center",wordWrap=True,height=55)

    def selection():
        for i,button in enumerate(buttons):
            if cmds.radioButton(button,q=True,select=True):
                return i
        raise RuntimeError("Select a modeling engine first")

    def refresh(*_):
        cmds.text(note,e=True,label=ENGINES[selection()][2])
    for button in buttons:
        cmds.radioButton(button,e=True,onCommand=refresh)

    cmds.separator(style="in")

    def next_step(*_):
        import importlib
        module_name=ENGINES[selection()][1]
        try:
            module=importlib.import_module(module_name)
            module.launch()
        except Exception as exc:
            cmds.confirmDialog(title="Engine launch failed",
                               message=str(exc)[-1500:],button=["OK"])
            cmds.warning("[BDFR] "+str(exc))
            return
        if cmds.window(win,exists=True):
            cmds.deleteUI(win)

    cmds.button(label="NEXT — OPEN MODELING WORKSPACE",
                height=48,command=next_step)
    cmds.text(label="All four engines are available; none has been removed.",
              align="center",height=25)
    cmds.showWindow(win)
    return win
