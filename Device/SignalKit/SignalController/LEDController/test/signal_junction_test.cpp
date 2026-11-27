// Host tests for coordinated junctions: the shared clock, cycle alignment and
// east slots that keep conflicting east-west greens apart.
#include "../signal_plan.h"
#include "check.h"

namespace {

// Advance in 100 ms steps, as loop() would, and return the time of the first
// phase change (or 0 when none happens within the window).
uint32_t advanceUntilChange(SignalPlan &plan, uint32_t &now, uint32_t windowMs) {
  for (uint32_t step = 0; step < windowMs; step += 100) {
    now += 100;
    if (plan.update(now)) return now;
  }
  return 0;
}

// Two boards of one junction, powered on 7.3 s apart with their own millis()
// origins, must show the same phase at every instant of the shared clock.
void coordinatedBoardsShareEveryPhase() {
  SignalPlan a, b;
  a.setCoordinated(true);
  b.setCoordinated(true);
  const uint32_t aOrigin = 1000, bOrigin = 0xFFFFFFFFu - 4000;  // b wraps millis()
  uint32_t clock = 50000;
  a.begin(clock - 50000 + aOrigin);
  CHECK(a.phase() == Phase::ALL_RED);
  CHECK(a.remainingMs(aOrigin) == 0);  // waiting for the clock
  CHECK(!a.update(aOrigin + 60000));
  clock += 7300;
  b.begin(clock - 50000 + bOrigin);
  a.setClock(50000 - aOrigin, clock - 50000 + aOrigin);
  b.setClock(50000 - bOrigin, clock - 50000 + bOrigin);
  int agreed = 0;
  for (int step = 0; step < 1200; ++step) {  // 120 s in 100 ms steps
    clock += 100;
    a.update(clock - 50000 + aOrigin);
    b.update(clock - 50000 + bOrigin);
    if (a.phase() != b.phase()) {
      CHECK(a.phase() == b.phase());
      return;
    }
    if (a.phase() == Phase::NORTH_GREEN) ++agreed;
  }
  CHECK(agreed > 300);  // several greens ran, all in step
}

// A coordinated board lines NORTH_GREEN up with a cycle boundary of the clock
// by lengthening only the all red before it.
void alignsByLengtheningAllRedOnly() {
  SignalPlan plan;
  plan.setCoordinated(true);
  uint32_t now = 0;
  plan.begin(now);
  plan.setClock(1000, now);  // clock = millis + 1000; cycle is 30 s
  CHECK(advanceUntilChange(plan, now, 40000) == 29000);  // clock 30000
  CHECK(plan.phase() == Phase::NORTH_GREEN);
  CHECK(advanceUntilChange(plan, now, 20000) == 39000);  // green kept 10 s
  CHECK(advanceUntilChange(plan, now, 20000) == 42000);  // yellow kept 3 s
}

// The loop notices a phase end a few ms late; that must not cost a cycle.
// Every NORTH_GREEN starts on its 30 s boundary, within the loop step.
void lateLoopKeepsEveryCycle() {
  SignalPlan plan;
  plan.setCoordinated(true);
  uint32_t now = 0;
  plan.begin(now);
  plan.setClock(0, now);
  uint32_t greens = 0;
  for (uint32_t step = 0; step < 120000 / 7; ++step) {
    now += 7;  // does not divide any phase length
    if (plan.update(now) && plan.phase() == Phase::NORTH_GREEN) {
      CHECK(now % 30000 < 50);
      ++greens;
    }
  }
  CHECK(greens == 3);  // 30, 60 and 90 s: no cycle skipped
}

// Centre crossroads: north-south green together, then eastbound (board 1, slot
// 0) and westbound (board 2, slot 1) each alone, since both turn left.
void eastSlotsNeverOverlap() {
  SignalPlan east, west;
  east.setCoordinated(true, 0, 2);
  west.setCoordinated(true, 1, 2);
  uint32_t now = 0;
  east.begin(now);
  west.begin(now + 3);
  east.setClock(0, now);
  west.setClock(0, now + 3);
  bool sawEast = false, sawWest = false, sawNorth = false;
  for (uint32_t step = 0; step < 200000 / 7; ++step) {
    now += 7;
    east.update(now);
    west.update(now);
    bool eastGo = east.phase() == Phase::EAST_GREEN || east.phase() == Phase::EAST_YELLOW;
    bool westGo = west.phase() == Phase::EAST_GREEN || west.phase() == Phase::EAST_YELLOW;
    CHECK(!(eastGo && westGo));
    // North-south never runs beside either east-west approach.
    bool northGo = east.phase() == Phase::NORTH_GREEN || west.phase() == Phase::NORTH_GREEN ||
                   east.phase() == Phase::NORTH_YELLOW || west.phase() == Phase::NORTH_YELLOW;
    CHECK(!(northGo && (eastGo || westGo)));
    if (now > 46000 && (east.phase() == Phase::NORTH_GREEN) != (west.phase() == Phase::NORTH_GREEN)) {
      // after the first cycle both boards start and end north-south together
      CHECK(now % 45000 < 60 || (now - 10000) % 45000 < 60);
    }
    sawEast |= east.phase() == Phase::EAST_GREEN;
    sawWest |= west.phase() == Phase::EAST_GREEN;
    sawNorth |= east.phase() == Phase::NORTH_GREEN && west.phase() == Phase::NORTH_GREEN;
  }
  CHECK(sawEast && sawWest && sawNorth);
}

// Eastbound and westbound with their own greens and yellows (12 s + 4 s and
// 8 s + 2 s): each board learns the other's time, so the cycle (15 + 18 + 12 =
// 45 s) and the turns still match, and the two east greens never overlap.
void unequalEastSlotsStayApart() {
  SignalPlan east, west;
  east.setCoordinated(true, 0, 2);
  west.setCoordinated(true, 1, 2);
  uint32_t now = 0;
  east.begin(now);
  west.begin(now);
  CHECK(east.setTiming({10000, 12000, 3000, 2000, 4000, 10000}));
  CHECK(west.setTiming({10000, 8000, 3000, 2000, 2000, 16000}));
  east.setClock(0, now);
  west.setClock(0, now);
  uint32_t eastStarts = 0, westStarts = 0, northStarts = 0;
  for (uint32_t step = 0; step < 600000 / 7; ++step) {  // ten minutes
    now += 7;
    bool eastChanged = east.update(now);
    bool westChanged = west.update(now);
    bool eastGo = east.phase() == Phase::EAST_GREEN || east.phase() == Phase::EAST_YELLOW;
    bool westGo = west.phase() == Phase::EAST_GREEN || west.phase() == Phase::EAST_YELLOW;
    CHECK(!(eastGo && westGo));
    uint32_t at = now % 45000;  // cycle: 15 + 18 + 12 s
    if (eastChanged && east.phase() == Phase::NORTH_GREEN) {
      CHECK(at < 20);
      ++northStarts;
    }
    if (westChanged && west.phase() == Phase::NORTH_GREEN) CHECK(at < 20);
    if (eastChanged && east.phase() == Phase::EAST_GREEN) {
      CHECK(at - 15000 < 20);  // after north-south: 10 + 3 + 2 s
      ++eastStarts;
    }
    if (westChanged && west.phase() == Phase::EAST_GREEN) {
      CHECK(at - 33000 < 20);  // after eastbound: + 12 + 4 + 2 s
      ++westStarts;
    }
  }
  CHECK(northStarts >= 12 && eastStarts >= 12 && westStarts >= 12);
}

}  // namespace

void runSignalJunctionTests() {
  coordinatedBoardsShareEveryPhase();
  alignsByLengtheningAllRedOnly();
  lateLoopKeepsEveryCycle();
  eastSlotsNeverOverlap();
  unequalEastSlotsStayApart();
}
