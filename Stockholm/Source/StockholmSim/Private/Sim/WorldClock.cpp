#include "Sim/WorldClock.h"

#include <algorithm>
#include <cmath>
#include <cstdio>

namespace stockholm::sim {

namespace clock_detail {
constexpr double kPi = 3.14159265358979323846;
inline double Rad(double d) { return d * kPi / 180.0; }
inline double Deg(double r) { return r * 180.0 / kPi; }
inline double Clamp01(double v) { return std::min(1.0, std::max(0.0, v)); }

// Approximate Stockholm monthly mean temperatures (°C), SMHI 1991–2020 normals,
// rounded. Used only to drive atmosphere; not presented as data to players.
const double kMonthlyMeanC[12] = {-1.0, -1.0, 1.5, 6.5, 11.5, 15.5, 18.5, 17.5, 13.0, 7.5, 3.5, 0.5};

const char* kWeatherNames[] = {"clear", "partly_cloudy", "overcast", "fog", "drizzle", "rain", "light_snow", "heavy_snow"};
constexpr int kWeatherCount = 8;

// Hourly persistence and transition weights per season. Rows: from-state,
// columns: to-state. Weights are relative; precipitation kind (rain vs snow)
// is resolved by temperature afterwards.
const double kTransitions[4][kWeatherCount][kWeatherCount] = {
    // Winter: long overcast spells, frequent snow.
    {{70, 15, 8, 4, 0, 0, 3, 0}, {8, 64, 18, 3, 1, 0, 6, 0}, {2, 8, 66, 5, 3, 2, 12, 2},
     {6, 6, 20, 64, 1, 0, 3, 0}, {0, 2, 20, 4, 60, 8, 6, 0}, {0, 0, 18, 2, 12, 62, 6, 0},
     {1, 3, 16, 2, 1, 1, 66, 10}, {0, 0, 10, 1, 0, 0, 30, 59}},
    // Spring
    {{74, 16, 6, 2, 1, 0, 1, 0}, {10, 66, 16, 2, 3, 1, 2, 0}, {3, 12, 64, 4, 8, 6, 3, 0},
     {10, 10, 16, 62, 2, 0, 0, 0}, {2, 6, 22, 2, 58, 10, 0, 0}, {0, 4, 24, 1, 12, 59, 0, 0},
     {2, 6, 22, 2, 4, 2, 60, 2}, {0, 2, 16, 0, 2, 2, 30, 48}},
    // Summer: long bright days, convective showers.
    {{78, 16, 4, 1, 0, 1, 0, 0}, {12, 66, 14, 1, 3, 4, 0, 0}, {4, 16, 60, 2, 8, 10, 0, 0},
     {14, 12, 12, 62, 0, 0, 0, 0}, {2, 10, 22, 0, 56, 10, 0, 0}, {2, 10, 22, 0, 10, 56, 0, 0},
     {10, 20, 30, 0, 20, 20, 0, 0}, {10, 20, 30, 0, 20, 20, 0, 0}},
    // Autumn: grey, wet, foggy mornings.
    {{66, 18, 10, 4, 1, 1, 0, 0}, {6, 60, 22, 4, 4, 3, 1, 0}, {2, 8, 64, 6, 9, 9, 2, 0},
     {4, 6, 22, 64, 3, 1, 0, 0}, {0, 4, 22, 4, 58, 12, 0, 0}, {0, 2, 20, 2, 14, 62, 0, 0},
     {2, 4, 24, 2, 4, 4, 56, 4}, {0, 2, 16, 0, 2, 2, 34, 44}},
};
} // namespace clock_detail

uint64_t Rng::NextU64() {
    uint64_t x = state_;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    state_ = x;
    return x * 0x2545F4914F6CDD1DULL;
}

double Rng::NextDouble() {
    return static_cast<double>(NextU64() >> 11) * (1.0 / 9007199254740992.0);
}

// Howard Hinnant's public-domain civil calendar algorithms.
int64_t DaysFromCivil(int y, int m, int d) {
    y -= m <= 2 ? 1 : 0;
    const int64_t era = (y >= 0 ? y : y - 399) / 400;
    const unsigned yoe = static_cast<unsigned>(y - era * 400);
    const unsigned doy = static_cast<unsigned>((153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1);
    const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097 + static_cast<int64_t>(doe) - 719468;
}

CivilDate CivilFromDays(int64_t z) {
    z += 719468;
    const int64_t era = (z >= 0 ? z : z - 146096) / 146097;
    const unsigned doe = static_cast<unsigned>(z - era * 146097);
    const unsigned yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    const int64_t y = static_cast<int64_t>(yoe) + era * 400;
    const unsigned doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    const unsigned mp = (5 * doy + 2) / 153;
    const unsigned d = doy - (153 * mp + 2) / 5 + 1;
    const unsigned m = mp < 10 ? mp + 3 : mp - 9;
    CivilDate out;
    out.year = static_cast<int>(y + (m <= 2 ? 1 : 0));
    out.month = static_cast<int>(m);
    out.day = static_cast<int>(d);
    return out;
}

int DayOfWeek(int64_t days) {
    // 1970-01-01 was a Thursday (index 3 with Monday = 0).
    const int64_t w = (days + 3) % 7;
    return static_cast<int>(w < 0 ? w + 7 : w);
}

const char* SeasonToString(Season s) {
    switch (s) {
        case Season::Winter: return "winter";
        case Season::Spring: return "spring";
        case Season::Summer: return "summer";
        case Season::Autumn: return "autumn";
    }
    return "winter";
}

const char* WeatherToString(WeatherKind w) {
    return clock_detail::kWeatherNames[static_cast<int>(w)];
}

WeatherKind WeatherFromString(const std::string& s) {
    for (int i = 0; i < clock_detail::kWeatherCount; ++i) {
        if (s == clock_detail::kWeatherNames[i]) return static_cast<WeatherKind>(i);
    }
    return WeatherKind::Overcast;
}

double SwedenUtcOffset(const CivilDate& date, double localHour) {
    // EU rule: CEST from last Sunday of March 02:00 to last Sunday of October 03:00.
    auto lastSunday = [](int year, int month) {
        const int64_t lastDay = DaysFromCivil(year, month + 1, 1) - 1;
        return lastDay - (DayOfWeek(lastDay) + 1) % 7; // Monday = 0 … Sunday = 6
    };
    const int64_t today = DaysFromCivil(date.year, date.month, date.day);
    const int64_t start = lastSunday(date.year, 3);
    const int64_t end = lastSunday(date.year, 10);
    bool summer = today > start && today < end;
    if (today == start) summer = localHour >= 2.0;
    if (today == end) summer = localHour < 3.0;
    return summer ? 2.0 : 1.0;
}

SunPosition ComputeSunPosition(double latDeg, double lonDeg, const CivilDate& date, double localHour, double utcOffsetHours) {
    using namespace clock_detail;
    const int64_t days = DaysFromCivil(date.year, date.month, date.day);
    const int doy = static_cast<int>(days - DaysFromCivil(date.year, 1, 1)) + 1;
    const bool leap = (date.year % 4 == 0 && date.year % 100 != 0) || date.year % 400 == 0;
    const double yearDays = leap ? 366.0 : 365.0;
    const double utcHour = localHour - utcOffsetHours;
    const double g = 2.0 * kPi / yearDays * (doy - 1 + (utcHour - 12.0) / 24.0);

    const double eqTime = 229.18 * (0.000075 + 0.001868 * std::cos(g) - 0.032077 * std::sin(g) -
                                    0.014615 * std::cos(2 * g) - 0.040849 * std::sin(2 * g));
    const double decl = 0.006918 - 0.399912 * std::cos(g) + 0.070257 * std::sin(g) - 0.006758 * std::cos(2 * g) +
                        0.000907 * std::sin(2 * g) - 0.002697 * std::cos(3 * g) + 0.00148 * std::sin(3 * g);

    const double timeOffset = eqTime + 4.0 * lonDeg; // minutes, relative to UTC
    const double tst = utcHour * 60.0 + timeOffset;   // true solar time, minutes
    const double ha = Rad(tst / 4.0 - 180.0);
    const double phi = Rad(latDeg);

    double cosZen = std::sin(phi) * std::sin(decl) + std::cos(phi) * std::cos(decl) * std::cos(ha);
    cosZen = std::min(1.0, std::max(-1.0, cosZen));
    const double zen = std::acos(cosZen);

    SunPosition sp;
    sp.elevationDeg = 90.0 - Deg(zen);
    const double sinZen = std::sin(zen);
    if (sinZen > 1e-9) {
        double cosAz = (std::sin(decl) - std::sin(phi) * cosZen) / (std::cos(phi) * sinZen);
        cosAz = std::min(1.0, std::max(-1.0, cosAz));
        double az = Deg(std::acos(cosAz)); // from north, 0..180
        if (std::sin(ha) > 0) az = 360.0 - az; // afternoon: west of south
        sp.azimuthDeg = az;
    }
    return sp;
}

WorldClock::WorldClock() : startDays_(DaysFromCivil(2026, 1, 12)) {
    totalMinutes_ = 7.0 * 60.0 + 10.0; // 07:10 — still dark in a Stockholm January
}

int WorldClock::AdvanceMinutes(double minutes) {
    if (minutes <= 0.0) return 0;
    const int64_t hoursBefore = static_cast<int64_t>(std::floor(totalMinutes_ / 60.0));
    totalMinutes_ += minutes;
    const int64_t hoursAfter = static_cast<int64_t>(std::floor(totalMinutes_ / 60.0));
    return static_cast<int>(hoursAfter - hoursBefore);
}

int64_t WorldClock::DayIndex() const {
    return static_cast<int64_t>(std::floor(totalMinutes_ / 1440.0));
}

int64_t WorldClock::AbsoluteDays() const { return startDays_ + DayIndex(); }

CivilDate WorldClock::Date() const { return CivilFromDays(AbsoluteDays()); }

double WorldClock::HourOfDay() const {
    const double m = std::fmod(totalMinutes_, 1440.0);
    return m / 60.0;
}

int WorldClock::Minute() const {
    return static_cast<int>(std::fmod(totalMinutes_, 60.0));
}

Season WorldClock::CurrentSeason() const {
    const int m = Date().month;
    if (m == 12 || m <= 2) return Season::Winter;
    if (m <= 5) return Season::Spring;
    if (m <= 8) return Season::Summer;
    return Season::Autumn;
}

std::string WorldClock::FormatTime() const {
    char buf[8];
    const int h = static_cast<int>(HourOfDay());
    std::snprintf(buf, sizeof(buf), "%02d:%02d", h, Minute());
    return buf;
}

std::string WorldClock::FormatDate() const {
    static const char* kDays[] = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"};
    static const char* kMonths[] = {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"};
    const CivilDate d = Date();
    char buf[32];
    std::snprintf(buf, sizeof(buf), "%s %d %s %d", kDays[Weekday()], d.day, kMonths[d.month - 1], d.year);
    return buf;
}

SunPosition WorldClock::Sun() const {
    const CivilDate d = Date();
    const double h = HourOfDay();
    return ComputeSunPosition(kLatitude, kLongitude, d, h, SwedenUtcOffset(d, h));
}

double WorldClock::BaseTemperature() const {
    const CivilDate d = Date();
    // Interpolate monthly means mid-month to mid-month.
    const double monthPos = (d.month - 1) + (d.day - 15.0) / 30.0;
    const int m0 = (static_cast<int>(std::floor(monthPos)) % 12 + 12) % 12;
    const int m1 = (m0 + 1) % 12;
    const double t = monthPos - std::floor(monthPos);
    const double mean = clock_detail::kMonthlyMeanC[m0] * (1 - t) + clock_detail::kMonthlyMeanC[m1] * t;
    // Diurnal swing peaking ~15:00.
    const double diurnal = 3.0 * std::cos((HourOfDay() - 15.0) / 24.0 * 2.0 * clock_detail::kPi);
    return mean + diurnal;
}

void WorldClock::ApplyKind(WeatherKind kind, double blend) {
    struct Target { double cloud, precip, fog, wind; };
    static const Target kTargets[] = {
        {0.05, 0.0, 0.02, 3.0}, {0.4, 0.0, 0.04, 4.0}, {0.95, 0.0, 0.08, 5.0}, {0.8, 0.0, 0.7, 1.5},
        {0.95, 0.2, 0.15, 4.0}, {1.0, 0.65, 0.12, 7.0}, {0.9, 0.3, 0.12, 4.0}, {1.0, 0.85, 0.3, 9.0},
    };
    const Target& t = kTargets[static_cast<int>(kind)];
    weather_.kind = kind;
    weather_.cloudCover += (t.cloud - weather_.cloudCover) * blend;
    weather_.precipitation += (t.precip - weather_.precipitation) * blend;
    weather_.fogDensity += (t.fog - weather_.fogDensity) * blend;
    weather_.windMps += (t.wind - weather_.windMps) * blend;
}

void WorldClock::ForceWeather(WeatherKind kind) {
    ApplyKind(kind, 1.0);
    weather_.precipIsSnow = (kind == WeatherKind::LightSnow || kind == WeatherKind::HeavySnow);
}

void WorldClock::StepWeatherHour(Rng& rng) {
    using namespace clock_detail;
    const int season = static_cast<int>(CurrentSeason());
    const int from = static_cast<int>(weather_.kind);
    double total = 0.0;
    for (int i = 0; i < kWeatherCount; ++i) total += kTransitions[season][from][i];
    double r = rng.NextDouble() * total;
    int to = from;
    for (int i = 0; i < kWeatherCount; ++i) {
        r -= kTransitions[season][from][i];
        if (r <= 0.0) { to = i; break; }
    }

    // Temperature with cloud damping of the diurnal swing and a weather offset.
    const double base = BaseTemperature();
    weather_.temperatureC = base - weather_.cloudCover * 1.0 + (rng.NextDouble() - 0.5) * 1.0;

    // Resolve precipitation phase by temperature.
    WeatherKind kind = static_cast<WeatherKind>(to);
    const bool cold = weather_.temperatureC <= 0.5;
    if (cold && kind == WeatherKind::Rain) kind = WeatherKind::HeavySnow;
    if (cold && kind == WeatherKind::Drizzle) kind = WeatherKind::LightSnow;
    if (!cold && weather_.temperatureC > 3.0 && kind == WeatherKind::LightSnow) kind = WeatherKind::Drizzle;
    if (!cold && weather_.temperatureC > 3.0 && kind == WeatherKind::HeavySnow) kind = WeatherKind::Rain;
    ApplyKind(kind, 0.6);
    weather_.precipIsSnow = (kind == WeatherKind::LightSnow || kind == WeatherKind::HeavySnow);

    // Surface state.
    if (weather_.precipitation > 0.05) {
        if (weather_.precipIsSnow) weather_.snowCover = Clamp01(weather_.snowCover + 0.08 * weather_.precipitation);
        else weather_.wetness = Clamp01(weather_.wetness + 0.3 * weather_.precipitation);
    } else {
        weather_.wetness = Clamp01(weather_.wetness - (weather_.temperatureC > 5 ? 0.08 : 0.03));
    }
    if (weather_.temperatureC > 1.0) {
        const double melt = 0.01 * (weather_.temperatureC - 1.0);
        weather_.snowCover = Clamp01(weather_.snowCover - melt);
        weather_.wetness = Clamp01(weather_.wetness + melt * 0.5);
    }
}

JsonValue WorldClock::Save() const {
    JsonValue v = JsonValue::MakeObject();
    v.Set("start_days", static_cast<double>(startDays_));
    v.Set("total_minutes", totalMinutes_);
    v.Set("time_scale", timeScale);
    JsonValue w = JsonValue::MakeObject();
    w.Set("kind", WeatherToString(weather_.kind));
    w.Set("temperature", weather_.temperatureC);
    w.Set("cloud", weather_.cloudCover);
    w.Set("precip", weather_.precipitation);
    w.Set("snow_precip", weather_.precipIsSnow);
    w.Set("fog", weather_.fogDensity);
    w.Set("wetness", weather_.wetness);
    w.Set("snow_cover", weather_.snowCover);
    w.Set("wind", weather_.windMps);
    v.Set("weather", w);
    return v;
}

void WorldClock::Load(const JsonValue& v) {
    startDays_ = static_cast<int64_t>(v["start_days"].AsNumber(static_cast<double>(startDays_)));
    totalMinutes_ = v["total_minutes"].AsNumber(totalMinutes_);
    timeScale = v["time_scale"].AsNumber(timeScale);
    const JsonValue& w = v["weather"];
    weather_.kind = WeatherFromString(w["kind"].AsString("overcast"));
    weather_.temperatureC = w["temperature"].AsNumber(weather_.temperatureC);
    weather_.cloudCover = w["cloud"].AsNumber(weather_.cloudCover);
    weather_.precipitation = w["precip"].AsNumber(weather_.precipitation);
    weather_.precipIsSnow = w["snow_precip"].AsBool(weather_.precipIsSnow);
    weather_.fogDensity = w["fog"].AsNumber(weather_.fogDensity);
    weather_.wetness = w["wetness"].AsNumber(weather_.wetness);
    weather_.snowCover = w["snow_cover"].AsNumber(weather_.snowCover);
    weather_.windMps = w["wind"].AsNumber(weather_.windMps);
}

} // namespace stockholm::sim
