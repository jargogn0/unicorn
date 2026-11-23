// STOCKHOLM — processed city model (output of Tools/geodata/process_osm.py).
// Shared by the in-engine world builder, GPS, minimap and Founder Map.
// Source data © OpenStreetMap contributors, ODbL 1.0 — attribution required
// in credits and on the in-game map (see WORLD_DESIGN.md §4).
#pragma once

#include "Sim/Geo.h"
#include "Sim/Json.h"
#include "Sim/RoadGraph.h"

#include <string>
#include <vector>

namespace stockholm::sim {

struct Building {
    int64_t osmId = 0;
    std::vector<Vec2> outer;               // CCW after load
    std::vector<std::vector<Vec2>> holes;  // courtyards (rendered as separate walls for now)
    double heightMetres = 18.0;
    double minHeightMetres = 0.0;
    int levels = 0;
    std::string name;
    std::string kind;       // OSM building=* value
    std::string roofShape;  // OSM roof:shape
    std::string colour;     // OSM building:colour (hex or name) if present
    bool landmark = false;  // church, palace, public building with a name…
    bool heightFromData = false; // true when OSM had height/levels; false = district default
};

struct AreaPolygon {
    int64_t osmId = 0;
    std::string kind; // water | park | plaza | land
    std::string name;
    std::vector<Vec2> outer;
    std::vector<std::vector<Vec2>> holes;
};

struct CityBounds {
    double minX = 0, minY = 0, maxX = 0, maxY = 0;
    bool Contains(const Vec2& p) const { return p.x >= minX && p.x <= maxX && p.y >= minY && p.y <= maxY; }
};

class CityModel {
public:
    bool LoadFromJson(const JsonValue& doc, std::string* error = nullptr);
    bool LoadFromFile(const std::string& path, std::string* error = nullptr);

    double originLat = GeoProjection::kDefaultOriginLat;
    double originLon = GeoProjection::kDefaultOriginLon;
    std::string attribution;
    std::string sourceTimestamp;
    CityBounds bounds;
    RoadGraph roads;
    std::vector<Building> buildings;
    std::vector<AreaPolygon> areas;
    // Raw road polylines for rendering (one per OSM way), with metadata.
    struct RoadLine {
        std::vector<Vec2> points;
        RoadClass roadClass = RoadClass::Unknown;
        double widthMetres = 6.0;
        bool bridge = false;
        bool tunnel = false;
        int layer = 0;
        std::string name;
    };
    std::vector<RoadLine> roadLines;

    // Whether a point lies on water (inside a water area, not in its holes).
    bool IsWater(const Vec2& p) const;
    size_t BuildingsWithSourcedHeight() const;
};

} // namespace stockholm::sim
