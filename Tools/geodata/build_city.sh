#!/usr/bin/env bash
# Fetch + process the Milestone A slice into the file the game loads.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 Tools/geodata/fetch_osm.py --slice milestone_a
python3 Tools/geodata/process_osm.py Tools/geodata/cache/milestone_a.overpass.json \
  Stockholm/Content/Data/Geo/milestone_a_city.json --locations Stockholm/Content/Data/World/locations.json
