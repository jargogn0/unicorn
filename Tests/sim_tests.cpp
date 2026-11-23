// STOCKHOLM simulation-core tests. Built without exceptions/RTTI to mirror UE.
// Run: cmake -S Tests -B build && cmake --build build && ./build/sim_tests
#include "Sim/Content.h"
#include "Sim/FounderSim.h"
#include "Sim/FounderState.h"
#include "Sim/Geo.h"
#include "Sim/Json.h"
#include "Sim/RoadGraph.h"
#include "Sim/WorldClock.h"

#include <cmath>
#include <cstdio>
#include <functional>
#include <string>
#include <vector>

using namespace stockholm::sim;

namespace {
int g_failures = 0;
int g_checks = 0;
std::string g_current;

#define CHECK(cond)                                                                                   \
    do {                                                                                              \
        ++g_checks;                                                                                   \
        if (!(cond)) {                                                                                \
            ++g_failures;                                                                             \
            std::printf("  FAIL [%s] %s:%d: %s\n", g_current.c_str(), __FILE__, __LINE__, #cond);     \
        }                                                                                             \
    } while (0)

#define CHECK_NEAR(a, b, tol) CHECK(std::fabs((a) - (b)) <= (tol))

struct TestCase {
    const char* name;
    std::function<void()> fn;
};
std::vector<TestCase>& Registry() {
    static std::vector<TestCase> r;
    return r;
}
struct Registrar {
    Registrar(const char* n, std::function<void()> f) { Registry().push_back({n, std::move(f)}); }
};
#define TEST(name)                                         \
    static void name();                                    \
    static Registrar registrar_##name(#name, name);        \
    static void name()

bool LoadContent(FounderSim& sim) {
    std::string err;
    const bool ok = sim.Content().LoadFromManifest(STOCKHOLM_DATA_DIR, &err);
    if (!ok) std::printf("  content load error: %s\n", err.c_str());
    return ok;
}

// Plays the active dialogue. `picks` are choice indices (as authored) used in
// order whenever a choice node appears; when exhausted, picks the first available.
void PlayDialogue(FounderSim& sim, std::vector<int> picks = {}) {
    size_t pi = 0;
    for (int guard = 0; guard < 100 && sim.IsDialogueActive(); ++guard) {
        const DialogueLineView line = sim.CurrentLine();
        if (line.hasChoices) {
            const std::vector<ChoiceView> choices = sim.CurrentChoices();
            int pick = -1;
            if (pi < picks.size()) pick = picks[pi++];
            bool valid = false;
            for (const ChoiceView& c : choices) valid |= (c.index == pick && c.available);
            if (!valid) {
                for (const ChoiceView& c : choices) {
                    if (c.available) { pick = c.index; break; }
                }
            }
            if (!sim.ChooseDialogueOption(pick)) return;
        } else {
            sim.AdvanceDialogue();
        }
    }
}

bool Talk(FounderSim& sim, const std::string& npc, std::vector<int> picks = {}) {
    const std::string d = sim.DialogueForNpc(npc);
    if (d.empty() || !sim.StartDialogue(d)) return false;
    PlayDialogue(sim, std::move(picks));
    return true;
}

bool Phone(FounderSim& sim, std::vector<int> picks = {}) {
    const std::string d = sim.PendingPhoneCall();
    if (d.empty() || !sim.StartDialogue(d)) return false;
    PlayDialogue(sim, std::move(picks));
    return true;
}

std::string ObjectiveOf(FounderSim& sim, const std::string& mission) {
    const auto it = sim.Missions().find(mission);
    return it == sim.Missions().end() ? "" : it->second.objective;
}

// Advances the clock to the next occurrence of a local hour.
void AdvanceToHour(FounderSim& sim, double hour) {
    double delta = hour - sim.Clock().HourOfDay();
    if (delta <= 0.0) delta += 24.0;
    sim.AdvanceGameMinutes(delta * 60.0);
}

// Plays m00 + m01 along the "good listener" path; ends at the start of m02.
void PlayOpeningAndDiscovery(FounderSim& sim) {
    CHECK(sim.GetMissionStatus("m00_five_days") == MissionStatus::Active);
    CHECK(Phone(sim, {0}));
    sim.NotifyInteracted("laptop_home");
    CHECK(sim.GetMissionStatus("m00_five_days") == MissionStatus::Completed);
    CHECK(sim.GetMissionStatus("m01_show_me") == MissionStatus::Active);
    sim.AdvanceGameMinutes(35); // walk to Hornsgatan
    sim.NotifyReached("cafe_kollektivet", false);
    CHECK(ObjectiveOf(sim, "m01_show_me") == "o2");
    CHECK(Talk(sim, "noor", {0, 1, 0}));
    CHECK(sim.Fact("learned_scheduling_pain") == 1.0);
    CHECK(sim.Fact("learned_willingness_to_pay") == 1.0);
    sim.AdvanceGameMinutes(20);
    sim.NotifyReached("bakery_kanel", false);
    CHECK(Talk(sim, "aditi", {0, 1}));
    CHECK(sim.Fact("learned_offline_risk") == 1.0);
    sim.AdvanceGameMinutes(25);
    sim.NotifyReached("apt_player", false);
    sim.NotifyInteracted("laptop_home");
    CHECK(sim.GetMissionStatus("m01_show_me") == MissionStatus::Completed);
    CHECK(sim.GetMissionStatus("m02_first_pitch") == MissionStatus::Active);
}
} // namespace

// ============================================================== JSON

TEST(Json_RoundTrip) {
    std::string err;
    const JsonValue v = JsonValue::Parse(R"({"a":[1,2.5,true,null],"s":"Söder \"quoted\"\n","u":"å😀"})", &err);
    CHECK(err.empty());
    CHECK(v["a"].Size() == 4);
    CHECK_NEAR(v["a"][static_cast<size_t>(1)].AsNumber(), 2.5, 1e-12);
    CHECK(v["a"][static_cast<size_t>(2)].AsBool());
    CHECK(v["s"].AsString() == "Söder \"quoted\"\n");
    CHECK(v["u"].AsString() == "\xC3\xA5\xF0\x9F\x98\x80");
    const JsonValue again = JsonValue::Parse(v.Dump(2), &err);
    CHECK(err.empty());
    CHECK(again.Dump() == v.Dump());
    CHECK(v["missing"]["deeper"].IsNull());
}

