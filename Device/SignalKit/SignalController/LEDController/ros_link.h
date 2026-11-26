// micro-ROS entities over Wi-Fi UDP: one state publisher, one command subscriber.
#pragma once

#include <Arduino.h>

using CommandHandler = void (*)(const char *text);

// Start joining Wi-Fi and remember the agent address. Returns immediately.
void rosLinkBegin(CommandHandler handler);

// Call every loop. Joins the agent once Wi-Fi is up, keeps the session alive
// and reconnects when lost. Returns true while entities exist and the agent
// answers. Blocking bounds: a ping waits up to 100 ms per attempt (3 attempts
// while connected); creating entities after a reconnect can take up to about
// 1 s per entity (micro-ROS RMW_UXRCE_ENTITY_CREATION_TIMEOUT), during which
// the lamps hold their current phase.
bool rosLinkService();

// Publish one state document. Returns false when not connected.
bool rosLinkPublish(const char *json);
