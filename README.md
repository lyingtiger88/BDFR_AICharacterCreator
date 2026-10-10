# BDFR AI Character Creator

Maya character-building extension. **Current milestone: v0.1.0 procedural proxy**, not yet photo-to-3D reconstruction.

## Install / run

1. Download or clone the repository.
2. Open Autodesk Maya, Script Editor, **Python** tab.
3. Run (replace path with your local clone directory):

```python
import sys
sys.path.insert(0, r"D:\Projects\BDFR_AICharacterCreator")
from bdfr_character_creator import show
show()
```

4. Change Height, Body width, Head scale, click **CREATE / REBUILD CHARACTER**.
5. You should see a human-shaped proxy made from independent polygon meshes in Maya's viewport. Change controls and rebuild, then export OBJ or FBX using the buttons.

## Current features
- Maya-native control panel with three shape parameters
- Procedural articulated-looking **static** full-body proxy consisting of polygon meshes
- Named mesh components under `BDFR_Character` group
- Basic skin, clothing, and eye materials
- OBJ and FBX export via Maya export plug-ins (subject to installation)
- No third-party Python requirements for the current baseline

## Current limitations
- This is a **rough mannequin proxy**, not photorealistic/anatomically accurate character geometry.
- No face likeness reconstruction, uploaded-image processing, body image reconstruction, rig, joint system, or animation yet.
- Height slider uniformly scales a 175cm prototype; sliders rebuild meshes, not live deformations.
- Maya runtime and export workflows need testing in a real Maya installation.
- Rebuilding deletes the prior `BDFR_Character` hierarchy; save your scene first if you edited it.

## Development plan

- v0.2: coherent body topology, parametric anatomy, head/body connection, face fitting architecture
- v0.3: photo landmark detector adapter + EOS shape fitting (external model and dependency checks)
- v0.4: optional SMPL-X/AI fitting behind separately accepted licences
- v0.5: rigging, skin weights, professional export

## Licensing considerations

EOS source is Apache-2.0, but the supplied Surrey face model has **noncommercial** restrictions. SMPL-X, PIXIE and similar models may also have separate restrictions. No such third-party weights or datasets are redistributed here.

## Compatibility

Target Autodesk Maya with Python 3 and the standard `maya.cmds` API. This first version deliberately avoids a PySide-specific dependency to maximize compatibility. A dockable Qt panel is planned.
