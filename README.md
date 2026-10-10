## v0.4.5 Sculpted Morph Targets (replaces broken procedural sliders)

**What is implemented:** Old approximate breast/hip/glute vertex-bulge algorithm is no longer called by Live or Apply. A morphology library accepts **artist-authored topology-matched vertex deltas**, blended by the three existing sliders. Missing targets intentionally do nothing (and warn); this avoids surprising deformities. JSON morph files include explicit vertex IDs and offsets; accompanying reference.json binds them to the exact SMPL-X gender, beta vector and pose controls used to sculpt. Existing character presets remain supported.

**Authoring workflow in Maya:** Pull latest main, reload modules `bdfr_morph_targets`, `bdfr_smplx_persistent` and `bdfr_smplx_editor`. Launch the editor. Set the three detail sliders to zero, wait for latest Live evaluation and click **1. CAPTURE BASE**. Duplicate the character mesh, then sculpt the *duplicate* with Maya sculpt/soft selection tools, preserving exactly 10,475 vertices and their IDs. Select the duplicate, choose the matching Sculpt channel and Sculpt direction, then click **3. CAPTURE SELECTED SCULPT**; select a morph library folder. Repeat for each positive/negative channel. Use **2. LOAD MORPH LIBRARY** to reload. The same folder may hold all six targets. Morph sliders only operate for exactly the same base gender/betas/pose reference used while sculpting. To change body shape significantly, author/recompute compatible morphs.

This is a **working morph pipeline foundation**, not six finished professional anatomical sculpts. Maya sculpt assets remain to be authored and visually approved. No production-ready rigging or Unreal skeletal export is claimed. Unit tests are provided under `tests/test_morph_targets.py`, but Maya runtime validation is still outstanding. The now-unused `bdfr_body_details.py` is retained for historical compatibility only.

---

## Localized body detail correction (2026-10-11)

The breast control is now gated to **two front-facing cup patches**, excluding the sternum, back, and chest wall. The glute control targets **posterior cheek surfaces only**, excluding anterior thighs. Hip Width now targets side contours near the pelvis instead of the complete thigh. Spatial masks use bounded smooth falloffs and preserve vertex count and topology.

**Limitations:** this is still an experimental geometry-space approximation with a presumed +Z anterior orientation, not artist-painted vertex masks or anatomy-verified production blendshapes. The exact region positions may differ by gender/betas/pose; Maya front/side/back testing is required. To reload a hotfix in Maya, reload `bdfr_body_details` as well as `bdfr_smplx_persistent` and `bdfr_smplx_editor`.

Run `python -m unittest discover -s tests -v` for pure-Python checks.

---

## v0.4.4 detail-slider hotfix

If Breast Size, Hip Width or Glute Size looked unchanged, pull main and **reload bdfr_body_details, bdfr_smplx_persistent, and bdfr_smplx_editor**; a Python module imported earlier remains cached in Maya even if the file was updated. Revised spatial masks estimate torso/pelvis depth relative to mesh proportions and use stronger visible deformation. Script Editor now logs `[BDFR Details] breast=..., hips=..., glutes=..., max displacement=... mm` on successful live updates. If max displacement is 0 mm even at +1, share that line and a front/side screenshot so we can confirm orientation and shape region on your model. This remains experimental mesh shaping, not production rig-ready breast or glute blendshapes.

Reload command:
```python
import sys, importlib
sys.path.insert(0, r"D:\Projects\BDFR_AICharacterCreator")
import bdfr_body_details, bdfr_smplx_persistent, bdfr_smplx_editor
for m in (bdfr_body_details, bdfr_smplx_persistent, bdfr_smplx_editor):
    importlib.reload(m)
bdfr_smplx_editor.launch()
```

No Maya runtime test has been performed yet for this hotfix.

---

## v0.4.4 — Main Body Controls / Advanced Details

The editor is now organized with **MAIN BODY CONTROLS** before the ten **ADVANCED DETAILS** SMPL-X beta sliders. Main controls include **Breast Size**, **Hip Width** and **Glute Size**, each ranging from -1 to +1 (0 = no extra shaping). They respond to Live editing and manual Apply. The profile is stored in JSON presets; old presets load with all three new controls set to zero.

The three controls are **experimental localized vertex deformations applied after SMPL-X evaluation**, using smooth falloffs in SMPL-X local coordinates (+Y up, +Z front). This is NOT a native SMPL-X semantic breast/glute parameter, does not modify the licensed model, and is **not yet rig-safe**. Preview the front and rear in Maya before using large values. The modifier is regenerated from the original evaluated vertices for each Live update to avoid accumulation. Geometry is intended for future corrective blendshape work, not current Unreal skeletal export.

Update from PowerShell: `git pull origin main`. In Maya, reload `bdfr_smplx_persistent` and `bdfr_smplx_editor`, and call `bdfr_smplx_editor.launch()`.

Unit tests: `python -m unittest discover -s tests -v` (outside Maya). Maya 2027.2 visual test is still required.

---

## v0.4.3 — Unreal-style A-Pose preview

The existing v0.4 Live panel now includes **UNREAL A-POSE** and **RESET REST POSE** buttons. A-Pose sets the SMPL-X shoulder control to -35° (opposite sign on the mirrored shoulder via existing pose mapping), with elbows and hands neutral, and triggers an asynchronous mesh update. Rest Pose restores these pose sliders to zero. The shoulder slider range and preset validation are widened to ±60°, so presets can save A-Pose settings.

**Important:** This is a visual Unreal-style A-Pose preset for the existing SMPL-X deformation engine. It is *not* yet a verified Unreal Engine 5 mannequin reference pose, nor a skeletal FBX retarget profile. The exact orientation must be checked in Maya (front view); if arms lift instead of lower, reverse the shoulder sign in the preset. Skeleton hierarchy, skin weights and Unreal-ready export are later milestones.

After pulling `main`, reload `bdfr_smplx_editor` and open its panel. Press **UNREAL A-POSE** and check arms in front view. Press **RESET REST POSE** to return. No change to the original SMPL-X model weights.

---

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
