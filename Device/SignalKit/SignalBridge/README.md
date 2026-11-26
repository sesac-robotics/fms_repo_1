# SignalKit Bridge (ROS 2 ↔ Main Control)

신호등(ESP32)의 ROS 2 토픽과 Main Control의 HTTP API를 연결하는 노드입니다. Main Control은 ROS 2를 모르고, 신호등은 HTTP를 모릅니다. 이 노드가 그 사이에서 중계합니다.

```
ESP32 ──micro-ROS──▶ Agent ──DDS──▶ amode_signal_bridge ──HTTP──▶ Main Control ◀── FMS·Admin (IF-02/03)
```

- `/traffic_light_1/state`(JSON)를 받아 0.5초마다 `POST /internal/signals/state`로 보냅니다.
- 같은 주기로 `GET /internal/signals/SIG-01/commands`를 호출해, 운영자가 넣은 명령을 꺼내 `/traffic_light_1/cmd`로 발행합니다.
- 신호등은 처리한 마지막 명령을 `lastCommand`로 다시 보고합니다. 2초 안에 확인되지 않으면 같은 명령을 다시 보내고, 10초(총 5번) 안에 확인되지 않으면 오류를 기록하고 포기합니다. 그때는 운영자가 명령을 다시 보내야 합니다. 명령은 같은 것을 여러 번 받아도 결과가 같으므로 재전송해도 안전합니다.
- Main Control에 연결되지 않으면 오류를 한 번만 기록하고 계속 재시도합니다. 신호등은 서버와 상관없이 계속 동작합니다.
- HTTP 호출(요청당 최대 1초)은 작업 스레드 하나에서 실행하므로 ROS 콜백이 네트워크를 기다리지 않습니다. 이전 호출이 끝나지 않았으면 그 주기는 건너뜁니다.

## 구성

| 모듈 | 역할 |
| --- | --- |
| `confirmation.py` | 명령 확인·재전송 규칙 (I/O 없음, 단위 테스트) |
| `control_client.py` | Main Control 내부 API HTTP 어댑터 (표준 라이브러리만 사용) |
| `state_document.py` | 상태 메시지 JSON 해석 |
| `bridge_node.py` | ROS 2 노드: 토픽·파라미터·타이머와 작업 스레드 연결 |

| 토픽 | 방향 | 타입 | QoS |
| --- | --- | --- | --- |
| `/<signal_namespace>/state` | 구독 | `std_msgs/String` (JSON) | Best effort, depth 5 |
| `/<signal_namespace>/cmd` | 발행 | `std_msgs/String` (명령 문자열) | Reliable, depth 10 |

파라미터: `signal_namespace`(기본 `traffic_light_1`), `period_s`(0.1~5.0초, 기본 0.5). 범위를 벗어나면 노드가 시작하지 않습니다.

## 빌드와 실행

ROS 2 Jazzy의 ament_python 패키지입니다(`rclpy`, `std_msgs`, Python 표준 라이브러리). Main Control과 같은 PC에서 실행합니다. Main Control의 내부 HTTP는 루프백(127.0.0.1)에서만 열립니다.

```bash
source /opt/ros/jazzy/setup.bash
colcon build --base-paths Device/SignalKit/SignalBridge
source install/setup.bash
export ROS_DOMAIN_ID=16
export AMO_SIGNAL_INGEST_KEY='<Main Control과 같은 32자 이상 키>'
export AMO_CONTROL_URL=http://127.0.0.1:18088
ros2 run amode_signal_bridge signal_bridge
```

다른 신호등을 중계할 때는 `--ros-args -p signal_namespace:=traffic_light_2`를 붙입니다. 저장소 루트에서 빌드하면 생기는 `build/`, `install/`, `log/`는 Git에서 제외됩니다.

## 검사

```bash
ruff check Device/SignalKit/SignalBridge && ruff format --check Device/SignalKit/SignalBridge
colcon test --base-paths Device/SignalKit/SignalBridge && colcon test-result --verbose
```

Ruff 0.14.4(설정 `ruff.toml`)와 pytest를 씁니다.

