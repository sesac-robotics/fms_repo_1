// AMO SignalKit: ESP32 intersection signal reporting to Main Control via micro-ROS.
// The lamps always keep running locally; the network only observes and requests holds.

#include "config.h"
#include "led_output.h"
#include "ros_link.h"
#include "signal_command.h"
#include "signal_plan.h"

SignalPlan plan;
uint32_t seq = 0;
uint32_t lastPublishMs = 0;
uint32_t linkLostMs = 0;
bool linkUp = false;
bool stateDirty = true;
char lastCommand[40] = "";
const char *lastResult = "NONE";

// Apply one command from /traffic_light_N/cmd. Grammar and ranges: signal_command.h.
void handleCommand(const char *text) {
  Command command;
  bool ok = parseCommand(text, command);
  if (ok) {
    switch (command.type) {
      case CommandType::AUTO:
        plan.setAuto();
        break;
      case CommandType::HOLD:
        ok = plan.requestHold(command.holdTarget, millis());
        break;
      case CommandType::PLAN:
        ok = plan.setTiming(command.timing);
        break;
    }
  }
  strncpy(lastCommand, text, sizeof(lastCommand) - 1);
  lastCommand[sizeof(lastCommand) - 1] = '\0';
  lastResult = ok ? "ACCEPTED" : "REJECTED";
  ledShow(plan.phase());
  stateDirty = true;
}

void publishState(uint32_t now) {
  char hold[16] = "null";
  if (plan.mode() == Mode::HOLD) snprintf(hold, sizeof(hold), "\"%s\"", phaseName(plan.holdTarget()));
  char json[448];  // Best-effort messages must fit one 512-byte transport frame.
  const Timing &t = plan.timing();
  // lastCommand comes from the network; only plain command words are accepted,
  // but strip quotes anyway so the JSON stays valid.
  for (char *p = lastCommand; *p; ++p) {
    if (*p == '"' || *p == '\\' || static_cast<unsigned char>(*p) < 0x20) *p = '_';
  }
  snprintf(json, sizeof(json),
           "{\"signalId\":\"%s\",\"seq\":%lu,\"phase\":\"%s\",\"mode\":\"%s\","
           "\"holdTarget\":%s,\"remainingMs\":%lu,\"uptimeMs\":%lu,"
           "\"planMs\":[%lu,%lu,%lu,%lu],\"planPending\":%s,"
           "\"lastCommand\":\"%s\",\"commandResult\":\"%s\"}",
           AMO_SIGNAL_ID, (unsigned long)++seq, phaseName(plan.phase()), modeName(plan.mode()),
           hold, (unsigned long)plan.remainingMs(now), (unsigned long)now,
           (unsigned long)t.northGreenMs, (unsigned long)t.eastGreenMs, (unsigned long)t.yellowMs,
           (unsigned long)t.allRedMs, plan.timingPending() ? "true" : "false", lastCommand,
           lastResult);
  if (rosLinkPublish(json)) {
    lastPublishMs = now;
    stateDirty = false;
  }
}

void watchLink(uint32_t now) {
  bool up = rosLinkService();
  if (up != linkUp) {
    linkUp = up;
    linkLostMs = now;
    ledLinkStatus(up);
    stateDirty = true;
    Serial.println(up ? "[signal] agent connected" : "[signal] agent lost");
  }
  // Without the control link a manual hold could stall traffic, so return to the plan.
  if (!linkUp && plan.mode() == Mode::HOLD && now - linkLostMs > LINK_LOSS_FALLBACK_MS) {
    plan.setAuto();
    lastResult = "FALLBACK_AUTO";
    Serial.println("[signal] hold released after link loss");
  }
}

void setup() {
  Serial.begin(115200);
  ledBegin();
  plan.begin(millis());
  rosLinkBegin(handleCommand);
  Serial.println("[signal] started, waiting for micro-ROS agent");
}

void loop() {
  uint32_t now = millis();
  watchLink(now);
  if (plan.update(now)) {
    ledShow(plan.phase());
    stateDirty = true;
    Serial.printf("[signal] %s\n", phaseName(plan.phase()));
  }
  if (linkUp && (stateDirty || now - lastPublishMs >= STATE_PERIOD_MS)) publishState(now);
  delay(5);
}
