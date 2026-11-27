# AI Interface to Main Control

The first integration slice records detector observations for staff review.
Main Control neither advances a ride nor issues a vehicle command when it
receives an observation. This contract does not transport camera frames.

## Request

Send one JSON object to `POST /internal/vision/observations` with
`Content-Type: application/json` and the dedicated machine key in
`X-AMO-Vision-Key`. Use the internal URL and a machine key supplied by the
deployment owner. The receive endpoint defaults to denied with an empty key.
Main Control reads `AMO_VISION_INGEST_KEY` from the process environment or
`amo.vision-ingest-key` from Spring config. Set an independent random key of
at least 32 characters. Keep the key outside Git and redact it from all logs.

Example payload. Substitute a registered vehicle number and current UTC times:

```json
{
  "resultId": "e77cd853-6b12-4033-a605-21c1c6a67f79",
  "vehicleNo": "PINKY-01",
  "source": "TRAFFIC_RULES",
  "frameId": "camera-1:391",
  "capturedAt": "2026-11-26T01:00:00.100Z",
  "processedAt": "2026-11-26T01:00:00.275Z",
  "outcome": "DETECTED",
  "label": "EXAMPLE_SIGNAL",
  "confidence": 0.83
}
```

- Generate a result UUID once per detector result and reuse it with an
  unchanged payload on retry. A vehicle number is 1–64 ASCII letters,
  digits, underscores or hyphens. A frame ID is 1–96 ASCII letters, digits,
  underscores, hyphens, dots or colons.
- Source codes are `DRIVING_PERCEPTION`, `TRAFFIC_RULES` and
  `DIRECTION_RECOGNITION`. Outcome codes are `DETECTED`, `NOT_DETECTED`
  and `UNAVAILABLE`. `DETECTED` requires a stable label of 1–40 uppercase
  ASCII letters, digits or underscores. Only a detection may carry
  confidence, and its value must be finite and between 0 and 1 inclusive.
  Omit the label and confidence for the other outcomes. The values in the
  example do not establish a detector vocabulary or acceptance threshold.
- Supply ISO-8601 UTC timestamps for capture and processing. The receiver
  uses PostgreSQL microsecond precision. Capture must be at or before
  processing, which may be up to five seconds ahead of reception for clock
  skew. An image-delivery acknowledgement alone does not represent a
  detection. Do not send frame bytes, images or identity data.

## Response and storage

- `204` acknowledges a valid observation for a known vehicle, including
  retries and observations older than or equal to the stored capture time.
  Only a different result with a strictly newer capture time replaces
  the latest row for that vehicle and source.
- `400` identifies invalid input. `404 VEHICLE_NOT_FOUND` identifies an
  unknown vehicle or a vehicle currently assigned to a scenario review.
  `401` or `403` indicates lack of authorization. Client retries should
  be bounded and reserved for timeout or transient server errors.
- The existing AMO PostgreSQL retains up to one record per vehicle and
  source. Main Control records the reception time. Retaining a history
  and defining freshness thresholds require the detector team's cadence
  and retention requirements.

## Deployment boundary

Main Control HTTP listens on IPv4 loopback. For a co-located development
run, set a fixed free `AMO_CONTROL_HTTP_PORT` and use the loopback URL.
The classroom LAN proxy and Web gateway do not carry this write endpoint.
After the Vision source is available, verify the container network path
to the private listener in the combined deployment. The detector source,
its runtime configuration and camera verification come from the Vision
team's tested revision.


## Staff projection

The existing staff `GET /api/operations` response includes an optional
`vision` array of objects with `observation` (the fields above) and
`receivedAt` (ISO-8601 UTC). FMS displays capture time for its selected
vehicle. The PyQt and Web Admin overviews also display the vehicle, source,
outcome, frame ID and server reception time.
No service key is required by staff clients. Their existing session and
role checks apply. Passenger APIs do not expose this projection.
