"""Run with external Python: python smplx_export.py --models PATH --out PATH.
Requires pip install smplx torch numpy and licensed SMPL-X model weights.
"""
import argparse
import json
from pathlib import Path

def export(model_dir, output, gender="neutral", betas=None):
    import torch
    import smplx
    model_dir=Path(model_dir).expanduser().resolve()
    output=Path(output).expanduser().resolve()
    if gender not in ("neutral","male","female"):
        raise ValueError("Invalid SMPL-X gender")
    names=["SMPLX_"+gender.upper()+".npz", "SMPLX_"+gender.upper()+".pkl"]
    if gender=="neutral":
        names.append("SMPLX_NEUTRAL_2020.npz")
    files=[]
    for name in names:
        files.extend(sorted(model_dir.rglob(name)))
    if not files:
        raise FileNotFoundError("SMPL-X model weights missing for "+gender)
    # Official smplx.create(path) builds filename from path, gender, and ext.
    # Explicit model class loads the exact selected file, including _2020 variants.
    model=smplx.SMPLX(model_path=str(files[0]), gender=gender,
                      ext=files[0].suffix.lstrip("."),
                      use_pca=False, batch_size=1)
    count=int(model.num_betas)
    values=list(betas or [])[:count]
    values=values+[0.]*(count-len(values))
    params=torch.tensor([values],dtype=torch.float32)
    with torch.no_grad():
        result=model(betas=params,return_verts=True)
    vertices=result.vertices[0].detach().cpu().numpy()
    faces=model.faces
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("w",encoding="utf-8") as file:
        file.write("# Generated with licensed SMPL-X weights; Y up, meters\n")
        for x,y,z in vertices:
            file.write("v {:.8f} {:.8f} {:.8f}\n".format(float(x),float(y),float(z)))
        for a,b,c in faces:
            file.write("f {} {} {}\n".format(int(a)+1,int(b)+1,int(c)+1))
    return {"output":str(output),"model_file":str(files[0]),"vertices":len(vertices),"faces":len(faces)}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--models",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--gender",choices=["neutral","male","female"],default="neutral")
    ap.add_argument("--betas",nargs="*",type=float,default=[])
    args=ap.parse_args()
    print(json.dumps(export(args.models,args.out,args.gender,args.betas)))