TEST(Json_Errors) {
    std::string err;
    CHECK(JsonValue::Parse("{\"a\":}", &err).IsNull());
    CHECK(!err.empty());
    CHECK(JsonValue::Parse("[1,2", &err).IsNull());
    CHECK(JsonValue::Parse("{} trailing", &err).IsNull());
    CHECK(JsonValue::Parse("// comment\n{\"ok\":1}", &err)["ok"].AsInt() == 1);
}

// ============================================================== Geo

TEST(Geo_ProjectionRoundTrip) {
    const GeoProjection proj;
    const Vec2 o = proj.ToLocal(GeoProjection::kDefaultOriginLat, GeoProjection::kDefaultOriginLon);
    CHECK_NEAR(o.x, 0.0, 1e-9);
    CHECK_NEAR(o.y, 0.0, 1e-9);
    double lat = 0, lon = 0;
    const Vec2 p = proj.ToLocal(59.3196, 18.0717); // Slussen
    proj.ToGeo(p, lat, lon);
    CHECK_NEAR(lat, 59.3196, 1e-9);
    CHECK_NEAR(lon, 18.0717, 1e-9);
    // Local distance agrees with great-circle distance (Slussen → Sergels torg).
    const Vec2 q = proj.ToLocal(59.3324, 18.0636);
    const double local = std::hypot(q.x - p.x, q.y - p.y);
    const double gc = GeoProjection::HaversineMetres(59.3196, 18.0717, 59.3324, 18.0636);
    CHECK(gc > 1400 && gc < 1600);
    // Haversine uses a spherical Earth; the projection uses WGS84 radii of
    // curvature, which at 59°N are ~0.2-0.4 % larger. Agreement within 0.5 %.
    CHECK(std::fabs(local - gc) / gc < 0.005);
    // Unreal mapping: north is -Y, centimetres.
    const Vec3 ue = GeoProjection::LocalToUnreal(Vec2{10.0, 20.0}, 3.0);
    CHECK_NEAR(ue.x, 1000.0, 1e-9);
    CHECK_NEAR(ue.y, -2000.0, 1e-9);
    CHECK_NEAR(ue.z, 300.0, 1e-9);
}

