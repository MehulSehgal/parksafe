// ParkSafe Safety & Geo Engine (C++)
// -----------------------------------
// A small, dependency-free CLI engine used by the Python backend to do the
// numerically heavy lifting for ParkSafe: safety-score computation and
// haversine nearest-spot ranking. Kept dependency-free (standard library
// only) so it builds anywhere with just g++/clang++ and no package manager.
//
// PROTOCOL (stdin -> stdout), one line per spot, comma separated:
//   SPOT,<id>,<lat>,<lng>,<legalCode 0=Legal 1=Restricted 2=Illegal>,
//        <cctv 0/1>,<lighting 0/1>,<patrolled 0/1>,<theftReports int>,<towZone 0/1>
//   QUERY,<userLat>,<userLng>
//
// The QUERY line ends input. Output is one CSV line per spot, sorted by rank
// (safety score desc, then distance asc):
//   id,safetyScore,theftRisk,distanceKm
//
// Build:   g++ -O2 -std=c++17 -o safety_engine safety_engine.cpp
// Run:     ./safety_engine < spots.csv

#include <iostream>
#include <sstream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <stdexcept>
#include <iomanip>

struct Spot {
    long long id;
    double lat, lng;
    int legalCode;     // 0 Legal, 1 Restricted, 2 Illegal
    bool cctv, lighting, patrolled;
    int theftReports;
    bool towZone;

    int safetyScore = 0;
    std::string theftRisk;
    double distanceKm = 0.0;
};

static std::vector<std::string> splitCsv(const std::string& line) {
    std::vector<std::string> out;
    std::stringstream ss(line);
    std::string field;
    while (std::getline(ss, field, ',')) out.push_back(field);
    return out;
}

// Haversine distance in km between two lat/lng points.
static double haversineKm(double lat1, double lng1, double lat2, double lng2) {
    constexpr double R = 6371.0088; // mean Earth radius in km
    auto toRad = [](double d) { return d * M_PI / 180.0; };
    double dLat = toRad(lat2 - lat1);
    double dLng = toRad(lng2 - lng1);
    double a = std::sin(dLat / 2) * std::sin(dLat / 2) +
               std::cos(toRad(lat1)) * std::cos(toRad(lat2)) *
               std::sin(dLng / 2) * std::sin(dLng / 2);
    double c = 2 * std::atan2(std::sqrt(a), std::sqrt(1 - a));
    return R * c;
}

// Weighted safety score model (0-100). Mirrors the frontend's simplified
// version (index.html: computeSafetyScore) but with finer-grained inputs
// so community reports carry more nuance than the demo UI alone allows.
static int computeSafetyScore(const Spot& s) {
    double score = 50.0;

    switch (s.legalCode) {
        case 0: score += 30; break;  // Legal
        case 1: score += 5;  break;  // Restricted
        case 2: score -= 25; break;  // Illegal
    }

    if (s.cctv) score += 15;
    if (s.lighting) score += 8;
    if (s.patrolled) score += 10;
    if (s.towZone) score -= 20;

    // Each community-reported theft incident chips away at trust,
    // with diminishing severity so one outlier report doesn't tank a spot.
    double theftPenalty = 18.0 * (1.0 - std::exp(-0.35 * s.theftReports));
    score -= theftPenalty;

    if (score > 100) score = 100;
    if (score < 0) score = 0;
    return static_cast<int>(std::round(score));
}

static std::string theftRiskLabel(int score, int theftReports) {
    if (theftReports >= 8 || score < 45) return "High";
    if (theftReports >= 2 || score < 75) return "Medium";
    return "Low";
}

int main() {
    std::vector<Spot> spots;
    double qLat = 0.0, qLng = 0.0;
    bool haveQuery = false;

    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;
        auto f = splitCsv(line);
        if (f.empty()) continue;

        try {
            if (f[0] == "SPOT" && f.size() >= 10) {
                Spot s;
                s.id          = std::stoll(f[1]);
                s.lat         = std::stod(f[2]);
                s.lng         = std::stod(f[3]);
                s.legalCode   = std::stoi(f[4]);
                s.cctv        = std::stoi(f[5]) != 0;
                s.lighting    = std::stoi(f[6]) != 0;
                s.patrolled   = std::stoi(f[7]) != 0;
                s.theftReports= std::stoi(f[8]);
                s.towZone     = std::stoi(f[9]) != 0;
                spots.push_back(s);
            } else if (f[0] == "QUERY" && f.size() >= 3) {
                qLat = std::stod(f[1]);
                qLng = std::stod(f[2]);
                haveQuery = true;
                break; // QUERY line always terminates input
            }
        } catch (const std::exception&) {
            std::cerr << "ENGINE_ERROR,malformed_line," << line << "\n";
            return 1;
        }
    }

    for (auto& s : spots) {
        s.safetyScore = computeSafetyScore(s);
        s.theftRisk = theftRiskLabel(s.safetyScore, s.theftReports);
        if (haveQuery) s.distanceKm = haversineKm(qLat, qLng, s.lat, s.lng);
    }

    std::sort(spots.begin(), spots.end(), [](const Spot& a, const Spot& b) {
        if (a.safetyScore != b.safetyScore) return a.safetyScore > b.safetyScore;
        return a.distanceKm < b.distanceKm;
    });

    for (const auto& s : spots) {
        std::cout << s.id << "," << s.safetyScore << "," << s.theftRisk << ","
                   << std::fixed << std::setprecision(3) << s.distanceKm << "\n";
    }
    return 0;
}
