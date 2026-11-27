# Vision detector HTTP response

The AI Interface sends the camera JPEG as an `image/jpeg` request body to
`POST /infer`. Use `X-Frame-Id` to correlate the response. The camera and request
formats remain the same as the [camera transport contract](camera-transport-contract.md).

A detector that completes a request returns HTTP 200 and a JSON object
with `Content-Type: application/json`. This example is synthetic.

```json
{
  "frame_id": "01ab23cd45ef678901ab23cd45ef6789",
  "outcome": "DETECTED",
  "label": "RED_LIGHT",
  "confidence": 0.92,
  "processed_at": "2026-11-27T01:00:00.275Z"
}
```

- `frame_id` is the exact `X-Frame-Id` from the request.
- `outcome` is `DETECTED` when the detector returns a classified result,
  `NOT_DETECTED` when it ran successfully and found no supported target,
  or `UNAVAILABLE` when it received the frame and cannot classify it.
- `DETECTED` requires a stable `label` of 1–40 ASCII uppercase letters, digits,
  or underscores. `confidence` is optional and, if set, is a finite JSON
  number between 0 and 1 inclusive. Omit both fields for the other outcomes.
- `processed_at` is the detector's completion time in UTC, in ISO 8601
  ending in `Z` with up to six fractional digits. Synchronize the detector
  and camera clocks. The completion time must be at or after frame acquisition.
- The response contains only the fields above. Invalid requests return 4xx
  and a service failure can return 5xx. A transport error or the diagnostic
  `mock: true` receipt never becomes an observation.

The AI Interface selects the source from the configured detector endpoint,
maps the camera to a registered AMO vehicle, and derives acquisition time
from the ROS message. It generates the result UUID and converts the result
to the [Main Control observation contract](observation-contract.md).
After a transient write failure it retries once with the identical payload.
No image or passenger identity is sent to Main Control.