TEST(Geo_TriangulateAndExtrude) {
    const std::vector<Vec2> square = {{0, 0}, {10, 0}, {10, 10}, {0, 10}, {0, 0}};
    const std::vector<Vec2> clean = CleanRing(square);
    CHECK(clean.size() == 4);
    CHECK(SignedArea(clean) > 0);
    CHECK(TriangulateEarClip(clean).size() == 6);

    // Concave L-shape, given clockwise: must be re-wound and triangulated fully.
    std::vector<Vec2> l = {{0, 0}, {0, 20}, {10, 20}, {10, 10}, {20, 10}, {20, 0}};
    const std::vector<Vec2> lc = CleanRing(l);
    CHECK(SignedArea(lc) > 0);
    const std::vector<uint32_t> tris = TriangulateEarClip(lc);
    CHECK(tris.size() == (lc.size() - 2) * 3);
    double area = 0;
    for (size_t i = 0; i < tris.size(); i += 3) {
        area += SignedArea({lc[tris[i]], lc[tris[i + 1]], lc[tris[i + 2]]});
    }
    CHECK_NEAR(area, 300.0, 1e-6);

    const MeshData m = ExtrudeFootprint(square, 0.0, 21.0);
    CHECK(m.positions.size() == 4 * 4 + 4);
    CHECK(m.indices.size() == 4 * 6 + 6);
    // Every wall normal points away from the centroid.
    for (size_t i = 0; i < 16; ++i) {
        const Vec3& pos = m.positions[i];
        const Vec3& n = m.normals[i];
        CHECK((pos.x - 5.0) * n.x + (pos.y - 5.0) * n.y > 0.0);
    }
    const MeshData r = BuildRibbon({{0, 0}, {50, 0}, {50, 50}}, 8.0, 0.1);
    CHECK(r.positions.size() == 6);
    CHECK(r.indices.size() == 12);
}

// ============================================================== Roads

TEST(Roads_RoutingAndOneway) {
    RoadGraph g;
    // 3x3 grid, 100 m spacing. Middle row is one-way eastbound.
    uint32_t id[3][3];
    for (int y = 0; y < 3; ++y)
        for (int x = 0; x < 3; ++x) id[y][x] = g.AddNode(y * 10 + x, Vec2{x * 100.0, y * 100.0});
    for (int y = 0; y < 3; ++y) {
        g.AddWay({id[y][0], id[y][1], id[y][2]}, RoadClass::Residential, y == 1, 1, false, false, "row", 0);
    }
    for (int x = 0; x < 3; ++x) {
        g.AddWay({id[0][x], id[1][x], id[2][x]}, RoadClass::Residential, false, 1, false, false, "col", 0);
    }
    const Route east = g.FindRoute(id[1][0], id[1][2], TravelMode::Drive);
    CHECK(east.found);
    CHECK_NEAR(east.lengthMetres, 200.0, 1e-6);
    const Route west = g.FindRoute(id[1][2], id[1][0], TravelMode::Drive);
    CHECK(west.found);
    CHECK(west.lengthMetres > 200.0 + 1e-6); // must detour around the one-way
    const Route walkWest = g.FindRoute(id[1][2], id[1][0], TravelMode::Walk);
    CHECK_NEAR(walkWest.lengthMetres, 200.0, 1e-6); // pedestrians may walk against one-way
    CHECK(g.NearestNode(Vec2{190, 95}, TravelMode::Drive) == id[1][2]);
    CHECK(g.ReachableCount(id[0][0], TravelMode::Drive) == 9);
    CHECK(east.Polyline(g).size() == 3);
}

