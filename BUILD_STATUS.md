# STOCKHOLM — Build Status

Last updated: 2026-11-23. Read this file before claiming anything works. It records what exists, what was verified and how, and what is still missing.

## Environment this build was produced in

| Item | Finding |
|---|---|
| Machine | Cloud container, 4 vCPU, 15 GB RAM, **no GPU** (software rendering only: SwiftShader/lavapipe) |
| Unreal Engine | **Not installed, and it can't be installed here.** Epic distributes UE5 behind an Epic account (binary) or a linked GitHub account (source). A source build needs ~150 GB of disk and many hours of compiling; this container has 61 GB and 4 cores. The editor also needs a GPU. |
| Compilers | g++ 13.3, clang, CMake 3.28 (used for the engine-independent core) |
| Network | The Overpass mirrors and Geofabrik still fail at the egress proxy (`ws_closed_mid_exchange`). The main OpenStreetMap API (`api.openstreetmap.org`) works and was used for the Kungsgatan extract. Poly Haven, ambientCG and the MakeHuman asset server also work. Fab, Quixel, Sketchfab and Mixamo need logins. |
| GitHub | Pushed to `jargogn0/unicorn`, branch `claude/zealous-gauss-tgc83b`. The repository was empty, so this is its only branch (and default); no pull request exists because there is no base branch. Git LFS is disabled for the repository, so binaries are stored as normal objects. |
| User machine | None attached (no Remote Control folders shared). |

## Status by component

Legend: **Verified** means compiled and tested here. **Written** means source exists but has not been compiled. **Missing** means not started.

### Engine-independent simulation core: `Stockholm/Source/StockholmSim`

**Verified.** It compiles warning-free under `-Wall -Wextra -Wshadow -Wconversion -Werror -fno-exceptions -fno-rtti`, which mirrors Unreal's constraints. 20 tests and 318 checks pass (`Tests/sim_tests.cpp`):

- JSON parser/writer (no exceptions; UTF-8, surrogate pairs, errors).
- Geo projection (WGS84 local tangent plane ↔ Unreal axes), ear-clipping triangulation, footprint extrusion with outward normals, and road ribbons.
- Road graph: A* by travel time, one-way rules (pedestrians may walk against them), nearest-node grid index.
- World clock: calendar, Swedish DST, and the **real solar position for Stockholm**. The tests check a mid-January sunrise around 08:35, sunset around 15:15, and a midsummer noon elevation of about 54°.
- Seasonal weather Markov model: deterministic per seed; snow in winter, never in July.
- Founder state: 18 stats, rent cycle, recoverable eviction, cap table (SAFE conversion, priced rounds, option pool, board control), negotiation model.
- Data-driven missions (8 objective types, branching, deadlines, timers, recoverable failure), dialogue (timed choices, conditional routing on NPC memory), commitments, relationships, phone, Founder Map discovery, NPC routines, versioned save/load.
- The OSM city model loads processed OSM output (fixture test).
- **Four complete headless playthroughs of Chapter 1:**
  - Golden path.
  - Frozen demo → "Another Door" → low price → borrowing rent from Sami.
  - Late for Noor → retry the next day.
  - Broken promise remembered by an NPC.
- Save/load in the middle of a mission resumes identically.

### Chapter 1 content: `Stockholm/Content/Data/Story`

**Verified through the tests above.** It contains the opening plus missions m00, m01, m02, m02b and m03, 13 dialogues and 7 fictional NPCs. `ContentDatabase::Validate()` reports zero problems. Chapters 2–13 are **design only** (`chapters.json`, `content_status`).

### Stockholm ecosystem dataset: `Content/Data/Ecosystem/stockholm_ecosystem.json`

**Written and checked for structure.** It has 39 entries: 23 verified and 16 partially verified, with sources cited. No coordinates were invented: every `lat/lon` is null until geocoded. 17 entries have only city-level precision and are listed in the directory without a map pin. The facts come from web research done on 2026-11-23 and should be re-verified before release; Wikipedia rate-limited part of the research. See `STOCKHOLM_ECOSYSTEM.md`.