Main Control 쪽에는 같은 키를 `AMO_SIGNAL_INGEST_KEY`로, 고정 포트를 `AMO_CONTROL_HTTP_PORT=18088`로 설정합니다. `compose.yaml`은 포트를 환경변수로, 키를 `.env`에서 읽은 Compose 시크릿으로 넘겨줍니다. 키를 비워 두면 `/internal/signals/**`는 모두 거부됩니다.

## Main Control API

| 메서드 · 경로 | 호출자 | 인증 | 내용 |
| --- | --- | --- | --- |
| `POST /internal/signals/state` | 브리지 | `X-AMO-Signal-Key` | 펌웨어 상태 JSON을 그대로 보냅니다. `204`로 응답하며 신호별 최신값 1건을 저장합니다. 형식이 틀리면 `400 INVALID_SIGNAL_STATE` |
| `GET /internal/signals/{signalId}/commands` | 브리지 | `X-AMO-Signal-Key` | 아직 전달하지 않은 명령을 순서대로 돌려주고 전달됨으로 표시합니다. `[{"id":1,"signalId":"SIG-01","command":"AUTO"}]` |
| `POST /api/signals/{signalId}/commands` | 관리자·운영자 | 직원 세션 | `{"command":"PLAN 15000 8000 3000 2000"}` 형식입니다. 응답은 `202 {"id":N}`. 알 수 없거나 안전 범위를 벗어난 명령은 `400 INVALID_SIGNAL_COMMAND`, 한 번도 보고하지 않은 신호등은 `404 SIGNAL_NOT_FOUND` |
| `GET /api/operations` | 관리자·운영자 | 직원 세션 | 기존 응답에 `signals` 배열이 추가됩니다. 원소는 `{state, receivedAt}` 형식입니다 |

- 명령은 펌웨어와 같습니다: `AUTO` · `HOLD NORTH_GREEN` · `HOLD EAST_GREEN` · `HOLD ALL_RED` · `PLAN <북녹> <동녹> <황> <전적>`(ms). 서버가 펌웨어와 같은 안전 범위(녹색 3~120초, 황색 2~10초, 전적색 1~10초)로 먼저 검사합니다.
- `signalId`는 대문자·숫자·하이픈 1~32자입니다(예: `SIG-01`).
- 직원 명령은 IF-02(Web 게이트웨이)로도 전달됩니다. FMS의 IF-03 포트는 기존처럼 조회 전용입니다.
- DB: `V23__traffic_signals.sql`이 `signal_latest`(신호별 최신 상태)와 `signal_commands`(명령 대기열, 요청자와 시각 기록)를 만듭니다.

## 검증 (2026-11-26, 이 브랜치로 빌드한 로컬 Docker 스택 + ESP32)

- 운영자 계정으로 `PLAN 6000 6000 2000 1000`, `HOLD NORTH_GREEN`, 그리고 연속 명령 `AUTO` → `PLAN 10000 10000 3000 2000`을 보내면 순서대로 신호등에 적용되고, `/api/operations`의 `signals`에 `ACCEPTED`로 반영됩니다.
- 범위를 벗어난 `PLAN`은 `400`, 보고한 적 없는 `SIG-99`는 `404`로 거부됩니다.
- ESP32는 Agent가 다시 켜진 뒤 1~2초 안에 재접속합니다. Agent를 4초와 6초 끊은 동안 보낸 `HOLD EAST_GREEN`은 브리지가 다시 보내서 재접속 뒤에 적용됩니다. 확인 대기 시간을 6초(3번)로 두었을 때는 4초 끊김에서 명령을 놓쳐서 10초(5번)로 늘렸습니다.

## 아직 안 된 것

- FMS(PyQt)와 관리자 Web 화면에 신호등 표시와 조작 버튼을 넣는 일. 지금은 API와 `/api/operations` 응답까지만 있습니다.
- 교차로 진입 허가 로직(`tests/integration/one_way_operations.py`의 `green`)을 실제 `signals` 상태와 연결하는 일.
- 신호등이 여러 대일 때 브리지 하나로 여러 네임스페이스를 중계하는 기능.