// ============================================================== Clock & weather

TEST(Clock_Calendar) {
    CHECK(DayOfWeek(DaysFromCivil(2026, 1, 12)) == 0); // Monday
    const CivilDate d = CivilFromDays(DaysFromCivil(2028, 2, 29));
    CHECK(d.year == 2028 && d.month == 2 && d.day == 29);
    WorldClock c;
    CHECK(c.FormatDate() == "Mon 12 Jan 2026");
    CHECK(c.FormatTime() == "07:10");
    c.AdvanceMinutes(24 * 60 * 5);
    CHECK(c.Date().day == 17);
    CHECK(c.IsWeekend());
    CHECK_NEAR(SwedenUtcOffset({2026, 1, 12}, 12), 1.0, 1e-9);
    CHECK_NEAR(SwedenUtcOffset({2026, 7, 1}, 12), 2.0, 1e-9);
    CHECK_NEAR(SwedenUtcOffset({2026, 3, 29}, 1.0), 1.0, 1e-9); // last Sunday of March, before 02:00
    CHECK_NEAR(SwedenUtcOffset({2026, 3, 29}, 3.0), 2.0, 1e-9);
}

TEST(Clock_SunPositionStockholm) {
    // Winter: max elevation ~ 90 - 59.33 - 21.7 ≈ 9°; sunrise ~08:35, sunset ~15:15 in mid-January.
    double maxElev = -90;
    double sunrise = -1, sunset = -1, prev = -90;
    for (double h = 0; h < 24; h += 1.0 / 60.0) {
        const double e = ComputeSunPosition(59.3293, 18.0686, {2026, 1, 12}, h, 1.0).elevationDeg;
        if (e > maxElev) maxElev = e;
        if (prev < -0.833 && e >= -0.833 && sunrise < 0) sunrise = h;
        if (prev >= -0.833 && e < -0.833) sunset = h;
        prev = e;
    }
    CHECK(maxElev > 7.5 && maxElev < 10.5);
    CHECK(sunrise > 8.3 && sunrise < 9.0);
    CHECK(sunset > 14.9 && sunset < 15.5);
    // Midsummer noon ≈ 54°, azimuth near south around 13:10 CEST.
    const SunPosition summer = ComputeSunPosition(59.3293, 18.0686, {2026, 6, 21}, 13.1, 2.0);
    CHECK(summer.elevationDeg > 52.5 && summer.elevationDeg < 55.0);
    CHECK(summer.azimuthDeg > 170 && summer.azimuthDeg < 190);
}

TEST(Weather_DeterministicAndSeasonal) {
    auto simulate = [](uint64_t seed, int& snowHoursWinter, int& snowHoursJuly, double& minWet, double& maxWet) {
        WorldClock c;
        Rng rng(seed);
        snowHoursWinter = snowHoursJuly = 0;
        minWet = 1;
        maxWet = 0;
        for (int h = 0; h < 24 * 365; ++h) {
            c.AdvanceMinutes(60);
            c.StepWeatherHour(rng);
            const WeatherState& w = c.Weather();
            const bool snowing = w.kind == WeatherKind::LightSnow || w.kind == WeatherKind::HeavySnow;
            if (snowing && c.CurrentSeason() == Season::Winter) ++snowHoursWinter;
            if (snowing && c.Date().month == 7) ++snowHoursJuly;
            minWet = std::min(minWet, w.wetness);
            maxWet = std::max(maxWet, w.wetness);
        }
        return c.Weather().temperatureC;
    };
    int sw1, sj1, sw2, sj2;
    double a, b, c2, d2;
    const double t1 = simulate(42, sw1, sj1, a, b);
    const double t2 = simulate(42, sw2, sj2, c2, d2);
    CHECK(t1 == t2 && sw1 == sw2); // deterministic for a seed
    CHECK(sw1 > 100);              // it snows in a Stockholm winter
    CHECK(sj1 == 0);               // never in July
    CHECK(a >= 0.0 && b <= 1.0);
}

