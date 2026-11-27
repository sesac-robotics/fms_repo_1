// AMO SignalKit: ESP32 intersection signal reporting to Main Control via micro-ROS.
// The lamps always keep running locally; the network only observes and requests holds.
// Lamps run in their own FreeRTOS task, so a blocking reconnect in loop() (up to
// seconds while micro-ROS recreates entities) never delays a phase change; that
// matters on coordinated boards, whose partner keeps switching on time.

#include <WiFi.h>

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
volatile bool stateDirty = true;
SemaphoreHandle_t planLock;  // guards plan and the lamp outputs

// Holds planLock for one scope.
struct PlanGuard {
  PlanGuard() { xSemaphoreTake(planLock, portMAX_DELAY); }
  ~PlanGuard() { xSemaphoreGive(planLock); }
};
char lastCommand[48] = "";  // fits the six-number PLAN
const char *lastResult = "NONE";

// Apply one command from /traffic_light_N/cmd. Grammar and ranges: signal_command.h.
void handleCommand(const char *text) {
  PlanGuard guard;
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
  char json[448];  // Best-effort messages must fit one 512-byte transport frame.
  {
    PlanGuard guard;
    stateDirty = false;  // a phase change after this point publishes again
    char hold[16] = "null";
    if (plan.mode() == Mode::HOLD) {
      snprintf(hold, sizeof(hold), "\"%s\"", phaseName(plan.holdTarget()));
    }
    const Timing &t = plan.timing();
    // lastCommand comes from the network; only plain command words are accepted,
    // but strip quotes anyway so the JSON stays valid.
    for (char *p = lastCommand; *p; ++p) {
      if (*p == '"' || *p == '\\' || static_cast<unsigned char>(*p) < 0x20) *p = '_';
    }
    snprintf(json, sizeof(json),
             "{\"signalId\":\"%s\",\"seq\":%lu,\"phase\":\"%s\",\"mode\":\"%s\","
             "\"holdTarget\":%s,\"remainingMs\":%lu,\"uptimeMs\":%lu,"
             "\"planMs\":[%lu,%lu,%lu,%lu,%lu,%lu],\"planPending\":%s,"
             "\"lastCommand\":\"%s\",\"commandResult\":\"%s\"}",
             AMO_SIGNAL_ID, (unsigned long)++seq, phaseName(plan.phase()),
             modeName(plan.mode()), hold, (unsigned long)plan.remainingMs(now),
             (unsigned long)now, (unsigned long)t.northGreenMs, (unsigned long)t.eastGreenMs,
             (unsigned long)t.yellowMs, (unsigned long)t.allRedMs,
             (unsigned long)t.eastYellowMs, (unsigned long)t.partnerEastMs,
             plan.timingPending() ? "true" : "false", lastCommand, lastResult);
  }
  if (rosLinkPublish(json)) {
    lastPublishMs = now;
  } else {
    stateDirty = true;
  }
}

void watchLink(uint32_t now) {
  bool up = rosLinkService();
  if (up != linkUp) {
    linkUp = up;
    linkLostMs = now;
    ledLinkStatus(up);
    stateDirty = true;
    // RSSI below about -75 dBm usually explains a flapping link.
    Serial.printf("[signal] agent %s, Wi-Fi RSSI %d dBm\n", up ? "connected" : "lost", WiFi.RSSI());
  }
  // Without the control link a manual hold could stall traffic, so return to the plan.
  if (linkUp || now - linkLostMs <= LINK_LOSS_FALLBACK_MS) return;
  PlanGuard guard;
  if (plan.mode() == Mode::HOLD) {
    plan.setAuto();
    lastResult = "FALLBACK_AUTO";
    Serial.println("[signal] hold released after link loss");
  }
}

// Every 5 s on the serial port: Wi-Fi status, signal, channel and IP, to tell a
// weak radio from a lost agent when a board will not stay connected.
void reportWifi(uint32_t now) {
  static uint32_t lastMs = 0;
  if (now - lastMs < 5000) return;
  lastMs = now;
  Serial.printf("[signal] wifi status %d rssi %d dBm ch %d ap %s ip %s link %s\n",
                WiFi.status(), WiFi.RSSI(), WiFi.channel(), WiFi.BSSIDstr().c_str(),
                WiFi.localIP().toString().c_str(), linkUp ? "up" : "down");
}

// Advance the plan and drive the lamps every 5 ms, whatever loop() is doing.
void lampTask(void *) {
  for (;;) {
    uint32_t now = millis();
    {
      PlanGuard guard;
      if (plan.update(now)) {
        ledShow(plan.phase());
        stateDirty = true;
        Serial.printf("[signal] %s\n", phaseName(plan.phase()));
      }
      ledTick(now);
    }
    vTaskDelay(pdMS_TO_TICKS(5));
  }
}

void setup() {
  Serial.begin(115200);
  planLock = xSemaphoreCreateMutex();
  ledBegin();
  plan.setCoordinated(AMO_COORDINATED, AMO_EAST_SLOT, AMO_EAST_SLOTS);
  plan.begin(millis());
  // Above loop()'s priority (1) on the same core, so it preempts a busy loop.
  xTaskCreatePinnedToCore(lampTask, "lamps", 4096, nullptr, 2, nullptr, 1);
  rosLinkBegin(handleCommand);
  Serial.println("[signal] started, waiting for micro-ROS agent");
}

void loop() {
  uint32_t now = millis();
  watchLink(now);
  uint32_t clockOffset;
  if (rosLinkClock(clockOffset)) {
    PlanGuard guard;
    bool first = !plan.clockSet();
    plan.setClock(clockOffset, now);
    if (first) Serial.println("[signal] agent clock received");
  }
  reportWifi(now);
  if (linkUp && (stateDirty || now - lastPublishMs >= STATE_PERIOD_MS)) publishState(now);
  delay(5);
}
