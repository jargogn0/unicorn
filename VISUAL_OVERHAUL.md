# STOCKHOLM — Visual Quality Overhaul

Started 2026-11-23 in response to the owner's review: the gameplay prototype works, but the world looked like primitive shapes. This document records the audit, the assets acquired with their licences, what was rebuilt, the evidence, and what is still missing. Gameplay, missions, saves and interaction code were not changed.

## Phase 1: audit

**Engines and hardware**
- The only build that can run in this environment is the browser preview (three.js r160). Unreal Engine 5 is not installed and there is no GPU. All rendering here is software WebGL; it is correct but slow.
- Blender 5.3 runs headless here as a Python module (`pip install bpy`), including Cycles CPU rendering.

**What was real and what was generated, before the overhaul**

| Element | Before | Imported 3D asset? |
|---|---|---|
| City buildings | Extruded boxes with one generated window texture | No |
| Roads, sidewalks | Flat ribbons, flat colours | No |
| Characters | Capsules and spheres with procedural limb swing | No |
| Cars | Boxes; the owner's sedan blockout GLB for traffic | Blockout only |
| Props | None, apart from generated lamp poles | No |
| Materials | Flat colours, canvas-drawn textures, cel ramp | No |
| Lighting | Analytic sky, one sun, pooled point lights | n/a |
| Interior | The owner's studio blockout GLB | Blockout only |

**Network audit: which sources work from here**

| Source | Result |
|---|---|
| Poly Haven (API and downloads) | Works. Licence CC0. |
| ambientCG | API reachable (CC0); not needed yet. |
| OpenStreetMap main API (`api.openstreetmap.org/api/0.6/map`) | Works (ODbL). The Overpass mirrors still fail. |
| MakeHuman asset server, Blender Extensions | Reachable; used for the character. |
| Fab, Quixel Megascans | Sites reachable, but downloads need an Epic login and the assets are Unreal-format. **Blocked from here**; do this on the Unreal workstation. |
| Sketchfab | Downloads need an account token. Blocked. |
| Mixamo | Needs an Adobe login. Blocked. |

## Phase 2: assets acquired

The full machine-readable lists with every file URL are `Assets/ThirdParty/polyhaven_manifest.json` and `Assets/ThirdParty/character_manifest.json`. Re-download with `Tools/assets/fetch_polyhaven.py` and `Tools/blender/character/fetch_assets.py`. Required attributions are in `CREDITS.md` and on the game's title screen.

| Asset | Type | Source | Licence | Used for |
|---|---|---|---|---|
| painted_plaster_wall | PBR texture set | Poly Haven | CC0 | Facade plaster (tinted per building) |
| white_plaster_02 | PBR texture set | Poly Haven | CC0 | Window surrounds, cornices, trim |
| brick_wall_10 | PBR texture set | Poly Haven | CC0 | Brick blocks |
| granite_wall | PBR texture set | Poly Haven | CC0 | Ground-floor piers, kerbs, bridge decks |
| asphalt_02, asphalt_snow | PBR texture sets | Poly Haven | CC0 | Carriageway, slushy road edges |
| concrete_pavement | PBR texture set | Poly Haven | CC0 | Sidewalk slabs |
| snow_02 | PBR texture set | Poly Haven | CC0 | Roofs, ledges, ploughed snowbanks |
| box_profile_metal_sheet | Normal map | Poly Haven | CC0 | Standing-seam mansard roofs |
| winter_evening, snowy_park_01 | HDRIs | Poly Haven | CC0 | Image-based lighting (dusk/night, day) |
| modular_street_seating | Model kit | Poly Haven | CC0 | Bench (assembled in Blender) |
| metal_trash_can | Model | Poly Haven | CC0 | Litter bin |
| standing_chalkboard_01 | Model | Poly Haven | CC0 | Café A-board |
| outdoor_table_chair_set_01 | Model | Poly Haven | CC0 | Café table set |
| planter_box_01, utility_box_01, water_manhole_cover, street_lamp_01 | Models | Poly Haven | CC0 | Street dressing |
| Kungsgatan map extract | Geodata | OpenStreetMap | ODbL 1.0 | Footprints, storeys, road widths, bridges |
| Human base mesh, rig, skins, eyes, hair, system clothes | Character base | MakeHuman / MPFB2 | CC0 | Doudou and the pedestrians |
| Hooded jacket (Elvaerwyn), jeans and shoes (punkduck), cardigans and trousers (Mindfront) | Clothing | MakeHuman community packs | CC BY (attribution in CREDITS.md) | Doudou's hoodie, jeans and sneakers; pedestrian outfits. All modified. |
| Idle, walk, run and gesture motion | Animation | three.js r160 example character (Mixamo-origin data) | three.js MIT; Mixamo royalty-free in projects | Retargeted onto every character |
| Stockholm facade kit (22 modules) | Modelled here in Blender | This project | Project-owned | All hero-street facades |

