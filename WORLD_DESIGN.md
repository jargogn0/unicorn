# STOCKHOLM — World Design

## 1. Principle

Build a convincing, **geographically recognisable** Stockholm: the real islands, waterways, bridges, main roads and landmarks, in their real relationships. Start from documented, licensed data, not invented Scandinavian streets. Ship a small, excellent playable slice before expanding. Mark non-playable regions clearly; the Founder Map labels districts that aren't built as "not built yet".

## 2. Districts

`Content/Data/World/districts.json` has anchors and build status for each district.

| District | Role in play | Build status |
|---|---|---|
| Gamla Stan | History, tourism, atmospheric lanes, the bakery | Milestone A core |
| Norrmalm | Commercial centre, coworking, founders' breakfast | Milestone A (south part) |
| Södermalm | Home, cafés, creative scene, nightlife; Hornsgatan, Mariatorget, Slussen | Milestone A (north edge) |
| Kungsholmen | Residential, waterfront, City Hall; Mälarbröd office | Milestone A (east tip) |
| Östermalm / Stureplan | Investors, networking, the Investor Party | Not built |
| KTH / Valhallavägen | Student founders, research, hackathons | Not built |
| Kista | Telecom and enterprise customers | Not built |
| Vasastan, Solna | Connective districts | Not built |

**Milestone A slice:** bbox 59.3150–59.3360 N, 18.0480–18.0850 E, about 2.1 × 2.3 km. It contains the full Chapter 1 route: Söder apartment → Hornsgatan café → Gamla Stan bakery → Centralbron / Vasabron → Kungsholmen office → Strömgatan breakfast.

## 3. Geographic data sources

| Need | Source | Licence | Status |
|---|---|---|---|
| Roads, footprints, water, parks, names | OpenStreetMap via Overpass or Geofabrik extracts | ODbL 1.0 | Pipeline written; fetch blocked by the network (BUILD_STATUS.md) |
| Building heights | OSM `height` / `building:levels`; LiDAR-derived heights later | ODbL / see below | District defaults are flagged when tags are missing |
| Terrain (Söder heights, quay levels) | Lantmäteriet open elevation data, or Copernicus DEM GLO-30 | Check the current terms before use | Not started |
| Landmark detail | Public-domain and freely licensed reference photos; artists' site visits | Per asset | Not started |
| Photogrammetry | Own captures only (drone rules apply in central Stockholm; check permits) | Own | Investigation |

We do **not** extract or redistribute commercial map imagery, Street View, or Google or Apple 3D tiles.

## 4. Licensing and attribution

- Derived city data (`Content/Data/Geo/*.json`) is an ODbL derivative database. Keep `attribution` and `license` in the file and publish the processing code (`Tools/geodata`).
- Show "© OpenStreetMap contributors" on the in-game map and in the credits. `UStockholmSimSubsystem::GetMapAttribution` already supplies the string.
- Ecosystem pins carry their sources and precision. District-level pins are labelled "approximate area". Entries with only city-level precision get no pin at all, which is enforced by `ResolveEcosystemPosition` and tested.

## 5. Coordinate system

There is one local tangent plane for the whole city (origin Riksbron, 59.3275 N, 18.0680 E). Core x points east and y north, in metres. Unreal uses X = east and Y = south, in centimetres. Accuracy is better than 0.1 % over 10 km, verified against haversine in the tests. Kista (about 9 km away) stays in the same frame; World Partition and large-world coordinates handle the extent.

## 6. Reaching GTA-class visual quality (production plan)

The code builds a **correct layout**: blockout geometry from real data. The look comes from art production in Unreal Engine 5, in this order.

1. **Base kit: Epic City Sample tech.** City Sample is free for Unreal projects. Integrate its Mass Crowd, Mass Traffic and ZoneGraph setup, its vehicle and pedestrian LOD strategy (AnimToTexture), and its lighting approach. Replace its American architecture with Stockholm kits.
2. **Stockholm facade kits**, as Nanite modular sets in three style families:
   - Gamla Stan: 1600s–1700s plastered fronts in ochre, rust and cream, iron wall anchors, steep tin and copper roofs, 3–5 storeys, narrow lanes.
   - Södermalm and Kungsholmen: 1890s–1930s stone-plinth apartment blocks with bay windows, courtyards and 6–7 storeys.
   - Norrmalm: 1960s modernism around Sergels torg and the Hötorget towers, plus glass offices.

   Buy the closest licensed kits on Fab, then commission the Stockholm-specific pieces.
3. **Procedural assembly with PCG.** Each OSM footprint is filled with kit modules by district style, height and age; ground-floor shops face the main streets. The procedural extrusion in `ACityBuilder` is the input shape.
4. **Hero landmarks, built bespoke:** the Royal Palace, Storkyrkan, Riddarholmskyrkan's cast-iron spire, Tyska kyrkan, Riksdagshuset, Stadshuset's tower and three crowns, Katarina kyrka, Slussen and Katarinahissen, the bridges.
5. **Surfaces:** wet asphalt and puddles, snow accumulation driven by `MPC_Weather`, cobbles, granite quays, ice on Riddarfjärden in winter.
6. **Characters:** MetaHuman for the player and every story NPC. Mass Crowd uses MetaHuman-derived LODs. Animation comes from motion-matching locomotion plus conversation gestures (the `anim` tags in dialogue), recorded with mocap.
7. **Vehicles:** licensed Nordic-plausible fictional car models with physics assets. No real brands without licences; "Sami's Volvo" becomes a fictional estate car in the shipped game unless licensed.
8. **Lighting:** Lumen at Stockholm's low winter sun (the real solar model), long blue hours, sodium-warm street light, lit windows, Christmas lights in Kungsträdgården in January.

The brief rules out claiming AAA quality before rendered evidence exists. Every milestone review needs in-engine captures on target hardware.

## 7. The city without missions

The city should hold your attention even with no mission running:

- Ambient activities: cafés, bakeries, viewpoints, ferries, saunas, the laptop.
- People: pedestrians with routines, story NPCs at their own places, density that varies by hour and weather.
- Traffic, boats, buses (SL-style but fictional livery), cyclists in summer.
- Seasons and weather: snow, slush, rain, fog, midsummer light.
- Discovery: Founder Map pins unlock through people and places.

## 8. Expansion order

1. Milestone A slice.
2. Rest of Södermalm and Norrmalm.
3. Östermalm / Stureplan (Investor Party).
4. KTH / Valhallavägen.
5. Kista (a separate streaming region reached via the E18 / tunnelbana travel sequence).
6. San Francisco: SoMa, the Mission, Mission Bay, plus investor offices; its own visually distinct region.
