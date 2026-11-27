#include "signal_command.h"

#include <string.h>

namespace {

// Read 1 to 6 decimal digits. sscanf is avoided because it accepts signs,
// leading spaces and overflow, which the server's grammar rejects.
bool readMs(const char *&p, uint32_t &out) {
  uint32_t value = 0;
  int digits = 0;
  while (*p >= '0' && *p <= '9') {
    if (++digits > 6) return false;
    value = value * 10 + static_cast<uint32_t>(*p - '0');
    ++p;
  }
  out = value;
  return digits > 0;
}

// Four numbers, or six with the east yellow and the partner's east time.
bool parsePlan(const char *p, Timing &out) {
  uint32_t *fields[] = {&out.northGreenMs, &out.eastGreenMs,  &out.yellowMs,
                        &out.allRedMs,     &out.eastYellowMs, &out.partnerEastMs};
  int count = 0;
  for (; count < 6 && *p != '\0'; ++count) {
    if (count > 0 && *p++ != ' ') return false;
    if (!readMs(p, *fields[count])) return false;
  }
  if (count == 4) {
    out.eastYellowMs = out.yellowMs;
    out.partnerEastMs = 0;
  }
  return (count == 4 || count == 6) && *p == '\0' && timingValid(out);
}

}  // namespace

bool parseCommand(const char *text, Command &out) {
  if (text == nullptr) return false;
  if (strcmp(text, "AUTO") == 0) {
    out.type = CommandType::AUTO;
    return true;
  }
  struct Hold {
    const char *text;
    Phase target;
  };
  static const Hold holds[] = {{"HOLD NORTH_GREEN", Phase::NORTH_GREEN},
                               {"HOLD EAST_GREEN", Phase::EAST_GREEN},
                               {"HOLD ALL_RED", Phase::ALL_RED}};
  for (const Hold &hold : holds) {
    if (strcmp(text, hold.text) == 0) {
      out.type = CommandType::HOLD;
      out.holdTarget = hold.target;
      return true;
    }
  }
  if (strncmp(text, "PLAN ", 5) == 0 && parsePlan(text + 5, out.timing)) {
    out.type = CommandType::PLAN;
    return true;
  }
  return false;
}