// ============================================================== Economy & cap table

TEST(CapTable_SafeThenPricedRound) {
    CapTable t;
    CHECK_NEAR(t.FounderOwnership(), 1.0, 1e-12);
    t.AddSafe({"helena", "Helena", 500000, 10000000, 0.2});
    const RoundResult preview = t.PreviewPricedRound(5000000, 20000000, 0.0);
    // price = 20M / 10M = 2.0; SAFE price = min(1.6, 1.0) = 1.0 → 500k shares; investor 2.5M shares.
    CHECK_NEAR(preview.pricePerShare, 2.0, 1e-9);
    CHECK_NEAR(preview.convertedSafeShares, 500000, 1e-6);
    CHECK_NEAR(preview.newInvestorShares, 2500000, 1e-6);
    CHECK_NEAR(preview.founderOwnershipAfter, 10.0 / 13.0, 1e-9);
    const RoundResult r = t.PricedRound("fund", "Saltsjö Ventures", HolderType::Fund, 5000000, 20000000, 0.0, true);
    CHECK(r.ok);
    CHECK_NEAR(t.FounderOwnership(), preview.founderOwnershipAfter, 1e-12);
    CHECK(t.safes.empty());
    CHECK(t.BoardSeatsInvestors() == 1);
    CHECK(t.FounderControl() < 1.0);
    // Option pool top-up of 10 % of post-money.
    CapTable p;
    const RoundResult pr = p.PricedRound("fund", "F", HolderType::Fund, 2000000, 8000000, 0.10, false);
    CHECK_NEAR(p.OwnershipOf("option_pool"), 0.10, 1e-9);
    CHECK_NEAR(pr.postMoney, 10000000.0 / 0.9, 1.0);
    // Save/load round trip.
    CapTable q;
    q.Load(t.Save());
    CHECK_NEAR(q.FounderOwnership(), t.FounderOwnership(), 1e-12);
}

TEST(Negotiation_Monotonic) {
    NegotiationContext weak;
    weak.runwayMonths = 1.0;
    NegotiationContext strong;
    strong.traction = 200000;
    strong.reputation = 60;
    strong.productQuality = 70;
    strong.competingOffers = 2;
    strong.runwayMonths = 12;
    CHECK(CounterAcceptProbability(strong, 1.25) > CounterAcceptProbability(weak, 1.25));
    NegotiationContext mid;
    mid.traction = 20000;
    mid.reputation = 20;
    mid.runwayMonths = 5;
    CHECK(CounterAcceptProbability(mid, 1.1) > CounterAcceptProbability(mid, 1.5));
    CHECK(CounterAcceptProbability(weak, 1.0) == 1.0);
}

TEST(Economy_RentEviction_IsRecoverable) {
    FounderSim sim;
    CHECK(LoadContent(sim));
    sim.BeginNewGame();
    sim.AdvanceGameMinutes(24 * 60 * 18); // never pay rent
    CHECK(sim.Fact("evicted") == 1.0);
    CHECK(sim.State().Get(Stat::HousingTier) == 0.0);
    CHECK(sim.State().Get(Stat::RentMonthly) == 0.0);
    bool landlordMessaged = false;
    for (const PhoneMessage& m : sim.Messages()) landlordMessaged |= (m.sender == "landlord");
    CHECK(landlordMessaged);
}

// ============================================================== Content

TEST(Content_LoadsAndValidates) {
    FounderSim sim;
    CHECK(LoadContent(sim));
    const std::vector<std::string> problems = sim.Content().Validate();
    for (const std::string& p : problems) std::printf("  content problem: %s\n", p.c_str());
    CHECK(problems.empty());
    CHECK(sim.Content().missions.size() == 5);
    CHECK(sim.Content().chapters.size() == 13);
    CHECK(sim.Content().ecosystem.size() >= 30);
    CHECK(sim.Content().FindEcosystem("spotify") != nullptr);
}

