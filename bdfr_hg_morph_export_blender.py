"""Export raw Blender Shape Key coordinate arrays (same mesh vertex order).

The arrays are stored in Blender-local object coordinates and contain both Basis
and targets. Maya importer MUST validate vertex correspondence before applying.
"""
import argparse,json,struct,sys
from pathlib import Path

def main():
    import bpy
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    parser.add_argument("--object",required=True)
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    obj=bpy.data.objects.get(args.object)
    if obj is None or obj.type!="MESH" or not obj.data.shape_keys:
        raise ValueError("Shape-key mesh not found: "+args.object)
    keys=obj.data.shape_keys.key_blocks
    basis=keys.get("Basis") or keys[0]
    if len(basis.data)!=len(obj.data.vertices):raise ValueError("Inconsistent topology")
    out=Path(args.out).resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    manifest={"object":obj.name,"count":len(basis.data),"keys":[]}
    def dump(path,block):
        with path.open("wb") as f:
            for v in block.data:
                f.write(struct.pack("<3f",*v.co))
    dump(out.with_name(out.stem+"_basis.bin"),basis)
    manifest["basis"]=out.with_name(out.stem+"_basis.bin").name
    for i,key in enumerate(keys):
        if key==basis:continue
        name="shape_%04d.bin"%i
        dump(out.with_name(out.stem+"_"+name),key)
        manifest["keys"].append({"name":key.name,"file":out.stem+"_"+name,
                                "min":float(key.slider_min),"max":float(key.slider_max),
                                "value":float(key.value)})
    out.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print("BDFR_MORPHS_OK",len(manifest["keys"]),len(basis.data))
if __name__=="__main__":
    main()
