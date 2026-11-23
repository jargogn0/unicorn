#include "Sim/FounderSim.h"

#include <algorithm>
#include <cinttypes>
#include <cmath>
#include <cstdio>
#include <cstdlib>

namespace stockholm::sim {

namespace sim_detail {
constexpr int kMaxApplyDepth = 32;
constexpr double kMinutesPerDay = 1440.0;

std::string U64ToHex(uint64_t v) {
    char buf[24];
    std::snprintf(buf, sizeof(buf), "%016" PRIx64, v);
    return buf;
}
uint64_t HexToU64(const std::string& s) {
    return static_cast<uint64_t>(std::strtoull(s.c_str(), nullptr, 16));
}

const char* kMissionStatus[] = {"locked", "available", "active", "completed", "failed"};
const char* kEventTypes[] = {
    "phone_message", "notification", "mission_available", "mission_started", "objective_changed",
    "mission_completed", "mission_failed", "chapter_changed", "poi_discovered", "commitment_made",
    "commitment_broken", "commitment_fulfilled", "stat_changed", "rent_due", "rent_overdue", "evicted",
    "offer_received", "offer_accepted", "dialogue_started", "dialogue_ended", "world_event"};

// Effects/conditions may be authored as a single object or an array.
template <typename Fn>
void ForEachEntry(const JsonValue& v, Fn&& fn) {
    if (v.IsArray()) {
        for (const JsonValue& e : v.Elements()) fn(e);
    } else if (v.IsObject()) {
        fn(v);
    }
}

std::string FormatSek(double v) {
    char buf[48];
    std::snprintf(buf, sizeof(buf), "%.0f SEK", v);
    return buf;
}
} // namespace sim_detail

const char* MissionStatusToString(MissionStatus s) { return sim_detail::kMissionStatus[static_cast<int>(s)]; }
MissionStatus MissionStatusFromString(const std::string& s) {
    for (int i = 0; i < 5; ++i) {
        if (s == sim_detail::kMissionStatus[i]) return static_cast<MissionStatus>(i);
    }
    return MissionStatus::Locked;
}
const char* SimEventTypeToString(SimEventType t) { return sim_detail::kEventTypes[static_cast<int>(t)]; }

FounderSim::FounderSim(uint64_t seed) : rng_(seed) {}

void FounderSim::BeginNewGame() {
    clock_ = WorldClock();
    state_ = FounderState();
    facts_.clear();
    relationships_.clear();
    commitments_.clear();
    messages_.clear();
    discovered_.clear();
    events_.clear();
    missions_.clear();
    chapter_ = 1;
    minuteAccumulator_ = 0.0;
    lastDayIndex_ = clock_.DayIndex();
    dialogueId_.clear();
    dialogueNode_.clear();
    for (const auto& kv : content_.missions) missions_[kv.first] = MissionRuntime{};
    SetFact("chapter", 1);
    // Places every Stockholm founder knows exist from day one.
    for (const auto& kv : content_.ecosystem) {
        if (kv.second.HasCategory("unicorn_landmark") || kv.second.HasCategory("university_research")) {
            discovered_.insert(kv.first);
        }
    }
    // The opening cinematic is triggered by m00's on_start data, not hard-coded here.
    RefreshMissionAvailability();
    UpdateChapter();
}

// ------------------------------------------------------------------ time

void FounderSim::Tick(double realSeconds) {
    if (realSeconds <= 0.0) return;
    AdvanceGameMinutes(realSeconds * clock_.timeScale / 60.0);
}

void FounderSim::AdvanceGameMinutes(double minutes) {
    if (minutes <= 0.0) return;
    // Step at most one hour at a time so hourly/daily systems never skip.
    double remaining = minutes;
    while (remaining > 0.0) {
        const double step = std::min(remaining, 60.0);
        remaining -= step;
        const int hours = clock_.AdvanceMinutes(step);
        for (int h = 0; h < hours; ++h) OnHourPassed();
        while (clock_.DayIndex() > lastDayIndex_) {
            ++lastDayIndex_;
            OnDayPassed();
        }
        CheckMissionTimers();
        CheckCommitments();
    }
}

void FounderSim::Sleep(double hours) {
    if (hours <= 0.0) return;
    const double energyBefore = state_.Get(Stat::Energy);
    AdvanceGameMinutes(hours * 60.0);
    // Restores ~11 energy per hour slept; housing quality helps.
    const double housingBonus = 1.0 + 0.08 * state_.Get(Stat::HousingTier);
    state_.Set(Stat::Energy, energyBefore + hours * 11.0 * housingBonus);
    if (hours >= 6.5) state_.Add(Stat::Wellbeing, 2.0);
    if (hours < 4.0) state_.Add(Stat::Wellbeing, -3.0);
}

void FounderSim::OnHourPassed() {
    clock_.StepWeatherHour(rng_);
    const double hour = clock_.HourOfDay();
    if (hour >= 7.0 && hour <= 23.5) state_.Add(Stat::Energy, -2.5);
    if (state_.Get(Stat::Energy) < 15.0) state_.Add(Stat::Wellbeing, -0.5);
}

void FounderSim::OnDayPassed() {
    const CivilDate date = clock_.Date();

    // Personal living costs.
    state_.Add(Stat::PersonalCash, -state_.Get(Stat::LivingCostDaily));

    // Company economics (daily accrual of monthly figures).
    const double dailyNet = (state_.Get(Stat::Mrr) - state_.Get(Stat::MonthlyBurn)) / 30.0;
    state_.Add(Stat::CompanyCash, dailyNet);

    // Monthly churn on the 1st.
    if (date.day == 1) {
        const double customers = state_.Get(Stat::Customers);
        if (customers > 0.0) {
            const double lost = std::floor(customers * (1.0 - state_.Get(Stat::Retention)) + rng_.NextDouble());
            if (lost > 0.0) {
                const double arpa = state_.Get(Stat::Mrr) / customers;
                state_.Add(Stat::Customers, -lost);
                state_.Add(Stat::Mrr, -arpa * lost);
                Emit(SimEventType::Notification, "churn", "A customer cancelled this month.", lost);
            }
        }
        state_.rentPaidThisMonth = false;
    }

    // Rent cycle.
    if (state_.Get(Stat::RentMonthly) > 0.0) {
        const int due = state_.rentDueDayOfMonth;
        if (!state_.rentPaidThisMonth && date.day == due - 5) {
            Emit(SimEventType::RentDue, "rent", "Rent due in 5 days.", state_.Get(Stat::RentMonthly));
        }
        if (!state_.rentPaidThisMonth && (date.day > due || state_.rentOverdueDays > 0)) {
            ++state_.rentOverdueDays;
            SetFact("rent_overdue_days", state_.rentOverdueDays);
            if (state_.rentOverdueDays == 1) {
                Emit(SimEventType::RentOverdue, "rent", "Rent is overdue.", state_.Get(Stat::RentMonthly));
                SendPhoneMessage("landlord", "Hi, the rent didn't come through. Can you sort it this week?");
            } else if (state_.rentOverdueDays == 6) {
                SendPhoneMessage("landlord", "I need the rent by Friday or I'll have to give the room to someone else.");
                state_.Add(Stat::Wellbeing, -6.0);
            } else if (state_.rentOverdueDays >= 10) {
                // Recoverable failure: you lose the sublet and move onto a friend's sofa.
                state_.Set(Stat::HousingTier, 0.0);
                state_.Set(Stat::RentMonthly, 0.0);
                state_.Add(Stat::Wellbeing, -15.0);
                state_.rentOverdueDays = 0;
                SetFact("evicted", 1);
                Emit(SimEventType::Evicted, "sublet", "You lost the room. Sami says the sofa is yours for now.");
            }
        }
    }

    // Wellbeing drifts with energy and relationships.
    const double energy = state_.Get(Stat::Energy);
    if (energy > 60.0) state_.Add(Stat::Wellbeing, 0.5);
    if (energy < 25.0) state_.Add(Stat::Wellbeing, -1.5);
    if (state_.Get(Stat::PersonalCash) < 0.0) state_.Add(Stat::Wellbeing, -1.0);

    // Offer expiry.
    const double now = clock_.TotalMinutes();
    for (size_t i = 0; i < state_.openOffers.size();) {
        const FundingOffer& o = state_.openOffers[i];
        if (now - o.createdAtMinute > o.expiresInDays * sim_detail::kMinutesPerDay) {
            SetFact("offer_expired_" + o.id, 1);
            Emit(SimEventType::Notification, o.id, o.investorName + "'s offer has expired.");
            state_.openOffers.erase(state_.openOffers.begin() + static_cast<std::ptrdiff_t>(i));
        } else {
            ++i;
        }
    }
    SetFact("day", static_cast<double>(clock_.DayIndex()));
    RefreshMissionAvailability();
}

void FounderSim::CheckCommitments() {
    const double now = clock_.TotalMinutes();
    for (size_t i = 0; i < commitments_.size(); ++i) {
        if (commitments_[i].status != Commitment::Status::Pending || now <= commitments_[i].dueMinute) continue;
        commitments_[i].status = Commitment::Status::Broken;
        const Commitment c = commitments_[i]; // copy: Apply may push more commitments
        NpcRelationship& rel = Relationship(c.npcId);
        rel.memories.insert("broke:" + c.id);
        if (c.onBroken.IsNull()) {
            rel.trust = std::max(0.0, rel.trust - 12.0);
        } else {
            Apply(c.onBroken);
        }
        Emit(SimEventType::CommitmentBroken, c.id, c.text);
    }
}

// ------------------------------------------------------------------ facts & relationships

double FounderSim::Fact(const std::string& key) const {
    const auto it = facts_.find(key);
    return it == facts_.end() ? 0.0 : it->second;
}

void FounderSim::SetFact(const std::string& key, double value) { facts_[key] = value; }

NpcRelationship& FounderSim::Relationship(const std::string& npcId) { return relationships_[npcId]; }

const ChapterDef* FounderSim::CurrentChapterDef() const {
    for (const ChapterDef& c : content_.chapters) {
        if (c.number == chapter_) return &c;
    }
    return nullptr;
}

void FounderSim::UpdateChapter() {
    bool advanced = true;
    while (advanced) {
        advanced = false;
        for (const ChapterDef& c : content_.chapters) {
            if (c.number != chapter_ + 1) continue;
            if (!c.entry.IsNull() && Evaluate(c.entry)) {
                chapter_ = c.number;
                SetFact("chapter", chapter_);
                Emit(SimEventType::ChapterChanged, c.id, c.title, chapter_);
                advanced = true;
            }
            break;
        }
    }
}

// ------------------------------------------------------------------ conditions

bool FounderSim::Compare(double lhs, const std::string& op, double rhs) {
    if (op == ">=") return lhs >= rhs;
    if (op == ">") return lhs > rhs;
    if (op == "<=") return lhs <= rhs;
    if (op == "<") return lhs < rhs;
    if (op == "!=") return std::fabs(lhs - rhs) > 1e-9;
    return std::fabs(lhs - rhs) <= 1e-9; // "==" default
}

bool FounderSim::Evaluate(const JsonValue& conditions) {
    if (conditions.IsNull()) return true;
    if (conditions.IsArray()) {
        for (const JsonValue& c : conditions.Elements()) {
            if (!EvaluateOne(c)) return false;
        }
        return true;
    }
    return EvaluateOne(conditions);
}

bool FounderSim::EvaluateOne(const JsonValue& c) {
    if (!c.IsObject()) return true;
    const std::string op = c["op"].AsString("==");
    if (c.Has("all")) return Evaluate(c["all"]);
    if (c.Has("any")) {
        for (const JsonValue& sub : c["any"].Elements()) {
            if (EvaluateOne(sub)) return true;
        }
        return false;
    }
    if (c.Has("not")) return !Evaluate(c["not"]);
    if (c.Has("fact")) {
        const double v = Fact(c["fact"].AsString());
        if (!c.Has("value")) return v != 0.0;
        return Compare(v, op, c["value"].AsNumber());
    }
    if (c.Has("stat")) {
        if (c["stat"].AsString() == "runway_months") return Compare(state_.RunwayMonths(), op, c["value"].AsNumber());
        if (c["stat"].AsString() == "founder_ownership")
            return Compare(state_.capTable.FounderOwnership(), op, c["value"].AsNumber());
        Stat s;
        if (!StatFromString(c["stat"].AsString(), s)) return false;
        return Compare(state_.Get(s), op, c["value"].AsNumber());
    }
    if (c.Has("rel")) {
        const NpcRelationship& r = Relationship(c["rel"].AsString());
        const std::string field = c["field"].AsString("affinity");
        const double v = field == "trust" ? r.trust : r.affinity;
        return Compare(v, op, c["value"].AsNumber());
    }
    if (c.Has("met")) return Relationship(c["met"].AsString()).met;
    if (c.Has("memory")) {
        const NpcRelationship& r = Relationship(c["memory"].AsString());
        if (c.Has("has")) return r.memories.count(c["has"].AsString()) > 0;
        if (c.Has("lacks")) return r.memories.count(c["lacks"].AsString()) == 0;
        return !r.memories.empty();
    }
    if (c.Has("mission")) {
        const MissionStatus st = GetMissionStatus(c["mission"].AsString());
        return st == MissionStatusFromString(c["status"].AsString("completed"));
    }
    if (c.Has("objective")) {
        // {"objective": "o3", "mission": ...} handled above; here: {"objective":"m/o"} active check
        const std::string ref = c["objective"].AsString();
        const size_t slash = ref.find('/');
        if (slash == std::string::npos) return false;
        const auto it = missions_.find(ref.substr(0, slash));
        return it != missions_.end() && it->second.status == MissionStatus::Active &&
               it->second.objective == ref.substr(slash + 1);
    }
    if (c.Has("chapter_at_least")) return chapter_ >= c["chapter_at_least"].AsInt();
    if (c.Has("hour_between")) {
        const double from = c["hour_between"][static_cast<size_t>(0)].AsNumber();
        const double to = c["hour_between"][static_cast<size_t>(1)].AsNumber();
        const double h = clock_.HourOfDay();
        return from <= to ? (h >= from && h < to) : (h >= from || h < to);
    }
    if (c.Has("weekend")) return clock_.IsWeekend() == c["weekend"].AsBool(true);
    if (c.Has("weather_in")) {
        const std::string w = WeatherToString(clock_.Weather().kind);
        for (const JsonValue& k : c["weather_in"].Elements()) {
            if (k.AsString() == w) return true;
        }
        return false;
    }
    if (c.Has("discovered")) return IsDiscovered(c["discovered"].AsString());
    if (c.Has("commitment")) {
        const std::string want = c["status"].AsString("fulfilled");
        for (const Commitment& cm : commitments_) {
            if (cm.id != c["commitment"].AsString()) continue;
            const char* st = cm.status == Commitment::Status::Pending ? "pending"
                             : cm.status == Commitment::Status::Fulfilled ? "fulfilled" : "broken";
            return want == st;
        }
        return want == "none";
    }
    if (c.Has("offer_open")) {
        for (const FundingOffer& o : state_.openOffers) {
            if (o.id == c["offer_open"].AsString()) return true;
        }
        return false;
    }
    if (c.Has("can_afford")) return state_.Get(Stat::PersonalCash) >= c["can_afford"].AsNumber();
    if (c.Has("rent_paid")) return state_.rentPaidThisMonth == c["rent_paid"].AsBool(true);
    return true; // unknown keys are permissive; Validate() tooling reports them
}

// ------------------------------------------------------------------ effects

void FounderSim::Apply(const JsonValue& effects) {
    if (effects.IsNull()) return;
    if (applyDepth_ >= sim_detail::kMaxApplyDepth) return; // runaway authoring loop guard
    ++applyDepth_;
    sim_detail::ForEachEntry(effects, [this](const JsonValue& e) { ApplyOne(e); });
    --applyDepth_;
    if (applyDepth_ == 0) {
        RefreshMissionAvailability();
        UpdateChapter();
    }
}

void FounderSim::ApplyOne(const JsonValue& e) {
    if (!e.IsObject()) return;
    auto statEffect = [&](const std::string& name, double value, bool set) {
        Stat s;
        if (!StatFromString(name, s)) return;
        const double before = state_.Get(s);
        if (set) state_.Set(s, value); else state_.Add(s, value);
        if (state_.Get(s) != before) Emit(SimEventType::StatChanged, name, "", state_.Get(s) - before);
    };

    if (e.Has("add_stat")) { statEffect(e["add_stat"].AsString(), e["value"].AsNumber(), false); return; }
    if (e.Has("set_stat")) { statEffect(e["set_stat"].AsString(), e["value"].AsNumber(), true); return; }
    if (e.Has("set_fact")) { SetFact(e["set_fact"].AsString(), e.Has("value") ? e["value"].AsNumber(1.0) : 1.0); return; }
    if (e.Has("add_fact")) {
        const std::string k = e["add_fact"].AsString();
        SetFact(k, Fact(k) + e["value"].AsNumber(1.0));
        return;
    }
    if (e.Has("rel")) {
        NpcRelationship& r = Relationship(e["rel"].AsString());
        r.affinity = std::min(100.0, std::max(-100.0, r.affinity + e["affinity"].AsNumber()));
        r.trust = std::min(100.0, std::max(0.0, r.trust + e["trust"].AsNumber()));
        return;
    }
    if (e.Has("meet")) {
        NpcRelationship& r = Relationship(e["meet"].AsString());
        r.met = true;
        r.lastSeenMinute = clock_.TotalMinutes();
        return;
    }
    if (e.Has("remember")) {
        Relationship(e["remember"].AsString()).memories.insert(e["memory"].AsString());
        return;
    }
    if (e.Has("forget")) {
        Relationship(e["forget"].AsString()).memories.erase(e["memory"].AsString());
        return;
    }
    if (e.Has("commit")) {
        const JsonValue& cj = e["commit"];
        Commitment c;
        c.id = cj["id"].AsString();
        c.npcId = cj["npc"].AsString();
        c.text = cj["text"].AsString();
        c.dueMinute = clock_.TotalMinutes() + cj["due_hours"].AsNumber(24.0) * 60.0;
        c.onBroken = cj["on_broken"];
        c.onFulfilled = cj["on_fulfilled"];
        commitments_.push_back(c);
        Emit(SimEventType::CommitmentMade, c.id, c.text, c.dueMinute);
        return;
    }
    if (e.Has("fulfil")) {
        const std::string id = e["fulfil"].AsString();
        for (size_t i = 0; i < commitments_.size(); ++i) {
            if (commitments_[i].id != id || commitments_[i].status != Commitment::Status::Pending) continue;
            commitments_[i].status = Commitment::Status::Fulfilled;
            const Commitment c = commitments_[i];
            NpcRelationship& rel = Relationship(c.npcId);
            rel.memories.insert("kept:" + c.id);
            rel.trust = std::min(100.0, rel.trust + 6.0);
            Apply(c.onFulfilled);
            Emit(SimEventType::CommitmentFulfilled, c.id, c.text);
            break;
        }
        return;
    }
    if (e.Has("message")) {
        SendPhoneMessage(e["message"]["from"].AsString(), e["message"]["text"].AsString());
        return;
    }
    if (e.Has("notify")) { Emit(SimEventType::Notification, "", e["notify"].AsString()); return; }
    if (e.Has("start_mission")) { StartMission(e["start_mission"].AsString()); return; }
    if (e.Has("fail_mission")) { FailMission(e["fail_mission"].AsString()); return; }
    if (e.Has("discover")) { Discover(e["discover"].AsString()); return; }
    if (e.Has("advance_time")) { AdvanceGameMinutes(e["advance_time"].AsNumber()); return; }
    if (e.Has("pay_rent")) { PayRent(); return; }
    if (e.Has("to_company")) { TransferToCompany(e["to_company"].AsNumber()); return; }
    if (e.Has("company_name")) { state_.companyName = e["company_name"].AsString(); return; }
    if (e.Has("product_name")) { state_.productName = e["product_name"].AsString(); return; }
    if (e.Has("world_event")) { Emit(SimEventType::WorldEvent, e["world_event"].AsString(), e["text"].AsString("")); return; }
    if (e.Has("start_dialogue")) { StartDialogue(e["start_dialogue"].AsString()); return; }
    if (e.Has("add_customer")) {
        // {"add_customer": "name", "mrr": 4900}
        state_.Add(Stat::Customers, 1.0);
        state_.Add(Stat::Mrr, e["mrr"].AsNumber());
        SetFact("customer_" + e["add_customer"].AsString(), 1);
        Emit(SimEventType::StatChanged, "customers", e["add_customer"].AsString(), 1.0);
        return;
    }
    if (e.Has("invoice")) {
        // Settles a customer invoice using the deal facts set during the
        // pricing decision and negotiation (see missions_ch1.json, m03).
        //   amount = price × locations × monthsUpfront × (1 − discount) + setupFee
        // An invoicing service keeps 6 %. Sole-trader income lands in the
        // founder's personal account; an aktiebolag's lands in company cash.
        // (Tax is deliberately not simulated in Chapter 1; see GAME_DESIGN.md.)
        const JsonValue& ij = e["invoice"];
        const std::string customer = ij["customer"].AsString("customer");
        const double locations = ij["locations"].AsNumber(1.0);
        const double price = Fact("price_per_location");
        double amount = price * locations * Fact("deal_months_upfront") * (1.0 - Fact("deal_discount")) +
                        Fact("deal_setup_fee");
        const int form = static_cast<int>(Fact("company_form"));
        if (form == 3) amount *= 0.94;
        state_.Add(form == 2 ? Stat::CompanyCash : Stat::PersonalCash, amount);
        state_.Add(Stat::Customers, 1.0);
        state_.Add(Stat::Mrr, price * locations);
        SetFact("customer_" + customer, 1);
        SetFact("first_payment_amount", amount);
        SetFact("revenue_total", Fact("revenue_total") + amount);
        Emit(SimEventType::Notification, "payment", "Payment received: " + sim_detail::FormatSek(amount), amount);
        Emit(SimEventType::StatChanged, "customers", customer, 1.0);
        return;
    }
    if (e.Has("offer")) {
        FundingOffer o = FundingOffer::Load(e["offer"]);
        o.createdAtMinute = clock_.TotalMinutes();
        state_.openOffers.push_back(o);
        Emit(SimEventType::OfferReceived, o.id, o.investorName, o.amount);
        return;
    }
    if (e.Has("accept_offer")) { AcceptOffer(e["accept_offer"].AsString()); return; }
    if (e.Has("decline_offer")) { DeclineOffer(e["decline_offer"].AsString()); return; }
    if (e.Has("chance")) {
        const bool hit = rng_.NextDouble() < e["chance"].AsNumber(0.5);
        Apply(hit ? e["then"] : e["else"]);
        return;
    }
    if (e.Has("if")) {
        Apply(Evaluate(e["if"]) ? e["then"] : e["else"]);
        return;
    }
}

// ------------------------------------------------------------------ missions

MissionStatus FounderSim::GetMissionStatus(const std::string& missionId) const {
    const auto it = missions_.find(missionId);
    return it == missions_.end() ? MissionStatus::Locked : it->second.status;
}

void FounderSim::RefreshMissionAvailability() {
    if (refreshing_) return;
    refreshing_ = true;
    for (int pass = 0; pass < 4; ++pass) {
        bool changed = false;
        for (const auto& kv : content_.missions) {
            MissionRuntime& rt = missions_[kv.first];
            if (rt.status != MissionStatus::Locked) continue;
            if (!Evaluate(kv.second.prerequisites)) continue;
            rt.status = MissionStatus::Available;
            changed = true;
            Emit(SimEventType::MissionAvailable, kv.first, kv.second.title);
            if (kv.second.autoStart) StartMission(kv.first);
        }
        if (!changed) break;
    }
    refreshing_ = false;
}

bool FounderSim::StartMission(const std::string& missionId) {
    const MissionDef* def = content_.FindMission(missionId);
    if (!def) return false;
    MissionRuntime& rt = missions_[missionId];
    if (rt.status == MissionStatus::Active || rt.status == MissionStatus::Completed) return false;
    if (rt.status == MissionStatus::Locked && !Evaluate(def->prerequisites)) return false;
    rt.status = MissionStatus::Active;
    rt.attempts += 1;
    rt.history.clear();
    rt.missionStartMinute = clock_.TotalMinutes();
    Emit(SimEventType::MissionStarted, missionId, def->title);
    Apply(def->onStart);
    if (missions_[missionId].status == MissionStatus::Active) EnterObjective(missionId, def->startObjective);
    return true;
}

void FounderSim::EnterObjective(const std::string& missionId, const std::string& objectiveId) {
    const MissionDef* def = content_.FindMission(missionId);
    if (!def) return;
    const auto oit = def->objectives.find(objectiveId);
    if (oit == def->objectives.end()) {
        FailMission(missionId);
        return;
    }
    MissionRuntime& rt = missions_[missionId];
    rt.objective = objectiveId;
    rt.objectiveStartMinute = clock_.TotalMinutes();
    rt.history.push_back(objectiveId);
    Emit(SimEventType::ObjectiveChanged, missionId, oit->second.text);
    Apply(oit->second.onStart);
}

std::string FounderSim::ResolveNext(const ObjectiveDef& o) {
    for (const ObjectiveBranch& b : o.nextIf) {
        if (Evaluate(b.conditions)) return b.next;
    }
    return o.next.empty() ? "@complete" : o.next;
}

void FounderSim::GoTo(const std::string& missionId, const std::string& next) {
    if (missions_[missionId].status != MissionStatus::Active) return; // effects may have ended it
    if (next == "@complete") CompleteMission(missionId);
    else if (next == "@fail") FailMission(missionId);
    else EnterObjective(missionId, next);
}

void FounderSim::CompleteObjective(const std::string& missionId) {
    const MissionDef* def = content_.FindMission(missionId);
    if (!def) return;
    const std::string current = missions_[missionId].objective;
    const auto oit = def->objectives.find(current);
    if (oit == def->objectives.end()) return;
    Apply(oit->second.onComplete);
    if (missions_[missionId].objective != current) return; // effects moved the mission on
    GoTo(missionId, ResolveNext(oit->second));
}

void FounderSim::FailObjective(const std::string& missionId) {
    const MissionDef* def = content_.FindMission(missionId);
    if (!def) return;
    const std::string current = missions_[missionId].objective;
    const auto oit = def->objectives.find(current);
    if (oit == def->objectives.end()) return;
    Apply(oit->second.onFail);
    if (missions_[missionId].objective != current) return;
    GoTo(missionId, oit->second.failNext.empty() ? "@fail" : oit->second.failNext);
}

void FounderSim::CompleteMission(const std::string& missionId) {
    const MissionDef* def = content_.FindMission(missionId);
    if (!def) return;
    MissionRuntime& rt = missions_[missionId];
    rt.status = MissionStatus::Completed;
    rt.objective.clear();
    SetFact("mission_done_" + missionId, 1);
    Emit(SimEventType::MissionCompleted, missionId, def->title);
    Apply(def->onComplete);
}

void FounderSim::FailMission(const std::string& missionId) {
    const MissionDef* def = content_.FindMission(missionId);
    if (!def) return;
    MissionRuntime& rt = missions_[missionId];
    if (rt.status != MissionStatus::Active) return;
    rt.status = MissionStatus::Failed;
    rt.objective.clear();
    Emit(SimEventType::MissionFailed, missionId, def->recoveryHint);
    Apply(def->onFail);
}

double FounderSim::DeadlineMinute(const ObjectiveDef& o, const MissionRuntime& rt) {
    if (o.deadlineHour < 0.0) return -1.0;
    const double anchor = o.deadlineFromMissionStart ? rt.missionStartMinute : rt.objectiveStartMinute;
    double deadline = std::floor(anchor / sim_detail::kMinutesPerDay) * sim_detail::kMinutesPerDay + o.deadlineHour * 60.0;
    if (o.deadlineDayOffset >= 0) return deadline + o.deadlineDayOffset * sim_detail::kMinutesPerDay;
    if (deadline < anchor) deadline += sim_detail::kMinutesPerDay;
    return deadline;
}

void FounderSim::CheckMissionTimers() {
    const double now = clock_.TotalMinutes();
    std::vector<std::string> active;
    for (const auto& kv : missions_) {
        if (kv.second.status == MissionStatus::Active) active.push_back(kv.first);
    }
    for (const std::string& id : active) {
        const MissionDef* def = content_.FindMission(id);
        const MissionRuntime& rt = missions_[id];
        if (!def || rt.status != MissionStatus::Active) continue;
        const auto oit = def->objectives.find(rt.objective);
        if (oit == def->objectives.end()) continue;
        const ObjectiveDef& o = oit->second;
        const double elapsed = now - rt.objectiveStartMinute;
        if (o.type == ObjectiveType::WaitUntil && o.deadlineHour >= 0.0) {
            if (now >= DeadlineMinute(o, rt)) CompleteObjective(id);
            continue;
        }
        if (o.timeLimitMinutes > 0.0 && elapsed > o.timeLimitMinutes) {
            FailObjective(id);
            continue;
        }
        if (o.deadlineHour >= 0.0 && now > DeadlineMinute(o, rt)) FailObjective(id);
    }
}

std::vector<ObjectiveView> FounderSim::ActiveObjectives() {
    std::vector<ObjectiveView> out;
    const double now = clock_.TotalMinutes();
    for (const auto& kv : missions_) {
        if (kv.second.status != MissionStatus::Active) continue;
        const MissionDef* def = content_.FindMission(kv.first);
        if (!def) continue;
        const auto oit = def->objectives.find(kv.second.objective);
        if (oit == def->objectives.end()) continue;
        const ObjectiveDef& o = oit->second;
        ObjectiveView v;
        v.valid = true;
        v.missionId = kv.first;
        v.missionTitle = def->title;
        v.objectiveId = o.id;
        v.text = o.text;
        v.type = o.type;
        v.target = o.target;
        v.marker = o.marker;
        if (o.timeLimitMinutes > 0.0) v.minutesRemaining = o.timeLimitMinutes - (now - kv.second.objectiveStartMinute);
        if (o.deadlineHour >= 0.0 && o.type != ObjectiveType::WaitUntil) {
            const double remaining = DeadlineMinute(o, kv.second) - now;
            v.minutesRemaining = v.minutesRemaining < 0.0 ? remaining : std::min(v.minutesRemaining, remaining);
        }
        v.decisionSeconds = o.decisionSeconds;
        v.decisionDefault = o.decisionDefault;
        for (size_t i = 0; i < o.options.size(); ++i) {
            ChoiceView cv;
            cv.index = static_cast<int>(i);
            cv.text = o.options[i].text;
            cv.available = Evaluate(o.options[i].conditions);
            v.options.push_back(cv);
        }
        out.push_back(v);
    }
    return out;
}

bool FounderSim::ChooseDecision(const std::string& missionId, int optionIndex) {
    const MissionDef* def = content_.FindMission(missionId);
    if (!def || GetMissionStatus(missionId) != MissionStatus::Active) return false;
    const std::string current = missions_[missionId].objective;
    const auto oit = def->objectives.find(current);
    if (oit == def->objectives.end() || oit->second.type != ObjectiveType::Decision) return false;
    const ObjectiveDef& o = oit->second;
    if (optionIndex < 0 || optionIndex >= static_cast<int>(o.options.size())) return false;
    const DecisionOption& opt = o.options[static_cast<size_t>(optionIndex)];
    if (!Evaluate(opt.conditions)) return false;
    SetFact(missionId + ":" + o.id, optionIndex + 1);
    Apply(opt.effects);
    if (missions_[missionId].objective != current) return true;
    Apply(o.onComplete);
    if (missions_[missionId].objective != current) return true;
    GoTo(missionId, opt.next.empty() ? ResolveNext(o) : opt.next);
    return true;
}

void FounderSim::NotifyReached(const std::string& locationId, bool inVehicle) {
    std::vector<std::string> toComplete;
    for (const auto& kv : missions_) {
        if (kv.second.status != MissionStatus::Active) continue;
        const MissionDef* def = content_.FindMission(kv.first);
        if (!def) continue;
        const auto oit = def->objectives.find(kv.second.objective);
        if (oit == def->objectives.end() || oit->second.target != locationId) continue;
        const ObjectiveType t = oit->second.type;
        if (t == ObjectiveType::Reach || (t == ObjectiveType::Drive && inVehicle)) toComplete.push_back(kv.first);
    }
    for (const std::string& id : toComplete) CompleteObjective(id);
    SetFact("visited_" + locationId, 1);
}

void FounderSim::NotifyInteracted(const std::string& targetId) {
    std::vector<std::string> toComplete;
    for (const auto& kv : missions_) {
        if (kv.second.status != MissionStatus::Active) continue;
        const MissionDef* def = content_.FindMission(kv.first);
        if (!def) continue;
        const auto oit = def->objectives.find(kv.second.objective);
        if (oit != def->objectives.end() && oit->second.type == ObjectiveType::Interact && oit->second.target == targetId)
            toComplete.push_back(kv.first);
    }
    for (const std::string& id : toComplete) CompleteObjective(id);
}

void FounderSim::NotifyCustomEvent(const std::string& eventId) {
    std::vector<std::string> toComplete;
    for (const auto& kv : missions_) {
        if (kv.second.status != MissionStatus::Active) continue;
        const MissionDef* def = content_.FindMission(kv.first);
        if (!def) continue;
        const auto oit = def->objectives.find(kv.second.objective);
        if (oit != def->objectives.end() && oit->second.type == ObjectiveType::Custom && oit->second.target == eventId)
            toComplete.push_back(kv.first);
    }
    for (const std::string& id : toComplete) CompleteObjective(id);
}

std::string FounderSim::DialogueForNpc(const std::string& npcId) const {
    for (const auto& kv : missions_) {
        if (kv.second.status != MissionStatus::Active) continue;
        const MissionDef* def = content_.FindMission(kv.first);
        if (!def) continue;
        const auto oit = def->objectives.find(kv.second.objective);
        if (oit != def->objectives.end() && oit->second.type == ObjectiveType::Talk && oit->second.target == npcId)
            return oit->second.dialogue;
    }
    const std::string ambient = npcId + "_ambient";
    return content_.dialogues.count(ambient) ? ambient : std::string();
}

std::string FounderSim::PendingPhoneCall() const {
    for (const auto& kv : missions_) {
        if (kv.second.status != MissionStatus::Active) continue;
        const MissionDef* def = content_.FindMission(kv.first);
        if (!def) continue;
        const auto oit = def->objectives.find(kv.second.objective);
        if (oit != def->objectives.end() && oit->second.type == ObjectiveType::PhoneCall) return oit->second.dialogue;
    }
    return std::string();
}

// ------------------------------------------------------------------ dialogue

bool FounderSim::StartDialogue(const std::string& dialogueId) {
    const DialogueDef* d = content_.FindDialogue(dialogueId);
    if (!d || IsDialogueActive()) return false;
    dialogueId_ = dialogueId;
    Emit(SimEventType::DialogueStarted, dialogueId);
    EnterDialogueNode(d->start);
    return true;
}

void FounderSim::EnterDialogueNode(const std::string& nodeId) {
    const DialogueDef* d = content_.FindDialogue(dialogueId_);
    if (!d) { EndDialogue(); return; }
    const auto nit = d->nodes.find(nodeId);
    if (nit == d->nodes.end()) { EndDialogue(); return; }
    dialogueNode_ = nodeId;
    const DialogueNode& n = nit->second;
    if (content_.npcs.count(n.speaker)) {
        NpcRelationship& r = Relationship(n.speaker);
        r.met = true;
        r.lastSeenMinute = clock_.TotalMinutes();
    }
    const std::string before = dialogueId_;
    Apply(n.effects);
    if (dialogueId_ != before || dialogueNode_ != nodeId) return;
    if (!n.branches.empty()) {
        for (const ConditionalNext& b : n.branches) {
            if (Evaluate(b.conditions)) {
                EnterDialogueNode(b.next);
                return;
            }
        }
        EndDialogue(); // no branch matched and no fallback: authoring error, fail safe
    }
}

DialogueLineView FounderSim::CurrentLine() const {
    DialogueLineView v;
    const DialogueDef* d = content_.FindDialogue(dialogueId_);
    if (!d) return v;
    const auto nit = d->nodes.find(dialogueNode_);
    if (nit == d->nodes.end()) return v;
    const DialogueNode& n = nit->second;
    v.active = true;
    v.dialogueId = dialogueId_;
    v.nodeId = n.id;
    v.speaker = n.speaker;
    const NpcDef* npc = content_.FindNpc(n.speaker);
    v.speakerName = npc ? npc->name : (n.speaker == "player" ? "You" : "");
    v.text = n.text;
    v.animation = n.animation;
    v.camera = n.camera;
    v.timeoutSeconds = n.timeoutSeconds;
    v.timeoutChoice = n.timeoutChoice;
    v.hasChoices = !n.choices.empty();
    v.isEnd = n.end || (n.next.empty() && n.choices.empty());
    return v;
}

std::vector<ChoiceView> FounderSim::CurrentChoices() {
    std::vector<ChoiceView> out;
    const DialogueDef* d = content_.FindDialogue(dialogueId_);
    if (!d) return out;
    const auto nit = d->nodes.find(dialogueNode_);
    if (nit == d->nodes.end()) return out;
    for (size_t i = 0; i < nit->second.choices.size(); ++i) {
        const DialogueChoice& c = nit->second.choices[i];
        const bool ok = Evaluate(c.conditions);
        if (!ok && c.hideIfLocked) continue;
        ChoiceView cv;
        cv.index = static_cast<int>(i);
        cv.text = c.text;
        cv.available = ok;
        cv.lockedHint = ok ? "" : c.lockedHint;
        out.push_back(cv);
    }
    return out;
}

bool FounderSim::ChooseDialogueOption(int index) {
    const DialogueDef* d = content_.FindDialogue(dialogueId_);
    if (!d) return false;
    const auto nit = d->nodes.find(dialogueNode_);
    if (nit == d->nodes.end()) return false;
    if (index < 0 || index >= static_cast<int>(nit->second.choices.size())) return false;
    const DialogueChoice c = nit->second.choices[static_cast<size_t>(index)];
    if (!Evaluate(c.conditions)) return false;
    SetFact("said:" + dialogueId_ + ":" + dialogueNode_, index + 1);
    const std::string before = dialogueId_;
    Apply(c.effects);
    if (dialogueId_ != before) return true;
    if (c.next.empty()) EndDialogue();
    else EnterDialogueNode(c.next);
    return true;
}

bool FounderSim::AdvanceDialogue() {
    const DialogueDef* d = content_.FindDialogue(dialogueId_);
    if (!d) return false;
    const auto nit = d->nodes.find(dialogueNode_);
    if (nit == d->nodes.end()) return false;
    if (!nit->second.choices.empty()) return false;
    if (nit->second.next.empty()) EndDialogue();
    else EnterDialogueNode(nit->second.next);
    return true;
}

void FounderSim::EndDialogue() {
    const std::string id = dialogueId_;
    dialogueId_.clear();
    dialogueNode_.clear();
    if (id.empty()) return;
    SetFact("dialogue_done_" + id, 1);
    Emit(SimEventType::DialogueEnded, id);
    OnDialogueFinished(id);
}

void FounderSim::OnDialogueFinished(const std::string& dialogueId) {
    std::vector<std::string> toComplete;
    for (const auto& kv : missions_) {
        if (kv.second.status != MissionStatus::Active) continue;
        const MissionDef* def = content_.FindMission(kv.first);
        if (!def) continue;
        const auto oit = def->objectives.find(kv.second.objective);
        if (oit == def->objectives.end()) continue;
        const ObjectiveType t = oit->second.type;
        if ((t == ObjectiveType::Talk || t == ObjectiveType::PhoneCall) && oit->second.dialogue == dialogueId)
            toComplete.push_back(kv.first);
    }
    for (const std::string& id : toComplete) CompleteObjective(id);
}

// ------------------------------------------------------------------ phone & money

void FounderSim::SendPhoneMessage(const std::string& from, const std::string& text) {
    PhoneMessage m;
    m.thread = from;
    m.sender = from;
    m.text = text;
    m.minute = clock_.TotalMinutes();
    messages_.push_back(m);
    Emit(SimEventType::PhoneMessage, from, text);
}

int FounderSim::UnreadCount() const {
    int n = 0;
    for (const PhoneMessage& m : messages_) n += (!m.read && m.sender != "player") ? 1 : 0;
    return n;
}

void FounderSim::MarkThreadRead(const std::string& thread) {
    for (PhoneMessage& m : messages_) {
        if (m.thread == thread) m.read = true;
    }
}

bool FounderSim::PayRent() {
    const double rent = state_.Get(Stat::RentMonthly);
    if (state_.rentPaidThisMonth || rent <= 0.0) return false;
    if (state_.Get(Stat::PersonalCash) < rent) {
        Emit(SimEventType::Notification, "rent", "Not enough money for rent. " + sim_detail::FormatSek(rent) + " needed.");
        return false;
    }
    state_.Add(Stat::PersonalCash, -rent);
    state_.rentPaidThisMonth = true;
    state_.rentOverdueDays = 0;
    SetFact("rent_overdue_days", 0);
    SetFact("rent_paid_count", Fact("rent_paid_count") + 1);
    Emit(SimEventType::Notification, "rent", "Rent paid: " + sim_detail::FormatSek(rent));
    if (applyDepth_ == 0) {
        RefreshMissionAvailability();
        UpdateChapter();
    }
    return true;
}

bool FounderSim::TransferToCompany(double amount) {
    if (amount <= 0.0 || state_.Get(Stat::PersonalCash) < amount) return false;
    state_.Add(Stat::PersonalCash, -amount);
    state_.Add(Stat::CompanyCash, amount);
    SetFact("founder_loan", Fact("founder_loan") + amount);
    return true;
}

bool FounderSim::AcceptOffer(const std::string& offerId) {
    for (size_t i = 0; i < state_.openOffers.size(); ++i) {
        if (state_.openOffers[i].id != offerId) continue;
        const FundingOffer o = state_.openOffers[i];
        state_.openOffers.erase(state_.openOffers.begin() + static_cast<std::ptrdiff_t>(i));
        switch (o.instrument) {
            case Instrument::Safe:
                state_.capTable.AddSafe({o.investorId, o.investorName, o.amount, o.valuation, o.discount});
                break;
            case Instrument::PricedEquity:
                state_.capTable.PricedRound(o.investorId, o.investorName, o.investorType, o.amount, o.valuation,
                                            o.optionPoolTopUp, o.boardSeat);
                break;
            case Instrument::Grant:
                break;
            case Instrument::Loan:
                // Repaid over 24 months plus interest, modelled as extra burn.
                state_.Add(Stat::MonthlyBurn, o.amount / 24.0 + o.amount * o.loanInterestApr / 12.0);
                break;
        }
        state_.Add(Stat::CompanyCash, o.amount);
        SetFact("offer_accepted_" + o.id, 1);
        SetFact("raised_total", Fact("raised_total") + (o.instrument == Instrument::Loan ? 0.0 : o.amount));
        Relationship(o.investorId).memories.insert("invested");
        Emit(SimEventType::OfferAccepted, o.id, o.investorName, o.amount);
        if (applyDepth_ == 0) {
            RefreshMissionAvailability();
            UpdateChapter();
        }
        return true;
    }
    return false;
}

void FounderSim::DeclineOffer(const std::string& offerId) {
    for (size_t i = 0; i < state_.openOffers.size(); ++i) {
        if (state_.openOffers[i].id != offerId) continue;
        SetFact("offer_declined_" + offerId, 1);
        Relationship(state_.openOffers[i].investorId).memories.insert("declined_offer");
        state_.openOffers.erase(state_.openOffers.begin() + static_cast<std::ptrdiff_t>(i));
        return;
    }
}

bool FounderSim::Discover(const std::string& entryId) {
    if (!content_.FindEcosystem(entryId) && !content_.FindLocation(entryId)) return false;
    if (!discovered_.insert(entryId).second) return false;
    const EcosystemEntry* e = content_.FindEcosystem(entryId);
    Emit(SimEventType::PoiDiscovered, entryId, e ? e->name : entryId);
    return true;
}

// ------------------------------------------------------------------ routines & events

const RoutineEntry* FounderSim::CurrentRoutine(const std::string& npcId) const {
    const NpcDef* npc = content_.FindNpc(npcId);
    if (!npc) return nullptr;
    const double h = clock_.HourOfDay();
    const bool weekend = clock_.IsWeekend();
    for (const RoutineEntry& r : npc->routine) {
        if (r.days == "weekdays" && weekend) continue;
        if (r.days == "weekends" && !weekend) continue;
        const bool inWindow = r.fromHour <= r.toHour ? (h >= r.fromHour && h < r.toHour) : (h >= r.fromHour || h < r.toHour);
        if (inWindow) return &r;
    }
    return nullptr;
}

void FounderSim::Emit(SimEventType type, const std::string& id, const std::string& text, double value) {
    events_.push_back(SimEvent{type, id, text, value});
    // Bounded queue: the world layer drains every frame; headless tests may not.
    while (events_.size() > 512) events_.pop_front();
}

bool FounderSim::PollEvent(SimEvent& out) {
    if (events_.empty()) return false;
    out = events_.front();
    events_.pop_front();
    return true;
}

// ------------------------------------------------------------------ persistence

JsonValue FounderSim::Save() const {
    JsonValue v = JsonValue::MakeObject();
    v.Set("version", kSaveVersion);
    v.Set("clock", clock_.Save());
    v.Set("state", state_.Save());
    v.Set("rng", sim_detail::U64ToHex(rng_.State()));
    v.Set("chapter", chapter_);
    v.Set("last_day", static_cast<double>(lastDayIndex_));

    JsonValue facts = JsonValue::MakeObject();
    for (const auto& kv : facts_) facts.Set(kv.first, kv.second);
    v.Set("facts", facts);

    JsonValue rels = JsonValue::MakeObject();
    for (const auto& kv : relationships_) {
        JsonValue r = JsonValue::MakeObject();
        r.Set("affinity", kv.second.affinity);
        r.Set("trust", kv.second.trust);
        r.Set("met", kv.second.met);
        r.Set("last_seen", kv.second.lastSeenMinute);
        JsonValue mem = JsonValue::MakeArray();
        for (const std::string& m : kv.second.memories) mem.Push(m);
        r.Set("memories", mem);
        rels.Set(kv.first, r);
    }
    v.Set("relationships", rels);

    JsonValue cms = JsonValue::MakeArray();
    for (const Commitment& c : commitments_) {
        JsonValue o = JsonValue::MakeObject();
        o.Set("id", c.id);
        o.Set("npc", c.npcId);
        o.Set("text", c.text);
        o.Set("due", c.dueMinute);
        o.Set("status", c.status == Commitment::Status::Pending ? "pending"
                        : c.status == Commitment::Status::Fulfilled ? "fulfilled" : "broken");
        o.Set("on_broken", c.onBroken);
        o.Set("on_fulfilled", c.onFulfilled);
        cms.Push(o);
    }
    v.Set("commitments", cms);

    JsonValue msgs = JsonValue::MakeArray();
    for (const PhoneMessage& m : messages_) {
        JsonValue o = JsonValue::MakeObject();
        o.Set("thread", m.thread);
        o.Set("sender", m.sender);
        o.Set("text", m.text);
        o.Set("minute", m.minute);
        o.Set("read", m.read);
        msgs.Push(o);
    }
    v.Set("messages", msgs);

    JsonValue ms = JsonValue::MakeObject();
    for (const auto& kv : missions_) {
        JsonValue o = JsonValue::MakeObject();
        o.Set("status", MissionStatusToString(kv.second.status));
        o.Set("objective", kv.second.objective);
        o.Set("objective_start", kv.second.objectiveStartMinute);
        o.Set("mission_start", kv.second.missionStartMinute);
        o.Set("attempts", kv.second.attempts);
        JsonValue hist = JsonValue::MakeArray();
        for (const std::string& h : kv.second.history) hist.Push(h);
        o.Set("history", hist);
        ms.Set(kv.first, o);
    }
    v.Set("missions", ms);

    JsonValue disc = JsonValue::MakeArray();
    for (const std::string& d : discovered_) disc.Push(d);
    v.Set("discovered", disc);
    return v;
}

bool FounderSim::Load(const JsonValue& save, std::string* error) {
    if (!save.IsObject()) {
        if (error) *error = "save is not a JSON object";
        return false;
    }
    const int version = save["version"].AsInt(0);
    if (version < 1 || version > kSaveVersion) {
        if (error) *error = "unsupported save version " + std::to_string(version);
        return false;
    }
    clock_ = WorldClock();
    clock_.Load(save["clock"]);
    state_ = FounderState();
    state_.Load(save["state"]);
    rng_.SetState(sim_detail::HexToU64(save["rng"].AsString("1")));
    chapter_ = save["chapter"].AsInt(1);
    lastDayIndex_ = static_cast<int64_t>(save["last_day"].AsNumber(static_cast<double>(clock_.DayIndex())));

    facts_.clear();
    for (const auto& kv : save["facts"].Items()) facts_[kv.first] = kv.second.AsNumber();

    relationships_.clear();
    for (const auto& kv : save["relationships"].Items()) {
        NpcRelationship r;
        r.affinity = kv.second["affinity"].AsNumber();
        r.trust = kv.second["trust"].AsNumber(20.0);
        r.met = kv.second["met"].AsBool();
        r.lastSeenMinute = kv.second["last_seen"].AsNumber(-1.0);
        for (const JsonValue& m : kv.second["memories"].Elements()) r.memories.insert(m.AsString());
        relationships_[kv.first] = r;
    }

    commitments_.clear();
    for (const JsonValue& o : save["commitments"].Elements()) {
        Commitment c;
        c.id = o["id"].AsString();
        c.npcId = o["npc"].AsString();
        c.text = o["text"].AsString();
        c.dueMinute = o["due"].AsNumber();
        const std::string st = o["status"].AsString("pending");
        c.status = st == "fulfilled" ? Commitment::Status::Fulfilled
                   : st == "broken" ? Commitment::Status::Broken : Commitment::Status::Pending;
        c.onBroken = o["on_broken"];
        c.onFulfilled = o["on_fulfilled"];
        commitments_.push_back(c);
    }

    messages_.clear();
    for (const JsonValue& o : save["messages"].Elements()) {
        PhoneMessage m;
        m.thread = o["thread"].AsString();
        m.sender = o["sender"].AsString();
        m.text = o["text"].AsString();
        m.minute = o["minute"].AsNumber();
        m.read = o["read"].AsBool();
        messages_.push_back(m);
    }

    missions_.clear();
    for (const auto& kv : content_.missions) missions_[kv.first] = MissionRuntime{};
    for (const auto& kv : save["missions"].Items()) {
        if (!content_.missions.count(kv.first)) continue; // mission removed from content: drop safely
        MissionRuntime rt;
        rt.status = MissionStatusFromString(kv.second["status"].AsString("locked"));
        rt.objective = kv.second["objective"].AsString();
        rt.objectiveStartMinute = kv.second["objective_start"].AsNumber();
        rt.missionStartMinute = kv.second["mission_start"].AsNumber();
        rt.attempts = kv.second["attempts"].AsInt();
        for (const JsonValue& h : kv.second["history"].Elements()) rt.history.push_back(h.AsString());
        missions_[kv.first] = rt;
    }

    discovered_.clear();
    for (const JsonValue& d : save["discovered"].Elements()) discovered_.insert(d.AsString());
    events_.clear();
    dialogueId_.clear();
    dialogueNode_.clear();
    return true;
}

} // namespace stockholm::sim
