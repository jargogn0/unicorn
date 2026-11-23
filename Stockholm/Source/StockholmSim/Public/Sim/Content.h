// STOCKHOLM — data-driven content definitions loaded from Content/Data/*.json.
// Conditions and effects are kept as JSON and interpreted by FounderSim so
// writers can author missions without recompiling (see GAME_DESIGN.md §9).
#pragma once

#include "Sim/Geo.h"
#include "Sim/Json.h"

#include <map>
#include <string>
#include <vector>

namespace stockholm::sim {

struct RoutineEntry {
    std::string days = "all"; // all | weekdays | weekends
    double fromHour = 0.0;    // may wrap past midnight (from > to)
    double toHour = 24.0;
    std::string location;     // LocationDef id
    std::string activity;     // work, coffee, gym, party, sleep, commute, ...
};

struct NpcDef {
    std::string id;
    std::string name;
    std::string role;        // e.g. "procurement lead", "angel investor"
    std::string pronouns;
    std::string background;  // short biography (fictional character)
    std::string motivation;
    std::vector<std::string> traits;
    std::string homeDistrict;
    std::vector<RoutineEntry> routine;
    std::string appearance;  // MetaHuman preset / outfit tags for the art pipeline
    std::string voice;       // VO casting note
};

// A condition → target pair, used for dialogue routing nodes and objective branches.
struct ConditionalNext {
    JsonValue conditions;
    std::string next;
};

struct DialogueChoice {
    std::string text;
    JsonValue conditions;   // array/object, empty = always
    JsonValue effects;      // array
    std::string next;       // node id or "" to end
    bool hideIfLocked = false;
    std::string lockedHint; // shown greyed out when locked and not hidden
};

struct DialogueNode {
    std::string id;
    std::string speaker;    // npc id, "player" or "narrator"
    std::string text;
    std::string animation;  // gesture tag for the dialogue animation system
    std::string camera;     // shot tag: "two_shot", "close_npc", "close_player", "phone", ...
    JsonValue effects;      // applied on entering the node
    std::string next;       // auto-advance target when there are no choices
    std::vector<DialogueChoice> choices;
    // Routing node: when non-empty, the first branch whose conditions hold is
    // entered immediately (after effects). Used for memory-dependent lines.
    std::vector<ConditionalNext> branches;
    double timeoutSeconds = 0.0; // > 0: timed choice (real seconds)
    int timeoutChoice = -1;      // index chosen on timeout
    bool end = false;
};

struct DialogueDef {
    std::string id;
    std::string start;
    std::map<std::string, DialogueNode> nodes;
};

using ObjectiveBranch = ConditionalNext;

struct DecisionOption {
    std::string id;
    std::string text;
    JsonValue conditions;
    JsonValue effects;
    std::string next;
};

enum class ObjectiveType : uint8_t {
    Reach,      // arrive at a location trigger (on foot or by vehicle)
    Drive,      // arrive at a location while driving
    Talk,       // complete a dialogue with an NPC
    Interact,   // use a world object (laptop, door, whiteboard, phone)
    Decision,   // in-world timed decision (prompt wheel)
    WaitUntil,  // until a time of day
    PhoneCall,  // answer/complete a phone conversation
    Custom      // completed by a scripted event id from the world
};
ObjectiveType ObjectiveTypeFromString(const std::string& s);
const char* ObjectiveTypeToString(ObjectiveType t);

struct ObjectiveDef {
    std::string id;
    ObjectiveType type = ObjectiveType::Reach;
    std::string text;
    std::string target;      // location id, npc id, object id or event id
    std::string dialogue;    // for Talk / PhoneCall
    std::string marker;      // location id for the GPS marker (defaults to target for Reach/Drive)
    double timeLimitMinutes = 0.0; // game minutes, 0 = none
    double deadlineHour = -1.0;    // next occurrence of this hour after the anchor, -1 = none
    bool deadlineFromMissionStart = false; // anchor = mission start instead of objective start
    int deadlineDayOffset = -1; // >= 0: anchor's calendar day + N days at deadlineHour ("tomorrow 10:00" = 1)
    double decisionSeconds = 0.0;  // real-time limit for Decision
    int decisionDefault = -1;
    std::vector<DecisionOption> options;
    JsonValue onStart;
    JsonValue onComplete;
    std::string next;        // objective id, "@complete" or "@fail"
    std::vector<ObjectiveBranch> nextIf; // first matching branch wins over `next`
    JsonValue onFail;
    std::string failNext;    // objective id or "@fail"
};

struct MissionDef {
    std::string id;
    int chapter = 1;
    std::string title;
    std::string summary;
    std::string giver;
    std::string inspiration; // optional ecosystem entry id that inspired it
    JsonValue prerequisites;
    bool autoStart = false;
    std::string startObjective;
    std::map<std::string, ObjectiveDef> objectives;
    JsonValue onStart;
    JsonValue onComplete;
    JsonValue onFail;
    std::string recoveryHint; // tells the player how failure can be recovered from
};

struct ChapterDef {
    int number = 1;
    std::string id;
    std::string title;
    std::string summary;
    JsonValue entry;          // conditions to enter
    std::string contentStatus; // implemented | partial | design_only
};

struct LocationDef {
    std::string id;
    std::string name;
    std::string district;
    std::string kind;     // apartment, cafe, office, coworking, event_space, landmark, street
    double lat = 0.0;
    double lon = 0.0;
    bool hasCoordinates = false;
    bool interior = false;
    double radiusMetres = 12.0;
    std::string provenance; // "osm:<id>", "fictional venue on real street", ...
    std::string note;
};

struct DistrictDef {
    std::string id;
    std::string name;
    double anchorLat = 0.0;
    double anchorLon = 0.0;
    std::string buildStatus; // playable | blockout | not_built
    std::string description;
    std::vector<std::string> themes;
};

struct EcosystemLocation {
    std::string label;
    std::string address;
    std::string district;
    std::string period;
    std::string precision; // address | street | district | city
    double lat = 0.0;
    double lon = 0.0;
    bool hasCoordinates = false;
    std::string source;
};

struct EcosystemEntry {
    std::string id;
    std::string name;
    std::vector<std::string> categories;
    int foundedYear = 0;
    std::string summary;
    std::string statusLabel;
    std::string statusDetail;
    std::string verification;
    std::vector<std::string> storylineHooks;
    std::vector<EcosystemLocation> locations;
    std::vector<std::string> sourceUrls;
    bool HasCategory(const std::string& c) const;
};

class ContentDatabase {
public:
    // Loads every file listed in <dataRoot>/manifest.json.
    bool LoadFromManifest(const std::string& dataRoot, std::string* error = nullptr);
    // Loads one document; dispatches on its top-level "kind" field
    // (npcs, dialogues, missions, chapters, locations, districts, ecosystem).
    bool AddDocument(const JsonValue& doc, std::string* error = nullptr);

