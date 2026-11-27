import assert from "node:assert/strict";
import { test } from "node:test";

import { parseVisionReadings } from "../src/visionReadings.js";

const receiptTime = "2026-11-26T01:00:00.275Z";
const capturedAt = "2026-11-26T01:00:00.100Z";
const observation = {
  vehicleNo: "PINKY-01",
  source: "TRAFFIC_RULES",
  frameId: "camera-1:391",
  capturedAt,
  outcome: "DETECTED",
  label: "EXAMPLE_SIGNAL",
};

test("keeps the same outcome, vehicle, frame and times as desktop", () => {
  assert.deepEqual(
    parseVisionReadings([{ observation, receivedAt: receiptTime }]),
    [
      {
        vehicleNo: "PINKY-01",
        source: "TRAFFIC_RULES",
        frameId: "camera-1:391",
        capturedAt,
        receivedAt: receiptTime,
        outcomeKey: "visionDetected",
        label: "EXAMPLE_SIGNAL",
      },
    ],
  );
});

test("keeps undetected and unavailable outcomes distinct", () => {
  const rows = ["NOT_DETECTED", "UNAVAILABLE"].map((outcome) => ({
    observation: { ...observation, outcome, label: null },
    receivedAt: receiptTime,
  }));
  assert.deepEqual(
    parseVisionReadings(rows).map(({ outcomeKey, label }) => [
      outcomeKey,
      label,
    ]),
    [
      ["visionNotDetected", ""],
      ["visionUnavailable", ""],
    ],
  );
});

test("accepts missing legacy data, but skips invalid rows", () => {
  assert.deepEqual(parseVisionReadings(undefined), []);
  assert.deepEqual(
    parseVisionReadings([
      null,
      { observation, receivedAt: "bad timestamp" },
      {
        observation: { ...observation, outcome: "RECEIVED" },
        receivedAt: receiptTime,
      },
      {
        observation: { ...observation, source: "UNKNOWN" },
        receivedAt: receiptTime,
      },
      { observation, receivedAt: receiptTime },
    ]).map(({ frameId }) => frameId),
    ["camera-1:391"],
  );
});