TEST(Content_EcosystemNeverInventsPins) {
    FounderSim sim;
    CHECK(LoadContent(sim));
    const GeoProjection proj;
    int placed = 0, unplaced = 0;
    for (const auto& kv : sim.Content().ecosystem) {
        Vec2 pos;
        bool approx = false;
        const bool ok = ResolveEcosystemPosition(kv.second, sim.Content(), proj, pos, approx);
        bool anyCoords = false, anyDistrict = false;
        for (const EcosystemLocation& l : kv.second.locations) {
            anyCoords |= l.hasCoordinates;
            anyDistrict |= sim.Content().FindDistrict(l.district) != nullptr;
        }
        CHECK(ok == (anyCoords || anyDistrict));
        if (ok && !anyCoords) CHECK(approx); // district-only pins must be labelled approximate
        (ok ? placed : unplaced) += 1;
    }
    CHECK(placed > 0);
    std::printf("  ecosystem pins: %d placed (district/address), %d directory-only\n", placed, unplaced);
}

TEST(Npc_Routines) {
    FounderSim sim;
    CHECK(LoadContent(sim));
    sim.BeginNewGame();
    sim.AdvanceGameMinutes(3 * 60); // Monday 10:10
    const RoutineEntry* r = sim.CurrentRoutine("noor");
    CHECK(r && r->location == "cafe_kollektivet");
    sim.AdvanceGameMinutes(14 * 60); // Tuesday 00:10
    const RoutineEntry* s = sim.CurrentRoutine("sami");
    CHECK(s && s->activity == "night_shift");
}

// ============================================================== Chapter 1 playthroughs

TEST(Playthrough_GoldenPath) {
    FounderSim sim(7);
    CHECK(LoadContent(sim));
    sim.BeginNewGame();
    PlayOpeningAndDiscovery(sim);

    // Night → morning; catch Sami at 07:45 and borrow the car.
    AdvanceToHour(sim, 7.75);
    CHECK(sim.Clock().HourOfDay() > 7.0 && sim.Clock().HourOfDay() < 10.0);
    CHECK(sim.ChooseDecision("m02_first_pitch", 0));
    CHECK(Talk(sim, "sami", {0, 0}));
    CHECK(sim.Fact("has_sami_car") == 1.0);
    sim.AdvanceGameMinutes(20);
    sim.NotifyReached("office_malarbrod_parking", true);
    CHECK(ObjectiveOf(sim, "m02_first_pitch") == "o3");
    CHECK(sim.Fact("late_to_pitch") == 0.0);
    CHECK(Talk(sim, "elin", {0}));
    sim.NotifyInteracted("laptop_demo");
    CHECK(ObjectiveOf(sim, "m02_first_pitch") == "o5");
    CHECK(sim.ChooseDecision("m02_first_pitch", 0)); // fix it live
    sim.NotifyCustomEvent("demo_fix_success");
    CHECK(sim.Fact("demo_recovered") == 1.0);
    CHECK(Talk(sim, "elin"));
    CHECK(sim.Fact("pilot_agreed") == 1.0);
    CHECK(ObjectiveOf(sim, "m02_first_pitch") == "o8");
    sim.AdvanceGameMinutes(30);
    sim.NotifyReached("sami_car_spot", true);
    CHECK(sim.GetMissionStatus("m02_first_pitch") == MissionStatus::Completed);
    CHECK(sim.Relationship("sami").memories.count("kept:sami_car") == 1);

    // First payment: fair price, sole trader, monthly.
    CHECK(sim.GetMissionStatus("m03_first_payment") == MissionStatus::Active);
    sim.NotifyInteracted("laptop_home");
    CHECK(sim.ChooseDecision("m03_first_payment", 1));
    CHECK(sim.Relationship("elin").memories.count("kept:send_proposal") == 1);
    CHECK(!sim.ChooseDecision("m03_first_payment", 1)); // AB locked: can't afford share capital
    CHECK(sim.ChooseDecision("m03_first_payment", 0));
    CHECK(ObjectiveOf(sim, "m03_first_payment") == "o4_elin");
    CHECK(Phone(sim, {0}));
    sim.NotifyInteracted("laptop_home");
    const double cashBefore = sim.State().Get(Stat::PersonalCash);
    sim.AdvanceGameMinutes(24 * 60);
    CHECK_NEAR(sim.Fact("first_payment_amount"), 2900.0 * 3, 1e-6);
    CHECK(sim.State().Get(Stat::PersonalCash) > cashBefore + 8000);
    CHECK(sim.State().Get(Stat::Customers) == 1.0);
    CHECK_NEAR(sim.State().Get(Stat::Mrr), 8700.0, 1e-6);
    CHECK(sim.ChooseDecision("m03_first_payment", 0)); // pay rent
    CHECK(sim.State().rentPaidThisMonth);
    CHECK(sim.GetMissionStatus("m03_first_payment") == MissionStatus::Completed);
    CHECK(sim.CurrentChapter() == 2);
    CHECK(sim.IsDiscovered("norrsken_house"));
    std::printf("  golden path finished %s %s, cash %.0f SEK, MRR %.0f SEK\n", sim.Clock().FormatDate().c_str(),
                sim.Clock().FormatTime().c_str(), sim.State().Get(Stat::PersonalCash), sim.State().Get(Stat::Mrr));
}

