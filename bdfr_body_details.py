"""Strictly localized body-detail preview for upright SMPL-X meshes.

Coordinates: Y up; +Z is assumed anterior. Geometry-relative surface masks
keep the chest wall and anterior thighs unchanged. No topology edits.
For production, sculpt and validate anatomical blendshape masks on the real mesh.
"""
import math

DETAIL_KEYS=("breast_size","hip_width","glute_size")

def _smooth(lo, hi, value):
    t=max(0.0,min(1.0,(value-lo)/(hi-lo)))
    return t*t*(3.0-2.0*t)

def deform(vertices, breast_size=0.0, hip_width=0.0, glute_size=0.0):
    controls=(breast_size,hip_width,glute_size)
    if any(isinstance(v,bool) or not isinstance(v,(int,float))
           or not math.isfinite(v) or abs(v)>1 for v in controls):
        raise ValueError("Details must be finite numbers in [-1,1]")
    points=[tuple(p) for p in vertices]
    if not points or not any(controls):
        return points
    bottom=min(p[1] for p in points)
    height=max(p[1] for p in points)-bottom
    if height<1e-9:
        return points
    # Evaluate position relative to torso centre instead of world Z=0.
    torso=[p[2] for p in points
           if .57<(p[1]-bottom)/height<.78 and abs(p[0])/height<.045]
    pelvis=[p[2] for p in points
            if .39<(p[1]-bottom)/height<.53 and abs(p[0])/height<.050]
    def median(seq):
        if not seq:return 0.0
        ordered=sorted(seq)
        return ordered[len(ordered)//2]
    chest_middle=median(torso)
    hip_middle=median(pelvis)
    result=[]
    for x,y,z in points:
        h=(y-bottom)/height
        lateral=abs(x)/height
        front_depth=(z-chest_middle)/height
        back_depth=(hip_middle-z)/height
        dx=dz=0.0
        if breast_size:
            # Two bounded oval cup regions; zero influence on sternum, ribs,
            # collarbone and back. Full influence on outward-facing breast skin.
            lateral_band=_smooth(.035,.065,lateral)*(1-_smooth(.125,.165,lateral))
            vertical_band=_smooth(.645,.685,h)*(1-_smooth(.748,.785,h))
            anterior_skin=_smooth(.035,.065,front_depth)
            cup=lateral_band*vertical_band*anterior_skin
            dz+=height*.070*breast_size*cup
        if hip_width:
            # Side-only hip contour, not entire leg or abdomen.
            vertical_band=_smooth(.415,.455,h)*(1-_smooth(.52,.58,h))
            side_band=_smooth(.085,.125,lateral)*(1-_smooth(.23,.29,lateral))
            dx+=math.copysign(height*.034*hip_width*vertical_band*side_band,x) if x else 0.0
        if glute_size:
            # Two rear cheek lobes. Strict posterior surface criterion excludes
            # the front thighs even at maximal slider values.
            lateral_band=_smooth(.030,.065,lateral)*(1-_smooth(.13,.19,lateral))
            vertical_band=_smooth(.385,.425,h)*(1-_smooth(.49,.535,h))
            posterior_skin=_smooth(.035,.075,back_depth)
            cheek=lateral_band*vertical_band*posterior_skin
            dz-=height*.080*glute_size*cheek
        result.append((x+dx,y,z+dz))
    return result
