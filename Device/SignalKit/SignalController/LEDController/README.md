# SignalKit LEDController (ESP32 · micro-ROS)

교차로 한 곳의 신호등입니다. ESP32가 북쪽·동쪽 두 방향의 적·황·녹 LED를 고정 신호 계획대로 돌립니다. 현재 신호 상태는 micro-ROS로 관제 PC에 보고합니다. 관제는 토픽 명령으로 특정 신호를 유지(HOLD)하라고 요청할 수 있습니다.

- 신호는 **항상 ESP32 안에서 돌아갑니다.** 네트워크가 끊겨도 꺼지지 않습니다.
- 수동 유지(HOLD) 중에 에이전트와의 연결이 5초 넘게 끊기면 고정 계획(AUTO)으로 돌아갑니다.
- 단계 이름은 `experiments/deepfleet`의 `NORTH_GREEN`·`EAST_GREEN`·`ALL_RED`를 따릅니다. 실물 신호용으로 `NORTH_YELLOW`·`EAST_YELLOW`를 추가했습니다. 황색과 전적색에서는 새로 진입할 수 없습니다.

## 신호 계획

`NORTH_GREEN 10s → NORTH_YELLOW 3s → ALL_RED 2s → EAST_GREEN 10s → EAST_YELLOW 3s → ALL_RED 2s` 순서로 반복합니다. 전원을 켜면 항상 `ALL_RED`에서 시작합니다. 시간은 `config.h`에서 바꿉니다.

녹색을 바꾸는 HOLD 명령이 오면 현재 녹색을 바로 끊지 않습니다. 황색과 전적색을 거친 뒤 목표 녹색으로 넘어갑니다.

## 배선

**벤치 테스트**: 적·황·녹 신호등 모듈 하나를 GPIO 25·26·27에 연결하면 북쪽 방향이 표시됩니다(기본값, `AMO_RGB_TEST 0`). 동쪽 핀은 비워 둬도 됩니다. RGB LED 하나로 시험하려면 `AMO_RGB_TEST`를 1로 바꿉니다. 이때 R=25·G=26·B=27이고, 황색은 R+G로 표시합니다. 공통 애노드 LED라면 `AMO_RGB_COMMON_ANODE`를 1로 바꿉니다.

| 신호 | GPIO | | 신호 | GPIO |
| --- | --- | --- | --- | --- |
| 북 적 | 25 | | 동 적 | 32 |
| 북 황 | 26 | | 동 황 | 33 |
| 북 녹 | 27 | | 동 녹 | 14 |
| 연결 상태 LED | 4 | | | |

LED마다 220~330 Ω 저항을 직렬로 연결하고 GND에 물립니다(HIGH = 켜짐). 핀은 `config.h`에서 바꿉니다. 부팅에 쓰이는 0·2·12·15번 핀은 피하세요.

## 준비

1. Arduino IDE에 **ESP32 보드 패키지(Espressif) 2.0.17**을 설치합니다. **3.x는 쓰지 마세요.** 3.x에서도 빌드와 연결은 되지만, micro-ROS 미리 빌드본은 32비트 `time_t` 기준이라 내부 시계가 1초 단위로만 움직입니다. 그러면 루프가 매번 약 1초씩 멈추고, 상태 발행과 신호 전환이 최대 1초 늦어집니다(2026-11-26 보드 실측).
2. **micro_ros_arduino v2.0.8-jazzy**를 `Device/SignalKit/third_party/micro_ros_arduino/`에 풉니다. 이 폴더는 Git에서 제외되므로 각자 받습니다. Arduino IDE를 쓴다면 같은 ZIP을 *스케치 → 라이브러리 포함하기 → .ZIP 라이브러리 추가*로도 설치합니다.

   ```bash
   cd Device/SignalKit && mkdir -p third_party && cd third_party
   curl -L -o micro_ros_arduino.zip https://github.com/micro-ROS/micro_ros_arduino/archive/refs/tags/v2.0.8-jazzy.zip
   sha256sum micro_ros_arduino.zip   # f24757f032318c1d1baac2566a668c353d5edbf210319f2f51652569f5fb01f2
   unzip -q micro_ros_arduino.zip && mv micro_ros_arduino-2.0.8-jazzy micro_ros_arduino
   ```