TEST(Playthrough_FrozenDemo_AnotherDoor_LowPrice) {
    FounderSim sim(11);
    CHECK(LoadContent(sim));
    sim.BeginNewGame();
    PlayOpeningAndDiscovery(sim);
    AdvanceToHour(sim, 8.5);
    CHECK(sim.ChooseDecision("m02_first_pitch", 1)); // transit
    sim.AdvanceGameMinutes(40);
    sim.NotifyReached("office_malarbrod", false);
    CHECK(Talk(sim, "elin"));
    sim.NotifyInteracted("laptop_demo");
    // The player freezes: the UI fires the decision default on timeout.
    const std::vector<ObjectiveView> views = sim.ActiveObjectives();
    CHECK(views.size() == 1 && views[0].decisionSeconds == 12.0);
    CHECK(sim.ChooseDecision("m02_first_pitch", views[0].decisionDefault));
    CHECK(Talk(sim, "elin"));
    CHECK(sim.Fact("lost_contract") == 1.0);
    CHECK(sim.GetMissionStatus("m02_first_pitch") == MissionStatus::Completed);
    CHECK(sim.GetMissionStatus("m02b_another_door") == MissionStatus::Active);

    AdvanceToHour(sim, 7.5);
    sim.NotifyReached("breakfast_strommen", false);
    CHECK(Talk(sim, "mateo", {0}));
    CHECK(sim.IsDiscovered("epicenter"));
    sim.NotifyReached("cafe_kollektivet", false);
    CHECK(Talk(sim, "noor", {0}));
    CHECK(sim.GetMissionStatus("m03_first_payment") == MissionStatus::Active);

    sim.NotifyInteracted("laptop_home");
    CHECK(sim.ChooseDecision("m03_first_payment", 0)); // low price
    CHECK(sim.ChooseDecision("m03_first_payment", 2)); // invoicing service
    CHECK(ObjectiveOf(sim, "m03_first_payment") == "o4_noor");
    sim.NotifyReached("cafe_kollektivet", false);
    CHECK(Talk(sim, "noor", {0})); // monthly
    sim.NotifyInteracted("laptop_home");
    sim.AdvanceGameMinutes(24 * 60);
    CHECK_NEAR(sim.Fact("first_payment_amount"), 1490.0 * 3 * 0.94, 1e-6);
    // Low price + 6 % fee: rent is out of reach — the borrow option is the way out.
    CHECK(sim.State().Get(Stat::PersonalCash) < 9400.0);
    CHECK(!sim.ChooseDecision("m03_first_payment", 0));
    CHECK(sim.ChooseDecision("m03_first_payment", 2)); // borrow from Sami
    CHECK(sim.State().rentPaidThisMonth);
    bool owesSami = false;
    for (const Commitment& c : sim.Commitments()) owesSami |= (c.id == "repay_sami" && c.status == Commitment::Status::Pending);
    CHECK(owesSami);
    CHECK(sim.CurrentChapter() == 2);
}

