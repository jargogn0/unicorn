# STOCKHOLM — Technical Architecture

## 1. Platform decision

- **Engine:** Unreal Engine 5.5+, with C++ for systems and Blueprints for content glue.
- **World:** World Partition with a 128 m runtime grid, plus One File Per Actor so many people can edit the city.
- **Rendering:** Lumen (hardware ray tracing when available), Nanite, Virtual Shadow Maps, TSR.
- **Input:** Enhanced Input. Vehicles use Chaos Vehicles.
- **Crowds and traffic:** Mass Entity, Mass Crowd and Mass Traffic, following City Sample's ZoneGraph approach.
- **Characters:** MetaHuman.
- **Rendering hardware interfaces:** Windows is DX12 SM6; Linux is Vulkan SM6.

Rejected alternatives:

- A web engine: the brief forbids it. The `WebPreview/` folder is a disposable playtest tool, not the product.
- Unity: the brief specifies Unreal.

## 2. Module layout

```
Stockholm/                      UE project
  Source/StockholmSim/          engine-independent C++17 simulation (no UE types)
    Public/Sim/*.h  Private/Sim/*.cpp      ← also built by Tests/CMakeLists.txt
  Source/Stockholm/             game module (UE types)
    Core/        settings, sim subsystem, save game, game mode, BP types
    Player/      character, controller, runtime Enhanced Input, interaction
    Vehicles/    Chaos vehicle + wheels
    World/       city builder, atmosphere/weather/lights, traffic, pedestrians
    Narrative/   story NPCs, props, mission world director, cinematics
    UI/          HUD (Canvas now → UMG/CommonUI later)
  Content/Data/                 runtime JSON (staged as loose files)
    Story/ World/ Ecosystem/ Geo/ Cinematics/ manifest.json
Tools/geodata/                  OSM fetch → process → city JSON (ODbL)
Tools/ue/                       editor Python (map/material bootstrapping)
Tests/                          CMake test runner for StockholmSim
WebPreview/                     three.js playtest preview (same JSON data)
```

**Why split out an engine-independent core?** It makes the gameplay rules testable in CI without the engine (20 tests run in seconds). It also lets us verify the logic even where Unreal can't run, and lets writers iterate on JSON with fast validation (`ContentDatabase::Validate`). The core avoids exceptions and RTTI, compiles with `-Werror -Wshadow -Wconversion`, and its helper namespaces have unique names so they are safe in Unreal unity builds.

## 3. Simulation core (`stockholm::sim`)

| File | Responsibility |
|---|---|
| `Json` | Parser and writer; tolerates `//` comments in hand-authored data. |
| `Geo` | Local tangent projection (origin 59.3275 N, 18.0680 E). Unreal mapping: X = east, Y = south, cm. Ear clipping, extrusion, ribbons. |
| `RoadGraph` | OSM-derived graph; A* by travel time; one-way twin edges (walkable, not drivable); grid index. |
| `City` | Processed OSM document → buildings, areas, road polylines, graph. |
| `WorldClock` | Calendar, DST, NOAA solar position, seasonal weather Markov chain, surface wetness and snow cover. |
| `FounderState` | 18 stats, rent, cap table (SAFE / priced / pool / board), funding offers, negotiation model. |
| `Content` | NPCs, dialogue (with routing branches), missions, chapters, locations, districts, ecosystem; cross-reference validator. |
| `FounderSim` | Facade: time, economy, conditions/effects interpreter, missions, dialogue, commitments, phone, discovery, routines, events, save/load. |

**Narrative data language.** Conditions and effects are JSON objects interpreted at runtime, documented in GAME_DESIGN.md §9. Writers add missions without recompiling. Failure always routes to another objective or a recoverable state.

**Events.** `FounderSim` queues `SimEvent`s. `UStockholmSimSubsystem` drains them each tick and broadcasts `OnSimEvent`. The HUD, `ACinematicDirector` and `AMissionWorldDirector` subscribe; world hooks are named `world_event` ids such as `cinematic:opening`, `weather:heavy_snow` and `travel:taxi:<loc>`.

**Saves.** `FounderSim::Save()` writes versioned JSON (`kSaveVersion`). `UStockholmSaveGame` wraps it, together with the player and vehicle transforms. A schema change bumps the version, and migration lives in `Load`. Saving during a conversation is refused, so conversations stay atomic. Autosave runs every 120 s.

## 4. World construction pipeline

