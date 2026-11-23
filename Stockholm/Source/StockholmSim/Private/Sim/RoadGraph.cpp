#include "Sim/RoadGraph.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <queue>

namespace stockholm::sim {

namespace road_detail {
struct ClassInfo {
    RoadClass cls;
    const char* name;
    double speedKmh;
    double laneWidth;
};
// Speeds follow Swedish urban defaults (30/40/50 km/h zones in Stockholm innerstad).
const ClassInfo kClassTable[] = {
    {RoadClass::Motorway, "motorway", 70.0, 3.5},
    {RoadClass::Trunk, "trunk", 60.0, 3.5},
    {RoadClass::Primary, "primary", 50.0, 3.25},
    {RoadClass::Secondary, "secondary", 40.0, 3.25},
    {RoadClass::Tertiary, "tertiary", 40.0, 3.0},
    {RoadClass::Residential, "residential", 30.0, 3.0},
    {RoadClass::Service, "service", 20.0, 3.0},
    {RoadClass::Pedestrian, "pedestrian", 5.0, 3.0},
    {RoadClass::Footway, "footway", 5.0, 2.0},
    {RoadClass::Cycleway, "cycleway", 18.0, 2.0},
    {RoadClass::Steps, "steps", 2.5, 2.0},
    {RoadClass::Unknown, "unknown", 20.0, 3.0},
};
const ClassInfo& Info(RoadClass c) {
    for (const ClassInfo& ci : kClassTable) {
        if (ci.cls == c) return ci;
    }
    return kClassTable[sizeof(kClassTable) / sizeof(kClassTable[0]) - 1];
}
constexpr double kWalkSpeedMps = 1.4;

int64_t CellKey(int64_t cx, int64_t cy) { return (cx << 32) ^ (cy & 0xffffffffLL); }
} // namespace road_detail

RoadClass RoadClassFromString(const std::string& s) {
    for (const auto& ci : road_detail::kClassTable) {
        if (s == ci.name) return ci.cls;
    }
    // Map OSM link roads and synonyms onto base classes.
    if (s == "motorway_link") return RoadClass::Motorway;
    if (s == "trunk_link") return RoadClass::Trunk;
    if (s == "primary_link") return RoadClass::Primary;
    if (s == "secondary_link") return RoadClass::Secondary;
    if (s == "tertiary_link") return RoadClass::Tertiary;
    if (s == "living_street" || s == "unclassified") return RoadClass::Residential;
    if (s == "path" || s == "corridor") return RoadClass::Footway;
    return RoadClass::Unknown;
}

const char* RoadClassToString(RoadClass c) { return road_detail::Info(c).name; }

bool IsDrivable(RoadClass c) {
    switch (c) {
        case RoadClass::Motorway: case RoadClass::Trunk: case RoadClass::Primary:
        case RoadClass::Secondary: case RoadClass::Tertiary: case RoadClass::Residential:
        case RoadClass::Service:
            return true;
        default:
            return false;
    }
}

bool IsWalkable(RoadClass c) {
    return c != RoadClass::Motorway && c != RoadClass::Trunk;
}

double DefaultSpeedKmh(RoadClass c) { return road_detail::Info(c).speedKmh; }

double DefaultWidthMetres(RoadClass c, int lanes) {
    return road_detail::Info(c).laneWidth * std::max(1, lanes);
}

std::vector<Vec2> Route::Polyline(const RoadGraph& g) const {
    std::vector<Vec2> out;
    for (size_t i = 0; i < edges.size(); ++i) {
        const RoadEdge& e = g.Edge(edges[i]);
        for (size_t k = (i == 0 ? 0 : 1); k < e.shape.size(); ++k) out.push_back(e.shape[k]);
    }
    return out;
}

uint32_t RoadGraph::AddNode(int64_t osmId, const Vec2& pos) {
    const auto it = osmToIndex_.find(osmId);
    if (it != osmToIndex_.end()) return it->second;
    const uint32_t idx = static_cast<uint32_t>(nodes_.size());
    RoadNode n;
    n.osmId = osmId;
    n.pos = pos;
    nodes_.push_back(n);
    osmToIndex_[osmId] = idx;
    indexDirty_ = true;
    return idx;
}

void RoadGraph::AddWay(const std::vector<uint32_t>& ids, RoadClass cls, bool oneway, int lanes,
                       bool bridge, bool tunnel, const std::string& name, double speedKmh) {
    if (ids.size() < 2) return;
    if (speedKmh <= 0.0) speedKmh = DefaultSpeedKmh(cls);
    // One edge per consecutive node pair: keeps intersections exact because
    // processed data splits ways at shared nodes only implicitly.
    for (size_t i = 0; i + 1 < ids.size(); ++i) {
        const uint32_t a = ids[i];
        const uint32_t b = ids[i + 1];
        if (a == b || a >= nodes_.size() || b >= nodes_.size()) continue;
        const Vec2 pa = nodes_[a].pos;
        const Vec2 pb = nodes_[b].pos;
        const double len = std::hypot(pb.x - pa.x, pb.y - pa.y);
        auto addEdge = [&](uint32_t f, uint32_t t, bool against) {
            RoadEdge e;
            e.from = f;
            e.to = t;
            e.lengthMetres = len;
            e.speedKmh = speedKmh;
            e.roadClass = cls;
            e.lanes = lanes;
            e.bridge = bridge;
            e.tunnel = tunnel;
            e.againstOneway = against;
            e.name = name;
            e.shape = {nodes_[f].pos, nodes_[t].pos};
            const uint32_t ei = static_cast<uint32_t>(edges_.size());
            edges_.push_back(std::move(e));
            nodes_[f].outEdges.push_back(ei);
        };
        addEdge(a, b, false);
        // The reverse twin always exists so pedestrians can walk against
        // one-way traffic; drive mode rejects it via againstOneway.
        addEdge(b, a, oneway);
    }
}

bool RoadGraph::LoadFromJson(const JsonValue& doc, std::string* error) {
    const JsonValue& roads = doc.Has("roads") ? doc["roads"] : doc;
    const JsonValue& nodes = roads["nodes"];
    const JsonValue& ways = roads["ways"];
    if (!nodes.IsArray() || !ways.IsArray()) {
        if (error) *error = "road JSON missing 'nodes' or 'ways' arrays";
        return false;
    }
    for (const JsonValue& n : nodes.Elements()) {
        if (n.Size() < 3) continue;
        AddNode(static_cast<int64_t>(n[0].AsNumber()), Vec2{n[1].AsNumber(), n[2].AsNumber()});
    }
    for (const JsonValue& w : ways.Elements()) {
        std::vector<uint32_t> ids;
        for (const JsonValue& id : w["nodes"].Elements()) {
            const auto it = osmToIndex_.find(static_cast<int64_t>(id.AsNumber()));
            if (it != osmToIndex_.end()) ids.push_back(it->second);
        }
        const RoadClass cls = RoadClassFromString(w["class"].AsString("unknown"));
        AddWay(ids, cls, w["oneway"].AsBool(false), w["lanes"].AsInt(1), w["bridge"].AsBool(false),
               w["tunnel"].AsBool(false), w["name"].AsString(""), w["maxspeed"].AsNumber(0.0));
    }
    return true;
}

bool RoadGraph::EdgeAllowed(const RoadEdge& e, TravelMode mode) const {
    if (mode == TravelMode::Walk) return IsWalkable(e.roadClass);
    return IsDrivable(e.roadClass) && !e.againstOneway;
}

void RoadGraph::RebuildSpatialIndex() const {
    grid_.clear();
    for (uint32_t i = 0; i < nodes_.size(); ++i) {
        const int64_t cx = static_cast<int64_t>(std::floor(nodes_[i].pos.x / cellSize_));
        const int64_t cy = static_cast<int64_t>(std::floor(nodes_[i].pos.y / cellSize_));
        grid_[road_detail::CellKey(cx, cy)].push_back(i);
    }
    indexDirty_ = false;
}

uint32_t RoadGraph::NearestNode(const Vec2& p, TravelMode mode) const {
    if (nodes_.empty()) return std::numeric_limits<uint32_t>::max();
    if (indexDirty_) RebuildSpatialIndex();
    auto usable = [&](uint32_t ni) {
        for (const uint32_t ei : nodes_[ni].outEdges) {
            if (EdgeAllowed(edges_[ei], mode)) return true;
        }
        return false;
    };
    const int64_t cx = static_cast<int64_t>(std::floor(p.x / cellSize_));
    const int64_t cy = static_cast<int64_t>(std::floor(p.y / cellSize_));
    uint32_t best = std::numeric_limits<uint32_t>::max();
    double bestD = std::numeric_limits<double>::max();
    for (int r = 0; r < 64; ++r) {
        for (int64_t dx = -r; dx <= r; ++dx) {
            for (int64_t dy = -r; dy <= r; ++dy) {
                if (std::max(std::llabs(dx), std::llabs(dy)) != r) continue; // ring only
                const auto it = grid_.find(road_detail::CellKey(cx + dx, cy + dy));
                if (it == grid_.end()) continue;
                for (const uint32_t ni : it->second) {
                    const double d = std::hypot(nodes_[ni].pos.x - p.x, nodes_[ni].pos.y - p.y);
                    if (d < bestD && usable(ni)) { bestD = d; best = ni; }
                }
            }
        }
        // Anything in ring r+1 is at least r*cellSize away.
        if (best != std::numeric_limits<uint32_t>::max() && bestD <= r * cellSize_) break;
    }
    return best;
}

Route RoadGraph::FindRoute(uint32_t start, uint32_t goal, TravelMode mode) const {
    Route route;
    if (start >= nodes_.size() || goal >= nodes_.size()) return route;
    const double maxSpeedMps = mode == TravelMode::Walk ? road_detail::kWalkSpeedMps : 70.0 / 3.6;
    const Vec2 gp = nodes_[goal].pos;
    auto heuristic = [&](uint32_t n) {
        return std::hypot(nodes_[n].pos.x - gp.x, nodes_[n].pos.y - gp.y) / maxSpeedMps;
    };
    const size_t n = nodes_.size();
    std::vector<double> g(n, std::numeric_limits<double>::infinity());
    std::vector<uint32_t> viaEdge(n, std::numeric_limits<uint32_t>::max());
    using QItem = std::pair<double, uint32_t>;
    std::priority_queue<QItem, std::vector<QItem>, std::greater<QItem>> open;
    g[start] = 0.0;
    open.push({heuristic(start), start});
    while (!open.empty()) {
        const auto [f, cur] = open.top();
        open.pop();
        if (cur == goal) break;
        if (f - heuristic(cur) > g[cur] + 1e-9) continue; // stale entry
        for (const uint32_t ei : nodes_[cur].outEdges) {
            const RoadEdge& e = edges_[ei];
            if (!EdgeAllowed(e, mode)) continue;
            const double speed = mode == TravelMode::Walk ? road_detail::kWalkSpeedMps : e.speedKmh / 3.6;
            const double cost = e.lengthMetres / std::max(0.5, speed);
            const double ng = g[cur] + cost;
            if (ng < g[e.to]) {
                g[e.to] = ng;
                viaEdge[e.to] = ei;
                open.push({ng + heuristic(e.to), e.to});
            }
        }
    }
    if (!std::isfinite(g[goal])) return route;
    route.found = true;
    route.seconds = g[goal];
    for (uint32_t c = goal; c != start;) {
        const uint32_t ei = viaEdge[c];
        route.edges.push_back(ei);
        route.lengthMetres += edges_[ei].lengthMetres;
        c = edges_[ei].from;
    }
    std::reverse(route.edges.begin(), route.edges.end());
    route.nodes.push_back(start);
    for (const uint32_t ei : route.edges) route.nodes.push_back(edges_[ei].to);
    return route;
}

Route RoadGraph::FindRoute(const Vec2& from, const Vec2& to, TravelMode mode) const {
    return FindRoute(NearestNode(from, mode), NearestNode(to, mode), mode);
}

size_t RoadGraph::ReachableCount(uint32_t start, TravelMode mode) const {
    if (start >= nodes_.size()) return 0;
    std::vector<bool> seen(nodes_.size(), false);
    std::vector<uint32_t> stack{start};
    seen[start] = true;
    size_t count = 0;
    while (!stack.empty()) {
        const uint32_t c = stack.back();
        stack.pop_back();
        ++count;
        for (const uint32_t ei : nodes_[c].outEdges) {
            const RoadEdge& e = edges_[ei];
            if (!EdgeAllowed(e, mode) || seen[e.to]) continue;
            seen[e.to] = true;
            stack.push_back(e.to);
        }
    }
    return count;
}

} // namespace stockholm::sim