TEST(Playthrough_LateForNoor_RetryNextDay) {
    FounderSim sim;
    CHECK(LoadContent(sim));
    sim.BeginNewGame();
    CHECK(Phone(sim, {2}));
    sim.NotifyInteracted("laptop_home");
    sim.AdvanceGameMinutes(7 * 60); // dawdle past 13:00
    CHECK(sim.Fact("late_to_noor") == 1.0);
    CHECK(ObjectiveOf(sim, "m01_show_me") == "o1_retry");
    sim.AdvanceGameMinutes(19 * 60); // next morning past 08:00
    CHECK(ObjectiveOf(sim, "m01_show_me") == "o1b");
    sim.NotifyReached("cafe_kollektivet", false);
    CHECK(ObjectiveOf(sim, "m01_show_me") == "o2");
}

TEST(Commitment_LateCar_IsRemembered) {
    FounderSim sim;
    CHECK(LoadContent(sim));
    sim.BeginNewGame();
    PlayOpeningAndDiscovery(sim);
    AdvanceToHour(sim, 7.75);
    CHECK(sim.ChooseDecision("m02_first_pitch", 0));
    CHECK(Talk(sim, "sami", {1, 0}));
    sim.NotifyReached("office_malarbrod_parking", true);
    CHECK(Talk(sim, "elin"));
    sim.NotifyInteracted("laptop_demo");
    CHECK(sim.ChooseDecision("m02_first_pitch", 1)); // manual walkthrough
    CHECK(Talk(sim, "elin"));
    CHECK(sim.Fact("proposal_requested") == 1.0);
    sim.AdvanceGameMinutes(14 * 60); // miss the 20:00 return
    CHECK(sim.Relationship("sami").memories.count("car_late") == 1);
    CHECK(sim.Relationship("sami").memories.count("broke:sami_car") == 1);
    // The ambient line reflects the memory.
    CHECK(sim.StartDialogue("sami_ambient"));
    CHECK(sim.CurrentLine().nodeId == "sore");
}

TEST(Save_LoadMidMission) {
    FounderSim a(99);
    CHECK(LoadContent(a));
    a.BeginNewGame();
    PlayOpeningAndDiscovery(a);
    const std::string saved = a.Save().Dump(2);

    FounderSim b(1);
    CHECK(LoadContent(b));
    std::string err;
    CHECK(b.Load(JsonValue::Parse(saved), &err));
    CHECK(err.empty());
    CHECK(b.Save().Dump(2) == saved);
    CHECK(b.GetMissionStatus("m02_first_pitch") == MissionStatus::Active);
    CHECK(b.Relationship("noor").met);
    CHECK(b.Clock().FormatTime() == a.Clock().FormatTime());
    // Both continue identically (RNG state restored).
    a.AdvanceGameMinutes(600);
    b.AdvanceGameMinutes(600);
    CHECK(a.Save().Dump() == b.Save().Dump());
    // Version guard.
    JsonValue bad = JsonValue::Parse(saved);
    bad.Set("version", 999);
    CHECK(!b.Load(bad, &err));
}

int main() {
    int failedTests = 0;
    for (const TestCase& t : Registry()) {
        g_current = t.name;
        const int before = g_failures;
        t.fn();
        const bool ok = g_failures == before;
        failedTests += ok ? 0 : 1;
        std::printf("[%s] %s\n", ok ? " OK " : "FAIL", t.name);
    }
    std::printf("\n%zu tests, %d checks, %d failed checks, %d failed tests\n", Registry().size(), g_checks, g_failures,
                failedTests);
    return failedTests == 0 ? 0 : 1;
}
