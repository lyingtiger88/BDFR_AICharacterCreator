"""BDFR v0.4.2 character parameter presets. Pure Python, no Maya dependency."""
import json
import math
from pathlib import Path

SCHEMA=1
FIELDS=("shoulder","elbow","hand","expression")
LIMITS={"shoulder":(-30,30),"elbow":(-60,60),"hand":(0,45),"expression":(-2,2)}

def validated(data):
    if not isinstance(data,dict) or data.get("schema")!=SCHEMA:
        raise ValueError("Unsupported preset schema")
    gender=data.get("gender")
    if gender not in ("neutral","male","female"):
        raise ValueError("Invalid body model")
    betas=data.get("betas")
    if not isinstance(betas,list) or len(betas)!=10:
        raise ValueError("Preset must contain ten shape betas")
    result={"schema":SCHEMA,"gender":gender,"betas":[]}
    for value in betas:
        if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or not -3<=value<=3:
            raise ValueError("Invalid beta value")
        result["betas"].append(float(value))
    for name in FIELDS:
        value=data.get(name)
        low,high=LIMITS[name]
        if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or not low<=value<=high:
            raise ValueError("Invalid "+name)
        result[name]=float(value)
    return result

def save(path,data):
    checked=validated(data)
    target=Path(path)
    target.parent.mkdir(parents=True,exist_ok=True)
    tmp=target.with_name(target.name+".tmp")
    try:
        tmp.write_text(json.dumps(checked,indent=2),encoding="utf-8")
        tmp.replace(target)
    finally:
        if tmp.exists():tmp.unlink()
    return str(target)

def load(path):
    return validated(json.loads(Path(path).read_text(encoding="utf-8")))
