#include "Sim/Geo.h"

#include <algorithm>
#include <cmath>

namespace stockholm::sim {

namespace geo_detail {
constexpr double kPi = 3.14159265358979323846;
constexpr double kEarthRadius = 6371008.8; // mean Earth radius, metres
inline double DegToRad(double d) { return d * kPi / 180.0; }

inline double Cross(const Vec2& o, const Vec2& a, const Vec2& b) {
    return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
}

bool PointInTriangle(const Vec2& p, const Vec2& a, const Vec2& b, const Vec2& c) {
    const double d1 = Cross(a, b, p);
    const double d2 = Cross(b, c, p);
    const double d3 = Cross(c, a, p);
    const bool hasNeg = (d1 < 0) || (d2 < 0) || (d3 < 0);
    const bool hasPos = (d1 > 0) || (d2 > 0) || (d3 > 0);
    return !(hasNeg && hasPos);
}
} // namespace geo_detail

GeoProjection::GeoProjection(double originLat, double originLon)
    : originLat_(originLat), originLon_(originLon) {
    // WGS84 meridional / prime-vertical approximations (series form).
    const double phi = geo_detail::DegToRad(originLat);
    metresPerDegLat_ = 111132.92 - 559.82 * std::cos(2 * phi) + 1.175 * std::cos(4 * phi) - 0.0023 * std::cos(6 * phi);
    metresPerDegLon_ = 111412.84 * std::cos(phi) - 93.5 * std::cos(3 * phi) + 0.118 * std::cos(5 * phi);
}

Vec2 GeoProjection::ToLocal(double lat, double lon) const {
    return Vec2{(lon - originLon_) * metresPerDegLon_, (lat - originLat_) * metresPerDegLat_};
}

void GeoProjection::ToGeo(const Vec2& local, double& outLat, double& outLon) const {
    outLat = originLat_ + local.y / metresPerDegLat_;
    outLon = originLon_ + local.x / metresPerDegLon_;
}

Vec3 GeoProjection::LocalToUnreal(const Vec2& local, double heightMetres) {
    return Vec3{local.x * 100.0, -local.y * 100.0, heightMetres * 100.0};
}

Vec2 GeoProjection::UnrealToLocal(const Vec3& ue) {
    return Vec2{ue.x / 100.0, -ue.y / 100.0};
}

double GeoProjection::HaversineMetres(double lat1, double lon1, double lat2, double lon2) {
    using geo_detail::DegToRad;
    const double dLat = DegToRad(lat2 - lat1);
    const double dLon = DegToRad(lon2 - lon1);
    const double a = std::sin(dLat / 2) * std::sin(dLat / 2) +
                     std::cos(DegToRad(lat1)) * std::cos(DegToRad(lat2)) * std::sin(dLon / 2) * std::sin(dLon / 2);
    return 2 * geo_detail::kEarthRadius * std::atan2(std::sqrt(a), std::sqrt(1 - a));
}

double SignedArea(const std::vector<Vec2>& ring) {
    double a = 0.0;
    const size_t n = ring.size();
    for (size_t i = 0; i < n; ++i) {
        const Vec2& p = ring[i];
        const Vec2& q = ring[(i + 1) % n];
        a += p.x * q.y - q.x * p.y;
    }
    return a * 0.5;
}

bool PointInPolygon(const Vec2& p, const std::vector<Vec2>& ring) {
    bool inside = false;
    const size_t n = ring.size();
    for (size_t i = 0, j = n - 1; i < n; j = i++) {
        const Vec2& a = ring[i];
        const Vec2& b = ring[j];
        if (((a.y > p.y) != (b.y > p.y)) && (p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x)) {
            inside = !inside;
        }
    }
    return inside;
}

Vec2 Centroid(const std::vector<Vec2>& ring) {
    const double area = SignedArea(ring);
    if (std::fabs(area) < 1e-9) {
        Vec2 avg;
        for (const Vec2& p : ring) { avg.x += p.x; avg.y += p.y; }
        if (!ring.empty()) { avg.x /= static_cast<double>(ring.size()); avg.y /= static_cast<double>(ring.size()); }
        return avg;
    }
    double cx = 0.0, cy = 0.0;
    const size_t n = ring.size();
    for (size_t i = 0; i < n; ++i) {
        const Vec2& p = ring[i];
        const Vec2& q = ring[(i + 1) % n];
        const double f = p.x * q.y - q.x * p.y;
        cx += (p.x + q.x) * f;
        cy += (p.y + q.y) * f;
    }
    return Vec2{cx / (6.0 * area), cy / (6.0 * area)};
}

std::vector<Vec2> CleanRing(const std::vector<Vec2>& ring, double epsilon) {
    std::vector<Vec2> out;
    out.reserve(ring.size());
    for (const Vec2& p : ring) {
        if (!out.empty() && std::hypot(p.x - out.back().x, p.y - out.back().y) < epsilon) continue;
        out.push_back(p);
    }
    while (out.size() > 1 && std::hypot(out.front().x - out.back().x, out.front().y - out.back().y) < epsilon) {
        out.pop_back();
    }
    // Remove collinear vertices.
    bool changed = true;
    while (changed && out.size() > 3) {
        changed = false;
        for (size_t i = 0; i < out.size(); ++i) {
            const Vec2& a = out[(i + out.size() - 1) % out.size()];
            const Vec2& b = out[i];
            const Vec2& c = out[(i + 1) % out.size()];
            const double len = std::hypot(c.x - a.x, c.y - a.y);
            if (len < 1e-9 || std::fabs(geo_detail::Cross(a, b, c)) / len < epsilon * 0.2) {
                out.erase(out.begin() + static_cast<std::ptrdiff_t>(i));
                changed = true;
                break;
            }
        }
    }
    if (out.size() >= 3 && SignedArea(out) < 0) std::reverse(out.begin(), out.end());
    return out;
}

std::vector<uint32_t> TriangulateEarClip(const std::vector<Vec2>& ring) {
    std::vector<uint32_t> tris;
    const size_t n = ring.size();
    if (n < 3) return tris;
    std::vector<uint32_t> idx(n);
    for (size_t i = 0; i < n; ++i) idx[i] = static_cast<uint32_t>(i);

    size_t guard = 0;
    const size_t maxIterations = n * n + 16;
    while (idx.size() > 3 && guard++ < maxIterations) {
        bool clipped = false;
        const size_t m = idx.size();
        for (size_t i = 0; i < m; ++i) {
            const uint32_t ia = idx[(i + m - 1) % m];
            const uint32_t ib = idx[i];
            const uint32_t ic = idx[(i + 1) % m];
            const Vec2& a = ring[ia];
            const Vec2& b = ring[ib];
            const Vec2& c = ring[ic];
            if (geo_detail::Cross(a, b, c) <= 1e-12) continue; // reflex or degenerate
            bool containsOther = false;
            for (size_t k = 0; k < m; ++k) {
                const uint32_t ik = idx[k];
                if (ik == ia || ik == ib || ik == ic) continue;
                if (geo_detail::PointInTriangle(ring[ik], a, b, c)) { containsOther = true; break; }
            }
            if (containsOther) continue;
            tris.push_back(ia);
            tris.push_back(ib);
            tris.push_back(ic);
            idx.erase(idx.begin() + static_cast<std::ptrdiff_t>(i));
            clipped = true;
            break;
        }
        if (!clipped) {
            // Self-intersecting or numerically awkward input: fall back to a fan
            // so the building still renders; flagged by the caller via counts.
            for (size_t i = 1; i + 1 < idx.size(); ++i) {
                tris.push_back(idx[0]);
                tris.push_back(idx[i]);
                tris.push_back(idx[i + 1]);
            }
            return tris;
        }
    }
    if (idx.size() == 3) {
        tris.push_back(idx[0]);
        tris.push_back(idx[1]);
        tris.push_back(idx[2]);
    }
    return tris;
}

void MeshData::Append(const MeshData& other) {
    const uint32_t base = static_cast<uint32_t>(positions.size());
    positions.insert(positions.end(), other.positions.begin(), other.positions.end());
    normals.insert(normals.end(), other.normals.begin(), other.normals.end());
    uvs.insert(uvs.end(), other.uvs.begin(), other.uvs.end());
    indices.reserve(indices.size() + other.indices.size());
    for (const uint32_t i : other.indices) indices.push_back(base + i);
}

MeshData ExtrudeFootprint(const std::vector<Vec2>& footprint, double baseZ, double heightMetres) {
    MeshData mesh;
    const std::vector<Vec2> ring = CleanRing(footprint);
    if (ring.size() < 3 || heightMetres <= 0.0) return mesh;
    const double topZ = baseZ + heightMetres;
    const size_t n = ring.size();

    // Walls: one quad per edge, unshared vertices for hard normals.
    double uCursor = 0.0;
    for (size_t i = 0; i < n; ++i) {
        const Vec2& a = ring[i];
        const Vec2& b = ring[(i + 1) % n];
        const double len = std::hypot(b.x - a.x, b.y - a.y);
        if (len < 1e-6) continue;
        // Outward normal of a CCW ring edge is (dy, -dx).
        const Vec3 nrm{(b.y - a.y) / len, -(b.x - a.x) / len, 0.0};
        const uint32_t base = static_cast<uint32_t>(mesh.positions.size());
        mesh.positions.push_back({a.x, a.y, baseZ});
        mesh.positions.push_back({b.x, b.y, baseZ});
        mesh.positions.push_back({b.x, b.y, topZ});
        mesh.positions.push_back({a.x, a.y, topZ});
        for (int k = 0; k < 4; ++k) mesh.normals.push_back(nrm);
        mesh.uvs.push_back({uCursor, 0.0});
        mesh.uvs.push_back({uCursor + len, 0.0});
        mesh.uvs.push_back({uCursor + len, heightMetres});
        mesh.uvs.push_back({uCursor, heightMetres});
        uCursor += len;
        // CCW seen from outside.
        mesh.indices.insert(mesh.indices.end(), {base, base + 1, base + 2, base, base + 2, base + 3});
    }

    // Roof.
    const std::vector<uint32_t> roof = TriangulateEarClip(ring);
    const uint32_t roofBase = static_cast<uint32_t>(mesh.positions.size());
    for (const Vec2& p : ring) {
        mesh.positions.push_back({p.x, p.y, topZ});
        mesh.normals.push_back({0.0, 0.0, 1.0});
        mesh.uvs.push_back({p.x, p.y});
    }
    for (const uint32_t i : roof) mesh.indices.push_back(roofBase + i);
    return mesh;
}

MeshData BuildRibbon(const std::vector<Vec2>& line, double width, double z) {
    MeshData mesh;
    if (line.size() < 2 || width <= 0.0) return mesh;
    const double half = width * 0.5;
    double v = 0.0;
    for (size_t i = 0; i < line.size(); ++i) {
        // Miter direction from averaged segment normals.
        Vec2 dir{0, 0};
        if (i > 0) {
            const double l = std::hypot(line[i].x - line[i - 1].x, line[i].y - line[i - 1].y);
            if (l > 1e-9) { dir.x += (line[i].x - line[i - 1].x) / l; dir.y += (line[i].y - line[i - 1].y) / l; }
            v += l;
        }
        if (i + 1 < line.size()) {
            const double l = std::hypot(line[i + 1].x - line[i].x, line[i + 1].y - line[i].y);
            if (l > 1e-9) { dir.x += (line[i + 1].x - line[i].x) / l; dir.y += (line[i + 1].y - line[i].y) / l; }
        }
        const double dl = std::hypot(dir.x, dir.y);
        if (dl < 1e-9) dir = {1, 0}; else { dir.x /= dl; dir.y /= dl; }
        const Vec2 left{-dir.y, dir.x};
        mesh.positions.push_back({line[i].x + left.x * half, line[i].y + left.y * half, z});
        mesh.positions.push_back({line[i].x - left.x * half, line[i].y - left.y * half, z});
        mesh.normals.push_back({0, 0, 1});
        mesh.normals.push_back({0, 0, 1});
        mesh.uvs.push_back({0.0, v});
        mesh.uvs.push_back({width, v});
    }
    for (uint32_t i = 0; i + 1 < static_cast<uint32_t>(line.size()); ++i) {
        const uint32_t l0 = i * 2, r0 = i * 2 + 1, l1 = i * 2 + 2, r1 = i * 2 + 3;
        // Upward-facing CCW in right-handed (x east, y north, z up).
        mesh.indices.insert(mesh.indices.end(), {l0, r0, r1, l0, r1, l1});
    }
    return mesh;
}

} // namespace stockholm::sim
