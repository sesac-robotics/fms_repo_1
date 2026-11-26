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
3. **신호등**: 펌웨어를 업로드합니다. 상태 LED(GPIO 4)가 켜지면 Agent에 연결된 것입니다.
4. **브리지**: `colcon build` 후 `ros2 run amode_signal_bridge signal_bridge`. 서버와 같은 `AMO_SIGNAL_INGEST_KEY`를 씁니다.
5. **FMS**: `GUI/MainControllerPC/AMOAdmin`에서 실행하고 운영자 계정으로 로그인한 뒤 왼쪽 메뉴의 **신호등**을 엽니다.

ROS 도메인 ID는 펌웨어(`config.h`)에서 16으로 정합니다. `ros2` 명령을 쓰는 터미널도 `export ROS_DOMAIN_ID=16`으로 맞춥니다.

## 4. 운영자 명령

`POST /api/signals/SIG-01/commands`에 `{"command": "..."}`를 보냅니다(관리자·운영자 세션). 명령은 `AUTO`, `HOLD NORTH_GREEN`, `HOLD EAST_GREEN`, `HOLD ALL_RED`, `PLAN <북녹> <동녹> <황> <전적>`(ms)입니다. FMS 화면은 조회 전용입니다. 자세한 계약은 [SignalBridge README](SignalBridge/README.md#main-control-api)에 있습니다.