3. `secrets.example.h`를 `secrets.h`로 복사해 Wi-Fi와 에이전트 PC의 IP를 넣습니다. `secrets.h`는 Git에 올라가지 않습니다.
4. 신호등이 여러 대라면 `config.h`의 `AMO_SIGNAL_ID`와 네임스페이스(`traffic_light_1`, `traffic_light_2` …)를 기기마다 다르게 정합니다.
5. 빌드와 업로드는 `sketch.yaml`의 `esp32dev` 프로필로 합니다(FQBN `esp32:esp32:esp32`, 코어 2.0.17, 위 라이브러리). Arduino IDE에서는 보드 *ESP32 Dev Module*을 고르면 됩니다. 시리얼 모니터는 115200 baud입니다.

   ```bash
   arduino-cli compile --profile esp32dev --warnings all .
   arduino-cli upload --profile esp32dev -p /dev/ttyUSB0 .
   ```

## 호스트 테스트

신호 순서와 명령 규칙(`signal_plan.*`, `signal_command.*`, `signal_timing.h`)은 보드 없이 PC에서 시험합니다. `test/` 폴더는 펌웨어 빌드에 포함되지 않습니다.

```bash
./test/run_host_tests.sh
```

## 블로킹과 타이밍

- 신호 전환은 `millis()` 경과 시간으로 진행하고 `loop()`는 5 ms마다 돕니다. Wi-Fi 연결은 기다리지 않고 진행되므로, 접속 전에도 신호는 정상적으로 돕니다.
- micro-ROS 호출은 아래 시간만큼 `loop()`를 막을 수 있고, 그동안 램프는 현재 상태를 유지합니다: Agent 핑은 시도당 최대 100 ms(연결 중 3회), 재접속 직후 엔티티 생성은 엔티티당 최대 약 1초.
- 코어 3.x에서는 micro-ROS 내부 시계 문제로 매 루프가 약 1초씩 막힙니다. 반드시 2.0.17을 씁니다.

## 에이전트 실행 (관제 PC)

```bash
docker run -it --rm --net=host microros/micro-ros-agent:jazzy udp4 --port 8888
```

ROS 도메인 ID는 **ESP32 펌웨어에서** 정합니다(`config.h`의 `AMO_ROS_DOMAIN_ID`, 현재 16). 확인하는 PC의 터미널도 `export ROS_DOMAIN_ID=16`으로 맞춥니다.

에이전트에 연결되면 GPIO 4의 상태 LED가 켜지고, 시리얼에 `agent connected`가 찍힙니다.

## 토픽 계약

| 방향 | 토픽 | 타입 | 내용 |
| --- | --- | --- | --- |
| ESP32 → 관제 | `/traffic_light_1/state` | `std_msgs/msg/String` | 아래 JSON. 단계가 바뀔 때마다, 그리고 0.5초마다. **Best-effort** QoS |
| 관제 → ESP32 | `/traffic_light_1/cmd` | `std_msgs/msg/String` | `AUTO` · `HOLD NORTH_GREEN` · `HOLD EAST_GREEN` · `HOLD ALL_RED` · `PLAN …`. Reliable QoS |

```json
{"signalId":"SIG-01","seq":42,"phase":"NORTH_GREEN","mode":"AUTO","holdTarget":null,
 "remainingMs":7300,"uptimeMs":123456,"planMs":[10000,10000,3000,2000],"planPending":false,
 "lastCommand":"","commandResult":"NONE"}
```

### 신호 시간 바꾸기: `PLAN`

`PLAN <북쪽 녹색> <동쪽 녹색> <황색> <전적색>` 형식이고 단위는 ms입니다. 예: `PLAN 15000 8000 3000 2000`

- 지금 켜져 있는 단계는 원래 길이대로 끝나고, **다음 단계부터** 새 시간이 적용됩니다. 그 사이에는 `planPending`이 `true`입니다.
- 안전 범위(`config.h`)를 벗어나면 `REJECTED`로 응답하고 기존 시간을 유지합니다. 녹색 3~120초, 황색 2~10초, 전적색 1~10초입니다. 숫자가 4개가 아니거나 뒤에 다른 글자가 붙어도 거부합니다.
- `planMs`는 다음 단계부터 쓸 시간입니다. 재부팅하면 `config.h`의 기본값으로 돌아갑니다.

