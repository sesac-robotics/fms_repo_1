# AMO AI Interface

Pinky 전방 카메라의 ROS 2 JPEG를 받아 Vision 세 곳으로 HTTP `/infer`를
호출합니다. 카메라별 대기 프레임을 한 장으로 제한하고 200ms 이상 대기한 프레임을
폐기합니다. 기본 진단 실행은 각 수신기가 같은 바이트를 받았는지 확인합니다.

[카메라 전송 계약](camera-transport-contract.md) · [Main Control 판정 전달 계약](observation-contract.md)

## 로컬 모의 재현

저장소 루트에서 Ubuntu 24.04, Python 3.12, ROS 2 Jazzy 환경을 사용합니다.
시험은 임시 카메라 입력을 사용하고 외부 장비, classroom DB, 원격 서비스에
접속하지 않습니다. 빌드·로그·카메라 입력은 저장소 밖의 임시 경로를 사용합니다.

```bash
source /opt/ros/jazzy/setup.bash
export PYTHONDONTWRITEBYTECODE=1
workspace=$(mktemp -d)
colcon --log-base "$workspace/log" build \
  --base-paths Device/AMOVehicle/AmoControlBoard/CameraStreamer Server/AMOAIServer/AMOAIInterface \
  --build-base "$workspace/build" --install-base "$workspace/install"
source "$workspace/install/local_setup.bash"
export PYTHONPATH="$PWD/Server/AMOAIServer/Vision:${PYTHONPATH:-}"
python3 -m unittest discover -s tests/integration/vision -p 'test_*.py' -v
python3 tests/integration/vision/verify_vision_ros.py
```

## 실제 카메라 수신 시험

먼저 [Vision 수신 확인 서비스](../Vision/README.md) 세 개를 로컬에서 실행합니다.
차량과 수신기 양쪽에서 같은 DDS 도메인과 승인된 검색 범위를 지정합니다.
아래 예시에서는 수신기가 실행되는 컴퓨터의 루프백 포트만 사용하며,
`AMO_ROBOT_ID`에는 시험 차량에 설정한 ID를 넣습니다.

```bash
ros2 run amo_ai_interface ai_interface --robot-id "$AMO_ROBOT_ID" \
  --driving-perception-url http://127.0.0.1:18101/infer \
  --traffic-rules-url http://127.0.0.1:18102/infer \
  --direction-recognition-url http://127.0.0.1:18103/infer
```

그다음 [Pinky 카메라 송신기](../../../Device/AMOVehicle/AmoControlBoard/CameraStreamer/README.md)를 실행합니다.
`camera_frame_sent`, `camera_frame_received`, `camera_frame_dropped`와
`vision_receipts`의 `confirmed=3/3` 건수를 각각 기록합니다.
기존 UDP 5000 비교는 [Vision 팀 수신 비교 자료](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/13697052)의
독립 시험 경로를 사용합니다.

## 실제 판정 관제 연동

[Vision 응답 계약](detector-response-contract.md)에 맞춰 실제 판정기 한 종류를
실행합니다. 수신 확인 서비스의 `mock: true` 응답은 관제 판정으로 저장되지 않습니다.
예를 들어 교통규칙 판정기를 먼저 연결하려면 다음과 같이 실행합니다. 로봇 ID와
차량 번호는 서로 다른 값이므로 AMO에 등록된 차량과 정확히 매핑합니다.

```bash
export AMO_VISION_KEY_FILE=/path/outside/git/vision.key
ros2 run amo_ai_interface ai_interface --robot-id "$AMO_ROBOT_ID" \
  --detector-service traffic-rules --traffic-rules-url "$AMO_DETECTOR_URL" \
  --vehicle-map "$AMO_ROBOT_ID=$AMO_VEHICLE_NO" \
  --main-control-url "http://127.0.0.1:$AMO_VISION_MAIN_PORT/internal/vision/observations"
```

AI Interface에는 Main Control의 내부 포트와 동일한 전송 키를 지정합니다. 기존 관제·DB 연결을
사용하며 관제 전송이 성공하면 `vision_observation_acknowledged` 로그가 남습니다.
운영 조회와 화면에서 같은 차량, 출처, 결과 및 프레임 ID가 보이는지 확인합니다.
출발 승인, 주행 명령, 승객용 결과는 이 관제 연동으로 생성되지 않습니다.

### Compose로 함께 실행

`docker/vision.compose.yaml`은 기본 Compose에 추가하는 선택 구성입니다.
실제 실행 전 IF-07의 ROS 2 표기와 팀 설정을 확인합니다. 운영 데이터베이스나
교실 서비스를 바꾸지 않고 검증하려면 별도 개발 환경을 사용합니다.

기존 Compose 설정에 다음 값을 추가합니다. 실제 키와 장비 주소는 저장소 밖의
설정에 보관합니다.

| 설정 | 입력 값 |
| --- | --- |
| `AMO_VISION_MAIN_PORT` | 비어 있는 Main Control 내부 HTTP 포트 |
| `AMO_VISION_INGEST_KEY` | 32자 이상의 전용 키. 두 서비스의 시크릿 파일로 전달 |
| `AMO_VISION_ROS_DOMAIN_ID` | Pinky와 같은 ROS 2 도메인 번호 |
| `AMO_VISION_ROS_DISCOVERY_RANGE` | 개발 기본값 `LOCALHOST`. 실차 시험은 승인된 검색 범위를 설정 |
| `AMO_VISION_ROS_STATIC_PEERS` | 팀 구성에 필요한 경우에만 지정하는 DDS 상대 주소 |
| `AMO_VISION_ROBOT_ID`, `AMO_VISION_VEHICLE_NO` | 시험 Pinky 로봇 ID와 해당 AMO 차량 번호 |
| `AMO_VISION_SERVICE`, `AMO_VISION_DETECTOR_URL` | 판정기 이름과 이미 실행 중인 검증된 HTTP `/infer` 주소 |

먼저 프로젝트, 외부 DB, 포트 및 차량 설정을 확인한 뒤 구성을 검사합니다.

```bash
docker compose -f compose.yaml -f docker/vision.compose.yaml config --quiet
```

검증용 프로젝트에서 판정기를 먼저 실행한 뒤 같은 Compose 명령에
`up -d --build main-control ai-interface`를 사용합니다. 강의실은 기존 실행 구성과
같은 프로젝트에 적용하고, 기존 데이터베이스와 로그인 설정을 유지합니다.

## 로컬 FMS 가림 영상 시험

시험용으로만 기존 AI Interface 실행 명령에 아래 옵션을 추가합니다.
시스템 Python에서 OpenCV와 NumPy를 불러올 수 있어야 합니다. 노트북에서
`preview_dir=$(mktemp -d)`로 현재 사용자 전용 폴더를 만들고, 송신기와
같은 로봇 ID를 지정합니다. 예시는 00001 시험에 한정한 차량 지정입니다.

```bash
--local-preview-directory "$preview_dir" --local-preview-map pinky_example=PINKY-01
```

AI Interface는 16×12칸, 네 단계 밝기의 회색 전체 화면 모자이크만
차량별 최신 파일에 씁니다. 원본 JPEG는 미리보기 파일에 저장하지 않습니다.
이 시험은 실차 영상 연결을 확인하며 운영용 얼굴 가림 성능 검증과 배포는 별도입니다.
