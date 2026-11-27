# SignalKit · 교차로 신호등 (SR-027)

ESP32 신호등을 micro-ROS로 관제 서버(Main Control)에 붙이고, FMS에서 상태를 봅니다. 이 문서는 **처음 받는 팀원이 준비할 것과 실행 순서**를 모은 안내서입니다. 자세한 내용은 각 폴더의 README를 봅니다.

```
ESP32 (LEDController) ──Wi-Fi UDP──▶ micro-ROS Agent ──ROS 2 (도메인 16)──▶ SignalBridge ──HTTP──▶ Main Control ──IF-03──▶ FMS
```

| 폴더 | 내용 |
| --- | --- |
| [SignalController/LEDController](SignalController/LEDController/README.md) | ESP32 펌웨어 (Arduino, micro-ROS) |
| [SignalBridge](SignalBridge/README.md) | ROS 2 토픽 ↔ Main Control 중계 노드, 서버 API 설명 |
| `third_party/` | 각자 받는 외부 라이브러리 (Git 제외) |

## 1. Git에 없어서 각자 준비하는 것

저장소를 받은 뒤 아래 항목은 직접 만들거나 내려받습니다. 모두 `.gitignore`에 들어 있어 커밋되지 않습니다.

| 항목 | 위치 | 준비 방법 |
| --- | --- | --- |
| micro_ros_arduino v2.0.8-jazzy | `Device/SignalKit/third_party/micro_ros_arduino/` | GitHub 릴리스 ZIP을 받아 풉니다. 주소와 SHA-256은 [펌웨어 README](SignalController/LEDController/README.md#준비)에 있습니다. 풀면 약 170 MB입니다 |
| Wi-Fi·Agent 설정 | `SignalController/LEDController/secrets.h` | `secrets.example.h`를 복사해 Wi-Fi 이름·비밀번호와 Agent PC의 IP를 넣습니다. ESP32는 2.4 GHz Wi-Fi만 씁니다 |
| 서버 비밀값 | 저장소 루트 `.env` | 루트 [README](../../README.md)의 항목에 더해 `AMO_SIGNAL_INGEST_KEY`를 넣습니다. 예: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |
| 빌드·실행 결과 | `build/`, `install/`, `log/`, `target/`, `.venv/` 등 | 빌드하면 다시 생깁니다 |

## 2. 저장소 밖에 설치하는 것

| 도구 | 버전 | 설치 |
| --- | --- | --- |
| ROS 2 | Jazzy | 팀 개발 환경 기준 |
| ESP32 보드 패키지 | **2.0.17** | Arduino IDE 보드 매니저, 또는 `arduino-cli core install esp32:esp32@2.0.17`. **3.x에서는 micro-ROS 타이밍이 깨집니다** |
| micro-ROS Agent | jazzy 이미지 | `docker pull microros/micro-ros-agent:jazzy` |
| Docker Compose | 서버 실행용 | 루트 README의 Ubuntu 실행 안내 |
| `libxcb-cursor0` | Ubuntu 패키지 | `sudo apt install libxcb-cursor0`. PyQt6 6.5 이상으로 FMS 창을 띄울 때 필요합니다 |

## 3. 실행 순서

1. **서버**: 저장소 루트에서 `.env`를 준비하고 `docker compose up --build -d`를 실행합니다. Main Control 내부 HTTP는 `127.0.0.1:18088`에 열립니다.
2. **Agent**: `docker run -it --rm --net=host microros/micro-ros-agent:jazzy udp4 --port 8888`
3. **신호등**: 보드마다 `AMO_BOARD`(1~4)를 정해 펌웨어를 업로드합니다([LEDController README](SignalController/LEDController/README.md)). 상태 LED(GPIO 4)가 켜지면 Agent에 연결된 것입니다.
4. **브리지**: `colcon build` 후 보드마다 하나씩 띄웁니다. 서버와 같은 `AMO_SIGNAL_INGEST_KEY`를 씁니다. 네 개를 한 터미널에서 띄우고 `Ctrl+C` 한 번으로 함께 끄려면 다음처럼 실행합니다.
   ```bash
   bash -c 'for n in 1 2 3 4; do ros2 run amode_signal_bridge signal_bridge --ros-args -r __node:=amo_signal_bridge_$n -p signal_namespace:=traffic_light_$n & done; wait'
   ```
5. **FMS**: `GUI/MainControllerPC/AMOAdmin`에서 실행하고 운영자 계정으로 로그인한 뒤 왼쪽 메뉴의 **신호등**을 엽니다.

ROS 도메인 ID는 펌웨어(`config.h`)에서 16으로 정합니다. `ros2` 명령을 쓰는 터미널도 `export ROS_DOMAIN_ID=16`으로 맞춥니다.

| 보드 | 신호 ID | 교차로 | a | b |
| --- | --- | --- | --- | --- |
| 1 | SIG-01 | 중앙 +자 | 남→북 | 서→동 직좌 |
| 2 | SIG-02 | 중앙 +자 | 북→남 | 동→서 직좌 |
| 3 | SIG-03 | 북쪽 T자 | 보행자(횡단보도 동쪽 끝) | 서→동 |
| 4 | SIG-04 | 북쪽 T자 | 보행자(횡단보도 서쪽 끝) | 동→서 |

### 서버 없이 켰을 때

- 신호등은 서버나 Agent가 없어도 혼자 기본 계획으로 돕니다. 연결이 끊겨도 바뀌지 않습니다.
- 다만 같은 교차로의 보드(1·2번, 3·4번)는 **Agent 시계를 한 번은 받아야** 박자를 맞출 수 있습니다. 시계를 받기 전에는 전방향 적색으로 기다립니다. 한 번 받은 뒤에는 연결이 끊겨도 계속 같은 박자로 돕니다.
- Agent에 연결되면 시계를 받고, 주기 경계(+자 45초, T자 30초)까지 기다렸다가 시작합니다. 켜자마자 한동안 적색인 건 정상입니다.

### 다른 PC의 서버로 옮길 때

1. 그 PC에서 이 브랜치를 받고 `docker compose up --build -d`로 서버를 빌드합니다. V24 마이그레이션이 들어간 서버라야 숫자 6개 `PLAN`을 받습니다.
2. 그 PC에서 Agent(UDP 8888)와 브리지 네 개를 띄웁니다. 브리지 터미널은 `ROS_DOMAIN_ID=16`입니다.
3. `secrets.h`의 `AMO_AGENT_IP`를 그 PC의 IP로 바꿉니다. PC IP는 `hostname -I`로 확인합니다. 보드는 같은 Wi-Fi에 있어야 합니다.
4. 보드마다 `AMO_BOARD`를 맞춰 다시 업로드합니다. IP는 펌웨어에 들어가므로, 바꾸면 네 보드를 모두 다시 올려야 합니다.
5. 시리얼 모니터(115200)에 `agent connected`와 `agent clock received`가 찍히면 연결된 것입니다.

## 4. 운영자 명령

`POST /api/signals/SIG-01/commands`에 `{"command": "..."}`를 보냅니다(관리자·운영자 세션). 명령은 `AUTO`, `HOLD NORTH_GREEN`, `HOLD EAST_GREEN`, `HOLD ALL_RED`, `PLAN <북녹> <동녹> <황> <전적>` 또는 동서 황색과 상대 보드 동서 시간까지 넣는 숫자 6개 형식(ms)입니다. FMS의 신호등 페이지에서도 신호 시간(`PLAN`)을 바꿀 수 있습니다. 모니터 지도 가운데 교차로를 누르면 그 페이지로 넘어갑니다. 자세한 계약은 [SignalBridge README](SignalBridge/README.md#main-control-api)에 있습니다.