- `seq`는 재부팅하면 1부터 다시 셉니다. `uptimeMs`가 줄어들면 재부팅으로 봅니다.
- `remainingMs`는 다음 단계까지 남은 시간입니다. HOLD로 멈춰 있으면 `0`입니다.
- `commandResult`는 `NONE`·`ACCEPTED`·`REJECTED`·`FALLBACK_AUTO`(연결이 끊겨 HOLD를 풀었음) 중 하나입니다.
- 시각은 ESP32 부팅 기준입니다. 실제 시각은 받는 쪽에서 수신 시각으로 기록합니다.

## 동작 확인

```bash
ros2 topic echo /traffic_light_1/state
```

```bash
ros2 topic pub --once /traffic_light_1/cmd std_msgs/msg/String "{data: 'HOLD EAST_GREEN'}"
```

```bash
ros2 topic pub --once /traffic_light_1/cmd std_msgs/msg/String "{data: 'AUTO'}"
```

```bash
ros2 topic pub --once /traffic_light_1/cmd std_msgs/msg/String "{data: 'PLAN 15000 8000 3000 2000'}"
```

## 파일 구성

| 파일 | 역할 |
| --- | --- |
| `LEDController.ino` | `setup()`·`loop()` 조율, 명령 적용, 상태 JSON, 연결 끊김 시 복귀 |
| `signal_plan.*` | 단계 순서 상태 머신 (하드웨어·ROS 의존 없음) |
| `signal_command.*` | 명령 문자열 해석과 검증 (Main Control과 같은 문법·범위) |
| `signal_timing.h` | 기본 신호 시간과 `PLAN` 안전 범위 |
| `test/` | 호스트 테스트 |
| `led_output.*` | LED 출력. 한쪽을 적색으로 먼저 바꾼 뒤 다른 쪽을 엽니다 |
| `ros_link.*` | Wi-Fi UDP micro-ROS 연결, 에이전트 재접속 상태 머신 |
| `config.h` | 핀, ID, 토픽, 도메인, 연결 설정 |
| `sketch.yaml` | arduino-cli 빌드 프로필 |

이름 규칙은 Arduino 스타일을 따릅니다: 함수는 camelCase, 상수는 UPPER_CASE, 타입은 PascalCase.

## 보드 검증 결과 (2026-11-26, ESP32 Dev Module, 코어 2.0.17)

- 도메인 16에서 `/traffic_light_1/state`가 약 2 Hz로 들어옵니다. 단계 시간 오차는 10 ms 이내입니다.
- `HOLD EAST_GREEN`·`HOLD NORTH_GREEN`은 황색과 전적색을 거쳐 유지됩니다. 알 수 없는 명령은 `REJECTED`로 응답하고, `AUTO`를 보내면 고정 계획으로 돌아갑니다.
- `PLAN 5000 5000 2000 1000`을 보내면 다음 단계부터 녹색 5.0초, 황색 2.0초, 전적색 1.0초로 돕니다(측정 오차 10 ms 이내). 범위를 벗어난 `PLAN 1000 …`은 `REJECTED`로 응답합니다.
- 명령 해석을 모듈로 분리한 뒤(2026-11-26) 다시 시험했습니다: `PLAN 6000 6000 2000 1000`은 적용되고, 7자리 숫자가 들어간 `PLAN 0006000 …`은 `REJECTED`로 응답합니다.
- HOLD 중에 Agent를 끄면 5초 뒤 `FALLBACK_AUTO`로 고정 계획에 복귀합니다. Agent를 다시 켜면 자동으로 재접속합니다.

## 아직 안 된 것

- **화면 조작**: 토픽은 [SignalBridge](../../SignalBridge/README.md)가 Main Control로 중계합니다. FMS는 조회만 하고, 버튼으로 명령을 보내는 화면은 아직 없습니다.
- 교차로 진입 허가 로직(`tests/integration/one_way_operations.py`의 `green`)을 실제 신호 상태와 연결하는 작업.
- 6등식(LED 6개) 배선 검증. 지금까지는 신호등 모듈 하나로 북쪽 방향만 확인했습니다.
