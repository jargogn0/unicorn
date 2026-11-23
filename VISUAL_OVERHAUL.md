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

The full machine-readable list with every file URL is `Assets/ThirdParty/polyhaven_manifest.json`. Re-download with `Tools/assets/fetch_polyhaven.py`.

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

In progress. A rigged MakeHuman-based Doudou (lavender hoodie, jeans, white sneakers) with retargeted locomotion clips is being built in headless Blender. **Until that lands, the character in the game is still the procedural stand-in**, and this phase is not done.

## Phase 5: lighting

- Physically based materials replace the cel ramp. The ink-outline look is still in the code behind one switch (`INK`), off by default.
- Image-based lighting from the two HDRIs, scaled by time of day.
- Sun from the real solar model, with a 4096 px shadow map.
- Per-window interior lighting: about a third of windows are lit, in varied warm and cool tones.
- Pooled street-lamp lights, emissive shop interiors and signs, bloom, ACES tone mapping.

Not done yet: ambient occlusion, screen-space reflections on wet asphalt, volumetric fog.

## Phase 6: evidence

Before/after pairs from the same camera, in `docs/visual_overhaul/`:

- `A_kungsgatan_dusk_before_after.jpg`
- `B_kungsgatan_day_before_after.jpg`
- `C_kungsgatan_night_before_after.jpg`
- `D_shopfront_dusk_before_after.jpg`

Facade kit QA renders (Blender Cycles) were inspected during the build.

**Performance measured here** (software rendering, 1280×720):

| Metric | Value |
|---|---|
| Draw calls per frame at the hero street | 553 |
| Triangles per frame, including the shadow pass | ~3.7 million |
| Page load | ~9 s |
| Frame time in software WebGL | ~2.7 s (not representative of any GPU) |

**GPU frame rate has not been measured.** 3.7 million triangles is fine for a discrete GPU and likely too heavy for integrated graphics. A quality switch (no shadow pass, fewer detail parts) is the first optimisation to add.

## Honest status

The street is a clear step up, with real architecture, materials and street furniture on real geography. It is not GTA-quality:

- The character is unfinished and the cars are blockouts.
- The facade kit is one modeller-day of work rather than a commercial kit.
- There is no ambient occlusion or reflections.
- Nothing has run on a GPU.
- Only this one area is rebuilt; the rest of the city is still the stylized blockout.

## Next steps, in order

1. Finish and integrate the rigged character; replace pedestrians with animated variants.
2. Cars: obtain licensed vehicle models (the Unreal workstation can pull them from Fab), or model a proper sedan in Blender.
3. Ambient occlusion, wet-road reflections, a quality switch, and GPU profiling on real hardware.
4. Extend the same pipeline to Stureplan, then Gamla Stan (new kit style: narrow 1700s fronts).
5. Port the kit and placement to Unreal (the FBX kit is already exported to `Stockholm/Content/Import/FacadeKit`).
