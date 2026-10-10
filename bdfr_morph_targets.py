"""Validated, topology-preserving character morph targets.
Artist-sculpted per-vertex deltas, not geometry-coordinate heuristics.
"""
import json
import math
from pathlib import Path

KEYS=("breast_size","hip_width","glute_size")
N_VERTS=10475
def _points(data):
    if len(data)!=N_VERTS:raise ValueError("Expected 10475 vertices")
    out=[]
    for p in data:
        if len(p)!=3 or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in p):
            raise ValueError("Invalid coordinate")
        out.append(tuple(float(v) for v in p))
    return out

def author(base, sculpt, key, direction):
    if key not in KEYS or direction not in ("positive","negative"):
        raise ValueError("Invalid morph channel")
    b=_points(base); s=_points(sculpt)
    offsets=[]
    for i,(a,c) in enumerate(zip(b,s)):
        delta=tuple(c[j]-a[j] for j in range(3))
        if any(abs(v)>1e-8 for v in delta):offsets.append([i,*delta])
    if not offsets:raise ValueError("Sculpt has no changes")
    return {"version":1,"key":key,"direction":direction,"count":N_VERTS,"offsets":offsets}

def validate(morph):
    if morph.get("version")!=1 or morph.get("count")!=N_VERTS or morph.get("key") not in KEYS or morph.get("direction") not in ("negative","positive"):
        raise ValueError("Unsupported morph")
    seen=set()
    for entry in morph.get("offsets",[]):
        if len(entry)!=4:raise ValueError("Bad offset")
        i=entry[0]
        if type(i)!=int or not 0<=i<N_VERTS or i in seen:
            raise ValueError("Invalid/duplicate vertex index")
        seen.add(i)
        if any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>.5 for v in entry[1:]):
            raise ValueError("Invalid offset range")
    if not seen:raise ValueError("Empty morph")
    return morph

def apply(base, library, values):
    base=_points(base)
    result=[list(p) for p in base]
    for key,weight in zip(KEYS,values):
        if not math.isfinite(weight) or not -1<=weight<=1:raise ValueError("Invalid slider weight")
        if abs(weight)<1e-9:continue
        direction="positive" if weight>0 else "negative"
        morph=library.get((key,direction))
        if not morph:continue
        validate(morph)
        for i,dx,dy,dz in morph["offsets"]:
            result[i][0]+=abs(weight)*dx
            result[i][1]+=abs(weight)*dy
            result[i][2]+=abs(weight)*dz
    return result

def save(path,morph):
    validate(morph)
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(morph,separators=(",",":")),encoding="utf-8")

def load_folder(folder):
    library={}
    for path in Path(folder).glob("*.json"):
        if path.name=="reference.json":continue
        obj=validate(json.loads(path.read_text(encoding="utf-8")))
        key=(obj["key"],obj["direction"])
        if key in library:raise ValueError("Duplicate morph: "+str(key))
        library[key]=obj
    return library
