// STOCKHOLM — the founder simulation facade. Owns time, economy, cap table,
// relationships, missions, dialogue, phone and Founder Map discovery state.
// The Unreal layer (UStockholmSimSubsystem) forwards world events into this
// class and drains SimEvents to drive UI, cinematics and world changes.
#pragma once

#include "Sim/Content.h"
#include "Sim/FounderState.h"
#include "Sim/Json.h"
#include "Sim/WorldClock.h"

#include <deque>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace stockholm::sim {

constexpr int kSaveVersion = 1;

struct NpcRelationship {
    double affinity = 0.0; // -100..100 how much they like you
    double trust = 20.0;   // 0..100 whether they believe you deliver
    bool met = false;
    std::set<std::string> memories;
    double lastSeenMinute = -1.0;
};

struct Commitment {
    std::string id;
    std::string npcId;
    std::string text;
    double dueMinute = 0.0;
    enum class Status : uint8_t { Pending, Fulfilled, Broken } status = Status::Pending;
    JsonValue onBroken;
    JsonValue onFulfilled;
};

struct PhoneMessage {
    std::string thread;  // contact id
    std::string sender;  // contact id or "player"
    std::string text;
    double minute = 0.0;
    bool read = false;
};

enum class MissionStatus : uint8_t { Locked, Available, Active, Completed, Failed };
const char* MissionStatusToString(MissionStatus s);
MissionStatus MissionStatusFromString(const std::string& s);

struct MissionRuntime {
    MissionStatus status = MissionStatus::Locked;
    std::string objective;
    double missionStartMinute = 0.0;
    double objectiveStartMinute = 0.0;
    int attempts = 0;
    std::vector<std::string> history; // objective ids visited, for debugging/branch analytics
};

enum class SimEventType : uint8_t {
    PhoneMessage, Notification, MissionAvailable, MissionStarted, ObjectiveChanged, MissionCompleted,
    MissionFailed, ChapterChanged, PoiDiscovered, CommitmentMade, CommitmentBroken, CommitmentFulfilled,
    StatChanged, RentDue, RentOverdue, Evicted, OfferReceived, OfferAccepted, DialogueStarted, DialogueEnded,
    WorldEvent // scripted hook for the world layer (cinematics, spawns, door unlocks…)
};
const char* SimEventTypeToString(SimEventType t);

struct SimEvent {
    SimEventType type = SimEventType::Notification;
    std::string id;
    std::string text;
    double value = 0.0;
};

struct DialogueLineView {
    bool active = false;
    std::string dialogueId;
    std::string nodeId;
    std::string speaker;
    std::string speakerName;
    std::string text;
    std::string animation;
    std::string camera;
    double timeoutSeconds = 0.0;
    int timeoutChoice = -1;
    bool hasChoices = false;
    bool isEnd = false;
};

struct ChoiceView {
    int index = 0;
    std::string text;
    bool available = true;
    std::string lockedHint;
};

struct ObjectiveView {
    bool valid = false;
    std::string missionId;
    std::string missionTitle;
    std::string objectiveId;
    std::string text;
    ObjectiveType type = ObjectiveType::Reach;
    std::string target;
    std::string marker;
    double minutesRemaining = -1.0;
    double decisionSeconds = 0.0;
    int decisionDefault = -1;
    std::vector<ChoiceView> options;
};

class FounderSim {
public:
    explicit FounderSim(uint64_t seed = 0x5EED5EEDULL);

    // ---- setup -------------------------------------------------------------
    ContentDatabase& Content() { return content_; }
    const ContentDatabase& Content() const { return content_; }
    // Call after content is loaded; starts the opening sequence state.
    void BeginNewGame();

    // ---- time --------------------------------------------------------------
    // Real seconds → advances the game clock by timeScale.
    void Tick(double realSeconds);
    void AdvanceGameMinutes(double minutes);
    void Sleep(double hours); // bed interaction: restores energy, advances time
    WorldClock& Clock() { return clock_; }
    const WorldClock& Clock() const { return clock_; }

    // ---- state -------------------------------------------------------------
    FounderState& State() { return state_; }
    const FounderState& State() const { return state_; }
    double Fact(const std::string& key) const;
    void SetFact(const std::string& key, double value);
    NpcRelationship& Relationship(const std::string& npcId);
    const std::map<std::string, NpcRelationship>& Relationships() const { return relationships_; }
    const std::vector<Commitment>& Commitments() const { return commitments_; }
    int CurrentChapter() const { return chapter_; }
    const ChapterDef* CurrentChapterDef() const;

