"""Maya adapter for Blender 4.4 / Human Generator 4.0.26 authored assets.

Only subprocesses Blender's public command-line export and imports FBX. The user
must have Human Generator installed/licensed and a saved .blend character scene.
"""
from pathlib import Path
import subprocess
import json
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
    # Track only meshes from this import for safe fallback material assignment.
    before=set(cmds.ls(type="mesh",long=True) or [])
    cmds.file(str(fbx),i=True,type="FBX",ignoreVersion=True,
              mergeNamespacesOnClash=False,namespace="BDFRHumanGenerator",
              preserveReferences=True,options="fbx")
    after=set(cmds.ls(type="mesh",long=True) or [])
    return sorted(after-before)


def reconnect_materials(fbx, imported_shapes=None):
    """Reconnect extracted image maps to FBX-imported Maya materials."""
    report_path=Path(fbx).with_suffix(".json")
    if not report_path.is_file():return {"connected":0,"warnings":["Missing texture manifest"]}
    report=json.loads(report_path.read_text(encoding="utf-8"))
    entries=report.get("materials",{})
    found=cmds.ls(materials=True) or []
    connected=0
    warnings=list(report.get("texture_copy_failures",[]))
    imported_shapes=imported_shapes or []
    for original,info in entries.items():
        # Namespace prefixes are common after FBX import.
        matching=[n for n in found if n.split(":")[-1]==original]
        if not matching:
            # Single mesh/material FBX fallback: preserve all other scene shading.
            if len(entries)==1 and len(imported_shapes)==1:
                mat=cmds.shadingNode("lambert",asShader=True,name="BDFR_HG_Skin")
                sg=cmds.sets(renderable=True,noSurfaceShader=True,empty=True,name="BDFR_HG_SkinSG")
                cmds.connectAttr(mat+".outColor",sg+".surfaceShader",force=True)
                cmds.sets(imported_shapes[0],edit=True,forceElement=sg)
                matching=[mat]
            else:
                warnings.append("Maya material not found: "+original)
                continue
        mat=matching[-1]
        for channel,path in info.get("images",{}).items():
            if not Path(path).is_file():
                warnings.append("Texture file missing: "+path)
                continue
            target_attr={"base_color":("color","baseColor"),
                         "roughness":("specularRoughness","roughness"),
                         "metallic":("metalness","metallic"),
                         "normal":("normalCamera","normalCamera")}.get(channel)
            if not target_attr:continue
            attr=next((attr for attr in target_attr if cmds.attributeQuery(attr,node=mat,exists=True)),None)
            if not attr:
                warnings.append("Unsupported material channel: "+mat+"."+channel)
                continue
            name="BDFR_HG_"+channel.replace("_","")+"Texture"
            file_node=cmds.shadingNode("file",asTexture=True,name=name)
            place=cmds.shadingNode("place2dTexture",asUtility=True,name="BDFR_HG_place2d")
            for src,dst in (("outUV","uvCoord"),("outUvFilterSize","uvFilterSize")):
                cmds.connectAttr(place+"."+src,file_node+"."+dst,force=True)
            cmds.setAttr(file_node+".fileTextureName",str(Path(path).resolve()),type="string")
            if channel!="base_color" and cmds.attributeQuery("colorSpace",node=file_node,exists=True):
                try:cmds.setAttr(file_node+".colorSpace","Raw",type="string")
                except Exception:pass
            try:
                if channel=="normal":
                    # Correct RGB normal conversion requires a tangent-space normal node.
                    # Keep the map extracted, do not wire an RGB signal into a scalar bump input.
                    warnings.append("Normal texture exported, manual tangent-normal shader setup required for "+mat)
                    continue
                elif channel=="base_color":
                    cmds.connectAttr(file_node+".outColor",mat+"."+attr,force=True)
                else:
                    cmds.connectAttr(file_node+".outColorR",mat+"."+attr,force=True)
                connected+=1
            except Exception as exc:
                warnings.append(str(exc))
    return {"connected":connected,"warnings":warnings}


