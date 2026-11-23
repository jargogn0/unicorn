# STOCKHOLM — Initial 3D conversion handoff

## What exists
Three **actual GLB 3D mesh files** generated from a procedural interpretation of the supplied concepts:

- `STK_District_Prototype.glb`: a fictional 180 m × 140 m urban blockout with roads, 6 buildings, lamps and windows. **Not a georeferenced or accurate Stockholm model**.
- `VEH_Scandinavian_Sedan_Blockout.glb`: a low-detail sedan body and separate wheel meshes, intended as a placeholder for Chaos Vehicles.
- `INT_Founder_Studio_Blockout.glb`: an approximately 6.4 m × 5 m furnished studio blockout.

None of these are photorealistic, textured at production quality, rigged or animated. The supplied founder turnaround images are **reference only**, not a converted character. GLB meshes include flat vertex colors.

## Unreal Engine 5 handoff
1. Create an Unreal Engine 5 Games project with a third-person starter template.
2. Enable the Interchange glTF importer (or import through a Blender FBX conversion if your UE build lacks glTF support).
3. Import the 3 GLBs into `/Game/Stockholm/Blockout/`. In importer settings, confirm meters-to-centimeters scale, normals, and each mesh's coordinate orientation. Unreal commonly works in centimeters; GLB positions were authored in meters.
4. Place the district at world origin and give road/building meshes collision appropriate for simple exploration; do not apply complex collision to every decorative window.
5. Place the studio interior in a separate level/interior environment or inside a suitable building. Add door transition trigger.
6. For the sedan, make a Chaos vehicle pawn and proper skeletal wheel setup; these meshes alone are **not** a driveable vehicle. Use the sedan as a reference/placeholder, not a skeletal mesh.
7. Use the original PNGs as style references and material-generation input; avoid assigning them directly as arbitrary UV textures.
8. For protagonist: create a proper mesh via a DCC tool or image-to-3D service, retopologize, rig to a compatible UE skeleton, author walk/run/enter vehicle animations. The turnaround does not magically become a rig.

## Suggested real asset pipeline

`Gemini concept sheet -> image-to-3D base mesh / Blender modelling -> cleanup & retopology -> UV + PBR materials -> rig/animation for people/cars -> exports (.fbx/.glb) -> UE5 import -> collisions, LODs and in-engine validation.`

For the REAL city, replace the procedural blockout with legally usable map data (road centerlines, footprints and elevation) and locally authored facades. Validate coordinates against real Stockholm references.

## Reproducibility
`build_blockouts.py` is included. It uses Python `trimesh`, `numpy`, and generates the three GLBs. Execute from an environment with those packages installed. The provided version writes to an absolute temporary path: update `out=...` near the start to your own destination.

## Gaps
- No runtime engine project, Chaos vehicle controller, UE character rig, AAA photoreal materials, or accurate city geography included.
- This environment does not have Blender or Unreal installed, so in-engine import and playtesting were not performed.
