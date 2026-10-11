"""BDFR Character Creator — engine selection before mesh generation.

SMPL-X keeps its established editor. The alternative uses the already present
official MakeHuman CC0 base-mesh import path (early experimental Game Character mode).
No claim of finished game-ready anatomy, LODs, UVs, skinning or Unreal retargeting.
"""
import maya.cmds as cmds

WINDOW="BDFRCharacterCreatorEngineSelect"
PAGES={"smplx":"SMPL-X Parametric","game":"BDFR Game Character (MakeHuman foundation)"}

def launch():
    if cmds.window(WINDOW,exists=True):
        cmds.deleteUI(WINDOW)
    win=cmds.window(WINDOW,title="BDFR AI Character Creator | Choose Modeling Engine",
                    sizeable=True,widthHeight=(550,330))
    cmds.columnLayout(adjustableColumn=True,rowSpacing=13)
    cmds.text(label="STEP 1 OF 2   —   SELECT MODELING ENGINE",
              font="boldLabelFont",height=36,align="center")
    selector=cmds.radioButtonGrp(label="Modeling engine",numberOfRadioButtons=2,
        labelArray2=("SMPL-X","Game Character"),select=1,
        columnWidth3=(140,140,180))
    note=cmds.text(label="SMPL-X: existing parametric body/pose editor.",
                   align="center",wordWrap=True,height=60)
    def refresh(*_):
        selected=cmds.radioButtonGrp(selector,q=True,select=True)
        if selected==1:
            cmds.text(note,e=True,label="SMPL-X: existing Live editor, betas, pose and body-joint guide. Original workflow stays intact.")
        else:
            cmds.text(note,e=True,label="Game Character: CC0 MakeHuman base import foundation. Advanced morphs, topology refinement and rig are not implemented yet.")
    cmds.radioButtonGrp(selector,e=True,changeCommand=refresh)
    cmds.separator(style="in")
    cmds.text(label="STEP 2 opens the appropriate modeling workspace. Engines use separate meshes.",
              align="center",wordWrap=True)
    def next_step(*_):
        selected=cmds.radioButtonGrp(selector,q=True,select=True)
        try:
            if selected==1:
                import bdfr_smplx_editor
                bdfr_smplx_editor.launch()
            else:
                import bdfr_makehuman_auto
                bdfr_makehuman_auto.launch()
            cmds.deleteUI(win)
        except Exception as err:
            cmds.confirmDialog(title="Engine launch failed",message=str(err),button=["OK"])
            raise
    cmds.button(label="NEXT  —  OPEN MODELING WORKSPACE",height=47,command=next_step)
    cmds.text(label="Research-backed choice: keep SMPL-X, develop separate MakeHuman-based game workflow.",
              align="center")
    cmds.showWindow(win)
    return win
