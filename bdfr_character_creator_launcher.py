"""BDFR Character Creator — engine selection before mesh generation.

SMPL-X keeps its established editor. The alternative uses the already present
official MakeHuman CC0 base-mesh import path (early experimental Game Character mode).
No claim of finished game-ready anatomy, LODs, UVs, skinning or Unreal retargeting.
"""
import maya.cmds as cmds

WINDOW="BDFRCharacterCreatorEngineSelect"
PAGES={"smplx":"SMPL-X Parametric","game":"BDFR Game Character (MakeHuman foundation)","hg":"Human Generator 4.0.26 (Blender Bridge)"}

def launch():
    if cmds.window(WINDOW,exists=True):
        cmds.deleteUI(WINDOW)
    win=cmds.window(WINDOW,title="BDFR AI Character Creator | Choose Modeling Engine",
                    sizeable=True,widthHeight=(620,510))
    cmds.columnLayout(adjustableColumn=True,rowSpacing=13)
    cmds.text(label="STEP 1 OF 2   —   SELECT MODELING ENGINE",
              font="boldLabelFont",height=36,align="center")
    cmds.text(label="Modeling engine",align="left")
    selector=cmds.radioCollection()
    options=[]
    for label in ("SMPL-X", "Game Character (MakeHuman)", "Human Generator (Blender 4.4)", "BDFR Native Human (Standalone Alpha)"):
        options.append(cmds.radioButton(label=label,select=(len(options)==0)))
    def selected_engine():
        for index,control in enumerate(options,1):
            if cmds.radioButton(control,q=True,select=True):
                return index
        raise RuntimeError("No modeling engine selected")
    note=cmds.text(label="SMPL-X: existing parametric body/pose editor.",
                   align="center",wordWrap=True,height=60)
    def refresh(*_):
        selected=selected_engine()
        if selected==1:
            cmds.text(note,e=True,label="SMPL-X: existing Live editor, betas, pose and body-joint guide. Original workflow stays intact.")
        elif selected==2:
            cmds.text(note,e=True,label="Game Character: CC0 MakeHuman base import foundation. Advanced morphs and rig still in development.")
        elif selected==3:
            cmds.text(note,e=True,label="Human Generator: Blender 4.4.3 bridge. Export an existing HG character from a saved .blend file to Maya FBX.")
        else:
            cmds.text(note,e=True,label="BDFR Native Human: standalone Maya morph library. No Human Generator or Blender required.")
    for item in options:
        cmds.radioButton(item,e=True,onCommand=refresh)
    cmds.separator(style="in")
    cmds.text(label="STEP 2 opens the appropriate modeling workspace. Engines use separate meshes.",
              align="center",wordWrap=True)
    def next_step(*_):
        selected=selected_engine()
        try:
            if selected==1:
                import bdfr_smplx_editor
                bdfr_smplx_editor.launch()
            elif selected==2:
                import bdfr_makehuman_auto
                bdfr_makehuman_auto.launch()
            elif selected==3:
                import bdfr_hg_maya_bridge
                bdfr_hg_maya_bridge.launch()
            else:
                import bdfr_native_human
                bdfr_native_human.launch()
            cmds.deleteUI(win)
        except Exception as err:
            cmds.confirmDialog(title="Engine launch failed",message=str(err),button=["OK"])
            raise
    cmds.button(label="NEXT  —  OPEN MODELING WORKSPACE",height=47,command=next_step)
    cmds.text(label="Native Human is an independent Maya alpha; original engines remain available.",
              align="center")
    cmds.showWindow(win)
    return win
