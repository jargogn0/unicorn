# STOCKHOLM (Founder City VI) — GTA-Style Art Direction & UE5 Handoff Bible

## 1. Visual Identity
- **Style:** Grand Theft Auto VI illustrated loading-screen / stylized AAA realism hybrid — bold black ink outlines, cel-shaded lighting ramps, vibrant golden-hour and winter-evening color contrast, grounded Stockholm & San Francisco architecture.
- **Unreal Engine 5 Post-Process Setup (`PP_GTA_Stylized`):**
  - Depth + Normal Sobel edge-detection post-process material (`OutlineWidth = 1.5px`, `OutlineColor = #0D0B12`).
  - 3-band stylized shadow ramp blended over Lumen GI so Stockholm landmarks retain architectural depth while characters and vehicles pop like GTA cover art.

## 2. Included Production Specs & Blueprints
- `00_ART_DIRECTION/ART_DIRECTION_BIBLE.md` & `STK_ART_KEY_VISUAL_FOUNDER_GTA_001.png`
- `01_CITY_STOCKHOLM/` — Sergels Torg & Stureplan environment plates
- `02_CHARACTERS/CHARACTER_ROSTER_SPECS.md` & Founder Turnaround/Detail sheets
- `03_VEHICLES/VEHICLE_SPECS.md` — Scandinavian Sedan, Compact EV, Executive SUV, Taxi, Delivery Van, SL City Bus
- `04_BUILDINGS/STOCKHOLM_BUILDING_SPECS.md` & Norrmalm–Stureplan block overview
- `05_INTERIORS/INTERIOR_BLUEPRINTS.md` — Starter Studio Apartment, Specialty Café, VC Boardroom, Coworking Space
- `06_PROPS/MODULAR_PROPS_SPEC.md` — Swedish street furniture, SL bus shelter, streetlamps, bicycles, laptop/phone props
- `07_MATERIAL_REFERENCES/UE5_GTA_SHADER_SPECS.md` — PBR + cel-shading parameter tables
- `08_CINEMATICS/ACT1_STORYBOARD_SCRIPT.md` — 6-scene cinematic breakdown from Day Zero Stockholm to San Francisco
- `09_SAN_FRANCISCO/SF_DISTRICT_SPEC.md` — Act II Golden Gate / SoMa unlock rules
- `10_ASSET_MANIFEST/asset_manifest.json` — Structured JSON manifest for Claude Code UE5 automation
