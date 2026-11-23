// STOCKHOLM — geographic projection and geometry helpers.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace stockholm::sim {

struct Vec2 {
    double x = 0.0; // metres east of origin
    double y = 0.0; // metres north of origin
};

struct Vec3 {
    double x = 0.0, y = 0.0, z = 0.0;
};

// Local tangent-plane projection around a fixed origin. For the ~10 km extent
// of central Stockholm the equirectangular approximation used here is accurate
// to well under 0.1 % which is far below building-placement tolerance.
//
// Unreal mapping (left-handed, centimetres, Z up):
//   UE.X = east  * 100
//   UE.Y = -north * 100   (so a top-down view with +X right shows north up)
//   UE.Z = up * 100
class GeoProjection {
public:
    // Default origin: Riksbron / Helgeandsholmen — the hinge between
    // Norrmalm and Gamla Stan, the centre of the Milestone A slice.
    static constexpr double kDefaultOriginLat = 59.3275;
    static constexpr double kDefaultOriginLon = 18.0680;

    GeoProjection(double originLat = kDefaultOriginLat, double originLon = kDefaultOriginLon);

    Vec2 ToLocal(double lat, double lon) const;
    void ToGeo(const Vec2& local, double& outLat, double& outLon) const;

    static Vec3 LocalToUnreal(const Vec2& local, double heightMetres = 0.0);
    static Vec2 UnrealToLocal(const Vec3& ue);

    double OriginLat() const { return originLat_; }
    double OriginLon() const { return originLon_; }

    // Great-circle distance in metres.
    static double HaversineMetres(double lat1, double lon1, double lat2, double lon2);

private:
    double originLat_;
    double originLon_;
    double metresPerDegLat_;
    double metresPerDegLon_;
};

// ---- Polygon utilities used for building extrusion ------------------------

double SignedArea(const std::vector<Vec2>& ring); // > 0 counter-clockwise
bool PointInPolygon(const Vec2& p, const std::vector<Vec2>& ring);
Vec2 Centroid(const std::vector<Vec2>& ring);

// Removes duplicate/closing vertices and collinear points, returns a CCW ring.
std::vector<Vec2> CleanRing(const std::vector<Vec2>& ring, double epsilon = 0.05);

// Ear-clipping triangulation of a simple polygon (no holes). Returns triangle
// indices into the (cleaned, CCW) ring. Returns empty on degenerate input.
std::vector<uint32_t> TriangulateEarClip(const std::vector<Vec2>& ccwRing);

struct MeshData {
    std::vector<Vec3> positions; // local metres, z up
    std::vector<Vec3> normals;
    std::vector<Vec2> uvs;       // world-scale UVs in metres (for tiling materials)
    std::vector<uint32_t> indices; // CCW when viewed from outside (right-handed)
    void Append(const MeshData& other);
};

// Extrudes a footprint into walls + flat roof. Wall UVs are in metres along the
// facade (u) and height (v) so facade materials tile per floor.
MeshData ExtrudeFootprint(const std::vector<Vec2>& footprint, double baseZ, double heightMetres);

// Builds a flat ribbon mesh for a polyline (road surface), width in metres.
MeshData BuildRibbon(const std::vector<Vec2>& polyline, double width, double z);

} // namespace stockholm::sim
