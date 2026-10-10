"""Lightweight local shape detailing on evaluated SMPL-X vertices.
Experimental geometry-space preview, not semantic SMPL-X coefficients.
All coordinates are model-local metres; no vertex indices or topology changes.
"""
import math

DETAIL_KEYS=("breast_size","hip_width","glute_size")

def deform(vertices, breast_size=0.0, hip_width=0.0, glute_size=0.0):
    """Return new xyz tuples; zero controls preserve input exactly.

    Assumes upright SMPL-X (+Y up, +Z front), with spatially smooth,
    low-amplitude deformations. Do not use as rig-ready corrective shapes.
    """
    controls=(breast_size,hip_width,glute_size)
    if any(not isinstance(v,(float,int)) or isinstance(v,bool) or
           not math.isfinite(v) or abs(v)>1 for v in controls):
        raise ValueError("Detail sliders must be finite values in [-1, 1]")
    if not any(controls):
        return [tuple(v) for v in vertices]
    points=[tuple(v) for v in vertices]
    if not points:return []
    ys=[v[1] for v in points]
    height=max(ys)-min(ys)
    if height<=1e-8:return points
    bottom=min(ys)
    def bell(value,centre,sigma):
        return math.exp(-0.5*((value-centre)/sigma)**2)
    out=[]
    for x,y,z in points:
        ny=(y-bottom)/height
        ax=abs(x)/height
        nz=z/height
        new_x,new_z=x,z
        if breast_size and nz>0:
            w=bell(ny,.705,.049)*bell(ax,.063,.043)*bell(nz,.075,.078)
            new_z+=height*.020*breast_size*w
        if hip_width:
            w=bell(ny,.445,.064)*bell(ax,.107,.075)
            # gradual symmetric widening, avoiding movement of vertices on midline
            new_x+=height*.014*hip_width*w*(1 if x>=0 else -1)*min(1,ax/.08)
        if glute_size and nz<0:
            w=bell(ny,.417,.060)*bell(ax,.065,.065)*bell(nz,-.063,.080)
            new_z-=height*.021*glute_size*w
        out.append((new_x,y,new_z))
    return out
