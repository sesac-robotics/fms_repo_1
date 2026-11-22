# Repository architecture

The team repository follows the execution boundaries in the hardware and software architecture drawings.

| Path | Responsibility |
| --- | --- |
| `apps/admin/` | Fleet monitoring and operator commands. |
| `services/main_control/` | Call intake, dispatch, vehicle availability, service state, command tracking, and database access. |
| `services/web_service/` | Browser-facing call and trip status flows. The mobile delivery format is a team decision. |
| `services/vision/` | Receive vehicle images, run perception, and report results to Main Control. |
| `ros2_ws/src/amode_driving/` | Vehicle motion, localization, actuator coordination, and local stop decisions. |
| `ros2_ws/src/amode_depot/` | ROS 2 integration for parking and charging stations. |
| `devices/` | Vehicle camera streaming, station and signal firmware, and cargo coupling hardware. |
| `maps/` | Team-reviewed maps and route data used by dispatch and driving. |
| `database/migrations/` | Versioned migrations for the approved database schema. |
| `tests/integration/` | End-to-end checks across the application, services, and ROS 2 boundaries. |

Main Control keeps domain rules in `src/domain/`, use cases in `src/application/`, and database and transport adapters in `src/adapters/`. Operator and user applications obtain fleet data through service interfaces.

Keep ROS 2 manifests and executable launch files alongside their implemented packages. Put per-vehicle and site configuration under the package that consumes it. Share real map revisions through `maps/`.

The first integration test covers a one-way call through dispatch, a simulated vehicle command and result, persisted history, and readback in the admin app. Include a disconnect case and verify that reconnection does not replay the old command.

[System Architecture](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/360590/System+Architecture) · [System Requirements](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/557330/System+Requirements+SR) · [Data Structure](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/557347/Data+Structure+ERD+Class+Diagram)
