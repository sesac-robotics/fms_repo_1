# Main Control and vehicle

Main Control coordinates trip and operator commands. The Driving Controller executes movement and makes local stop decisions. The software architecture connects them over ROS 2.

- Correlate each command and result with the vehicle, trip, and command identifiers.
- Report command receipt, rejection, completion, and failure as distinct outcomes. Attach the reason when available.
- Report pose, speed, battery, stop cause, and connection state with agreed units, coordinate frames, and source timestamps.
- On control-link loss, the vehicle stops locally. Reconnection does not replay earlier commands.

Confirm the ROS 2 message or action types, namespace rules, QoS, timeouts, and the evidence used to confirm a physical stop before the first integration test.

[Software Architecture](https://drive.google.com/file/d/1RhWCWb6gsMU9gWiC0s1vAgbAXr6wrRPA/view) · [System Requirements SR-023 and SR-030–032](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/557330/System+Requirements+SR)
