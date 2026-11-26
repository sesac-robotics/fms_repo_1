#!/usr/bin/env bash
# Build and run the SignalKit host tests with the system C++ compiler.
# Arduino builds only compile the sketch root and src/, so this folder is not
# part of the firmware image.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="$(mktemp -d)"
trap 'rm -rf "$out"' EXIT
g++ -std=c++17 -Wall -Wextra -Werror -I"$here/.." \
  "$here/main.cpp" "$here/signal_plan_test.cpp" "$here/signal_command_test.cpp" \
  "$here/../signal_plan.cpp" "$here/../signal_command.cpp" \
  -o "$out/signal_host_tests"
"$out/signal_host_tests"
