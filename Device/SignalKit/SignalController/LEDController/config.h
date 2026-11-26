// Board wiring, identity and link settings for one AMO intersection signal on ESP32
// (FQBN esp32:esp32:esp32, core 2.0.17; see sketch.yaml). Names follow Arduino style:
// camelCase functions, UPPER_CASE constants, PascalCase types.
#pragma once

#include <Arduino.h>

// Identity reported to Main Control. Change per physical signal.
#define AMO_SIGNAL_ID "SIG-01"

// ROS 2 names follow the team rule: one namespace per device (SR-027).
// Topics resolve to /traffic_light_1/state and /traffic_light_1/cmd.
#define AMO_NODE_NAMESPACE "traffic_light_1"
#define AMO_NODE_NAME "controller"
#define AMO_TOPIC_STATE "state"
#define AMO_TOPIC_COMMAND "cmd"

// micro-ROS takes the DDS domain from the client, so it is set here, not on the agent.
constexpr size_t AMO_ROS_DOMAIN_ID = 16;

// LED pins (active HIGH). Avoid strapping pins 0, 2, 12 and 15.
constexpr uint8_t PIN_NORTH_RED = 25;
constexpr uint8_t PIN_NORTH_YELLOW = 26;
constexpr uint8_t PIN_NORTH_GREEN = 27;
constexpr uint8_t PIN_EAST_RED = 32;
constexpr uint8_t PIN_EAST_YELLOW = 33;
constexpr uint8_t PIN_EAST_GREEN = 14;
constexpr uint8_t PIN_STATUS_LED = 4;  // Lit while the micro-ROS agent is connected.

// Bench test with one RGB LED showing only the north approach:
// red = R, yellow = R+G, green = G. Set AMO_RGB_TEST to 0 for six separate lamps.
#define AMO_RGB_TEST 0
#define AMO_RGB_COMMON_ANODE 0  // 1 if the RGB LED's common pin goes to 3.3V
constexpr uint8_t PIN_RGB_R = 25;
constexpr uint8_t PIN_RGB_G = 26;
constexpr uint8_t PIN_RGB_B = 27;

// Phase durations and PLAN safe ranges live in signal_timing.h (shared with host tests).

// Publish state at least this often, and immediately on every phase change.
constexpr uint32_t STATE_PERIOD_MS = 500;

// A manual hold falls back to the fixed plan when the agent is lost this long.
constexpr uint32_t LINK_LOSS_FALLBACK_MS = 5000;

// Agent ping settings used by the reconnect state machine.
constexpr uint32_t AGENT_PING_PERIOD_MS = 1000;
constexpr int AGENT_PING_TIMEOUT_MS = 100;
