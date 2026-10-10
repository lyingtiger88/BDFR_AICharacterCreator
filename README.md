# BDFR AI Character Creator — v0.4 Parametric SMPL-X milestone

This Maya project integrates **MakeHuman**, **SMPL-X**, **EOS**, and **mGear**. As of this milestone, the SMPL-X component can evaluate *real licensed weights* in an external Python environment and update an existing Maya mesh **in place**.

## Install

Use your existing local clone at `D:\Projects\BDFR_AICharacterCreator`.
Keep downloaded model weights only locally in `models\smplx` (excluded by .gitignore).
Install external Python dependencies once via `setup_smplx_windows.ps1` (Python 3.10/3.11 required).

Update the repository with `git pull origin main`.

In Maya Python Script Editor:

```python
import sys, importlib
sys.path.insert(0, r"D:\Projects\BDFR_AICharacterCreator")
import bdfr_smplx_editor
importlib.reload(bdfr_smplx_editor)
bdfr_smplx_editor.launch()
```

Alternatively, reopen the four-engine main panel and click **OPEN SMPL-X PARAMETRIC EDITOR v0.4**.

## Testing checklist

1. Start a blank Maya scene (save previous work beforehand).
2. Verify external Python / model weights paths appear; change manually if needed.
3. Choose Neutral, click **NEW CHARACTER / CHANGE GENDER**.
4. Adjust Beta 1 to 2, click **APPLY TO EXISTING CHARACTER**. The existing object `BDFR_SMPLX_Character` must be updated, not duplicated.
5. Change shoulder pose to 15 degrees and apply. The model should change shape in place.
6. Change gender with **NEW CHARACTER / CHANGE GENDER** and verify the bottom of the mesh is aligned to Y=0.
7. Observe Script Editor for tracebacks. This milestone has not been Maya-runtime-tested by the assistant.

## Scope and limitations

- Ten user-facing shape sliders are the first ten statistical PCA shape coefficients; they are *not* anatomically named muscle/height/weight controls. These require data-calibrated mappings.
- The shoulder, elbow and finger controls use subsets of official SMPL-X joint-angle parameters. They are prototype pose controls, not IK and do not create a Maya joint rig.
- The expression slider maps to the first SMPL-X expression coefficient and is not guaranteed to mean 'smile'.
- 'Apply' reevaluates the model in an external Python subprocess, then changes vertex positions on the existing Maya polygon mesh. It is *not* per-frame playback or instantaneous interactive dragging.
- Vertex count and topology are checked (10475 expected for SMPL-X); incompatible imported meshes are not overwritten.
- Scene data is not yet a reusable fully rigged SMPL-X asset with vertex skin weights and joint hierarchy. mGear integration, photo fitting via EOS, texture transfer, and MakeHuman-to-SMPL-X topology transfer remain outstanding.
- Changing gender with NEW CHARACTER deletes the previous generated object. Save your scene first.
- The public project does not redistribute restricted SMPL-X weight files.

## Main files

- `smplx_export.py`: official-model evaluation through PyTorch and export of OBJ vertices/faces, including optional body/hand pose/expression parameters.
- `bdfr_smplx_editor.py`: Maya UI and topology-protected in-place vertex update.
- `bdfr_smplx_maya.py`: earlier v0.3.5 importer (ground positioning validated by the user).
- `bdfr_four_engines.py`: entry point for the four-engine toolkit.
- `bdfr_makehuman_auto.py`: MakeHuman asset importer; separate mesh source.
- `setup_smplx_windows.ps1`: external dependencies installer.

## Licensed software

SMPL-X code/models are distributed under specific non-commercial research licensing; download models directly from the official SMPL-X website using an authorized account. EOS's bundled Surrey model also has its own noncommercial conditions. Review third-party licenses before distributing a product.
