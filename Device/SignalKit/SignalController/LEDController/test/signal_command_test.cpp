// Host tests for the command grammar shared with Main Control.
#include "../signal_command.h"
#include "check.h"

namespace {

bool accepts(const char *text) {
  Command command{};
  return parseCommand(text, command);
}

void parsesAutoAndHolds() {
  Command c{};
  CHECK(parseCommand("AUTO", c) && c.type == CommandType::AUTO);
  CHECK(parseCommand("HOLD NORTH_GREEN", c) && c.type == CommandType::HOLD &&
        c.holdTarget == Phase::NORTH_GREEN);
  CHECK(parseCommand("HOLD EAST_GREEN", c) && c.holdTarget == Phase::EAST_GREEN);
  CHECK(parseCommand("HOLD ALL_RED", c) && c.holdTarget == Phase::ALL_RED);
}

void parsesPlansAtTheRangeBounds() {
  Command c{};
  CHECK(parseCommand("PLAN 15000 8000 3000 2000", c) && c.type == CommandType::PLAN);
  CHECK(c.timing.northGreenMs == 15000 && c.timing.eastGreenMs == 8000);
  CHECK(c.timing.yellowMs == 3000 && c.timing.allRedMs == 2000);
  CHECK(accepts("PLAN 3000 120000 2000 1000"));
  CHECK(accepts("PLAN 120000 3000 10000 10000"));
}

void rejectsUnsafeOrMalformedText() {
  CHECK(!accepts(nullptr));
  CHECK(!accepts(""));
  CHECK(!accepts("auto"));
  CHECK(!accepts("AUTO "));
  CHECK(!accepts("HOLD NORTH_YELLOW"));
  CHECK(!accepts("PLAN 2999 8000 3000 2000"));
  CHECK(!accepts("PLAN 15000 120001 3000 2000"));
  CHECK(!accepts("PLAN 15000 8000 1999 2000"));
  CHECK(!accepts("PLAN 15000 8000 3000 999"));
  CHECK(!accepts("PLAN 15000 8000 3000"));
  CHECK(!accepts("PLAN 15000 8000 3000 2000 1"));
  CHECK(!accepts("PLAN 15000 8000 3000 2000x"));
  CHECK(!accepts("PLAN -1 8000 3000 2000"));
  CHECK(!accepts("PLAN 15000  8000 3000 2000"));
  CHECK(!accepts("PLAN 0015000 8000 3000 2000"));  // more than six digits
}

}  // namespace

void runSignalCommandTests() {
  parsesAutoAndHolds();
  parsesPlansAtTheRangeBounds();
  rejectsUnsafeOrMalformedText();
}
