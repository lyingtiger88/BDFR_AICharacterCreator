"""Anatomically approximate localized body details for SMPL-X (preview only).

Geometry-relative falloff (no hardcoded global Z side). Preserves vertex IDs.
Not a substitute for rig-aware blendshapes.
"""
import math
DETAIL_KEYS=("breast_size","hip_width","glute_size")

def deform(vertices, breast_size=0.0, hip_width=0.0, glute_size=0.0):
    controls=(breast_size,hip_width,glute_size)
    if any(isinstance(v,bool) or not isinstance(v,(float,int)) or
           not math.isfinite(v) or abs(v)>1 for v in controls):
        raise ValueError("Detail values must be finite in [-1,1]")
    points=[tuple(p) for p in vertices]
    if not points or not any(controls):return points
    bottom=min(p[1] for p in points)
    height=max(p[1] for p in points)-bottom
    if height<1e-8:return points
    def gauss(t,center,width):
        return math.exp(-.5*((t-center)/width)**2)
    # Choose the front/back axis by measuring which side of the head
    # protrudes farther from the head centre (nose). If the head is
    # ambiguous, use SMPL-X's common +Z-facing convention.
    head=[p[2] for p in points if (p[1]-bottom)/height>.85 and abs(p[0])<height*.055]
    front=1
    if len(head)>=20:
        mid=(max(head)+min(head))*.5
        front=1 if max(head)-mid >= mid-min(head) else -1
        # extrema around midpoint are symmetric, use median instead.
        head_sorted=sorted(head)
        median=head_sorted[len(head_sorted)//2]
        front=1 if max(head)-median>=median-min(head) else -1
    # Chest / pelvis mid-depth estimated locally, not from world zero.
    def centre_z(low,high):
        candidates=[p[2] for p in points if low<(p[1]-bottom)/height<high and abs(p[0])<height*.075]
        return sorted(candidates)[len(candidates)//2] if candidates else 0.0
    chest_z=centre_z(.67,.75)
    pelvis_z=centre_z(.39,.49)
    result=[]
    for x,y,z in points:
        h=(y-bottom)/height
        xx=abs(x)/height
        chest_depth=front*(z-chest_z)/height
        rear_depth=-front*(z-pelvis_z)/height
        dx,dz=0.0,0.0
        if breast_size:
            w=gauss(h,.717,.067)*gauss(xx,.088,.070)
            # Affect exposed front, not back. Soft falloff protects side seams.
            depth_mask=max(0.0,min(1.0,(chest_depth+.012)/.07))
            dz+=front*height*.058*breast_size*w*depth_mask
        if hip_width:
            w=gauss(h,.447,.095)*gauss(xx,.13,.105)
            dx+=math.copysign(1.0,x)*height*.042*hip_width*w*min(1.0,xx/.045) if x else 0
        if glute_size:
            w=gauss(h,.44,.075)*gauss(xx,.095,.085)
            depth_mask=max(0.0,min(1.0,(rear_depth+.012)/.075))
            dz-=front*height*.064*glute_size*w*depth_mask
        result.append((x+dx,y,z+dz))
    return result
