# Pinky 카메라 송신기

Pinky 전방 카메라의 JPEG를 ROS 2 Jazzy로 발행합니다. `rpicam-vid` 촬영 설정은
640×480, 5 FPS, 180° 회전입니다. ROS 2 토픽은
`/amo/<robot-id>/camera/compressed`이고 QoS는 Best Effort, Keep Last 1입니다.
모터나 주행 제어 토픽에는 연결하지 않습니다.

Ubuntu 24.04에서 ROS 2 Jazzy와 `rpicam-vid`를 사용할 수 있어야 합니다.
카메라 패키지를 포함해 빌드한 뒤, 두 장비에 같은 DDS 도메인과 승인된 검색 범위를
외부 환경 설정으로 지정합니다. 수신기를 먼저 시작하고 차량에 할당한 로봇 ID를
명시합니다. 아래 명령은 실제 카메라에서 30장을 발행하고 종료합니다.

```bash
source /opt/ros/jazzy/setup.bash
workspace=$(mktemp -d)
colcon --log-base "$workspace/log" build --base-paths . \
  --build-base "$workspace/build" --install-base "$workspace/install"
source "$workspace/install/local_setup.bash"
ros2 run amo_camera_streamer camera_streamer --robot-id "$AMO_ROBOT_ID" --frames 30
```

AI Interface 실행 및 카메라 없는 재현 절차는
[AI Interface 안내](../../../../Server/AMOAIServer/AMOAIInterface/README.md)에 있습니다.
