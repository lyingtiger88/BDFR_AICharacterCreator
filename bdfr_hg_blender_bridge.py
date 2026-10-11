"""Run in Blender 4.4.x via --python. No dependence on HG private APIs.

Usage: blender -b file.blend --python bdfr_hg_blender_bridge.py -- --out C:/path/human.fbx
Exports user-authored Human Generator character(s) by collection/selection.
"""
import argparse
import json
import sys
import shutil
import re
from pathlib import Path


def bake_missing_albedo(bpy, objects, textures, manifest, failures, size=2048):
    """Bake material diffuse COLOR only. Runs in the disposable background scene.

    Blender needs an active image texture node in every material slot. Uses
    Cycles diffuse color pass, excluding direct/indirect lighting.
    """
    scene=bpy.context.scene
    prior_engine=scene.render.engine
    prior_selected=list(bpy.context.selected_objects)
    prior_active=bpy.context.view_layer.objects.active
    baked=0
    try:
        scene.render.engine="CYCLES"
        scene.cycles.samples=1
        scene.render.bake.use_pass_color=True
        scene.render.bake.use_pass_direct=False
        scene.render.bake.use_pass_indirect=False
        scene.render.bake.margin=8
        for obj in objects:
            if obj.type!="MESH" or not obj.data.uv_layers:
                if obj.type=="MESH" and not obj.data.uv_layers:
                    failures.append(obj.name+": no UV map; cannot bake albedo")
                continue
            materials=[slot.material for slot in obj.material_slots if slot.material]
            if not materials:
                failures.append(obj.name+": no material assigned")
                continue
            # Only bake meshes whose own material lacks a traceable albedo.
            missing=[mat for mat in materials if not manifest.get(mat.name,{}).get("images",{}).get("base_color")]
            if not missing:continue
            image=bpy.data.images.new("BDFR_Albedo_"+obj.name,width=size,height=size,alpha=False)
            image.file_format="PNG"
            target_nodes=[]
            for mat in materials:
                mat.use_nodes=True
                node=mat.node_tree.nodes.new("ShaderNodeTexImage")
                node.name="BDFR_BAKE_ALBEDO"
                node.image=image
                mat.node_tree.nodes.active=node
                target_nodes.append((mat,node))
            try:
                bpy.ops.object.select_all(action="DESELECT")
                obj.hide_set(False)
                obj.select_set(True)
                bpy.context.view_layer.objects.active=obj
                bpy.ops.object.bake(type="DIFFUSE",use_clear=True)
                safe=re.sub(r"[^a-zA-Z0-9_.-]","_",obj.name)[:70]
                dest=textures/("BDFR_"+safe+"_albedo.png")
                image.filepath_raw=str(dest)
                image.save()
                for mat in missing:
                    manifest[mat.name]["images"]["base_color"]=str(dest)
                baked+=1
            except Exception as exc:
                failures.append("Albedo bake for "+obj.name+": "+str(exc))
            finally:
                for mat,node in target_nodes:
                    if mat.node_tree and node.name in mat.node_tree.nodes:
                        mat.node_tree.nodes.remove(node)
                bpy.data.images.remove(image)
    finally:
        scene.render.engine=prior_engine
        bpy.ops.object.select_all(action="DESELECT")
        for obj in prior_selected:
            try:obj.select_set(True)
            except Exception:pass
        try:bpy.context.view_layer.objects.active=prior_active
        except Exception:pass
    return baked

def main():
    import bpy
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    parser.add_argument("--collection",default="")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    target=Path(args.out).expanduser().resolve()
    if target.suffix.lower()!=".fbx":raise ValueError("Output must be .fbx")
    target.parent.mkdir(parents=True,exist_ok=True)
    if args.collection:
        coll=bpy.data.collections.get(args.collection)
        if coll is None:raise ValueError("Missing Blender collection: "+args.collection)
        roots=list(coll.all_objects)
    else:
        roots=list(bpy.context.selected_objects)
        if not roots:
            raise ValueError("No selected objects in saved blend file. Specify a collection.")
    allowed={"MESH","ARMATURE","EMPTY"}
    selected=[obj for obj in roots if obj.type in allowed]
    if not selected or not any(o.type=="MESH" for o in selected):
        raise ValueError("No mesh objects found for export")
    # Export selected objects; include armatures if they are in the chosen collection.
    bpy.ops.object.select_all(action="DESELECT")
    for obj in selected:obj.select_set(True)
    bpy.context.view_layer.objects.active=selected[0]
    bpy.ops.export_scene.fbx(filepath=str(target),use_selection=True,
                            object_types={"MESH","ARMATURE","EMPTY"},
                            add_leaf_bones=False,apply_unit_scale=True,
                            bake_anim=False, path_mode="AUTO")
    textures=target.parent/(target.stem+"_textures")
    textures.mkdir(parents=True,exist_ok=True)
    material_manifest={}
    failures=[]
    for obj in selected:
        if obj.type!="MESH":continue
        for slot in obj.material_slots:
            mat=slot.material
            if not mat or mat.name in material_manifest:continue
            record={"images":{}}
            if mat.use_nodes and mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.type!="BSDF_PRINCIPLED":continue
                    for input_name,key in (("Base Color","base_color"),("Normal","normal"),
                                           ("Roughness","roughness"),("Metallic","metallic")):
                        socket=node.inputs.get(input_name)
                        if not socket or not socket.is_linked:continue
                        stack=[link.from_node for link in socket.links]
                        visited=set()
                        while stack:
                            current=stack.pop()
                            if current.name in visited:continue
                            visited.add(current.name)
                            if current.type=="TEX_IMAGE" and current.image:
                                img=current.image
                                safe=re.sub(r"[^a-zA-Z0-9_.-]","_",img.name)[:90]
                                ext=Path(bpy.path.abspath(img.filepath or "")).suffix.lower()
                                if ext not in (".png",".jpg",".jpeg",".tif",".tiff",".tga",".exr"):
                                    ext=".png"
                                dest=textures/(safe+ext)
                                try:
                                    if img.packed_file:
                                        dest.write_bytes(img.packed_file.data)
                                    else:
                                        src=Path(bpy.path.abspath(img.filepath,library=img.library))
                                        if not src.is_file():raise FileNotFoundError(str(src))
                                        if src.resolve()!=dest.resolve():shutil.copy2(src,dest)
                                    record["images"][key]=str(dest)
                                except Exception as exc:
                                    failures.append(img.name+": "+str(exc))
                                break
                            stack.extend(link.from_node for inp in current.inputs for link in inp.links)
            material_manifest[mat.name]=record
    albedo_bakes=bake_missing_albedo(bpy,selected,textures,material_manifest,failures)
    report={"status":"ok","blender":bpy.app.version_string,
            "objects":len(selected),"meshes":sum(o.type=="MESH" for o in selected),
            "armatures":sum(o.type=="ARMATURE" for o in selected),
            "fbx":str(target),
            "materials":material_manifest,"albedo_bakes":albedo_bakes,
            "texture_copy_failures":failures,
            "note":"Objects exported from Blender scene; HG API not invoked."}
    report_path=target.with_suffix(".json")
    report_path.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("BDFR_HG_BRIDGE_OK",str(report_path))
if __name__=="__main__":
    main()
