"""Persistent SMPL-X engine. Protocol: one JSON line request, one JSON line response.
Requests never contain proprietary weights; engine loads licensed weights from disk.
Run: python smplx_server.py --models DIR
"""
import argparse
import base64
import json
import sys
import time
from pathlib import Path

def send(payload):
    sys.stdout.write(json.dumps(payload,separators=(",",":"))+"\n")
    sys.stdout.flush()

def main():
    import numpy as np
    import torch
    import smplx
    parser=argparse.ArgumentParser()
    parser.add_argument("--models",required=True)
    args=parser.parse_args()
    base=Path(args.models).expanduser().resolve()
    cache={}
    torch.set_grad_enabled(False)
    def load(gender):
        if gender not in ("neutral","male","female"):
            raise ValueError("Invalid gender")
        if gender not in cache:
            patterns=["SMPLX_"+gender.upper()+".npz","SMPLX_"+gender.upper()+".pkl"]
            if gender=="neutral": patterns.append("SMPLX_NEUTRAL_2020.npz")
            files=[]
            for pattern in patterns:files.extend(sorted(base.rglob(pattern)))
            if not files: raise FileNotFoundError("Model not found: "+gender)
            model=smplx.SMPLX(model_path=str(files[0]),gender=gender,
                              ext=files[0].suffix.lstrip("."),use_pca=False,
                              batch_size=1).eval()
            cache[gender]=model
        return cache[gender]
    for line in sys.stdin:
        try:
            req=json.loads(line)
            request_id=req.get("id")
            if req.get("cmd")=="shutdown":
                send({"id":request_id,"ok":True})
                break
            if req.get("cmd")!="evaluate":
                raise ValueError("Unknown command")
            t=time.perf_counter()
            model=load(req["gender"])
            def param(key,n):
                values=req.get(key,[])
                if len(values)>n:raise ValueError(key+" exceeds expected size")
                return torch.tensor([list(values)+[0.0]*(n-len(values))],
                                    dtype=torch.float32)
            out=model(betas=param("betas",int(model.num_betas)),
                      body_pose=param("body_pose",63),
                      left_hand_pose=param("left_hand",45),
                      right_hand_pose=param("right_hand",45),
                      expression=param("expression",int(model.num_expression_coeffs)),
                      return_verts=True)
            verts=out.vertices[0].detach().cpu().numpy().astype("<f4",copy=False)
            faces=np.asarray(model.faces,dtype="<i4")
            send({"id":request_id,"ok":True,"gender":req["gender"],
                  "vertices":base64.b64encode(verts.tobytes()).decode("ascii"),
                  "faces":base64.b64encode(faces.tobytes()).decode("ascii"),
                  "vertex_count":len(verts),"face_count":len(faces),
                  "compute_ms":round((time.perf_counter()-t)*1000,1)})
        except Exception as exc:
            send({"id":req.get("id") if isinstance(req,dict) else None,
                  "ok":False,"error":str(exc)})
if __name__=="__main__":
    main()
