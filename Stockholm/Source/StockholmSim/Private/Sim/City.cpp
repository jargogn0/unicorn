#include "Sim/City.h"

#include <algorithm>

namespace stockholm::sim {

namespace city_detail {
std::vector<Vec2> ReadRing(const JsonValue& ring) {
    std::vector<Vec2> out;
    out.reserve(ring.Size());
    for (const JsonValue& p : ring.Elements()) out.push_back(Vec2{p[static_cast<size_t>(0)].AsNumber(), p[static_cast<size_t>(1)].AsNumber()});
    return out;
}
} // namespace city_detail

bool CityModel::LoadFromFile(const std::string& path, std::string* error) {
    bool ok = false;
    const std::string text = ReadTextFile(path, &ok);
    if (!ok) {
        if (error) *error = "cannot read " + path;
        return false;
    }
    std::string parseError;
    const JsonValue doc = JsonValue::Parse(text, &parseError);
    if (doc.IsNull()) {
        if (error) *error = path + ": " + parseError;
        return false;
    }
    return LoadFromJson(doc, error);
}

bool CityModel::LoadFromJson(const JsonValue& doc, std::string* error) {
    if (doc["kind"].AsString("") != "city") {
        if (error) *error = "not a city document (kind != city)";
        return false;
    }
    originLat = doc["origin"]["lat"].AsNumber(originLat);
    originLon = doc["origin"]["lon"].AsNumber(originLon);
    attribution = doc["attribution"].AsString("© OpenStreetMap contributors (ODbL 1.0)");
    sourceTimestamp = doc["source_timestamp"].AsString("");
    const JsonValue& b = doc["bounds_local"];
    bounds.minX = b[static_cast<size_t>(0)].AsNumber();
    bounds.minY = b[static_cast<size_t>(1)].AsNumber();
    bounds.maxX = b[static_cast<size_t>(2)].AsNumber();
    bounds.maxY = b[static_cast<size_t>(3)].AsNumber();

    std::string roadError;
    if (!roads.LoadFromJson(doc, &roadError)) {
        if (error) *error = roadError;
        return false;
    }
    // Polylines for rendering, resolved from the node table.
    std::vector<std::pair<int64_t, Vec2>> nodeList;
    for (const JsonValue& n : doc["roads"]["nodes"].Elements()) {
        nodeList.push_back({static_cast<int64_t>(n[static_cast<size_t>(0)].AsNumber()),
                            Vec2{n[static_cast<size_t>(1)].AsNumber(), n[static_cast<size_t>(2)].AsNumber()}});
    }
    std::sort(nodeList.begin(), nodeList.end(), [](const auto& l, const auto& r) { return l.first < r.first; });
    auto findNode = [&](int64_t id, Vec2& out) {
        const auto it = std::lower_bound(nodeList.begin(), nodeList.end(), id,
                                         [](const auto& e, int64_t v) { return e.first < v; });
        if (it == nodeList.end() || it->first != id) return false;
        out = it->second;
        return true;
    };
    for (const JsonValue& w : doc["roads"]["ways"].Elements()) {
        RoadLine line;
        for (const JsonValue& id : w["nodes"].Elements()) {
            Vec2 p;
            if (findNode(static_cast<int64_t>(id.AsNumber()), p)) line.points.push_back(p);
        }
        if (line.points.size() < 2) continue;
        line.roadClass = RoadClassFromString(w["class"].AsString("unknown"));
        const int lanes = w["lanes"].AsInt(0);
        line.widthMetres = w["width"].AsNumber(DefaultWidthMetres(line.roadClass, lanes > 0 ? lanes : (IsDrivable(line.roadClass) ? 2 : 1)));
        line.bridge = w["bridge"].AsBool(false);
        line.tunnel = w["tunnel"].AsBool(false);
        line.layer = w["layer"].AsInt(0);
        line.name = w["name"].AsString("");
        roadLines.push_back(std::move(line));
    }

    for (const JsonValue& bj : doc["buildings"].Elements()) {
        Building bd;
        bd.osmId = static_cast<int64_t>(bj["id"].AsNumber());
        const JsonValue& rings = bj["rings"];
        if (rings.Size() == 0) continue;
        bd.outer = CleanRing(city_detail::ReadRing(rings[static_cast<size_t>(0)]));
        if (bd.outer.size() < 3) continue;
        for (size_t i = 1; i < rings.Size(); ++i) bd.holes.push_back(CleanRing(city_detail::ReadRing(rings[i])));
        bd.heightMetres = bj["height"].AsNumber(18.0);
        bd.minHeightMetres = bj["min_height"].AsNumber(0.0);
        bd.levels = bj["levels"].AsInt(0);
        bd.name = bj["name"].AsString("");
        bd.kind = bj["kind"].AsString("yes");
        bd.roofShape = bj["roof_shape"].AsString("");
        bd.colour = bj["colour"].AsString("");
        bd.landmark = bj["landmark"].AsBool(false);
        bd.heightFromData = bj["height_from_data"].AsBool(false);
        buildings.push_back(std::move(bd));
    }

    for (const JsonValue& aj : doc["areas"].Elements()) {
        AreaPolygon a;
        a.osmId = static_cast<int64_t>(aj["id"].AsNumber());
        a.kind = aj["kind"].AsString("land");
        a.name = aj["name"].AsString("");
        const JsonValue& rings = aj["rings"];
        if (rings.Size() == 0) continue;
        a.outer = city_detail::ReadRing(rings[static_cast<size_t>(0)]);
        if (a.outer.size() < 3) continue;
        for (size_t i = 1; i < rings.Size(); ++i) a.holes.push_back(city_detail::ReadRing(rings[i]));
        areas.push_back(std::move(a));
    }
    return true;
}

bool CityModel::IsWater(const Vec2& p) const {
    for (const AreaPolygon& a : areas) {
        if (a.kind != "water" || !PointInPolygon(p, a.outer)) continue;
        bool inHole = false;
        for (const auto& h : a.holes) inHole |= PointInPolygon(p, h);
        if (!inHole) return true;
    }
    return false;
}

size_t CityModel::BuildingsWithSourcedHeight() const {
    size_t n = 0;
    for (const Building& b : buildings) n += b.heightFromData ? 1 : 0;
    return n;
}

} // namespace stockholm::sim
