// Minimal assertion helper for the host tests; no test framework is needed.
#pragma once

#include <stdio.h>

extern int g_failures;

#define CHECK(condition)                                                     \
  do {                                                                       \
    if (!(condition)) {                                                      \
      ++g_failures;                                                          \
      printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #condition);            \
    }                                                                        \
  } while (0)

void runSignalPlanTests();
void runSignalCommandTests();
