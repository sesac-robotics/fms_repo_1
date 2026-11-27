// Host tests for the phase state machine: order, durations, holds and plans.
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

void startsAllRedAndRunsTheFixedOrder() {
  SignalPlan plan;
  uint32_t now = 0;
  plan.begin(now);
  CHECK(plan.phase() == Phase::ALL_RED);
  const Phase order[] = {Phase::NORTH_GREEN, Phase::NORTH_YELLOW, Phase::ALL_RED,
                         Phase::EAST_GREEN, Phase::EAST_YELLOW, Phase::ALL_RED};
  const uint32_t at[] = {2000, 12000, 15000, 17000, 27000, 30000};
  for (int i = 0; i < 6; ++i) {
    CHECK(advanceUntilChange(plan, now, 20000) == at[i]);
    CHECK(plan.phase() == order[i]);
  }
}

void holdPassesThroughYellowAndAllRed() {
  SignalPlan plan;
  uint32_t now = 0;
  plan.begin(now);
  advanceUntilChange(plan, now, 5000);  // NORTH_GREEN at 2 s
  CHECK(plan.requestHold(Phase::EAST_GREEN, now));
  CHECK(plan.phase() == Phase::NORTH_YELLOW);
  CHECK(advanceUntilChange(plan, now, 5000) == 5000);
  CHECK(plan.phase() == Phase::ALL_RED);
  advanceUntilChange(plan, now, 5000);
  CHECK(plan.phase() == Phase::EAST_GREEN);
  CHECK(advanceUntilChange(plan, now, 60000) == 0);  // held indefinitely
  CHECK(plan.remainingMs(now) == 0);
  CHECK(!plan.requestHold(Phase::NORTH_YELLOW, now));
  plan.setAuto();
  advanceUntilChange(plan, now, 1000);
  CHECK(plan.phase() == Phase::EAST_YELLOW);
}

void planAppliesFromTheNextPhase() {
  SignalPlan plan;
  uint32_t now = 0;
  plan.begin(now);
  advanceUntilChange(plan, now, 5000);  // NORTH_GREEN, 10 s
  CHECK(!plan.setTiming({1000, 8000, 3000, 2000, 3000, 0}));
  CHECK(plan.setTiming({15000, 8000, 4000, 1000, 4000, 0}));
  CHECK(plan.timingPending());
  CHECK(plan.remainingMs(now) == 10000);  // the running green keeps its length
  CHECK(advanceUntilChange(plan, now, 20000) == 12000);
  CHECK(!plan.timingPending());
  CHECK(plan.remainingMs(now) == 4000);  // new yellow
}

void survivesMillisWrapAround() {
  SignalPlan plan;
  uint32_t now = 0xFFFFFFFFu - 500;
  plan.begin(now);
  CHECK(advanceUntilChange(plan, now, 5000) == static_cast<uint32_t>(0xFFFFFFFFu - 500 + 2000));
  CHECK(plan.phase() == Phase::NORTH_GREEN);
}

}  // namespace

void runSignalPlanTests() {
  startsAllRedAndRunsTheFixedOrder();
  holdPassesThroughYellowAndAllRed();
  planAppliesFromTheNextPhase();
  survivesMillisWrapAround();
}
