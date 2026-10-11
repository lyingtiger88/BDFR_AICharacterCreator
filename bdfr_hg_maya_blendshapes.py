"""Safe live Maya blendShape binding for Shape Keys from a Blender .blend.

Only binds when vertex correspondence and axes can be verified. No approximate
nearest-neighbour projection; topology mismatches are rejected explicitly.
"""
import itertools,json,math,struct,subprocess,tempfile
from pathlib import Path
import maya.cmds as cmds
from maya.api import OpenMaya as om

SCRIPT=Path(__file__).resolve().parent/"bdfr_hg_morph_export_blender.py"

def _points(node):
    shapes=cmds.listRelatives(node,shapes=True,noIntermediate=True,fullPath=True,type="mesh") or []
    if len(shapes)!=1:raise ValueError("Target must have exactly one mesh shape")
    sel=om.MSelectionList()
    sel.add(shapes[0])
    fn=om.MFnMesh(sel.getDagPath(0))
    return fn,[(p.x,p.y,p.z) for p in fn.getPoints(om.MSpace.kObject)]

def _binary(path,count):
    data=Path(path).read_bytes()
    if len(data)!=count*12:raise ValueError("Invalid morph vertex buffer size")
    return list(struct.iter_unpack("<fff",data))

def _axis_fit(basis,maya):
    # Find an axis permutation + signed uniform scale and offset fitting
    # each corresponding vertex. Mismatched geometry/vertex order is refused.
    n=len(basis)
    step=max(1,n//250)
    indices=list(range(0,n,step))
    best=None
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((-1.0,1.0),repeat=3):
            xx=[[signs[j]*basis[i][perm[j]] for j in range(3)] for i in indices]
            yy=[maya[i] for i in indices]
            mean_x=[sum(p[j] for p in xx)/len(xx) for j in range(3)]
            mean_y=[sum(p[j] for p in yy)/len(yy) for j in range(3)]
            denominator=sum(sum((p[j]-mean_x[j])**2 for j in range(3)) for p in xx)
            if denominator<1e-9:continue
            numerator=sum(sum((xx[k][j]-mean_x[j])*(yy[k][j]-mean_y[j])
                              for j in range(3)) for k in range(len(xx)))
            scale=numerator/denominator
            if scale<=0:continue
            offset=[mean_y[j]-scale*mean_x[j] for j in range(3)]
            error=sum(sum((scale*xx[k][j]+offset[j]-yy[k][j])**2 for j in range(3))
                      for k in range(len(xx)))/len(xx)
            candidate=(math.sqrt(error),perm,signs,scale,offset)
            if best is None or candidate[0]<best[0]:best=candidate
    if best is None:raise ValueError("Unable to align Blender basis with Maya mesh")
    rms,perm,signs,scale,offset=best
    coords=[p[j] for p in maya for j in range(3)]
    diagonal=math.sqrt(sum((max(p[j] for p in maya)-min(p[j] for p in maya))**2 for j in range(3)))
    if rms>max(1e-5,diagonal*.002):
        raise ValueError("Mesh topology/vertex order or base shape differs (RMS {:.5f}; limit {:.5f}). Please import an unmodified Basis mesh using consistent FBX settings.".format(rms,diagonal*.002))
    return perm,signs,scale

def bind(blender,blend,source_object="HG_Body",target="HG_Body"):
    if not Path(blend).is_file():raise FileNotFoundError(blend)
    matches=[n for n in cmds.ls(type="transform",long=True) or []
             if n.split("|")[-1].split(":")[-1]==target and
             cmds.listRelatives(n,shapes=True,noIntermediate=True,type="mesh")]
    if len(matches)!=1:raise ValueError("Expected exactly one Maya {} mesh; found {}".format(target,len(matches)))
    mesh=matches[0]
    fn,maya=_points(mesh)
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/"hg_morphs.json"
        command=[blender,"-b",str(blend),"--python",str(SCRIPT),"--",
                 "--out",str(path),"--object",source_object]
        proc=subprocess.run(command,capture_output=True,text=True,timeout=240)
        if proc.returncode or not path.exists():
            raise RuntimeError("Blender Shape Key extraction failed:\n"+(proc.stdout+proc.stderr)[-2500:])
        manifest=json.loads(path.read_text(encoding="utf-8"))
        n=manifest["count"]
        if n!=len(maya):raise ValueError("Vertex count mismatch: Blender {}, Maya {}. Cannot safely bind shape keys.".format(n,len(maya)))
        basis=_binary(Path(folder)/manifest["basis"],n)
        perm,signs,scale=_axis_fit(basis,maya)
        # Blender's relative Shape Keys can have a different relative_key.
        # This first stage assumes Basis-relative keys, which is by far the
        # most common case and must be verified before binding.
        name="BDFR_HG_Live_BlendShape"
        if cmds.objExists(name):
            raise ValueError("BlendShape already exists. Delete it explicitly before rebuilding.")
        targets=[]
        try:
            for entry in manifest["keys"]:
                sculpt=_binary(Path(folder)/entry["file"],n)
                duplicate=cmds.duplicate(mesh,returnRootsOnly=True,name="BDFR_TEMP_HG_Morph")[0]
                target_fn,_=_points(duplicate)
                converted=[]
                for base_vertex,maya_vertex,key_vertex in zip(basis,maya,sculpt):
                    converted.append(om.MPoint(*[
                        maya_vertex[j]+scale*signs[j]*
                        (key_vertex[perm[j]]-base_vertex[perm[j]])
                        for j in range(3)]))
                target_fn.setPoints(converted,om.MSpace.kObject)
                targets.append((entry,duplicate))
            # Create targets through Maya, then remove the temporary meshes.
            blend_node=cmds.blendShape(mesh,frontOfChain=True,name=name)[0]
            aliases={}
            for index,(entry,duplicate) in enumerate(targets):
                cmds.blendShape(blend_node,e=True,target=(mesh,index,duplicate,1.0))
                alias="BDFR_HG_SK_%03d"%index
                cmds.aliasAttr(alias,blend_node+".weight[{}]".format(index))
                aliases[(source_object,entry["name"])]=(blend_node,alias,float(entry["min"]),float(entry["max"]))
                cmds.setAttr(blend_node+".weight[{}]".format(index),max(entry["min"],min(entry["max"],entry["value"])))
            return aliases
        finally:
            for _,duplicate in targets:
                if cmds.objExists(duplicate):cmds.delete(duplicate)
