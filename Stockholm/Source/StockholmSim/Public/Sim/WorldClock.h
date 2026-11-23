// STOCKHOLM — game clock, real solar position for Stockholm, seasonal weather.
#pragma once

#include "Sim/Json.h"

#include <cstdint>
#include <string>

namespace stockholm::sim {

// Small deterministic PRNG (xorshift64*), serialisable.
class Rng {
public:
    explicit Rng(uint64_t seed = 0x5EED5EEDULL) : state_(seed ? seed : 0x9E3779B97F4A7C15ULL) {}
    uint64_t NextU64();
    double NextDouble(); // [0,1)
    uint64_t State() const { return state_; }
    void SetState(uint64_t s) { state_ = s ? s : 0x9E3779B97F4A7C15ULL; }
private:
    uint64_t state_;
};

struct CivilDate {
    int year = 2026;
    int month = 1; // 1-12
    int day = 1;   // 1-31
};

int64_t DaysFromCivil(int y, int m, int d);
CivilDate CivilFromDays(int64_t days);
int DayOfWeek(int64_t days); // 0 = Monday … 6 = Sunday

enum class Season : uint8_t { Winter, Spring, Summer, Autumn };
const char* SeasonToString(Season s);

enum class WeatherKind : uint8_t { Clear, PartlyCloudy, Overcast, Fog, Drizzle, Rain, LightSnow, HeavySnow };
const char* WeatherToString(WeatherKind w);
WeatherKind WeatherFromString(const std::string& s);

struct SunPosition {
    double elevationDeg = 0.0; // above horizon
    double azimuthDeg = 0.0;   // clockwise from north
};

// Solar position (NOAA general solar position equations) for a latitude/
// longitude, local civil date/time, and UTC offset in hours.
SunPosition ComputeSunPosition(double latDeg, double lonDeg, const CivilDate& date, double localHour, double utcOffsetHours);

// Central European (Summer) Time offset for Sweden on a date.
double SwedenUtcOffset(const CivilDate& date, double localHour);

struct WeatherState {
    WeatherKind kind = WeatherKind::LightSnow;
    double temperatureC = -2.0;
    double cloudCover = 0.8;    // 0..1
    double precipitation = 0.3; // 0..1 intensity
    bool precipIsSnow = true;
    double fogDensity = 0.1;    // 0..1
    double wetness = 0.2;       // road wetness 0..1 (drives puddles/reflections)
    double snowCover = 0.4;     // ground snow 0..1
    double windMps = 4.0;
};

class WorldClock {
public:
    // Story start: a dark Monday in January.
    WorldClock();

    // Advances by game minutes; returns number of whole hours crossed.
    int AdvanceMinutes(double minutes);

    double TotalMinutes() const { return totalMinutes_; }
    int64_t DayIndex() const;          // days since start date
    int64_t AbsoluteDays() const;      // days since 1970-01-01
    CivilDate Date() const;
    double HourOfDay() const;          // 0..24 local time
    int Minute() const;
    int Weekday() const { return DayOfWeek(AbsoluteDays()); }
    bool IsWeekend() const { return Weekday() >= 5; }
    Season CurrentSeason() const;
    std::string FormatTime() const;    // "07:45"
    std::string FormatDate() const;    // "Mon 12 Jan 2026"

    SunPosition Sun() const;
    bool IsNight() const { return Sun().elevationDeg < -6.0; }

    // Real seconds → game minutes. GTA-style compression: 1 game day = 48 real minutes.
    double timeScale = 30.0; // game seconds per real second

    const WeatherState& Weather() const { return weather_; }
    void ForceWeather(WeatherKind kind);
    void StepWeatherHour(Rng& rng);

    JsonValue Save() const;
    void Load(const JsonValue& v);

    static constexpr double kLatitude = 59.3293;
    static constexpr double kLongitude = 18.0686;

private:
    void ApplyKind(WeatherKind kind, double hourBlend);
    double BaseTemperature() const;

    int64_t startDays_;
    double totalMinutes_ = 0.0;
    WeatherState weather_;
};

} // namespace stockholm::sim
