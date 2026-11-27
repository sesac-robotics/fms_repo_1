# AMO Vision

차량 내부 카메라 영상은 승객의 탑승을 안면 인식으로 확인하는 데 사용합니다. 모자이크가 얼굴 특징을 가리면 인식할 수 없으므로 인식 입력에는 모자이크를 적용하지 않습니다. 관제 화면에 표시하는 영상은 별도의 처리 경로에서 관리합니다. 현재 저장소에는 실제 안면 인식과 차량 카메라 연동 구현이 없습니다.

[AMO 회의 결정표](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/database/11763726)

## 전방 카메라 수신 확인

`receipt_stub.py`는 이미지 바이트 수, SHA-256, 프레임 ID와 `mock: true`를
돌려주는 로컬 시험 수신기입니다. 실제 판정은 별도 Vision 모델과 실행 계약이 필요합니다.
수신 확인은 Main Control의 판정 저장이나 차량 상태 전이에 사용하지 않습니다.

아래 명령을 저장소 루트에서 각각 별도의 터미널로 실행합니다.
서비스는 IPv4 루프백에만 바인딩하며 포트는 실행 시 지정합니다.

```bash
python3 -B Server/AMOAIServer/Vision/receipt_stub.py --vision-id 1 --port 18101
python3 -B Server/AMOAIServer/Vision/receipt_stub.py --vision-id 2 --port 18102
python3 -B Server/AMOAIServer/Vision/receipt_stub.py --vision-id 3 --port 18103
```

[AI Interface와 모의 재현](../AMOAIInterface/README.md)
