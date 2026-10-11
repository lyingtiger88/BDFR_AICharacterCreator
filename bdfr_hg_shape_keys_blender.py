"""Blender 4.4 background CLI: enumerate and set actual mesh Shape Keys.
Independent of proprietary Human Generator internal controls.
"""
import argparse,json,sys
from pathlib import Path
def main():
 import bpy
 p=argparse.ArgumentParser()
 p.add_argument("--list",required=True)
 p.add_argument("--changes",default="")
 p.add_argument("--out",default="")
 args=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
 meshes=[obj for obj in bpy.data.objects if obj.type=="MESH" and obj.data.shape_keys]
 data={}
 for obj in meshes:
  keys=[{"name":k.name,"min":k.slider_min,"max":k.slider_max,"value":k.value}
        for k in obj.data.shape_keys.key_blocks if k.name!="Basis"]
  if keys:data[obj.name]=keys
 if args.changes:
  changes=json.loads(Path(args.changes).read_text(encoding="utf-8"))
  for name,keys in changes.items():
   obj=bpy.data.objects.get(name)
   if obj is None or obj.type!="MESH" or not obj.data.shape_keys:raise ValueError("Missing shape key mesh "+name)
   for key,value in keys.items():
    block=obj.data.shape_keys.key_blocks.get(key)
    if block is None or key=="Basis":raise ValueError("Missing shape key "+key)
    val=float(value)
    if not block.slider_min<=val<=block.slider_max:raise ValueError("Shape key value outside limits: "+key)
    block.value=val
  if not args.out:raise ValueError("Provide --out")
  dest=Path(args.out)
  dest.parent.mkdir(parents=True,exist_ok=True)
  bpy.ops.object.select_all(action="DESELECT")
  for obj in bpy.data.objects:
   if obj.type in {"MESH","ARMATURE"}:obj.select_set(True)
  bpy.ops.export_scene.fbx(filepath=str(dest),use_selection=True,
            object_types={"MESH","ARMATURE"},add_leaf_bones=False,bake_anim=False)
 Path(args.list).write_text(json.dumps({"meshes":data},indent=2),encoding="utf-8")
 print("BDFR_SHAPE_KEYS_OK",len(data))
if __name__=="__main__":main()