1. **Fetch.** `Tools/geodata/fetch_osm.py` queries Overpass for a slice bbox and caches the result.
2. **Process.** `process_osm.py` projects coordinates and classifies roads, keeping one-way, lane, bridge and layer tags. It assembles multipolygons, derives building heights from the `height` or `building:levels` tags (falling back to a district default of 18 m, flagged), and marks landmarks. It also reports gameplay locations that fall inside buildings, so they can be snapped.
3. **Runtime blockout.** `ACityBuilder` generates tiled ProceduralMeshComponents with collision from the city JSON. This gives a playable, geographically correct layout immediately.
4. **Bake.** Planned: `Tools/ue/bake_city.py` converts tiles into static mesh actors in World Partition cells. The PCG graphs `PCG_StockholmBlock` then replace extrusions with modular facade-kit assemblies, chosen by district style and building age, as Nanite meshes. Landmarks are flagged for hand-built hero assets.
5. **Terrain.** Planned: a DEM (Lantmäteriet open elevation data or Copernicus GLO-30; check the licence) for the Södermalm heights, Slussen levels and quay walls.

## 5. Gameplay systems in Unreal

- **Character:** `ACharacter` with a spring-arm camera. Snow reduces maximum speed, and interaction uses an overlap plus a view cone. MetaHuman plus a motion-matching locomotion set replaces the template mannequin.
- **Vehicles:** `AWheeledVehiclePawn` with Chaos. Tyre friction scales with simulated snow and wetness (`SetWheelFrictionMultiplier`), so the weather is felt in driving.
- **Traffic:**
  - Now: kinematic instanced cars on road-graph edges (right-hand traffic, gap keeping, recycled around the player).
  - Target: Mass Traffic on ZoneGraph lanes generated from the same graph, with signals at OSM `highway=traffic_signals` nodes.
- **Pedestrians:**
  - Now: instanced agents on walkable edges, with density scaled by hour and precipitation.
  - Target: Mass Crowd with AnimToTexture LODs and MetaHuman close-up actors.
- **NPCs:** the simulation decides where each NPC is (from the routine, with mission overrides). The world layer only moves bodies there, so it can never disagree with the story state.
- **Atmosphere:** sun and moon from the solar model, plus fog, clouds, precipitation (Niagara) and `MPC_Weather` (wetness and snow for puddles, snow-cap materials). Street lights use a pooled set of real lights near the player, with emissive lamps elsewhere.

## 6. UI

The current UI is a Canvas HUD, so the game is playable without assets. The target is CommonUI widgets bound to the same `UStockholmSimSubsystem` UFUNCTIONs: phone apps (Messages, Bank, People, Calendar, Maps), a Founder Map rendered to a texture from the city model with category filters, and dialogue with a camera rig chosen by each node's `camera` tag.

## 7. Performance plan

| Tier | Target | Settings |
|---|---|---|
| Epic | RTX 3070 / RX 6800, 1440p60 with TSR | HW Lumen, VSM, 120 pedestrians, 40 cars |
| High | Current-gen consoles, 4K30 / 1440p60 | SW Lumen, 80 / 30 |
| Medium / Low | Steam Deck class | SSGI, CSM, 40 / 15 |

Budgets on the Epic tier:

- Game thread under 8 ms. The simulation tick is under 0.1 ms; the core is O(active missions).
- Mass crowd under 2 ms.
- Streaming: 128 m cells, a 512 m loading range on foot, extended in vehicles.

Profiling has not happened yet; see BUILD_STATUS.md.

## 8. Testing

- **Core:** `cmake -S Tests -B build && cmake --build build && ./build/sim_tests`. This covers four full Chapter 1 playthroughs, deterministic weather, the solar maths, cap-table maths, the OSM-to-city path, and save round-trips.
- **Content:** `ContentDatabase::Validate()` runs at startup in Unreal (warnings in the log) and in the tests (must be empty).
- **Planned:** Unreal automation tests (Gauntlet) for the build-and-boot smoke test, the mission spline drive-through and save-load in a map.

## 9. Data licensing

- **OSM-derived geometry** is ODbL 1.0: attribution in the credits and on the in-game map, and the derived database stays ODbL.
- **Ecosystem facts** come from cited public sources. Real people are never portrayed.
- **Characters, businesses and venues** are fictional.
- **Third-party assets** must be licensed for commercial redistribution in a game. MetaHuman and City Sample are licensed for Unreal Engine projects; check the current Epic terms at the time of integration.
