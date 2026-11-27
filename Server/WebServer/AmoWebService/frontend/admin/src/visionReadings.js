const sources = new Set([
  "DRIVING_PERCEPTION",
  "TRAFFIC_RULES",
  "DIRECTION_RECOGNITION",
]);

const outcomeKeys = new Map([
  ["DETECTED", "visionDetected"],
  ["NOT_DETECTED", "visionNotDetected"],
  ["UNAVAILABLE", "visionUnavailable"],
]);

/**
 * Extract displayable entries from the staff snapshot's optional vision array.
 * Each record contains the vehicle, source, outcome, frame and two UTC times.
 * Ignore missing or invalid rows, as in the desktop staff clients.
 * @param {unknown} value The value of GET /api/operations.vision.
 */
export function parseVisionReadings(value) {
  if (!Array.isArray(value)) return [];

  const readings = [];
  for (const row of value.slice(0, 400)) {
    const item = row?.observation;
    if (!item || !sources.has(item.source)) continue;
    const outcomeKey = outcomeKeys.get(item.outcome);
    const label = item.label ?? "";
    const { vehicleNo, source, frameId, capturedAt } = item;
    const { receivedAt } = row;
    if (
      !outcomeKey ||
      typeof label !== "string" ||
      ![vehicleNo, frameId, capturedAt, receivedAt].every(
        (field) => typeof field === "string" && field.length > 0,
      ) ||
      !Number.isFinite(Date.parse(capturedAt)) ||
      !Number.isFinite(Date.parse(receivedAt))
    ) {
      continue;
    }
    readings.push({
      vehicleNo,
      source,
      frameId,
      capturedAt,
      receivedAt,
      outcomeKey,
      label,
    });
  }
  return readings;
}
