// Phase durations and the safe ranges a PLAN command must respect.
// Pure C++ (no Arduino headers) so the rules can be tested on a host PC.
// Main Control's SignalCommand mirrors these ranges; change both together.
#pragma once

#include <stdint.h>

/// Phase durations in milliseconds.
struct Timing {
  uint32_t northGreenMs;
  uint32_t eastGreenMs;
  uint32_t yellowMs;      // after NORTH_GREEN
  uint32_t allRedMs;
  uint32_t eastYellowMs;  // after EAST_GREEN
  // Coordinated junctions only: the other board's east green plus east yellow,
  // so both boards compute one cycle. 0 means "same as this board's".
  uint32_t partnerEastMs;
};

/// Plan used after power-on until a PLAN command replaces it.
constexpr Timing DEFAULT_TIMING{10000, 10000, 3000, 2000, 3000, 0};

constexpr uint32_t TIMING_GREEN_MIN_MS = 3000;
constexpr uint32_t TIMING_GREEN_MAX_MS = 120000;
constexpr uint32_t TIMING_YELLOW_MIN_MS = 2000;
constexpr uint32_t TIMING_YELLOW_MAX_MS = 10000;
constexpr uint32_t TIMING_ALL_RED_MIN_MS = 1000;
constexpr uint32_t TIMING_ALL_RED_MAX_MS = 10000;

constexpr uint32_t TIMING_PARTNER_MIN_MS = TIMING_GREEN_MIN_MS + TIMING_YELLOW_MIN_MS;
constexpr uint32_t TIMING_PARTNER_MAX_MS = TIMING_GREEN_MAX_MS + TIMING_YELLOW_MAX_MS;

/// Return whether every duration lies inside its safe range (bounds inclusive).
constexpr bool timingValid(const Timing &t) {
  return t.northGreenMs >= TIMING_GREEN_MIN_MS && t.northGreenMs <= TIMING_GREEN_MAX_MS &&
         t.eastGreenMs >= TIMING_GREEN_MIN_MS && t.eastGreenMs <= TIMING_GREEN_MAX_MS &&
         t.yellowMs >= TIMING_YELLOW_MIN_MS && t.yellowMs <= TIMING_YELLOW_MAX_MS &&
         t.allRedMs >= TIMING_ALL_RED_MIN_MS && t.allRedMs <= TIMING_ALL_RED_MAX_MS &&
         t.eastYellowMs >= TIMING_YELLOW_MIN_MS && t.eastYellowMs <= TIMING_YELLOW_MAX_MS &&
         (t.partnerEastMs == 0 ||
          (t.partnerEastMs >= TIMING_PARTNER_MIN_MS && t.partnerEastMs <= TIMING_PARTNER_MAX_MS));
}