### Unreal Engine 5 project: `Stockholm/`

**Written, not compiled, not run.** It targets UE 5.5. The API usage was written carefully, but it has never been through UnrealBuildTool, so expect a round of compile fixes. It contains:

- `Stockholm.uproject`, the two targets, two modules (StockholmSim, Stockholm), configs (Lumen, Nanite, VSM, TSR, Enhanced Input, data staging), and scalability tiers.
- `UStockholmSimSubsystem`: owns `FounderSim` and the city model, ticks time, autosaves, broadcasts events, and exposes the full Blueprint API.
- `AStockholmCharacter`: third-person character with a spring-arm camera, jog/sprint, slower movement on snow, and an interaction component with custom-depth highlight.
- `AStockholmPlayerController` and `UStockholmInputConfig`: Enhanced Input actions and contexts are **created in C++**, for keyboard/mouse and gamepad, separately on foot and in vehicles.
- `AStockholmVehicle`: Chaos wheeled vehicle tuned as a front-wheel-drive estate car. Tyre friction scales with simulated snow and wetness. Enter/exit includes a safe-exit search.
- `ACityBuilder`: procedural blockout from OSM data (extruded buildings, roads, raised bridges, water, land and parks), chunked into 250 m tiles with collision.
- `AWorldAtmosphere`: sun and moon from the real solar model, sky, fog, clouds, Niagara precipitation hooks, a `MPC_Weather` material parameter collection, and pooled street lights.
- `ATrafficManager`: instanced kinematic traffic on the road graph. `AAmbientPopulation`: instanced pedestrians.
- `AStoryNpc`, `AStoryProp`, `AMissionWorldDirector`: location triggers, routine-driven NPCs whose placement missions can override, and scripted world events.
- `ACinematicDirector`: data-driven camera shots (`Content/Data/Cinematics/opening.json`).
- `AStockholmHUD`: a Canvas HUD covering money, clock, objective timer, prompt, minimap with GPS route, dialogue with timed choices, decisions, the demo-repair minigame, the phone and the Founder Map.

**Not done (requires the editor):**

- No `.umap`. The World Partition map `Stockholm_MilestoneA` has to be created; see the next build command.
- No art assets: no characters (it falls back to the UE template mannequin path), no car mesh (it falls back to the Vehicle template path), no materials (`M_CityBlockout`, `M_HarbourWater`, `MPC_Weather`), no Niagara systems, no audio.
- No apartment interior level instance. The opening shots assume one at the apartment anchor.
- No UMG/CommonUI widgets; the Canvas HUD is functional placeholder UI.
- The procedural mesh winding (`bFlipWinding`) and the sun-yaw convention must be checked visually in the editor.
- No profiling has been done.

### Geodata pipeline: `Tools/geodata`

**Written; verified on a fixture and on one real extract.** The Kungsgatan area was fetched through the main OSM API (`osm_xml_to_overpass.py` converts it) and processed into `Content/Data/Geo/hero_kungsgatan_city.json` (132 buildings, 343 ways). The full Milestone A slice has **not** been fetched yet: `fetch_osm.py` targets Overpass, which is still blocked, and the main API limits request size, so the slice needs tiling. Until `milestone_a_city.json` exists, the Unreal city builder logs a warning and builds nothing.

### Browser preview: `WebPreview/`

**Running, published privately as an Artifact:** https://claude.ai/artifact/KeK5mcPKnLk6K8Q9SD7EAZ. It is a three.js port of the simulation that runs the same mission, dialogue, NPC and ecosystem JSON.

Verified in headless Chromium with software WebGL: no console errors, the opening cinematic plays, phone reply → laptop → mission advance works, and talking to Noor, driving, night lighting and the Founder Map all work.

Limits:

- Outside Kungsgatan the city is **hand-placed and stylized**, not OSM, and its buildings are procedural boxes.
- Venue interiors are simple boxes; outside the Kungsgatan area the traffic drives through blockout streets.
- It ran at under 1 fps in software rendering; GPU frame rate has not been measured.

