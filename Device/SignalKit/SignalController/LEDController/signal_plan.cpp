#include "signal_plan.h"

namespace {
// Phase length that update() never reaches: a coordinated board waiting for
// its first clock. remainingMs() reports it as 0, "no scheduled change".
constexpr uint32_t WAIT_FOR_CLOCK = 0xFFFFFFFFu;
// A boundary missed by less than this still counts: the all red keeps its
// normal length and NORTH_GREEN starts that much late, instead of waiting a
// whole cycle because the loop noticed the phase end a few milliseconds late.
constexpr uint32_t ALIGN_SLACK_MS = 500;
// A phase noticed this late still starts at its due time, so the few ms each
// loop pass adds do not pile up over the cycle. A longer stall restarts the
// timing from now, keeping every phase at full length.
constexpr uint32_t ON_TIME_MS = 100;
}  // namespace

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
  uint32_t due = enteredMs_ + phaseLengthMs_;
  enter(mode_ == Mode::AUTO ? nextAuto() : nextTowardTarget(),
        nowMs - due < ON_TIME_MS ? due : nowMs);
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

void SignalPlan::setClock(uint32_t clockMinusMillis, uint32_t nowMs) {
  clockOffset_ = clockMinusMillis;
  clockSet_ = true;
  if (!aligning_) return;  // later all reds pick the new offset up
  phaseLengthMs_ = alignedAllRed();
  // A late clock may put the boundary behind us; wait for the next cycle.
  uint32_t elapsed = nowMs - enteredMs_;
  if (elapsed >= phaseLengthMs_) {
    phaseLengthMs_ += ((elapsed - phaseLengthMs_) / cycleMs() + 1) * cycleMs();
  }
}

uint32_t SignalPlan::remainingMs(uint32_t nowMs) const {
  if (holding() || phaseLengthMs_ == WAIT_FOR_CLOCK) return 0;  // no scheduled change
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
  aligning_ = alignsBefore(next);
  phaseLengthMs_ = aligning_ ? alignedAllRed() : durationOf(next);
  // Before this board's own east-west green: sit out the earlier boards' slots.
  if (coordinated_ && mode_ == Mode::AUTO && next == Phase::ALL_RED &&
      lastGreen_ == Phase::NORTH_GREEN) {
    // Two boards per junction: slot 1 waits for the slot-0 board's east slot.
    if (eastSlot_ > 0) phaseLengthMs_ += partnerSlotMs();
  }
}

// This board's east-west green with its yellow and all red.
uint32_t SignalPlan::eastSlotMs() const {
  return timing_.eastGreenMs + timing_.eastYellowMs + timing_.allRedMs;
}

// The other boards' east slots; each may have its own green and yellow.
uint32_t SignalPlan::partnerSlotMs() const {
  if (eastSlots_ <= 1) return 0;
  if (timing_.partnerEastMs == 0) return (eastSlots_ - 1) * eastSlotMs();
  return timing_.partnerEastMs + timing_.allRedMs;
}

// The junction's full cycle: north-south green, then every board's east slot.
uint32_t SignalPlan::cycleMs() const {
  return timing_.northGreenMs + timing_.yellowMs + timing_.allRedMs + eastSlotMs() +
         partnerSlotMs();
}

bool SignalPlan::alignsBefore(Phase next) const {
  return coordinated_ && mode_ == Mode::AUTO && next == Phase::ALL_RED &&
         lastGreen_ != Phase::NORTH_GREEN;
}

uint32_t SignalPlan::alignedAllRed() const {
  if (!clockSet_) return WAIT_FOR_CLOCK;
  uint32_t cycle = cycleMs();
  // Shared-clock time at which the normal all red would end. Unsigned wrap is
  // the same instant on every board, so they stay in step across it.
  uint32_t end = enteredMs_ + timing_.allRedMs + clockOffset_;
  uint32_t late = (end - ALIGN_SLACK_MS) % cycle;
  uint32_t length = timing_.allRedMs - ALIGN_SLACK_MS + (late == 0 ? 0 : cycle - late);
  return length < timing_.allRedMs ? timing_.allRedMs : length;
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
      return timing_.yellowMs;
    case Phase::EAST_YELLOW:
      return timing_.eastYellowMs;
    default:
      return timing_.allRedMs;
  }
}

bool SignalPlan::holding() const { return mode_ == Mode::HOLD && phase_ == target_; }
