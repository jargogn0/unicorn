# Owner's 3D starter pack (2026-11-23)

The original files are kept as received: `*.glb`, `build_blockouts.py`, `README_IMPORT.md`, `ASSET_METADATA.json`. `build_blockouts.py` has not been executed.

Findings:
- The GLBs were authored **Z-up** but saved as Y-up glTF, so they import lying on their side. `ASSET_METADATA.json` says Y-up.
- `INT_Founder_Studio_Blockout`: the two south-wall pieces meet at x = −1.2 m, so there's **no door gap**. The browser preview adds a door slab; Unreal needs the wall cut.
- `VEH_Scandinavian_Sedan_Blockout`: a static mesh (not a vehicle rig), 1.35 m tall against the 1.44 m spec, with wheels extending past the 1.85 m body.
- `STK_District_Prototype`: a fictional 180 × 140 m blockout. It isn't Stockholm and isn't used for the city; Stockholm comes from OSM.

`UE_Ready/` holds the output of `python3 Tools/blender/glb_to_ue_fbx.py --zup-authored` (Blender 5.3 headless): upright FBX and GLB files with a dimension report. `Tools/ue/create_milestone_a_map.py` imports the studio and sedan from here into `/Game/Stockholm/Blockout`.