Downloaded but not yet used: brick_wall_006, cobblestone_floor_08, grey_roof_01, street_lamp_02.

**Not acquired (blockers):**
- **A Nordic architectural kit from Fab or Megascans:** needs an Epic account. The facade kit here was modelled from scratch instead. It is real modelled architecture, not sourced scans, and it is simpler than a commercial kit.
- **Realistic cars:** no CC0 realistic vehicles were reachable without a login. Traffic and parked cars are still the owner's sedan blockout and box cars. This is the most visible remaining weakness on the street.
- **Bicycles, winter trees, bus shelters:** not available on Poly Haven; not built yet.

## Phase 3: one street, rebuilt

**Kungsgatan, Norrmalm**, from the Sveavägen crossing east past the Kungstornen towers, plus the surrounding blocks (Hötorget, Konserthuset, the Hötorget high-rises).

- **Real layout.** 131 OSM building footprints with their mapped storey counts. Kungsgatan carries its mapped 4 lanes, and the Malmskillnadsgatan and Regeringsgatan bridges cross above it. Both towers use their mapped heights (61 m and 60 m).
- **Facades.** `Tools/blender/build_facade_kit.py` builds 22 modules on the 4.0 m × 3.5 m grid from the owner's building spec:
  - Windows with reveals, cross-bar frames, sills and moulded surrounds.
  - Iron-railed balconies on consoles.
  - Glazed shopfronts with fascia signs, recessed shop doors and stone entrance portals with panelled timber doors.
  - Dentilled cornices, string courses, parapets and mansard roofs with dormers.
  - Brick, functionalist and 1920s tower bay types; awnings and blade signs.
  - Snow modelled on ledges.
- **Identity per building.** Each block gets one of five styles and its own plaster colour and roof metal. Named buildings are handled specifically: the towers get a set-back crown and lantern, and Konserthuset is blue.
- **Street.** Scanned asphalt with slush at the edges, dashed lane lines, zebra crossings at junctions, granite kerbs, ploughed snowbanks, scanned paving slabs.
- **Dressing.** 248 placed props, 51 lamps (suspended on wires across Kungsgatan, as in Stockholm, and post lamps on side streets), and winter garlands of 624 bulbs.
- **Shops.** Lit interiors behind real glazing, with fourteen fictional shop signs.

Current counts: 2,734 facade bays, 97,219 kit instances.

## Phase 4: player character

**Done in the browser build and verified in rendered frames of the running game.** Not done: turn-in-place clips, a facial rig, and the story NPCs (see below).

