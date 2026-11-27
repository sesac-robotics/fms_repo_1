# AMO AI Interface

Pinky 전방 카메라의 ROS 2 JPEG를 받아 Vision 세 곳으로 HTTP `/infer`를
호출합니다. 카메라별 대기 프레임을 한 장으로 제한하고 200ms 이상 대기한 프레임을
폐기합니다. 현재 실행 단계는 각 수신기가 같은 바이트를 받았는지 확인합니다.

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
