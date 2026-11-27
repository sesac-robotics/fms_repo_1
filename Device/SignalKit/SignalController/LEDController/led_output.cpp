#include "led_output.h"

#include "config.h"

namespace {

#if !AMO_RGB_TEST
void approach(uint8_t red, uint8_t yellow, uint8_t green, char lamp) {
  // Write the off lamps first so two colours are never lit together.
  if (lamp != 'R') digitalWrite(red, LOW);
  if (lamp != 'Y') digitalWrite(yellow, LOW);
  if (lamp != 'G') digitalWrite(green, LOW);
  digitalWrite(lamp == 'R' ? red : lamp == 'Y' ? yellow : green, HIGH);
}
#endif

#if AMO_RGB_TEST
void rgbWrite(uint8_t pin, bool on) {
  digitalWrite(pin, (on != (AMO_RGB_COMMON_ANODE != 0)) ? HIGH : LOW);
}

void rgbShow(char lamp) {
  rgbWrite(PIN_RGB_B, false);
  rgbWrite(PIN_RGB_R, lamp == 'R' || lamp == 'Y');
  rgbWrite(PIN_RGB_G, lamp == 'G' || lamp == 'Y');
}
#endif

Phase shown = Phase::ALL_RED;

}  // namespace

void ledBegin() {
#if AMO_RGB_TEST
  const uint8_t pins[] = {PIN_RGB_R, PIN_RGB_G, PIN_RGB_B, PIN_STATUS_LED};
#else
  const uint8_t pins[] = {PIN_A_RED, PIN_A_YELLOW, PIN_A_GREEN, PIN_B_RED,
                          PIN_B_YELLOW, PIN_B_GREEN, PIN_STATUS_LED};
#endif
  for (uint8_t pin : pins) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
  }
  ledShow(Phase::ALL_RED);
}

void ledShow(Phase phase) {
  char a = 'R';  // head a, lit in NORTH_* phases
  char b = 'R';  // head b, lit in EAST_* phases
  if (phase == Phase::NORTH_GREEN) a = 'G';
  if (phase == Phase::NORTH_YELLOW) a = 'Y';
  if (phase == Phase::EAST_GREEN) b = 'G';
  if (phase == Phase::EAST_YELLOW) b = 'Y';
  shown = phase;
#if AMO_HEAD_A_PEDESTRIAN
  if (a == 'Y') a = 'G';  // ledTick() flashes it; there is no yellow lamp.
#endif
#if AMO_RGB_TEST
  (void)b;  // Only head a is wired on the RGB bench setup.
  rgbShow(a);
#else
  // Turn the red side on before releasing the other side.
  if (a == 'R') {
    approach(PIN_A_RED, PIN_A_YELLOW, PIN_A_GREEN, a);
    approach(PIN_B_RED, PIN_B_YELLOW, PIN_B_GREEN, b);
  } else {
    approach(PIN_B_RED, PIN_B_YELLOW, PIN_B_GREEN, b);
    approach(PIN_A_RED, PIN_A_YELLOW, PIN_A_GREEN, a);
  }
#endif
}

void ledLinkStatus(bool connected) { digitalWrite(PIN_STATUS_LED, connected ? HIGH : LOW); }

void ledTick(uint32_t now) {
#if AMO_HEAD_A_PEDESTRIAN && !AMO_RGB_TEST
  if (shown == Phase::NORTH_YELLOW) {
    digitalWrite(PIN_A_GREEN, (now / PEDESTRIAN_FLASH_MS) % 2 == 0 ? HIGH : LOW);
  }
#else
  (void)now;
#endif
}
