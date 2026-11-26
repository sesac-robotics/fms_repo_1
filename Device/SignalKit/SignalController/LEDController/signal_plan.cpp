#include "signal_plan.h"

const char *phaseName(Phase phase) {
  switch (phase) {
    case Phase::NORTH_GREEN:
      return "NORTH_GREEN";
    case Phase::NORTH_YELLOW:
      return "NORTH_YELLOW";
    case Phase::EAST_GREEN:
      return "EAST_GREEN";
    case Phase::EAST_YELLOW:
      return "EAST_YELLOW";
    default:
      return "ALL_RED";
  }
}

const char *modeName(Mode mode) { return mode == Mode::HOLD ? "HOLD" : "AUTO"; }

void SignalPlan::begin(uint32_t nowMs) {
  mode_ = Mode::AUTO;
  timing_ = DEFAULT_TIMING;
  pendingSet_ = false;
  enter(Phase::ALL_RED, nowMs);  // Power-on always starts from all red.
}

bool SignalPlan::update(uint32_t nowMs) {
  if (holding()) return false;
  if (nowMs - enteredMs_ < phaseLengthMs_) return false;
  enter(mode_ == Mode::AUTO ? nextAuto() : nextTowardTarget(), nowMs);
  return true;
}

void SignalPlan::setAuto() { mode_ = Mode::AUTO; }

bool SignalPlan::setTiming(const Timing &timing) {
  if (!timingValid(timing)) return false;
  pending_ = timing;
  pendingSet_ = true;
  return true;
}

bool SignalPlan::requestHold(Phase target, uint32_t nowMs) {
  if (target != Phase::NORTH_GREEN && target != Phase::EAST_GREEN &&
      target != Phase::ALL_RED) {
    return false;
  }
  mode_ = Mode::HOLD;
  target_ = target;
  // A green ends through its yellow right away; yellow and all red finish
  // their own minimum time before moving on.
  if (phase_ == Phase::NORTH_GREEN && target != Phase::NORTH_GREEN) {
    enter(Phase::NORTH_YELLOW, nowMs);
  } else if (phase_ == Phase::EAST_GREEN && target != Phase::EAST_GREEN) {
    enter(Phase::EAST_YELLOW, nowMs);
  }
  return true;
}

uint32_t SignalPlan::remainingMs(uint32_t nowMs) const {
  if (holding()) return 0;  // 0 means "no scheduled change".
  uint32_t elapsed = nowMs - enteredMs_;
  return elapsed >= phaseLengthMs_ ? 0 : phaseLengthMs_ - elapsed;
}

void SignalPlan::enter(Phase next, uint32_t nowMs) {
  if (next == Phase::NORTH_GREEN || next == Phase::EAST_GREEN) lastGreen_ = next;
  if (pendingSet_) {
    timing_ = pending_;
    pendingSet_ = false;
  }
  phase_ = next;
  enteredMs_ = nowMs;
  phaseLengthMs_ = durationOf(next);
}

Phase SignalPlan::nextAuto() const {
  switch (phase_) {
    case Phase::NORTH_GREEN:
      return Phase::NORTH_YELLOW;
    case Phase::EAST_GREEN:
      return Phase::EAST_YELLOW;
    case Phase::NORTH_YELLOW:
    case Phase::EAST_YELLOW:
      return Phase::ALL_RED;
    default:
      return lastGreen_ == Phase::NORTH_GREEN ? Phase::EAST_GREEN : Phase::NORTH_GREEN;
  }
}

Phase SignalPlan::nextTowardTarget() const {
  if (phase_ == Phase::NORTH_YELLOW || phase_ == Phase::EAST_YELLOW) return Phase::ALL_RED;
  // In ALL_RED: go to the held green, or stay when the target is ALL_RED.
  return target_;
}

uint32_t SignalPlan::durationOf(Phase phase) const {
  switch (phase) {
    case Phase::NORTH_GREEN:
      return timing_.northGreenMs;
    case Phase::EAST_GREEN:
      return timing_.eastGreenMs;
    case Phase::NORTH_YELLOW:
    case Phase::EAST_YELLOW:
      return timing_.yellowMs;
    default:
      return timing_.allRedMs;
  }
}

bool SignalPlan::holding() const { return mode_ == Mode::HOLD && phase_ == target_; }
