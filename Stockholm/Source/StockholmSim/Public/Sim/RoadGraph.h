// STOCKHOLM — road network graph used by GPS routing, AI traffic and
// pedestrian navigation. Built from processed OpenStreetMap data
// (see Tools/geodata/process_osm.py and Content/Data/Geo/*.json).
#pragma once

#include "Sim/Geo.h"
#include "Sim/Json.h"

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace stockholm::sim {

enum class RoadClass : uint8_t {
    Motorway, Trunk, Primary, Secondary, Tertiary, Residential, Service,
    Pedestrian, Footway, Cycleway, Steps, Unknown
};

RoadClass RoadClassFromString(const std::string& s);
const char* RoadClassToString(RoadClass c);
bool IsDrivable(RoadClass c);
bool IsWalkable(RoadClass c);
double DefaultSpeedKmh(RoadClass c);
double DefaultWidthMetres(RoadClass c, int lanes);

struct RoadNode {
    int64_t osmId = 0;
    Vec2 pos;
    std::vector<uint32_t> outEdges; // edge indices leaving this node
};

struct RoadEdge {
    uint32_t from = 0;
    uint32_t to = 0;
    double lengthMetres = 0.0;
    double speedKmh = 30.0;
    RoadClass roadClass = RoadClass::Unknown;
    int lanes = 1;
    bool bridge = false;
    bool tunnel = false;
    bool againstOneway = false; // reverse twin of a one-way edge: walkable, not drivable
    std::string name;
    std::vector<Vec2> shape; // polyline including endpoints
};

enum class TravelMode : uint8_t { Drive, Walk };

struct Route {
    bool found = false;
    std::vector<uint32_t> nodes;
    std::vector<uint32_t> edges;
    double lengthMetres = 0.0;
    double seconds = 0.0;
    std::vector<Vec2> Polyline(const class RoadGraph& g) const;
};

class RoadGraph {
public:
    // Loads the "roads" section of a processed city JSON document:
    // { "nodes": [[id, x, y], ...], "ways": [{ "nodes":[...], "class":..., "oneway":bool, ...}] }
    bool LoadFromJson(const JsonValue& doc, std::string* error = nullptr);

    uint32_t AddNode(int64_t osmId, const Vec2& pos);
    void AddWay(const std::vector<uint32_t>& nodeIndices, RoadClass cls, bool oneway, int lanes,
                bool bridge, bool tunnel, const std::string& name, double speedKmh);

    size_t NodeCount() const { return nodes_.size(); }
    size_t EdgeCount() const { return edges_.size(); }
    const RoadNode& Node(uint32_t i) const { return nodes_[i]; }
    const RoadEdge& Edge(uint32_t i) const { return edges_[i]; }
    const std::vector<RoadEdge>& Edges() const { return edges_; }

    // Nearest node usable in the given mode. Returns UINT32_MAX if none.
    uint32_t NearestNode(const Vec2& p, TravelMode mode) const;

    // A* shortest path by travel time.
    Route FindRoute(uint32_t start, uint32_t goal, TravelMode mode) const;
    Route FindRoute(const Vec2& from, const Vec2& to, TravelMode mode) const;

    // Largest strongly-reachable component size from a node (diagnostics).
    size_t ReachableCount(uint32_t start, TravelMode mode) const;

private:
    bool EdgeAllowed(const RoadEdge& e, TravelMode mode) const;
    void RebuildSpatialIndex() const;

    std::vector<RoadNode> nodes_;
    std::vector<RoadEdge> edges_;
    std::unordered_map<int64_t, uint32_t> osmToIndex_;

    // Uniform grid spatial index (lazy).
    mutable bool indexDirty_ = true;
    mutable double cellSize_ = 50.0;
    mutable std::unordered_map<int64_t, std::vector<uint32_t>> grid_;
};

} // namespace stockholm::sim
