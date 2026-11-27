// Runs the SignalKit host tests; exits non-zero when any check fails.
#include "check.h"

int g_failures = 0;

int main() {
  runSignalPlanTests();
  runSignalCommandTests();
  runSignalJunctionTests();
  if (g_failures == 0) printf("signal host tests passed\n");
  return g_failures == 0 ? 0 : 1;
}