- **Doudou.** A rigged human built in headless Blender (`Tools/blender/build_character.py`) on the MakeHuman base: 1.82 m, lavender OctOpus hoodie (#9B87B8) with chest logo and pocket, washed-blue jeans, white sneakers. 52-joint skeleton, 49,202 triangles, textures up to 1024 px, 3.5 MB.
- **Animation.** Seven clips at 30 fps, all looping cleanly in place: Idle, Walk, Run, Talk, Interact, Agree, HeadShake. Idle, Walk, Run, Agree and HeadShake are retargeted motion capture; Talk and Interact are hand-keyed.
- **In the game.** The character is driven by a small state machine with cross-fades: Idle below 0.15 m/s, Walk up to 2.4 m/s, Run above that, with playback speed matched to ground speed. Talk plays while Doudou speaks in dialogue, and Interact plays when the player uses something. Turning is a smoothed heading change with a lean into the turn.
- **Camera.** Closer over-the-shoulder framing (3.9 m, offset 0.55 m), and the camera now pulls in instead of passing through walls.
- **Pedestrians.** Four rigged variants (a man in his 50s, a woman around 30, a woman in her 60s, a man in his 20s) at about 30,000 triangles each, with clothing tints for variety. 30 walk the streets; those beyond 150 m are not drawn or animated.

**Shortfalls, stated plainly:**
- There are no turn-in-place clips; the turn is procedural.
- The face is a generic MakeHuman face with a neutral expression, not a likeness of the reference art, and it has no facial rig, so lips do not move in dialogue.
- The hoodie reads slightly puffy and has no ribbed cuffs. The hair is a textured shell, not strands.
- Talk and Interact are serviceable keys, not motion capture, and the fingers do not articulate.
- One pedestrian's trouser leg clips her long coat on forward swings; another's shoe dips about 2 cm into the ground while walking.
- The pedestrians wear jackets, cardigans and knitwear, because no winter coat or hat assets with a usable licence were found.
- **Story NPCs (Noor, Sami and the others) are still the old procedural figures.** Dedicated rigged versions are being built with the same pipeline.

Blender QA renders of every character are in `docs/character_renders/`.

## Phase 5: lighting

- Physically based materials replace the cel ramp. The ink-outline look is still in the code behind one switch (`INK`), off by default.
- Image-based lighting from the two HDRIs, scaled by time of day.
- Sun from the real solar model, with a 4096 px shadow map.
- Per-window interior lighting: about a third of windows are lit, in varied warm and cool tones.
- Pooled street-lamp lights, emissive shop interiors and signs, bloom, ACES tone mapping.

- Ambient occlusion computed from the depth buffer (12 samples within about 0.6 m), skipped on lit windows and lamps.
- A soft fill light on the camera side of the player, standing in for bounce light, so the face reads in shade and at night.
- A High/Low graphics switch in the top bar. Low turns off sun shadows and ambient occlusion and draws pedestrians only within 70 m. If the first seconds of play run below about 24 fps and the player has not chosen, the game drops to Low by itself.

Not done yet: screen-space reflections on wet asphalt, volumetric fog.

## Phase 6: evidence

Before/after pairs from the same camera, in `docs/visual_overhaul/`:

- `A_kungsgatan_dusk_before_after.jpg`
- `B_kungsgatan_day_before_after.jpg`
- `C_kungsgatan_night_before_after.jpg`
- `D_shopfront_dusk_before_after.jpg`
- `E_doudou_dusk_before_after.jpg`, `F_doudou_day_before_after.jpg`, `G_doudou_night_before_after.jpg`: the same three street cameras with the player and pedestrians in frame, old figures against rigged characters.

Facade kit QA renders (Blender Cycles) were inspected during the build.

**Performance measured here** (software rendering, 1280×720):

| Metric | Value |
|---|---|
| Draw calls per frame at the hero street | 524 |
| Triangles per frame, including the shadow pass and characters | ~3.75 million |
| Page load | ~14 s (the five character models add about 18 MB) |
| Frame time in software WebGL | 1.2–3.1 s depending on machine load (not representative of any GPU) |

**GPU frame rate has not been measured.** 3.75 million triangles is fine for a discrete GPU and likely too heavy for integrated graphics, which is what the Low setting and its automatic fallback are for. The fallback logic has not been exercised on real hardware.

## Honest status

The street now has real architecture, materials and street furniture on real geography, with a rigged, animated player and pedestrians. It is a clear step up from the prototype. It is not GTA-quality:

- The cars are still blockouts. Modelled replacements are in progress.
- The story NPCs are still procedural figures. Rigged replacements are in progress.
- The character has no facial animation and no turn-in-place clips.
- The facade kit is one modeller-day of work rather than a commercial kit.
- There are no reflections on wet asphalt, no bicycles, no winter trees and no bus shelters.
- Nothing has run on a GPU.
- Only this one area is rebuilt; the rest of the city is still the stylized blockout.

## Next steps, in order

1. Integrate the modelled cars and bicycle, and the rigged story NPCs, when their builds finish.
2. GPU profiling on real hardware; tune the Low setting from measurements.
3. Wet-road reflections; winter trees and bus shelters.
4. Extend the same pipeline to Stureplan, then Gamla Stan (new kit style: narrow 1700s fronts).
5. Port the kit, characters and placement to Unreal (the FBX kit is already exported to `Stockholm/Content/Import/FacadeKit`).
