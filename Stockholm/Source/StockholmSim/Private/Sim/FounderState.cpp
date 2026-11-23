#include "Sim/FounderState.h"

#include <algorithm>
#include <cmath>

namespace stockholm::sim {

namespace founder_detail {
struct StatInfo {
    Stat stat;
    const char* name;
    double minValue;
    double maxValue;
    double initial;
};
// Opening situation: a modest sublet room on Södermalm, savings nearly gone,
// rent (9 400 SEK) due in five days, ~4 200 SEK in the bank.
const StatInfo kStats[] = {
    {Stat::PersonalCash, "personal_cash", -1e12, 1e12, 4200.0},
    {Stat::CompanyCash, "company_cash", -1e12, 1e12, 0.0},
    {Stat::MonthlyBurn, "monthly_burn", 0.0, 1e12, 600.0},
    {Stat::Mrr, "mrr", 0.0, 1e12, 0.0},
    {Stat::Customers, "customers", 0.0, 1e9, 0.0},
    {Stat::Pipeline, "pipeline", 0.0, 1e9, 0.0},
    {Stat::Retention, "retention", 0.0, 1.0, 0.92},
    {Stat::ProductQuality, "product_quality", 0.0, 100.0, 18.0},
    {Stat::Reputation, "reputation", 0.0, 100.0, 5.0},
    {Stat::TeamSize, "team_size", 1.0, 1e6, 1.0},
    {Stat::TeamCapability, "team_capability", 0.0, 100.0, 20.0},
    {Stat::InternationalReach, "international_reach", 0.0, 100.0, 0.0},
    {Stat::Wellbeing, "wellbeing", 0.0, 100.0, 55.0},
    {Stat::Energy, "energy", 0.0, 100.0, 70.0},
    {Stat::RentMonthly, "rent_monthly", 0.0, 1e9, 9400.0},
    {Stat::LivingCostDaily, "living_cost_daily", 0.0, 1e9, 140.0},
    {Stat::HousingTier, "housing_tier", 0.0, 4.0, 1.0},
    {Stat::OfficeTier, "office_tier", 0.0, 4.0, 0.0},
};
static_assert(sizeof(kStats) / sizeof(kStats[0]) == static_cast<size_t>(Stat::Count), "stat table mismatch");

const char* kHolderTypes[] = {"founder", "cofounder", "angel", "fund", "accelerator", "option_pool", "employee"};
const char* kInstruments[] = {"safe", "priced", "grant", "loan"};
constexpr double kInitialFounderShares = 10000000.0;
} // namespace founder_detail

const char* StatToString(Stat s) { return founder_detail::kStats[static_cast<int>(s)].name; }

bool StatFromString(const std::string& name, Stat& out) {
    for (const auto& info : founder_detail::kStats) {
        if (name == info.name) { out = info.stat; return true; }
    }
    return false;
}

double StatMin(Stat s) { return founder_detail::kStats[static_cast<int>(s)].minValue; }
double StatMax(Stat s) { return founder_detail::kStats[static_cast<int>(s)].maxValue; }

const char* HolderTypeToString(HolderType t) { return founder_detail::kHolderTypes[static_cast<int>(t)]; }
HolderType HolderTypeFromString(const std::string& s) {
    for (int i = 0; i < 7; ++i) {
        if (s == founder_detail::kHolderTypes[i]) return static_cast<HolderType>(i);
    }
    return HolderType::Angel;
}

const char* InstrumentToString(Instrument i) { return founder_detail::kInstruments[static_cast<int>(i)]; }
Instrument InstrumentFromString(const std::string& s) {
    for (int i = 0; i < 4; ++i) {
        if (s == founder_detail::kInstruments[i]) return static_cast<Instrument>(i);
    }
    return Instrument::Safe;
}

// ---------------------------------------------------------------- FundingOffer

JsonValue FundingOffer::Save() const {
    JsonValue v = JsonValue::MakeObject();
    v.Set("id", id);
    v.Set("investor_id", investorId);
    v.Set("investor_name", investorName);
    v.Set("investor_type", HolderTypeToString(investorType));
    v.Set("instrument", InstrumentToString(instrument));
    v.Set("amount", amount);
    v.Set("valuation", valuation);
    v.Set("discount", discount);
    v.Set("pool_top_up", optionPoolTopUp);
    v.Set("board_seat", boardSeat);
    v.Set("liq_pref", liquidationPreference);
    v.Set("loan_apr", loanInterestApr);
    v.Set("expires_in_days", expiresInDays);
    v.Set("created_at", createdAtMinute);
    return v;
}

FundingOffer FundingOffer::Load(const JsonValue& v) {
    FundingOffer o;
    o.id = v["id"].AsString("");
    o.investorId = v["investor_id"].AsString("");
    o.investorName = v["investor_name"].AsString("");
    o.investorType = HolderTypeFromString(v["investor_type"].AsString("angel"));
    o.instrument = InstrumentFromString(v["instrument"].AsString("safe"));
    o.amount = v["amount"].AsNumber();
    o.valuation = v["valuation"].AsNumber();
    o.discount = v["discount"].AsNumber();
    o.optionPoolTopUp = v["pool_top_up"].AsNumber();
    o.boardSeat = v["board_seat"].AsBool();
    o.liquidationPreference = v["liq_pref"].AsNumber(1.0);
    o.loanInterestApr = v["loan_apr"].AsNumber();
    o.expiresInDays = v["expires_in_days"].AsInt(14);
    o.createdAtMinute = v["created_at"].AsNumber();
    return o;
}

// ---------------------------------------------------------------- CapTable

CapTable::CapTable() {
    holders.push_back({"player", "You", HolderType::Founder, founder_detail::kInitialFounderShares});
}

double CapTable::TotalShares() const {
    double t = 0.0;
    for (const Shareholder& h : holders) t += h.shares;
    return t;
}

double CapTable::OwnershipOf(const std::string& id) const {
    const double total = TotalShares();
    if (total <= 0.0) return 0.0;
    for (const Shareholder& h : holders) {
        if (h.id == id) return h.shares / total;
    }
    return 0.0;
}

double CapTable::FounderControl() const {
    const int seats = founderBoardSeats + investorBoardSeats + independentBoardSeats;
    const double boardShare = seats > 0 ? static_cast<double>(founderBoardSeats) / seats : 1.0;
    double founderVotes = 0.0;
    for (const Shareholder& h : holders) {
        if (h.type == HolderType::Founder || h.type == HolderType::CoFounder) founderVotes += h.shares;
    }
    const double total = TotalShares();
    const double votingShare = total > 0.0 ? founderVotes / total : 1.0;
    return 0.5 * boardShare + 0.5 * votingShare;
}

Shareholder* CapTable::Find(const std::string& id) {
    for (Shareholder& h : holders) {
        if (h.id == id) return &h;
    }
    return nullptr;
}

RoundResult CapTable::PreviewPricedRound(double amount, double preMoney, double poolTopUpFraction) const {
    RoundResult r;
    if (amount <= 0.0 || preMoney <= 0.0) {
        r.error = "amount and pre-money must be positive";
        return r;
    }
    const double preShares = TotalShares();
    r.founderOwnershipBefore = OwnershipOf("player");
    r.pricePerShare = preMoney / preShares;
    for (const Safe& s : safes) {
        double price = r.pricePerShare * (1.0 - s.discount);
        if (s.valuationCap > 0.0) price = std::min(price, s.valuationCap / preShares);
        r.convertedSafeShares += s.amount / price;
    }
    r.newInvestorShares = amount / r.pricePerShare;
    const double postWithoutPool = preShares + r.convertedSafeShares + r.newInvestorShares;
    if (poolTopUpFraction > 0.0 && poolTopUpFraction < 0.5) {
        // Pool sized as a fraction of the fully-diluted post-money.
        r.poolShares = postWithoutPool * poolTopUpFraction / (1.0 - poolTopUpFraction);
    }
    const double post = postWithoutPool + r.poolShares;
    double founderShares = 0.0;
    for (const Shareholder& h : holders) {
        if (h.id == "player") founderShares = h.shares;
    }
    r.founderOwnershipAfter = founderShares / post;
    r.postMoney = post * r.pricePerShare;
    r.ok = true;
    return r;
}

RoundResult CapTable::PricedRound(const std::string& investorId, const std::string& investorName, HolderType type,
                                  double amount, double preMoney, double poolTopUpFraction, bool boardSeat) {
    RoundResult r = PreviewPricedRound(amount, preMoney, poolTopUpFraction);
    if (!r.ok) return r;
    const double preShares = TotalShares();
    for (const Safe& s : safes) {
        double price = r.pricePerShare * (1.0 - s.discount);
        if (s.valuationCap > 0.0) price = std::min(price, s.valuationCap / preShares);
        const double sh = s.amount / price;
        if (Shareholder* h = Find(s.investorId)) h->shares += sh;
        else holders.push_back({s.investorId, s.investorName, HolderType::Angel, sh});
    }
    safes.clear();
    if (Shareholder* h = Find(investorId)) h->shares += r.newInvestorShares;
    else holders.push_back({investorId, investorName, type, r.newInvestorShares});
    if (r.poolShares > 0.0) {
        if (Shareholder* pool = Find("option_pool")) pool->shares += r.poolShares;
        else holders.push_back({"option_pool", "Employee option pool", HolderType::OptionPool, r.poolShares});
    }
    if (boardSeat) ++investorBoardSeats;
    liquidationPreferenceStack += amount;
    return r;
}

double CapTable::ProjectedSafeOwnership(double amount, double cap) const {
    // Post-money SAFE semantics: ownership ≈ amount / post-money cap.
    if (cap <= 0.0) return 0.0;
    return amount / cap;
}

JsonValue CapTable::Save() const {
    JsonValue v = JsonValue::MakeObject();
    JsonValue hs = JsonValue::MakeArray();
    for (const Shareholder& h : holders) {
        JsonValue o = JsonValue::MakeObject();
        o.Set("id", h.id);
        o.Set("name", h.name);
        o.Set("type", HolderTypeToString(h.type));
        o.Set("shares", h.shares);
        hs.Push(o);
    }
    v.Set("holders", hs);
    JsonValue ss = JsonValue::MakeArray();
    for (const Safe& s : safes) {
        JsonValue o = JsonValue::MakeObject();
        o.Set("investor_id", s.investorId);
        o.Set("investor_name", s.investorName);
        o.Set("amount", s.amount);
        o.Set("cap", s.valuationCap);
        o.Set("discount", s.discount);
        ss.Push(o);
    }
    v.Set("safes", ss);
    v.Set("founder_seats", founderBoardSeats);
    v.Set("investor_seats", investorBoardSeats);
    v.Set("independent_seats", independentBoardSeats);
    v.Set("liq_pref_stack", liquidationPreferenceStack);
    return v;
}

void CapTable::Load(const JsonValue& v) {
    holders.clear();
    for (const JsonValue& o : v["holders"].Elements()) {
        holders.push_back({o["id"].AsString(""), o["name"].AsString(""), HolderTypeFromString(o["type"].AsString("angel")),
                           o["shares"].AsNumber()});
    }
    if (holders.empty()) holders.push_back({"player", "You", HolderType::Founder, founder_detail::kInitialFounderShares});
    safes.clear();
    for (const JsonValue& o : v["safes"].Elements()) {
        safes.push_back({o["investor_id"].AsString(""), o["investor_name"].AsString(""), o["amount"].AsNumber(),
                         o["cap"].AsNumber(), o["discount"].AsNumber()});
    }
    founderBoardSeats = v["founder_seats"].AsInt(1);
    investorBoardSeats = v["investor_seats"].AsInt(0);
    independentBoardSeats = v["independent_seats"].AsInt(0);
    liquidationPreferenceStack = v["liq_pref_stack"].AsNumber();
}

// ---------------------------------------------------------------- FounderState

FounderState::FounderState() {
    for (const auto& info : founder_detail::kStats) stats_[static_cast<int>(info.stat)] = info.initial;
}

void FounderState::Set(Stat s, double v) {
    stats_[static_cast<int>(s)] = std::min(StatMax(s), std::max(StatMin(s), v));
}

double FounderState::RunwayMonths() const {
    const double net = NetBurn();
    if (net <= 0.0) return 999.0;
    return std::max(0.0, Get(Stat::CompanyCash)) / net;
}

JsonValue FounderState::Save() const {
    JsonValue v = JsonValue::MakeObject();
    JsonValue stats = JsonValue::MakeObject();
    for (int i = 0; i < static_cast<int>(Stat::Count); ++i) {
        stats.Set(StatToString(static_cast<Stat>(i)), stats_[i]);
    }
    v.Set("stats", stats);
    v.Set("cap_table", capTable.Save());
    JsonValue offers = JsonValue::MakeArray();
    for (const FundingOffer& o : openOffers) offers.Push(o.Save());
    v.Set("offers", offers);
    v.Set("company_name", companyName);
    v.Set("product_name", productName);
    v.Set("rent_due_day", rentDueDayOfMonth);
    v.Set("rent_paid", rentPaidThisMonth);
    v.Set("rent_overdue_days", rentOverdueDays);
    return v;
}

void FounderState::Load(const JsonValue& v) {
    for (const auto& kv : v["stats"].Items()) {
        Stat s;
        if (StatFromString(kv.first, s)) Set(s, kv.second.AsNumber());
    }
    capTable.Load(v["cap_table"]);
    openOffers.clear();
    for (const JsonValue& o : v["offers"].Elements()) openOffers.push_back(FundingOffer::Load(o));
    companyName = v["company_name"].AsString(companyName);
    productName = v["product_name"].AsString(productName);
    rentDueDayOfMonth = v["rent_due_day"].AsInt(rentDueDayOfMonth);
    rentPaidThisMonth = v["rent_paid"].AsBool(false);
    rentOverdueDays = v["rent_overdue_days"].AsInt(0);
}

double CounterAcceptProbability(const NegotiationContext& ctx, double askMultiplier) {
    if (askMultiplier <= 1.0) return 1.0;
    // Leverage grows with traction (log scale), reputation, product, competition;
    // shrinks when the investor can see you are nearly out of money.
    double leverage = 0.0;
    leverage += std::log10(1.0 + std::max(0.0, ctx.traction) / 10000.0) * 0.35;
    leverage += ctx.reputation / 100.0 * 0.25;
    leverage += ctx.productQuality / 100.0 * 0.15;
    leverage += std::min(3, ctx.competingOffers) * 0.15;
    leverage += (ctx.investorConviction - 0.5) * 0.5;
    if (ctx.runwayMonths < 2.0) leverage -= 0.25;
    else if (ctx.runwayMonths > 9.0) leverage += 0.1;
    const double stretch = askMultiplier - 1.0; // 0.25 means asking 25 % more
    const double p = 0.85 - stretch * 1.6 + leverage;
    return std::min(0.97, std::max(0.03, p));
}

} // namespace stockholm::sim
