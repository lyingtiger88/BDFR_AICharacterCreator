## v0.4.2 — Stable character presets and live-result safeguards

The v0.4 interface is preserved. It adds **SAVE CHARACTER PRESET** and **LOAD CHARACTER PRESET** buttons. Presets store the ten SMPL-X beta values, gender, and four pose/expression sliders as validated JSON, without embedding restricted model weights. Loading a preset schedules a single asynchronous Live update.

The persistent engine now checks response IDs to avoid accidentally accepting mismatched responses and prevents schedules after the controller closes. It still coalesces slider events and is not guaranteed real-time 60 FPS.

### Update / Maya load
```powershell
cd D:\Projects\BDFR_AICharacterCreator
git pull origin main
```
```python
import sys, importlib
sys.path.insert(0, r"D:\Projects\BDFR_AICharacterCreator")
import bdfr_smplx_persistent, bdfr_smplx_editor
importlib.reload(bdfr_smplx_persistent)
importlib.reload(bdfr_smplx_editor)
bdfr_smplx_editor.launch()
```

### Tests

`python -m unittest discover -s tests -v` checks preset round-trip and invalid inputs in ordinary Python without Maya. **Maya 2027.2 UI and persistent process still require manual runtime verification.** Save/load concerns *parameters*, not an undoable Maya geometry history. Full Undo/Redo support for live mesh edits remains a separate milestone.

---

## v0.4.1 — Persistent SMPL-X Live Engine

The Maya v0.4 panel now uses `bdfr_smplx_persistent.py` and `smplx_server.py`.
The external Python process remains running and keeps the SMPL-X weights/PyTorch model cached for each gender. Qt QProcess communicates JSON requests over stdin and receives base64 little-endian float32 vertices (and triangle connectivity) over stdout. The Maya main thread updates the same mesh; there are **no intermediate OBJ files for live updates**. A 90ms debounce coalesces drag events and ignores stale results. Switching genders may require a one-time second model load.

Update:
```powershell
cd D:\Projects\BDFR_AICharacterCreator
git pull origin main
```
In Maya Script Editor (Python):
```python
import sys, importlib
sys.path.insert(0, r"D:\Projects\BDFR_AICharacterCreator")
import bdfr_smplx_persistent, bdfr_smplx_editor
importlib.reload(bdfr_smplx_persistent)
importlib.reload(bdfr_smplx_editor)
bdfr_smplx_editor.launch()
```

Move beta sliders; no Apply required. Script Editor prints `[BDFR] SMPL-X engine: X ms, 10475 verts` for successful updates. The first change can still be slow because PyTorch and the model need initialization; subsequent changes should be faster. For an accurate performance baseline compare repeat modifications on the **same gender** after warm-up. The old Apply button remains as a synchronous fallback. Old `bdfr_smplx_live.py` stays for legacy reference and is no longer used by the new panel.

**Testing status:** Code committed and reviewed, but NOT validated in a live Maya 2027.2 installation. On a crash/error, share the Maya Script Editor traceback; this module does not need any new model downloads or Python packages beyond your existing SMPL-X installation.

---

## Live preview update (v0.4 Live)

In Maya Python Script Editor, after `git pull origin main`:

```python
import sys, importlib
sys.path.insert(0, r"D:\\Projects\\BDFR_AICharacterCreator")
import bdfr_smplx_live, bdfr_smplx_editor
importlib.reload(bdfr_smplx_live)
importlib.reload(bdfr_smplx_editor)
bdfr_smplx_editor.launch()
```

The 10 beta sliders now have **descriptive, experimental names** based on visual tests (not official anatomical axis names). Drag and change callbacks trigger a debounced 200ms external process; each evaluation updates the **existing** Maya mesh without a manual Apply click. A pending/latest slider state supersedes earlier requests. Maya remains responsive while the separate Python process computes. Each update may still take seconds depending on CPU and model load; this is **asynchronous live preview**, not guaranteed 60 FPS manipulation. Apply remains available as a manual fallback.

The first slider direction was observed for the **neutral model with beta01 -3**, so names/effects are exploratory and may differ for Male/Female. No licensed SMPL-X data should be committed to this public repository. Changes in this update are source-level only and await a Maya 2027.2 runtime test.

---

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
