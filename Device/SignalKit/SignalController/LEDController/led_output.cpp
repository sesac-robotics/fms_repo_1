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

}  // namespace

void ledBegin() {
#if AMO_RGB_TEST
  const uint8_t pins[] = {PIN_RGB_R, PIN_RGB_G, PIN_RGB_B, PIN_STATUS_LED};
#else
  const uint8_t pins[] = {PIN_NORTH_RED, PIN_NORTH_YELLOW, PIN_NORTH_GREEN, PIN_EAST_RED,
                          PIN_EAST_YELLOW, PIN_EAST_GREEN, PIN_STATUS_LED};
#endif
  for (uint8_t pin : pins) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
  }
  ledShow(Phase::ALL_RED);
}

void ledShow(Phase phase) {
  char north = 'R';
  char east = 'R';
  if (phase == Phase::NORTH_GREEN) north = 'G';
  if (phase == Phase::NORTH_YELLOW) north = 'Y';
  if (phase == Phase::EAST_GREEN) east = 'G';
  if (phase == Phase::EAST_YELLOW) east = 'Y';
#if AMO_RGB_TEST
  (void)east;  // Only the north approach is wired on the bench.
  rgbShow(north);
#else
  // Turn the red side on before releasing the other side.
  if (north == 'R') {
    approach(PIN_NORTH_RED, PIN_NORTH_YELLOW, PIN_NORTH_GREEN, north);
    approach(PIN_EAST_RED, PIN_EAST_YELLOW, PIN_EAST_GREEN, east);
  } else {
    approach(PIN_EAST_RED, PIN_EAST_YELLOW, PIN_EAST_GREEN, east);
    approach(PIN_NORTH_RED, PIN_NORTH_YELLOW, PIN_NORTH_GREEN, north);
  }
#endif
}

void ledLinkStatus(bool connected) { digitalWrite(PIN_STATUS_LED, connected ? HIGH : LOW); }