def apply_body_albedo(fbx=None, mesh="HG_Body"):
    """Assign a dedicated textured Lambert to the actual imported body mesh.

    Works on a previously imported scene, not only fresh FBX imports.
    Avoids assuming that FBX material names survive the Blender->Maya transfer.
    """
    roots=cmds.ls(mesh,type="transform",long=True) or []
    if not roots:
        roots=[node for node in (cmds.ls(type="transform",long=True) or [])
               if node.split("|")[-1].split(":")[-1]==mesh]
    roots=[node for node in roots if cmds.listRelatives(
        node,shapes=True,noIntermediate=True,type="mesh")]
    if len(roots)!=1:
        raise RuntimeError("Expected exactly one HG_Body polygon transform, found {}".format(len(roots)))
    body=roots[0]
    if fbx:
        output=Path(fbx)
        texture_dir=output.parent/(output.stem+"_textures")
    else:
        texture_dir=Path.home()/"Documents"/"BDFR_HG_Character_textures"
    maps=sorted(texture_dir.glob("*_albedo.png"))
    if len(maps)!=1:
        raise RuntimeError("Expected one baked albedo in {} (found {})".format(texture_dir,len(maps)))
    albedo=maps[0]
    # Reuse dedicated shader if this command is run again.
    shader="BDFR_HG_Body_Albedo"
    shading_group="BDFR_HG_Body_AlbedoSG"
    file_node="BDFR_HG_Body_Albedo_File"
    if not cmds.objExists(shader):
        shader=cmds.shadingNode("lambert",asShader=True,name=shader)
    if not cmds.objExists(shading_group):
        shading_group=cmds.sets(renderable=True,noSurfaceShader=True,empty=True,name=shading_group)
    cmds.connectAttr(shader+".outColor",shading_group+".surfaceShader",force=True)
    if not cmds.objExists(file_node):
        file_node=cmds.shadingNode("file",asTexture=True,name=file_node)
        place=cmds.shadingNode("place2dTexture",asUtility=True,name="BDFR_HG_Body_Albedo_UV")
        cmds.connectAttr(place+".outUV",file_node+".uvCoord",force=True)
        cmds.connectAttr(place+".outUvFilterSize",file_node+".uvFilterSize",force=True)
    cmds.setAttr(file_node+".fileTextureName",str(albedo.resolve()),type="string")
    cmds.connectAttr(file_node+".outColor",shader+".color",force=True)
    cmds.sets(body,edit=True,forceElement=shading_group)
    # Maya hardware texture display is viewport-specific; do not mutate global UI.
    uvsets=cmds.polyUVSet(body,query=True,allUVSets=True) or []
    print("[BDFR HG] Albedo linked: {} -> {}, UV sets: {}".format(albedo,body,uvsets))
    return {"body":body,"albedo":str(albedo),"uv_sets":uvsets}

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
            imported=import_human(target)
            material_result=reconnect_materials(target,imported)
            print("[BDFR HG Materials]",material_result)
            try:
                apply_body_albedo(target)
            except Exception as e:
                cmds.warning("[BDFR HG] Body albedo direct assignment: "+str(e))
            cmds.confirmDialog(title="Human Generator bridge",message="Character imported. Texture connections: {}. Warnings: {}.\nPress 6 in viewport for textured display.".format(material_result["connected"],len(material_result["warnings"])),button=["OK"])
        except Exception as exc:
            cmds.confirmDialog(title="Human Generator bridge error",message=str(exc)[-1800:],button=["OK"])
        finally:
            cmds.waitCursor(state=False)
    cmds.button(label="EXPORT FROM BLENDER + IMPORT INTO MAYA",height=43,command=run)
    def fix_existing(*_):
        try:
            output=cmds.textFieldButtonGrp(out,q=True,text=True).strip()
            result=apply_body_albedo(output)
            cmds.confirmDialog(title="HG Albedo",message="Applied to {}. UV sets: {}. Press 6 to view.".format(
                result["body"],", ".join(result["uv_sets"])),button=["OK"])
        except Exception as exc:
            cmds.confirmDialog(title="HG Albedo error",message=str(exc),button=["OK"])
    cmds.button(label="APPLY BAKED ALBEDO TO EXISTING HG_BODY",height=36,command=fix_existing)
    def open_shape_controls(*_):
        import bdfr_hg_shape_keys_maya
        bdfr_hg_shape_keys_maya.launch(
            cmds.textFieldButtonGrp(blender,q=True,text=True).strip(),
            cmds.textFieldButtonGrp(blend,q=True,text=True).strip())
    cmds.button(label="OPEN BLENDER SHAPE KEY CONTROLS",height=36,command=open_shape_controls)
    cmds.text(label="Supports authored .blend characters; not live HG sliders or native HG generation in Maya.",wordWrap=True)
    cmds.showWindow(w)
    return w
