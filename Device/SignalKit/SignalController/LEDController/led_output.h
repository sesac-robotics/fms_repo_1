// Drives the signal lamps (two heads) and the link status LED.
#pragma once

#include "signal_plan.h"

void ledBegin();
void ledShow(Phase phase);
void ledLinkStatus(bool connected);
// Call every loop: flashes the pedestrian green on boards that have one.
void ledTick(uint32_t now);