It is a preview for playtesting the story and systems. **It is not the game and does not represent the target visual quality.**

### Visual overhaul (in progress)

See **VISUAL_OVERHAUL.md** for the audit, licences, evidence and gaps. In short:

- **Verified in the browser build:** Kungsgatan (Norrmalm) rebuilt from real OpenStreetMap footprints with a Blender-modelled facade kit, Poly Haven CC0 scanned materials, HDRI lighting and 248 street props. Before/after frames are in `docs/visual_overhaul/`.
- **Verified in the browser build:** a rigged, animated Doudou (lavender OctOpus hoodie, jeans, white sneakers; idle, walk, run, talk and interact) and four rigged pedestrian variants, built in Blender from MakeHuman CC0/CC BY assets. Depth-based ambient occlusion and a High/Low graphics switch.
- **Verified in the browser build:** rigged story NPCs (Noor, Sami, Aditi, Elin, Mateo and Helena; the landlord has no model) and 80 modelled winter trees along Sveavägen.
- **Verified in the browser build:** modelled cars (estate, saloon, hatchback) for the player, traffic and 30 parked cars, plus 42 parked bicycles; turn-on-the-spot for the player.
- **Not done:** facial animation, wet-road reflections, bus shelters, any measurement on a real GPU.
- **Art direction:** the owner's packs (`ArtReference/`, `Stockholm/Content/Import/StarterPack`) are filed and described in ART_PIPELINE.md. The protagonist is Doudou BA, founder of OctOpus (`Content/Data/Story/player.json`).

## Quality bar status (honest)

| Target | Status |
|---|---|
| GTA-class characters | **Not reached.** The browser build has MakeHuman-based rigged characters with retargeted motion capture. GTA-class needs MetaHuman (or a licensed character set), facial animation and a full motion-capture set inside UE5. |
| GTA-class city | **Not reached.** One street (Kungsgatan) is rebuilt from OSM with a modelled facade kit and scanned materials. GTA-class needs UE5, licensed kits or City Sample tech, wider real data and artists. Everything outside that street is blockout. |
| Lumen/Nanite visuals | Configured in `.ini`, never rendered. |
| Performance | Not profiled. |

## Next build commands

On a machine with UE 5.5 and a GPU (Windows example; Linux uses `Engine/Build/BatchFiles/Linux/Build.sh`):

```bat
"C:\Program Files\Epic Games\UE_5.5\Engine\Build\BatchFiles\Build.bat" StockholmEditor Win64 Development -Project="%CD%\Stockholm\Stockholm.uproject" -WaitMutex
```

Then generate the city and create the map:

```bash
bash Tools/geodata/build_city.sh
```

```bat
"C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "%CD%\Stockholm\Stockholm.uproject" -run=pythonscript -script="%CD%\Tools\ue\create_milestone_a_map.py"
```

Core tests run anywhere:

```bash
cmake -S Tests -B build && cmake --build build && ./build/sim_tests
```

## Running record of unfinished work

1. Get UE 5.5 onto a GPU machine (the user's workstation via Remote Control, or a cloud GPU VM). Compile and fix.
2. Unblock OSM: allow the hosts at the egress level, or download a Geofabrik extract elsewhere and commit `milestone_a.overpass.json` to `Tools/geodata/cache`.
3. Create `Stockholm_MilestoneA` (World Partition), the blockout materials and MPC, and the apartment level instance.
4. Characters: MetaHuman founder and 6 story NPCs, plus a locomotion and conversation animation set.
5. Vehicles: licensed estate car and traffic set with physics assets.
6. City art: a Stockholm facade kit (Gamla Stan, Södermalm 1890s blocks, Norrmalm 1960s), hero landmarks, a terrain DEM.
7. UI: replace the Canvas HUD with UMG/CommonUI.
8. Audio: ambience, vehicles, VO casting.
9. Profiling pass and platform scalability verification.
10. Chapters 2–13 content; San Francisco region.
