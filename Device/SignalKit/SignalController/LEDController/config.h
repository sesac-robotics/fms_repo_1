// Board wiring, identity and link settings for one AMO intersection signal on ESP32
// (FQBN esp32:esp32:esp32, core 2.0.17; see sketch.yaml). Names follow Arduino style:
// camelCase functions, UPPER_CASE constants, PascalCase types.
#pragma once

#include <Arduino.h>

// Board number 1-9: the only line to change per physical board. It gives the
// identity reported to Main Control (SIG-0N) and the ROS 2 namespace
// (traffic_light_N, one namespace per device per SR-027), so topics resolve to
// /traffic_light_N/state and /traffic_light_N/cmd. arduino-cli can also set it
// without editing: --build-property "compiler.cpp.extra_flags=-DAMO_BOARD=2".
#ifndef AMO_BOARD
#define AMO_BOARD 1
#endif
static_assert(AMO_BOARD >= 1 && AMO_BOARD <= 9, "AMO_BOARD must be 1-9");
#define AMO_STRINGIFY_(x) #x
#define AMO_STRINGIFY(x) AMO_STRINGIFY_(x)
#define AMO_SIGNAL_ID "SIG-0" AMO_STRINGIFY(AMO_BOARD)
#define AMO_NODE_NAMESPACE "traffic_light_" AMO_STRINGIFY(AMO_BOARD)
#define AMO_NODE_NAME "controller"
#define AMO_TOPIC_STATE "state"
#define AMO_TOPIC_COMMAND "cmd"

// micro-ROS takes the DDS domain from the client, so it is set here, not on the agent.
constexpr size_t AMO_ROS_DOMAIN_ID = 16;

// Team wiring convention for every SignalKit board (LEDs active HIGH):
//   head a, lit in NORTH_* phases: R D27, Y D26, G D25
//   head b, lit in EAST_* phases:  R D5,  Y D18, G D19
// Directions served per board: 1 = a northbound (S->N), b eastbound (W->E);
// 2 = a southbound (N->S), b westbound (E->W); 3 = a pedestrian crossing at
// the north T-junction (east end), b eastbound there; 4 = the same crossing's
// west end, b westbound there. Phase names keep the board-1
// wording on every board: NORTH_* means head a, EAST_* head b. GPIO5 is a strapping pin that
// may blink the red lamp briefly at boot; it is otherwise a normal output.
//
// Boards 3 and 4 replace head a with a two-lamp pedestrian signal: R D27, G D26
// (D25 unused). Its green stays on through NORTH_GREEN and flashes through
// NORTH_YELLOW, since pedestrian signals have no yellow lamp.
#define AMO_HEAD_A_PEDESTRIAN (AMO_BOARD == 3 || AMO_BOARD == 4)
#if AMO_HEAD_A_PEDESTRIAN
constexpr uint8_t PIN_A_RED = 27;
constexpr uint8_t PIN_A_YELLOW = 25;  // Not wired; kept LOW.
constexpr uint8_t PIN_A_GREEN = 26;
constexpr uint32_t PEDESTRIAN_FLASH_MS = 500;
#else
constexpr uint8_t PIN_A_RED = 27;
constexpr uint8_t PIN_A_YELLOW = 26;
constexpr uint8_t PIN_A_GREEN = 25;
#endif
constexpr uint8_t PIN_B_RED = 5;
constexpr uint8_t PIN_B_YELLOW = 18;
constexpr uint8_t PIN_B_GREEN = 19;
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

// Boards that share an intersection run on the agent's clock so their phases
// match (SignalPlan::setCoordinated). Boards 1 and 2 form the centre crossroads
// in three phases: northbound and southbound green together, then eastbound
// alone (board 1, east slot 0), then westbound alone (board 2, east slot 1),
// since both east-west approaches turn left with their through traffic.
// Both must carry the same PLAN; the FMS keeps the pair's fields linked.
// Boards 3 and 4 form the north T-junction and show identical signals: one
// east slot, so their pedestrian heads and car heads switch together.
#define AMO_COORDINATED (AMO_BOARD >= 1 && AMO_BOARD <= 4)
#define AMO_EAST_SLOT (AMO_BOARD == 2 ? 1 : 0)
#define AMO_EAST_SLOTS (AMO_BOARD <= 2 ? 2 : 1)
constexpr uint32_t CLOCK_SYNC_PERIOD_MS = 60000;  // after the first success
constexpr uint32_t CLOCK_RETRY_MS = 2000;         // until the first success
constexpr int CLOCK_SYNC_TIMEOUT_MS = 300;

// Agent ping settings used by the reconnect state machine. A busy shared Wi-Fi
// can take 100-300 ms per round trip, so one slow ping must not drop the link:
// only AGENT_PING_MISSES missed pings in a row do (about 3 s, inside the 5 s
// fallback above). A ping blocks the loop for at most AGENT_PING_TIMEOUT_MS.
constexpr uint32_t AGENT_PING_PERIOD_MS = 1000;
constexpr int AGENT_PING_TIMEOUT_MS = 400;
constexpr uint8_t AGENT_PING_MISSES = 3;
