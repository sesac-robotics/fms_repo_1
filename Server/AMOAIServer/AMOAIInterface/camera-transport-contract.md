# Front-camera receipt test

The Vision handoff selects ROS 2 Best Effort for the front-camera path.
The published IF-07 specification still lists direct UDP image transport.
This implementation exercises the selected transport in a development run.
Align IF-07 with the owners before enabling it in the classroom deployment.

- Publisher: Pinky front camera, 640 × 480 JPEG at 5 FPS, rotated 180 degrees.
- Subscriber: AI Interface, on `/amo/<robot-id>/camera/compressed`, using
  `sensor_msgs/msg/CompressedImage` with Best Effort, Keep Last depth 1 and
  Volatile durability. The robot ID uses 1–32 ASCII characters allowed in a
  ROS topic component and appears in `<robot-id>/front_optical_frame`.
- Timestamp: UTC Unix seconds plus nanoseconds assigned when a complete JPEG
  is read from the camera stream. This is a publisher timestamp. Exposure
  time and inter-device clock synchronization require independent evidence.
  Frame IDs are the big-endian hex robot hash (BLAKE2s, 8 bytes) followed by the
  big-endian publisher timestamp (8 bytes).
- Scheduling: accept one pending JPEG per configured robot. A newer frame
  replaces that robot's pending frame, and 200 ms of local monotonic queue
  time expires it. Reject duplicate and reversed stamps until five seconds
  without an accepted frame. At most one frame is in flight across the three
  destinations. One slow request can delay the next frame for any robot.
- Vision: make one HTTP `POST /infer` attempt per service and frame. Send
  `image/jpeg`, the JPEG bytes (up to 2 MiB), `X-Frame-Id`, `X-Robot-Id`
  and `X-Vision-Id` (1 driving-perception, 2 traffic-rules, 3
  direction-recognition). The response confirms frame ID, service ID/name,
  byte count and SHA-256 in diagnostic mode. Only that exact receipt with
  `mock: true` counts as a successful test delivery. One explicitly enabled
  detector can instead return the [detector response](detector-response-contract.md). Keep frames in memory and record metadata
  only. Direct UDP and camera retries remain in the handoff diagnostics.
- Main Control and clients: runtime configuration and actual detector output
  must satisfy the separate [observation contract](observation-contract.md)
  before publication. Receipt diagnostics do not publish observations. The
  optional detector route publishes staff metadata. Neither mode exposes a
  preview or produces a passenger status, ride transition or vehicle command.

## Handoff provenance

The Vision team supplied a file drop without Git metadata or model weights.
These SHA-256 values identify the original inputs used in this integration.

| Handoff file | SHA-256 |
| --- | --- |
| `ros_camera.py` | `0d35650efa40397df5dd316bd3a80dc26142daef9a22a3ff03686455c0aaec6a` |
| `stream_camera.py` | `0e780c1ec13281acbaa06baea069fde071e5aa679ac3a5b2d927502bc548b91d` |
| `ros_ingress.py` | `0a612e8b9d77e547a8c0ca03f9f4981b797038adc4f1509e32e25217af677492` |
| `interface.py` | `da822109436f001447590ce721ec37a0ba0080700454826dd690e6f848a86292` |
| `vision.py` | `3e5df7043899e74d7c7e01f18f782ef0df41365ead4632c3ce66065173f7e333` |
| `compose.yaml` | `d02b4d39d9a9f808f96cd54a7e5ee14cb6d671778dc9c521b384d8d8b5ba174f` |

[Vision transport comparison](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/13697052) ·
[Vision ROS 2 trial](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/13828243) ·
[System Architecture](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/360590) ·
[Interface Specification](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8028663)
