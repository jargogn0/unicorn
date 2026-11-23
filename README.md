# STOCKHOLM

An open-world, third-person founder game set in a recognisable Stockholm, built in Unreal Engine 5. You start as an unknown founder in a Södermalm sublet with rent due in five days. You walk, drive, meet people and build a company, and eventually you can take it to San Francisco.

**Start with [BUILD_STATUS.md](BUILD_STATUS.md)**. It says exactly what exists, what was verified, and what is still blocked.

| Document | Contents |
|---|---|
| [GAME_DESIGN.md](GAME_DESIGN.md) | Pillars, progression, 13 chapters, Chapter 1 missions, narrative data language |
| [WORLD_DESIGN.md](WORLD_DESIGN.md) | Districts, geodata sources and licences, the production plan for GTA-class visuals |
| [STOCKHOLM_ECOSYSTEM.md](STOCKHOLM_ECOSYSTEM.md) | Sourced research behind the Founder Map |
| [TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md) | Modules, simulation core, world pipeline, performance plan |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Milestones A–E, remaining work, team, risks |
| [VISUAL_OVERHAUL.md](VISUAL_OVERHAUL.md) | Visual audit, licensed assets acquired, the rebuilt Kungsgatan, before/after evidence, gaps |
| [CREDITS.md](CREDITS.md) | Third-party assets, licences and required attributions |
| [ART_PIPELINE.md](ART_PIPELINE.md) | The four-step art pipeline (concept → Blender → rigging → Unreal) with per-step contracts |

## Layout

- `Stockholm/`: the Unreal project. `Source/StockholmSim` is the engine-independent simulation; `Source/Stockholm` is the gameplay module; `Content/Data` holds the story, world and ecosystem JSON.
- `Tools/geodata/`: OpenStreetMap fetch and processing (ODbL).
- `Tools/ue/`: Unreal editor bootstrap scripts.
- `Tests/`: CMake test runner for the simulation core.
- `WebPreview/`: a three.js playtest preview that uses the same game data. It is not the product.

## Quick start

Run the simulation tests (any machine with CMake and a C++17 compiler):

```bash
cmake -S Tests -B build && cmake --build build && ./build/sim_tests
```

Build the game (UE 5.5 and a GPU): see "Next build commands" in BUILD_STATUS.md.

Map data © OpenStreetMap contributors (ODbL 1.0). Other credits are in CREDITS.md. Characters, businesses and venues are fictional.
