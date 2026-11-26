// Drives the six signal lamps and the link status LED.
#pragma once

#include "signal_plan.h"

void ledBegin();
void ledShow(Phase phase);
void ledLinkStatus(bool connected);