    // ---- narrative data interpreter -----------------------------------------
    bool Evaluate(const JsonValue& conditions);
    void Apply(const JsonValue& effects);

    // ---- world → sim notifications -----------------------------------------
    void NotifyReached(const std::string& locationId, bool inVehicle);
    void NotifyInteracted(const std::string& targetId);
    void NotifyCustomEvent(const std::string& eventId);

    // ---- missions -----------------------------------------------------------
    bool StartMission(const std::string& missionId);
    void FailMission(const std::string& missionId);
    MissionStatus GetMissionStatus(const std::string& missionId) const;
    const std::map<std::string, MissionRuntime>& Missions() const { return missions_; }
    std::vector<ObjectiveView> ActiveObjectives();
    // Decision objective choice (in-world prompt wheel).
    bool ChooseDecision(const std::string& missionId, int optionIndex);
    // Which conversation an NPC should open right now: the active Talk
    // objective targeting them, else "<npc>_ambient" if authored, else "".
    std::string DialogueForNpc(const std::string& npcId) const;
    // Dialogue of an active PhoneCall objective (the phone UI shows it as an
    // incoming call / unread thread), or "" when none.
    std::string PendingPhoneCall() const;

    // ---- dialogue -----------------------------------------------------------
    bool StartDialogue(const std::string& dialogueId);
    bool IsDialogueActive() const { return !dialogueId_.empty(); }
    DialogueLineView CurrentLine() const;
    std::vector<ChoiceView> CurrentChoices();
    bool ChooseDialogueOption(int index);
    bool AdvanceDialogue(); // for nodes without choices

    // ---- phone --------------------------------------------------------------
    const std::vector<PhoneMessage>& Messages() const { return messages_; }
    void SendPhoneMessage(const std::string& from, const std::string& text);
    int UnreadCount() const;
    void MarkThreadRead(const std::string& thread);

    // ---- money actions ------------------------------------------------------
    bool PayRent();
    bool TransferToCompany(double amount);
    bool AcceptOffer(const std::string& offerId);
    void DeclineOffer(const std::string& offerId);

    // ---- Founder Map ---------------------------------------------------------
    bool IsDiscovered(const std::string& entryId) const { return discovered_.count(entryId) > 0; }
    bool Discover(const std::string& entryId);
    const std::set<std::string>& Discovered() const { return discovered_; }

    // ---- events ---------------------------------------------------------------
    bool PollEvent(SimEvent& out);
    const std::deque<SimEvent>& PendingEvents() const { return events_; }

    // ---- NPC routines ---------------------------------------------------------
    const RoutineEntry* CurrentRoutine(const std::string& npcId) const;

    // ---- persistence ----------------------------------------------------------
    JsonValue Save() const;
    bool Load(const JsonValue& save, std::string* error = nullptr);

    Rng& Random() { return rng_; }

private:
    void Emit(SimEventType type, const std::string& id, const std::string& text = "", double value = 0.0);
    void OnHourPassed();
    void OnDayPassed();
    void CheckCommitments();
    void CheckMissionTimers();
    void RefreshMissionAvailability();
    void UpdateChapter();

    bool EvaluateOne(const JsonValue& c);
    void ApplyOne(const JsonValue& e);
    static bool Compare(double lhs, const std::string& op, double rhs);

    void EnterObjective(const std::string& missionId, const std::string& objectiveId);
    void CompleteObjective(const std::string& missionId);
    void FailObjective(const std::string& missionId);
    void CompleteMission(const std::string& missionId);
    std::string ResolveNext(const ObjectiveDef& o);
    static double DeadlineMinute(const ObjectiveDef& o, const MissionRuntime& rt); // < 0 if none
    void GoTo(const std::string& missionId, const std::string& next);

    void EnterDialogueNode(const std::string& nodeId);
    void EndDialogue();
    void OnDialogueFinished(const std::string& dialogueId);

    ContentDatabase content_;
    WorldClock clock_;
    FounderState state_;
    Rng rng_;
    std::map<std::string, double> facts_;
    std::map<std::string, NpcRelationship> relationships_;
    std::vector<Commitment> commitments_;
    std::vector<PhoneMessage> messages_;
    std::map<std::string, MissionRuntime> missions_;
    std::set<std::string> discovered_;
    std::deque<SimEvent> events_;
    int chapter_ = 1;
    double minuteAccumulator_ = 0.0;
    int64_t lastDayIndex_ = 0;
    int applyDepth_ = 0;
    bool refreshing_ = false;

    std::string dialogueId_;
    std::string dialogueNode_;
};

} // namespace stockholm::sim
