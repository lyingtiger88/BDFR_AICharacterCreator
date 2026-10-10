# BDFR AI Character Creator

Autodesk Maya extension. Current release: **v0.2.0 organic procedural body prototype**.

## What's working in the code
- Full-body procedural mesh made from smoothly connected ring sections.
- Separate editable torso/head, two arms/hands and legs/feet.
- Height, shoulder, waist, hip, muscle, and head proportion sliders.
- Neutral / Broad / Curvy presets.
- Standard Maya window or dockable workspace panel.
- OBJ and FBX export through installed Maya plug-ins.

**This is not an anatomically exact human, one-piece watertight skin, photo reconstruction, or AI-fitting system yet.** Face matching with EOS, photogrammetry, full body AI reconstruction and professional rigging remain future milestones. No licensed third-party model data is distributed.

## Install in Maya 2027.2 (and Maya Python 3 variants)

Clone / download this repository to `D:\Projects\BDFR_AICharacterCreator`. In Maya's Python Script Editor:

```python
import sys, importlib
sys.path.insert(0, r"D:\Projects\BDFR_AICharacterCreator")
import bdfr_body_v02, bdfr_character_creator
importlib.reload(bdfr_body_v02)
importlib.reload(bdfr_character_creator)
bdfr_character_creator.show(dock=True)
```

If your repo is located elsewhere, substitute its actual directory. Press **GENERATE ORGANIC BODY** to replace the previous `BDFR_Character`. **Save your current scene beforehand**: rebuilding deletes that named hierarchy and any manual edits to it.

To use the floating window instead: `bdfr_character_creator.show()`.

## Manual smoke tests
1. Generate with all default settings. Confirm a full-height figure appears in the viewport and Outliner contains `BDFR_Character/Body_Surface_GRP`.
2. Increase Shoulders to 1.25 and Waist to 0.85, regenerate and check silhouette changes.
3. Try the Broad and Curvy presets; verify symmetric limbs.
4. Check all components are polygon meshes and editable.
5. Export an OBJ and an FBX using the panel, then import into an empty Maya scene to verify exports.
6. Close and reopen the dockable panel; ensure controls load.

The v0.2 implementation has been reviewed at source level but **has not been executed in an Autodesk Maya runtime by the development environment**. Please send a Maya Script Editor traceback if an error occurs.

## Implementation
- `bdfr_character_creator.py`: Maya panel, v0.1 compatibility and exports, v0.2 UI and integration.
- `bdfr_body_v02.py`: organic procedural body mesh engine using Maya API 2.0.
- `launch_in_maya.py`: simple floating panel launcher.

## Licensing
EOS code Apache-2.0, while bundled Surrey face-model data has noncommercial restrictions. SMPL-X and other third-party weights require separate license reviews before commercialization.
