// Phase sequencing (a small state machine) for a two-approach intersection.
// Pure C++ with no hardware or ROS dependency, so it runs in host tests.
// Times are millis()-style unsigned milliseconds; wrap-around is handled by
// unsigned subtraction.
#pragma once

#include <stdint.h>

#include "signal_timing.h"

// Phase names follow experiments/deepfleet (NORTH_GREEN, EAST_GREEN, ALL_RED).
// Yellow phases are added for the physical lamp; they admit no new entry.
enum class Phase : uint8_t {
  NORTH_GREEN,
  NORTH_YELLOW,
  ALL_RED,
  EAST_GREEN,
  EAST_YELLOW,
};

// AUTO runs the fixed plan. HOLD keeps the target phase after a safe transition.
enum class Mode : uint8_t { AUTO, HOLD };

const char *phaseName(Phase phase);
const char *modeName(Mode mode);

class SignalPlan {
 public:
  void begin(uint32_t nowMs);

  // Advance timing. Returns true when the phase changed.
  bool update(uint32_t nowMs);

  // Run the fixed plan from the current phase.
  void setAuto();

  // Hold NORTH_GREEN, EAST_GREEN or ALL_RED. A green that conflicts with the
  // current green first passes through yellow and all red.
  bool requestHold(Phase target, uint32_t nowMs);

  // Replace the durations. The running phase keeps its length; the new values
  // apply from the next phase change. Returns false for an unsafe timing.
  bool setTiming(const Timing &timing);

  // Durations the next phase change will use (pending if not yet applied).
  const Timing &timing() const { return pendingSet_ ? pending_ : timing_; }
  bool timingPending() const { return pendingSet_; }

  Phase phase() const { return phase_; }
  Mode mode() const { return mode_; }
  Phase holdTarget() const { return target_; }
  uint32_t remainingMs(uint32_t nowMs) const;

 private:
  void enter(Phase next, uint32_t nowMs);
  Phase nextAuto() const;
  Phase nextTowardTarget() const;
  uint32_t durationOf(Phase phase) const;
  bool holding() const;

  Phase phase_ = Phase::ALL_RED;
  Phase target_ = Phase::ALL_RED;
  Phase lastGreen_ = Phase::EAST_GREEN;  // so AUTO starts with NORTH_GREEN
  Mode mode_ = Mode::AUTO;
  uint32_t enteredMs_ = 0;
  uint32_t phaseLengthMs_ = 0;  // fixed when the phase starts
  Timing timing_{};
  Timing pending_{};
  bool pendingSet_ = false;
};
