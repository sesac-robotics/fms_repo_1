// Parses the command text received on /traffic_light_N/cmd into a typed command.
// Pure C++ so the accepted grammar can be tested on a host PC. The grammar and
// ranges match Main Control's SignalCommand, which validates before queueing.
#pragma once

#include <stdint.h>

#include "signal_plan.h"
#include "signal_timing.h"

enum class CommandType : uint8_t { AUTO, HOLD, PLAN };

/// A validated command. Only the field matching `type` is meaningful.
struct Command {
  CommandType type;
  Phase holdTarget;  // HOLD: NORTH_GREEN, EAST_GREEN or ALL_RED
  Timing timing;     // PLAN: durations already inside the safe ranges
};

/// Parse one of:
///   "AUTO"
///   "HOLD NORTH_GREEN" | "HOLD EAST_GREEN" | "HOLD ALL_RED"
///   "PLAN <northGreenMs> <eastGreenMs> <yellowMs> <allRedMs>"
///   "PLAN <northGreenMs> <eastGreenMs> <yellowMs> <allRedMs> <eastYellowMs> <partnerEastMs>"
/// The short form uses <yellowMs> after both greens and no partner time.
/// Words are separated by exactly one space and nothing may follow.
/// Returns false, leaving `out` unspecified, for unknown or unsafe text.
bool parseCommand(const char *text, Command &out);
