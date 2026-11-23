# STOCKHOLM — Implementation Plan

A milestone is not done until it is integrated, visually inspected **in engine on target hardware**, and tested. Current state: BUILD_STATUS.md.

## Milestone A: Stockholm City (in progress)

**Done:**
- Engine-independent core with tests.
- Unreal project, gameplay C++ (character, Chaos car, procedural city builder, atmosphere, traffic, pedestrians, HUD).
- OSM pipeline, verified on a fixture.
- Browser playtest preview.

**Remaining:**
1. A UE 5.5 machine with a GPU (Remote Control on the user's workstation, or a cloud GPU VM). Compile and fix.
2. Fetch the OSM slice and generate `milestone_a_city.json`; snap gameplay locations using the `process_osm.py --locations` report.
3. Run `Tools/ue/create_milestone_a_map.py`. Verify mesh winding, the sun's direction and lighting.
4. Import a licensed car and the template mannequin as stand-ins; drive the full Chapter 1 route.
5. First art pass: blockout materials, wet and snow MPC, water, street lights, City Sample lighting reference.
6. Profile (Unreal Insights) and record frame captures in BUILD_STATUS.md.

**Exit criteria:** walk and drive Slussen → Gamla Stan → Centralbron → Kungsholmen at 60 fps on the Epic tier, with traffic, pedestrians, day/night and snow, and captures reviewed.

## Milestone B: Founder Map

**Done:**
- Sourced dataset (39 entries).
- Discovery and category model in the core.
- Canvas Founder Map in the HUD.
- A full interactive version in the preview.

**Remaining:**
- Geocode address-precision entries from OSM.
- Re-verify the partially verified entries.
- CommonUI map widget, waypoint to GPS, story cards with sources, and inspiration links from missions.

## Milestone C: The first 30 minutes

**Done:** opening plus m00–m03 data, simulation, dialogue, phone model, saves; four headless playthroughs.

**Remaining:**
- Apartment interior level instance; opening cinematic in engine (data-driven shots now, Sequencer later).
- Interiors for the café, bakery, office and breakfast venue.
- MetaHumans for Noor, Sami, Aditi, Elin, Mateo and the player.
- Conversation camera rig driven by `camera` tags; gesture set driven by `anim` tags.
- Phone UI in UMG; VO temp recordings.

## Milestone D: Living city

- Mass Crowd and Mass Traffic on ZoneGraph from the road graph; traffic signals; SL-style buses; boats.
- Pedestrian routines; ambient activities (sauna, ferry, meetups, KTH hackathon); shops and clothing; housing upgrades.
- Audio: ambience by district, weather, vehicles, interiors; music.
- World density pass; scalability tiers verified.

## Milestone E: Full campaign

- Chapters 2–13 content, designed in GAME_DESIGN.md §5–7.
- Östermalm, KTH and Kista regions; San Francisco region (separate World Partition map); the four routes to San Francisco.
- Funding, hiring and office systems built on the existing cap-table and stat models.
- Endings.

## Team the plan assumes

| Area | Roles |
|---|---|
| Engineering | Gameplay (2), tools/pipeline (1), rendering/performance (1) |
| World | Environment artists (4+), technical artist (1), lighting (1) |
| Characters | Character artists (2), animators (2), mocap |
| Narrative | Writer/narrative designer (2) |
| Audio | 1 |
| QA | 2 |

The code in this repository is the systems foundation. GTA-class content needs the art team and Unreal toolchain above.

## Risks

| Risk | Mitigation |
|---|---|
| OSM access blocked in CI | Commit the cached extract; ODbL allows redistribution with attribution |
| Ecosystem facts go stale | `researched_on` date; re-verify before each release; status is shown in game |
| Real people and brands | Fictional characters only; company stories are inspiration, never portrayal; no real car brands without a licence |
| Scope | Ship the Milestone A–C vertical slice before expanding the map |
