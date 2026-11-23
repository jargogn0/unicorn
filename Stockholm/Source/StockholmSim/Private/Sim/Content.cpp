#include "Sim/Content.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <set>

namespace stockholm::sim {

namespace content_detail {

std::vector<std::string> StringList(const JsonValue& v) {
    std::vector<std::string> out;
    for (const JsonValue& e : v.Elements()) {
        if (e.IsString()) out.push_back(e.AsString());
    }
    return out;
}

// Accepts 8.5 or "08:30".
double ParseHour(const JsonValue& v, double fallback) {
    if (v.IsNumber()) return v.AsNumber();
    if (v.IsString()) {
        const std::string& s = v.AsString();
        const size_t colon = s.find(':');
        if (colon == std::string::npos) return fallback;
        const int h = std::atoi(s.substr(0, colon).c_str());
        const int m = std::atoi(s.substr(colon + 1).c_str());
        return h + m / 60.0;
    }
    return fallback;
}

uint64_t StableHash(const std::string& s) {
    uint64_t h = 1469598103934665603ULL; // FNV-1a
    for (const char c : s) {
        h ^= static_cast<unsigned char>(c);
        h *= 1099511628211ULL;
    }
    return h;
}

bool IsSpecialTarget(const std::string& next) {
    return next.empty() || next == "@complete" || next == "@fail";
}

} // namespace content_detail

ObjectiveType ObjectiveTypeFromString(const std::string& s) {
    if (s == "reach") return ObjectiveType::Reach;
    if (s == "drive") return ObjectiveType::Drive;
    if (s == "talk") return ObjectiveType::Talk;
    if (s == "interact") return ObjectiveType::Interact;
    if (s == "decision") return ObjectiveType::Decision;
    if (s == "wait_until") return ObjectiveType::WaitUntil;
    if (s == "phone_call") return ObjectiveType::PhoneCall;
    return ObjectiveType::Custom;
}

const char* ObjectiveTypeToString(ObjectiveType t) {
    switch (t) {
        case ObjectiveType::Reach: return "reach";
        case ObjectiveType::Drive: return "drive";
        case ObjectiveType::Talk: return "talk";
        case ObjectiveType::Interact: return "interact";
        case ObjectiveType::Decision: return "decision";
        case ObjectiveType::WaitUntil: return "wait_until";
        case ObjectiveType::PhoneCall: return "phone_call";
        case ObjectiveType::Custom: return "custom";
    }
    return "custom";
}

bool EcosystemEntry::HasCategory(const std::string& c) const {
    return std::find(categories.begin(), categories.end(), c) != categories.end();
}

bool ContentDatabase::LoadFromManifest(const std::string& dataRoot, std::string* error) {
    bool ok = false;
    const std::string manifestText = ReadTextFile(dataRoot + "/manifest.json", &ok);
    if (!ok) {
        if (error) *error = "cannot read " + dataRoot + "/manifest.json";
        return false;
    }
    std::string parseError;
    const JsonValue manifest = JsonValue::Parse(manifestText, &parseError);
    if (!manifest.IsObject()) {
        if (error) *error = "manifest.json: " + parseError;
        return false;
    }
    for (const JsonValue& f : manifest["files"].Elements()) {
        const std::string path = dataRoot + "/" + f.AsString();
        const std::string text = ReadTextFile(path, &ok);
        if (!ok) {
            if (error) *error = "cannot read " + path;
            return false;
        }
        const JsonValue doc = JsonValue::Parse(text, &parseError);
        if (doc.IsNull()) {
            if (error) *error = path + ": " + parseError;
            return false;
        }
        std::string docError;
        if (!AddDocument(doc, &docError)) {
            if (error) *error = path + ": " + docError;
            return false;
        }
    }
    return true;
}

bool ContentDatabase::AddDocument(const JsonValue& doc, std::string* error) {
    const std::string kind = doc["kind"].AsString("");
    if (kind == "npcs") LoadNpcs(doc);
    else if (kind == "dialogues") LoadDialogues(doc);
    else if (kind == "missions") LoadMissions(doc);
    else if (kind == "chapters") LoadChapters(doc);
    else if (kind == "locations") LoadLocations(doc);
    else if (kind == "districts") LoadDistricts(doc);
    else if (kind == "ecosystem" || doc.Has("entries")) LoadEcosystem(doc);
    else {
        if (error) *error = "unknown document kind '" + kind + "'";
        return false;
    }
    return true;
}

void ContentDatabase::LoadNpcs(const JsonValue& doc) {
    for (const JsonValue& n : doc["npcs"].Elements()) {
        NpcDef d;
        d.id = n["id"].AsString("");
        d.name = n["name"].AsString("");
        d.role = n["role"].AsString("");
        d.pronouns = n["pronouns"].AsString("they/them");
        d.background = n["background"].AsString("");
        d.motivation = n["motivation"].AsString("");
        d.traits = content_detail::StringList(n["traits"]);
        d.homeDistrict = n["home_district"].AsString("");
        d.appearance = n["appearance"].AsString("");
        d.voice = n["voice"].AsString("");
        for (const JsonValue& r : n["routine"].Elements()) {
            RoutineEntry e;
            e.days = r["days"].AsString("all");
            e.fromHour = content_detail::ParseHour(r["from"], 0.0);
            e.toHour = content_detail::ParseHour(r["to"], 24.0);
            e.location = r["location"].AsString("");
            e.activity = r["activity"].AsString("idle");
            d.routine.push_back(e);
        }
        if (!d.id.empty()) npcs[d.id] = d;
    }
}

void ContentDatabase::LoadDialogues(const JsonValue& doc) {
    for (const JsonValue& dj : doc["dialogues"].Elements()) {
        DialogueDef d;
        d.id = dj["id"].AsString("");
        d.start = dj["start"].AsString("");
        const std::string defaultSpeaker = dj["speaker"].AsString("");
        for (const auto& kv : dj["nodes"].Items()) {
            const JsonValue& nj = kv.second;
            DialogueNode n;
            n.id = kv.first;
            n.speaker = nj["speaker"].AsString(defaultSpeaker);
            n.text = nj["text"].AsString("");
            n.animation = nj["anim"].AsString("");
            n.camera = nj["camera"].AsString("");
            n.effects = nj["effects"];
            n.next = nj["next"].AsString("");
            n.end = nj["end"].AsBool(false);
            n.timeoutSeconds = nj["timeout"].AsNumber(0.0);
            n.timeoutChoice = nj["timeout_choice"].AsInt(-1);
            for (const JsonValue& bj : nj["branch"].Elements()) {
                n.branches.push_back({bj["if"], bj["next"].AsString("")});
            }
            for (const JsonValue& cj : nj["choices"].Elements()) {
                DialogueChoice c;
                c.text = cj["text"].AsString("");
                c.conditions = cj["if"];
                c.effects = cj["effects"];
                c.next = cj["next"].AsString("");
                c.hideIfLocked = cj["hide_if_locked"].AsBool(false);
                c.lockedHint = cj["locked_hint"].AsString("");
                n.choices.push_back(c);
            }
            d.nodes[n.id] = n;
        }
        if (d.start.empty() && !d.nodes.empty()) d.start = d.nodes.begin()->first;
        if (!d.id.empty()) dialogues[d.id] = d;
    }
}

void ContentDatabase::LoadMissions(const JsonValue& doc) {
    for (const JsonValue& mj : doc["missions"].Elements()) {
        MissionDef m;
        m.id = mj["id"].AsString("");
        m.chapter = mj["chapter"].AsInt(1);
        m.title = mj["title"].AsString("");
        m.summary = mj["summary"].AsString("");
        m.giver = mj["giver"].AsString("");
        m.inspiration = mj["inspiration"].AsString("");
        m.prerequisites = mj["prerequisites"];
        m.autoStart = mj["auto_start"].AsBool(false);
        m.onStart = mj["on_start"];
        m.onComplete = mj["on_complete"];
        m.onFail = mj["on_fail"];
        m.recoveryHint = mj["recovery_hint"].AsString("");
        std::string firstId;
        for (const JsonValue& oj : mj["objectives"].Elements()) {
            ObjectiveDef o;
            o.id = oj["id"].AsString("");
            if (firstId.empty()) firstId = o.id;
            o.type = ObjectiveTypeFromString(oj["type"].AsString("reach"));
            o.text = oj["text"].AsString("");
            o.target = oj["target"].AsString("");
            o.dialogue = oj["dialogue"].AsString("");
            o.marker = oj["marker"].AsString("");
            if (o.marker.empty() && (o.type == ObjectiveType::Reach || o.type == ObjectiveType::Drive)) o.marker = o.target;
            o.timeLimitMinutes = oj["time_limit_minutes"].AsNumber(0.0);
            o.deadlineHour = content_detail::ParseHour(oj["deadline"], -1.0);
            o.deadlineFromMissionStart = oj["deadline_anchor"].AsString("objective") == "mission";
            o.deadlineDayOffset = oj["deadline_day_offset"].AsInt(-1);
            o.decisionSeconds = oj["decision_seconds"].AsNumber(0.0);
            o.decisionDefault = oj["decision_default"].AsInt(-1);
            for (const JsonValue& dj : oj["options"].Elements()) {
                DecisionOption opt;
                opt.id = dj["id"].AsString("");
                opt.text = dj["text"].AsString("");
                opt.conditions = dj["if"];
                opt.effects = dj["effects"];
                opt.next = dj["next"].AsString("");
                o.options.push_back(opt);
            }
            o.onStart = oj["on_start"];
            o.onComplete = oj["on_complete"];
            o.next = oj["next"].AsString("");
            for (const JsonValue& bj : oj["next_if"].Elements()) {
                o.nextIf.push_back({bj["if"], bj["next"].AsString("")});
            }
            o.onFail = oj["on_fail"];
            o.failNext = oj["fail_next"].AsString("@fail");
            m.objectives[o.id] = o;
        }
        m.startObjective = mj["start"].AsString(firstId);
        if (!m.id.empty()) missions[m.id] = m;
    }
}

void ContentDatabase::LoadChapters(const JsonValue& doc) {
    for (const JsonValue& cj : doc["chapters"].Elements()) {
        ChapterDef c;
        c.number = cj["number"].AsInt(1);
        c.id = cj["id"].AsString("");
        c.title = cj["title"].AsString("");
        c.summary = cj["summary"].AsString("");
        c.entry = cj["entry"];
        c.contentStatus = cj["content_status"].AsString("design_only");
        chapters.push_back(c);
    }
    std::sort(chapters.begin(), chapters.end(), [](const ChapterDef& a, const ChapterDef& b) { return a.number < b.number; });
}

void ContentDatabase::LoadLocations(const JsonValue& doc) {
    for (const JsonValue& lj : doc["locations"].Elements()) {
        LocationDef l;
        l.id = lj["id"].AsString("");
        l.name = lj["name"].AsString("");
        l.district = lj["district"].AsString("");
        l.kind = lj["kind"].AsString("street");
        l.hasCoordinates = lj["lat"].IsNumber() && lj["lon"].IsNumber();
        l.lat = lj["lat"].AsNumber();
        l.lon = lj["lon"].AsNumber();
        l.interior = lj["interior"].AsBool(false);
        l.radiusMetres = lj["radius"].AsNumber(12.0);
        l.provenance = lj["provenance"].AsString("");
        l.note = lj["note"].AsString("");
        if (!l.id.empty()) locations[l.id] = l;
    }
}

void ContentDatabase::LoadDistricts(const JsonValue& doc) {
    for (const JsonValue& dj : doc["districts"].Elements()) {
        DistrictDef d;
        d.id = dj["id"].AsString("");
        d.name = dj["name"].AsString("");
        d.anchorLat = dj["anchor"]["lat"].AsNumber();
        d.anchorLon = dj["anchor"]["lon"].AsNumber();
        d.buildStatus = dj["build_status"].AsString("not_built");
        d.description = dj["description"].AsString("");
        d.themes = content_detail::StringList(dj["themes"]);
        if (!d.id.empty()) districts[d.id] = d;
    }
}

void ContentDatabase::LoadEcosystem(const JsonValue& doc) {
    for (const JsonValue& ej : doc["entries"].Elements()) {
        EcosystemEntry e;
        e.id = ej["id"].AsString("");
        e.name = ej["name"].AsString("");
        e.categories = content_detail::StringList(ej["categories"]);
        e.foundedYear = ej["founded_year"].AsInt(0);
        e.summary = ej["summary"].AsString("");
        e.statusLabel = ej["status"]["label"].AsString("");
        e.statusDetail = ej["status"]["detail"].AsString("");
        e.verification = ej["verification"].AsString("unverified");
        e.storylineHooks = content_detail::StringList(ej["storyline_hooks"]);
        for (const JsonValue& lj : ej["locations"].Elements()) {
            EcosystemLocation l;
            l.label = lj["label"].AsString("");
            l.address = lj["address"].AsString("");
            l.district = lj["district"].AsString("");
            l.period = lj["period"].AsString("");
            l.precision = lj["precision"].AsString("city");
            l.hasCoordinates = lj["lat"].IsNumber() && lj["lon"].IsNumber();
            l.lat = lj["lat"].AsNumber();
            l.lon = lj["lon"].AsNumber();
            l.source = lj["source"].AsString("");
            e.locations.push_back(l);
        }
        for (const JsonValue& sj : ej["sources"].Elements()) {
            const std::string url = sj["url"].AsString("");
            if (!url.empty()) e.sourceUrls.push_back(url);
        }
        if (!e.id.empty()) ecosystem[e.id] = e;
    }
}

std::vector<std::string> ContentDatabase::EcosystemCategories() const {
    std::set<std::string> cats;
    for (const auto& kv : ecosystem) {
        for (const std::string& c : kv.second.categories) cats.insert(c);
    }
    return std::vector<std::string>(cats.begin(), cats.end());
}

const NpcDef* ContentDatabase::FindNpc(const std::string& id) const {
    const auto it = npcs.find(id);
    return it == npcs.end() ? nullptr : &it->second;
}
const DialogueDef* ContentDatabase::FindDialogue(const std::string& id) const {
    const auto it = dialogues.find(id);
    return it == dialogues.end() ? nullptr : &it->second;
}
const MissionDef* ContentDatabase::FindMission(const std::string& id) const {
    const auto it = missions.find(id);
    return it == missions.end() ? nullptr : &it->second;
}
const LocationDef* ContentDatabase::FindLocation(const std::string& id) const {
    const auto it = locations.find(id);
    return it == locations.end() ? nullptr : &it->second;
}
const DistrictDef* ContentDatabase::FindDistrict(const std::string& id) const {
    const auto it = districts.find(id);
    return it == districts.end() ? nullptr : &it->second;
}
const EcosystemEntry* ContentDatabase::FindEcosystem(const std::string& id) const {
    const auto it = ecosystem.find(id);
    return it == ecosystem.end() ? nullptr : &it->second;
}

std::vector<std::string> ContentDatabase::Validate() const {
    std::vector<std::string> problems;
    auto speakerKnown = [&](const std::string& s) {
        return s.empty() || s == "player" || s == "narrator" || s == "phone" || npcs.count(s) > 0;
    };
    for (const auto& dkv : dialogues) {
        const DialogueDef& d = dkv.second;
        if (!d.nodes.count(d.start)) problems.push_back("dialogue " + d.id + ": start node '" + d.start + "' missing");
        for (const auto& nkv : d.nodes) {
            const DialogueNode& n = nkv.second;
            if (!speakerKnown(n.speaker)) problems.push_back("dialogue " + d.id + "/" + n.id + ": unknown speaker " + n.speaker);
            if (!n.next.empty() && !d.nodes.count(n.next))
                problems.push_back("dialogue " + d.id + "/" + n.id + ": next '" + n.next + "' missing");
            for (const DialogueChoice& c : n.choices) {
                if (!c.next.empty() && !d.nodes.count(c.next))
                    problems.push_back("dialogue " + d.id + "/" + n.id + ": choice next '" + c.next + "' missing");
            }
            if (n.timeoutSeconds > 0 && (n.timeoutChoice < 0 || n.timeoutChoice >= static_cast<int>(n.choices.size())))
                problems.push_back("dialogue " + d.id + "/" + n.id + ": timeout_choice out of range");
            for (const ConditionalNext& b : n.branches) {
                if (!d.nodes.count(b.next))
                    problems.push_back("dialogue " + d.id + "/" + n.id + ": branch next '" + b.next + "' missing");
            }
            if (!n.branches.empty() && !n.branches.back().conditions.IsNull())
                problems.push_back("dialogue " + d.id + "/" + n.id + ": last branch should be unconditional (fallback)");
            if (!n.end && n.next.empty() && n.choices.empty() && n.branches.empty())
                problems.push_back("dialogue " + d.id + "/" + n.id + ": dead end (no next, no choices, not end)");
        }
    }
    for (const auto& mkv : missions) {
        const MissionDef& m = mkv.second;
        if (!m.objectives.count(m.startObjective))
            problems.push_back("mission " + m.id + ": start objective '" + m.startObjective + "' missing");
        if (!m.giver.empty() && !npcs.count(m.giver)) problems.push_back("mission " + m.id + ": unknown giver " + m.giver);
        for (const auto& okv : m.objectives) {
            const ObjectiveDef& o = okv.second;
            const std::string where = "mission " + m.id + "/" + o.id;
            auto checkNext = [&](const std::string& next, const char* field) {
                if (!content_detail::IsSpecialTarget(next) && !m.objectives.count(next))
                    problems.push_back(where + ": " + field + " '" + next + "' missing");
            };
            checkNext(o.next, "next");
            checkNext(o.failNext, "fail_next");
            for (const ObjectiveBranch& b : o.nextIf) checkNext(b.next, "next_if");
            for (const DecisionOption& opt : o.options) checkNext(opt.next, "option next");
            if ((o.type == ObjectiveType::Reach || o.type == ObjectiveType::Drive) && !locations.count(o.target))
                problems.push_back(where + ": unknown location " + o.target);
            if (!o.marker.empty() && !locations.count(o.marker))
                problems.push_back(where + ": unknown marker location " + o.marker);
            if ((o.type == ObjectiveType::Talk || o.type == ObjectiveType::PhoneCall)) {
                if (!dialogues.count(o.dialogue)) problems.push_back(where + ": unknown dialogue " + o.dialogue);
                if (o.type == ObjectiveType::Talk && !npcs.count(o.target)) problems.push_back(where + ": unknown npc " + o.target);
            }
            if (o.type == ObjectiveType::Decision && o.options.empty()) problems.push_back(where + ": decision without options");
            if (o.type == ObjectiveType::Decision && o.decisionSeconds > 0 &&
                (o.decisionDefault < 0 || o.decisionDefault >= static_cast<int>(o.options.size())))
                problems.push_back(where + ": decision_default out of range");
            if (o.next.empty() && o.nextIf.empty() && o.options.empty())
                problems.push_back(where + ": objective has no exit (next/next_if/options)");
        }
    }
    for (const auto& nkv : npcs) {
        for (const RoutineEntry& r : nkv.second.routine) {
            if (!r.location.empty() && !locations.count(r.location))
                problems.push_back("npc " + nkv.first + ": routine location '" + r.location + "' missing");
        }
    }
    for (const auto& lkv : locations) {
        if (!lkv.second.district.empty() && !districts.empty() && !districts.count(lkv.second.district))
            problems.push_back("location " + lkv.first + ": unknown district " + lkv.second.district);
    }
    return problems;
}

bool ResolveEcosystemPosition(const EcosystemEntry& e, const ContentDatabase& db, const GeoProjection& proj,
                              Vec2& outPos, bool& approximate) {
    // Prefer a current, coordinate-bearing location.
    const EcosystemLocation* best = nullptr;
    for (const EcosystemLocation& l : e.locations) {
        if (l.hasCoordinates && (best == nullptr || l.period == "current")) best = &l;
    }
    if (best) {
        approximate = best->precision != "address";
        outPos = proj.ToLocal(best->lat, best->lon);
        return true;
    }
    approximate = true;
    const DistrictDef* d = nullptr;
    for (const EcosystemLocation& l : e.locations) {
        const DistrictDef* candidate = db.FindDistrict(l.district);
        if (!candidate) continue;
        if (!d || l.period == "current") d = candidate;
        if (l.period == "current") break;
    }
    if (!d) return false;
    Vec2 anchor = proj.ToLocal(d->anchorLat, d->anchorLon);
    // Stable offset within a 60-220 m ring so pins in one district don't stack.
    const uint64_t h = content_detail::StableHash(e.id);
    const double angle = static_cast<double>(h % 3600) / 3600.0 * 6.283185307179586;
    const double radius = 60.0 + static_cast<double>((h >> 16) % 160);
    anchor.x += std::cos(angle) * radius;
    anchor.y += std::sin(angle) * radius;
    outPos = anchor;
    return true;
}

} // namespace stockholm::sim