    // Validates cross-references (dialogue next ids, mission objective links,
    // locations referenced by objectives, npc ids). Returns problems found.
    std::vector<std::string> Validate() const;

    const NpcDef* FindNpc(const std::string& id) const;
    const DialogueDef* FindDialogue(const std::string& id) const;
    const MissionDef* FindMission(const std::string& id) const;
    const LocationDef* FindLocation(const std::string& id) const;
    const DistrictDef* FindDistrict(const std::string& id) const;
    const EcosystemEntry* FindEcosystem(const std::string& id) const;

    std::map<std::string, NpcDef> npcs;
    std::map<std::string, DialogueDef> dialogues;
    std::map<std::string, MissionDef> missions;
    std::vector<ChapterDef> chapters; // sorted by number
    std::map<std::string, LocationDef> locations;
    std::map<std::string, DistrictDef> districts;
    std::map<std::string, EcosystemEntry> ecosystem;
    std::vector<std::string> EcosystemCategories() const;

private:
    void LoadNpcs(const JsonValue& doc);
    void LoadDialogues(const JsonValue& doc);
    void LoadMissions(const JsonValue& doc);
    void LoadChapters(const JsonValue& doc);
    void LoadLocations(const JsonValue& doc);
    void LoadDistricts(const JsonValue& doc);
    void LoadEcosystem(const JsonValue& doc);
};

// Resolves the in-world position of an ecosystem entry: exact coordinates when
// sourced, else the district anchor plus a stable per-id offset (`approximate`
// is then true and the Founder Map labels the pin "approximate area").
// Returns false when the entry has neither coordinates nor a known Stockholm
// district (e.g. city-level precision only): such entries are listed in the
// Founder Map directory but get no world pin, rather than an invented one.
bool ResolveEcosystemPosition(const EcosystemEntry& e, const ContentDatabase& db, const GeoProjection& proj,
                              Vec2& outPos, bool& approximate);

} // namespace stockholm::sim
