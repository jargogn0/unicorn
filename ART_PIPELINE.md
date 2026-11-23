# STOCKHOLM — Art Production Pipeline

This is the project owner's four-step route to GTA-class quality, turned into concrete deliverables and handoffs. Each step has a **contract**: what it must produce so the next step, and Claude Code's automation, can consume it without hand-fixing.

## 1. Gemini: art direction

**Inputs:** the art bible (`ArtReference/STOCKHOLM_ASSETS/00_ART_DIRECTION`), Stockholm photo references, WORLD_DESIGN.md §6.

**Deliverables per asset** (named `STK_<TYPE>_<NAME>_<NNN>.png`):
- **Characters:** an orthographic turnaround (front, ¾, left, right, back; A-pose; neutral grey; height marker), a face sheet (front, profile, 3 expressions), and close-ups of materials and logos. *Done for Doudou BA: `STK_CHAR_FOUNDER_TURNAROUND_001`.*
- **Buildings:** a facade elevation on the 400 cm module grid with 350 cm floor-to-floor, a corner detail, the ground-floor shop module, and roof profiles for each district style (Gamla Stan, Söder 1890s, Norrmalm 1960s, Östermalm).
- **Vehicles:** side, front, rear and top orthographics at the spec dimensions (`03_VEHICLES/VEHICLE_SPECS.md`), with livery sheets for the taxi and bus. Fictional brands only.
- **Props and materials:** swatch boards with hex values and roughness for each material in `07_MATERIAL_REFERENCES`.

**Rules:**
- No trademarks: no game logos, real car brands or real event or transit logos in shipping art. The pack's key visual carries the GTA VI logo and is reference only.
- The same character must stay consistent across sheets (seed or reference-image locking).

## 2. Blender + image-to-3D: modelling

**Tools:** an image-to-3D service for base meshes, then Blender for retopology, UVs and modular kits. Blender 5.3 runs headless in this repo's environment (`pip install bpy`), so repeatable steps live in `Tools/blender/`.

**Contract:**
- Units in metres, **Z-up** in Blender, exported as FBX for Unreal.
  - `Tools/blender/glb_to_ue_fbx.py` converts and validates any GLB, and reports dimensions to compare against the specs.
  - The script already caught one real problem: the starter-pack GLBs were Z-up data inside Y-up glTF, so they imported lying on their side.
- Names: `SM_` (static), `SK_` (skeletal), `MI_` (material instance), `T_` (texture, with `_BC`, `_N` and `_ORM` suffixes).
- Building kits snap to the 4.0 m × 3.5 m grid, with the pivot at the bottom-left of the module. Pieces are walls, corners, ground-floor shops, cornices, roof segments, balconies and doors. Every piece gets a Nanite-ready high mesh and a simple collision mesh (`UCX_`).
- Polygon budgets:
  - Hero character: about 60–80k tris (game-res), plus a MetaHuman face if possible.
  - Pedestrians: about 15–25k tris with 3 LODs.
  - Cars: about 60k tris with separate wheels.
  - Facade modules: Nanite.
- Textures: PBR at 2K for characters and 2K/1K for kits, with a trim sheet per district.

## 3. Character rigging and animation

- Skeleton: the **UE5 Manny/Quinn** hierarchy, so the engine's IK rigs, retargeting and the Game Animation Sample work out of the box. The face uses a MetaHuman face rig or ARKit-compatible blendshapes.
- Required animations:
  - Locomotion: idle, walk, jog, sprint, start, stop and turn (motion-matching set preferred).
  - Movement in the world: jump, enter car, exit car, drive idle and drive steer.
  - People: talk gestures matching the dialogue `anim` tags (`wave`, `shrug`, `lean_in`, `arms_crossed`, `nod`, `handshake`, `tablet_gesture`, …).
  - Work: sit at desk and type, phone in hand, sleep.
- Doudou's signature: the peace-sign wave from the key visual (`anim: "peace_wave"`).
- Delivery: FBX per clip at 30 fps, root motion on locomotion, plus a T-pose reference FBX.

## 4. Claude Code + Unreal Engine 5: integration

**Already in this repo:**
- Gameplay C++: character, Chaos vehicle, procedural city from OSM, atmosphere, traffic, pedestrians, NPCs, missions, dialogue, cinematics, HUD.
- `Tools/ue/create_milestone_a_map.py`: creates the World Partition map, materials and MPC, and imports the starter pack.

**Next automation, once assets arrive:**
- An import script for each asset folder: name and dimension validation, collision setup, LODs, Nanite enablement, material-instance creation from texture sets.
- PCG graphs that place facade kits on OSM footprints by district style.
- Character Blueprints that bind the skeletal mesh and AnimBP to `AStockholmCharacter` and `AStoryNpc`; Chaos vehicle Blueprints for each car (wheel bones `Phys_Wheel_FL/FR/BL/BR`).
- The `PP_GTA_Stylized` post-process (depth/normal Sobel ink lines at 1.5 px in `#0D0B12`, a 3-band ramp over Lumen) and the `M_GTA_Master` material. The browser preview already demonstrates the ink, cel and saturation look.

**Blocker for step 4:** it needs a machine with UE 5.5 and a GPU. This cloud container has neither. Connect the workstation through Claude Desktop → Settings → Claude Code → Remote Control, and Claude Code can build, run the editor scripts and capture screenshots there.

## Asset status board

| Asset | Step 1 | Step 2 | Step 3 | Step 4 |
|---|---|---|---|---|
| Doudou BA (founder) | ✅ turnaround + detail | ⬜ | ⬜ | Preview stand-in |
| Story NPCs (Noor, Sami, Aditi, Elin, Mateo, Helena) | ⬜ | ⬜ | ⬜ | Preview stand-ins |
| Pack roster (angel, VC partner, engineer, cofounder, YC interviewer) | Text spec | ⬜ | ⬜ | ⬜ |
| Founder studio interior | Spec | 🟨 blockout (axis-fixed) | n/a | Preview ✅; UE import scripted |
| Scandinavian sedan | Spec | 🟨 blockout (axis-fixed) | ⬜ wheel rig | Preview traffic ✅ |
| Taxi, SL-style bus | Spec | ⬜ | ⬜ | Preview stand-ins |
| Stockholm facade kits | Plates (Sergels, Stureplan, Norrmalm) | ⬜ | n/a | Procedural blockout |
| Sergels torg hero set | Plate | ⬜ | n/a | Preview stand-in |
