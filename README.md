# BDFR AI Character Creator

## v0.3 — Four-engine architecture

This project now uses **existing character systems**, not procedural primitives as its primary character source.

| Engine | Responsibility | Implemented now |
|---|---|---|
| MakeHuman | Real full-body geometry, UVs, potentially skeleton | Maya OBJ/FBX importer |
| SMPL-X | Parametric body/hands/face | Local asset / Python prerequisite checker |
| EOS | 3D face fit from photograph + supplied landmark data | Adapter invokes original EOS executable |
| mGear | Professional Maya rig pipeline | Maya environment detection |

**Important:** The photo-to-body SMPL-X fitting and MakeHuman-to-mGear rigging are not implemented yet. EOS requires the externally built executable, iBUG landmarks, appropriate model and mapping. Face meshes are not yet registered onto MakeHuman topology. This is **integration stage 1**, not a complete automatic photo-to-character product.

### Maya install

Clone repository (or download source zip) to `D:\Projects\BDFR_AICharacterCreator`. Script Editor > Python:

```python
import sys, importlib
sys.path.insert(0, r"D:\Projects\BDFR_AICharacterCreator")
import bdfr_four_engines
importlib.reload(bdfr_four_engines)
bdfr_four_engines.launch()
```

Export an **OBJ or FBX full-body character from MakeHuman** first. In Maya use `IMPORT MAKEHUMAN CHARACTER` and select that file. For models with a skeleton and materials, prefer MakeHuman FBX export when supported by your installed MakeHuman version.

Check SMPL-X, EOS and mGear prerequisites using the other buttons. Do not place noncommercial model weights into this public repository.

### EOS direct fitting example

```python
from bdfr_four_engines import eos_fit_from_photo
eos_fit_from_photo(
    r"D:\data\portrait.png",
    r"D:\data\portrait.pts",
    r"D:\eos\share\sfm_shape_3448.bin",
    r"D:\eos\share\ibug_to_sfm.txt",
    exe=r"D:\eos\build\fit-model-simple.exe",
    output_dir=r"D:\data\eos_output"
)
```

Check your EOS build's command line options and its license. This function wraps existing EOS only; it does not detect landmarks.

### Notes
- `bdfr_four_engines.py` is the new integration entrypoint. The older `bdfr_character_creator.py` and `bdfr_body_v02.py` are kept as **legacy prototypes** for reference, not as the recommended production pipeline.
- Do not assume compatible topology between MakeHuman, EOS and SMPL-X: mappings and retopology are a separate development task.
- The MakeHuman app and mGear must be installed separately and model files obtained lawfully.
- Source is not Maya-runtime-tested here. Please report any traceback from Script Editor.

### Licenses

The EOS code is Apache-2.0, but the Surrey data distributed with it is noncommercial-only. SMPL-X models have separate usage restrictions; MakeHuman outputs and its code have different licenses. mGear has its own license. Review each license before commercial use.
