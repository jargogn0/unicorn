// STOCKHOLM — the founder's multi-dimensional progression state:
// personal life, company economics, cap table and funding instruments.
#pragma once

#include "Sim/Json.h"

#include <cstdint>
#include <string>
#include <vector>

namespace stockholm::sim {

// Every stat that narrative data can read (conditions) or change (effects).
// Money is in Swedish kronor (SEK).
enum class Stat : uint8_t {
    PersonalCash,      // founder's own bank account
    CompanyCash,       // company bank account
    MonthlyBurn,       // company spend per month (salaries, tools, office)
    Mrr,               // monthly recurring revenue
    Customers,         // paying customers
    Pipeline,          // qualified leads
    Retention,         // monthly logo retention 0..1
    ProductQuality,    // 0..100 — demo reliability, polish, depth
    Reputation,        // 0..100 — ecosystem standing
    TeamSize,          // people incl. founder
    TeamCapability,    // 0..100
    InternationalReach,// 0..100
    Wellbeing,         // 0..100 — sleep, relationships, stress
    Energy,            // 0..100 — short-term stamina (sleep restores)
    RentMonthly,       // personal housing cost
    LivingCostDaily,   // food, SL travel card, phone
    HousingTier,       // 0 couch, 1 sublet room, 2 own flat, 3 nice flat, 4 penthouse
    OfficeTier,        // 0 kitchen table, 1 café/coworking day pass, 2 desk, 3 office, 4 HQ
    Count
};

const char* StatToString(Stat s);
bool StatFromString(const std::string& name, Stat& out);
double StatMin(Stat s);
double StatMax(Stat s);

enum class HolderType : uint8_t { Founder, CoFounder, Angel, Fund, Accelerator, OptionPool, Employee };
const char* HolderTypeToString(HolderType t);
HolderType HolderTypeFromString(const std::string& s);

struct Shareholder {
    std::string id;
    std::string name;
    HolderType type = HolderType::Founder;
    double shares = 0.0;
};

// Post-money-style SAFE simplified for gameplay; converts at the next priced
// round at the lower of the cap price and the discounted round price.
struct Safe {
    std::string investorId;
    std::string investorName;
    double amount = 0.0;
    double valuationCap = 0.0;
    double discount = 0.0; // e.g. 0.2
};

enum class Instrument : uint8_t { Safe, PricedEquity, Grant, Loan };
const char* InstrumentToString(Instrument i);
Instrument InstrumentFromString(const std::string& s);

struct FundingOffer {
    std::string id;
    std::string investorId;
    std::string investorName;
    HolderType investorType = HolderType::Angel;
    Instrument instrument = Instrument::Safe;
    double amount = 0.0;
    double valuation = 0.0;    // cap for SAFEs, pre-money for priced rounds
    double discount = 0.0;
    double optionPoolTopUp = 0.0; // fraction of post-money reserved for pool (priced only)
    bool boardSeat = false;
    double liquidationPreference = 1.0;
    double loanInterestApr = 0.0;
    int expiresInDays = 14;
    double createdAtMinute = 0.0;
    JsonValue Save() const;
    static FundingOffer Load(const JsonValue& v);
};

struct RoundResult {
    bool ok = false;
    std::string error;
    double pricePerShare = 0.0;
    double newInvestorShares = 0.0;
    double convertedSafeShares = 0.0;
    double poolShares = 0.0;
    double founderOwnershipBefore = 0.0;
    double founderOwnershipAfter = 0.0;
    double postMoney = 0.0;
};

class CapTable {
public:
    CapTable();

    double TotalShares() const;
    double OwnershipOf(const std::string& id) const;
    double FounderOwnership() const { return OwnershipOf("player"); }
    int BoardSeatsFounders() const { return founderBoardSeats; }
    int BoardSeatsInvestors() const { return investorBoardSeats; }
    // 0..1: voting share combined with board control.
    double FounderControl() const;

    void AddSafe(const Safe& s) { safes.push_back(s); }
    // Issues a priced round. Unconverted SAFEs convert first.
    RoundResult PricedRound(const std::string& investorId, const std::string& investorName, HolderType type,
                            double amount, double preMoney, double poolTopUpFraction, bool boardSeat);
    // Projection without mutating (for negotiation UI).
    RoundResult PreviewPricedRound(double amount, double preMoney, double poolTopUpFraction) const;
    double ProjectedSafeOwnership(double amount, double cap) const;

    std::vector<Shareholder> holders;
    std::vector<Safe> safes;
    int founderBoardSeats = 1;
    int investorBoardSeats = 0;
    int independentBoardSeats = 0;
    double liquidationPreferenceStack = 0.0; // sum of preferences owed before common

    JsonValue Save() const;
    void Load(const JsonValue& v);

private:
    Shareholder* Find(const std::string& id);
};

class FounderState {
public:
    FounderState();

    double Get(Stat s) const { return stats_[static_cast<int>(s)]; }
    void Set(Stat s, double v);
    void Add(Stat s, double delta) { Set(s, Get(s) + delta); }

    double NetBurn() const { return Get(Stat::MonthlyBurn) - Get(Stat::Mrr); }
    // Months of runway. Returns a large sentinel (999) when default-alive.
    double RunwayMonths() const;
    bool DefaultAlive() const { return NetBurn() <= 0.0; }

    CapTable capTable;
    std::vector<FundingOffer> openOffers;
    std::vector<std::string> loans; // descriptive; repayment handled via burn
    std::string companyName = "Untitled";
    std::string productName = "MVP";
    int rentDueDayOfMonth = 17;
    bool rentPaidThisMonth = false;
    int rentOverdueDays = 0;

    JsonValue Save() const;
    void Load(const JsonValue& v);

private:
    double stats_[static_cast<int>(Stat::Count)];
};

// Investor negotiation model: deterministic score from leverage, used by the
// "First Check" mission and later funding rounds.
struct NegotiationContext {
    double traction = 0.0;      // MRR in SEK
    double reputation = 0.0;    // 0..100
    double productQuality = 0.0;
    int competingOffers = 0;
    double runwayMonths = 0.0;
    double investorConviction = 0.5; // 0..1, set by mission performance / relationship
};
// Probability (0..1) that the investor accepts a counter-proposal asking for
// `askMultiplier` × their offered valuation.
double CounterAcceptProbability(const NegotiationContext& ctx, double askMultiplier);

} // namespace stockholm::sim
