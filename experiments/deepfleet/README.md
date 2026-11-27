# 교차로 혼잡 예측 실험

확정 도면 중앙 교차로 한 곳에서 모의 차량 4대를 실행합니다. 10초와 30초 뒤의 대기 차량 수와 다음 허가까지 남은 시간을 예측합니다. [DeepFleet 검토안](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/12681362/DeepFleet) · [인터페이스 명세](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8028663)

## 실행과 FMS 확인

저장소 루트에서 실행합니다. 출력 경로는 새 디렉터리여야 합니다.

```sh
uv run --locked --project experiments/deepfleet amo-deepfleet --output /tmp/amo-pilot-01
```

| 출력 | 내용 |
| --- | --- |
| `training.parquet` | 실행 ID, 학습·평가 구분, 관측값과 비교 기준이 담긴 학습 데이터 |
| `report.json` | 분리된 실행 시드, 예측 시간별 평균 절대 오차(MAE), 모델 계수 |
| `forecast.json` | 평가용 첫 실행에서 FMS에 표시할 예측·기준·관측 기록 |

기존 FMS 실행 환경에서 파일 경로를 지정합니다. 로그인 후 왼쪽 **혼잡 예측 실험**에서 시간 슬라이더를 옮겨 수치와 확정 도면의 교차로 표시를 확인합니다. 파일의 SHA-256 기준 지도와 FMS 지도가 일치해야 합니다.

```sh
AMO_CONGESTION_FORECAST_FILE=/tmp/amo-pilot-01/forecast.json \
  uv run --locked --project GUI/MainControllerPC/AMOAdmin amo-fms
```

## 원본 로그 저장

실험 DB 연결이 준비되면 해당 접속 정보를 `AMO_LEARNING_DSN`에 설정하고 `--postgres`를 붙입니다. 기본 실행은 파일만 반환합니다. PostgreSQL 쓰기는 `amo_learning`에 한정되고, 한 실험의 실행·표본·이벤트가 함께 커밋됩니다. 접속 값은 환경에만 두고 출력 디렉터리는 저장소 밖에 둡니다.

```sh
uv run --locked --project experiments/deepfleet amo-deepfleet --output /tmp/amo-pilot-02 --postgres
```

- 실행마다 시드, 수요 수준, 신호 계획과 모의 정책 버전을 저장합니다. 위치·목표·적재와 대기 사유, 신호·출구 상태, 요청·허가·진입·완전 이탈을 연결합니다. 시간은 실행 시작이 0인 100 ms 틱이고, 이벤트 구간은 시작을 포함하고 종료를 제외합니다.
- 도로 그래프 `confirmed-pilot-v1`은 도면에 맞춘 모의 좌표입니다. 원점은 도면 좌상단이며 800×730 기준 도면의 1픽셀을 0.003 모의 미터로 환산했습니다. 지점 ID는 간선의 끝점일 때만 저장합니다. 자유 주행·물리적 차간거리·현장 좌표 변환은 이 시험에서 검증하지 않습니다.
- 관측 정답의 대기시간은 예측 대상 시점에 대기 중인 차량 가운데 다음 진입 허가까지의 시간입니다. 빈 대기열은 0초이며, 실행 종료로 확인할 수 없는 표본은 제외합니다. 비교 기준은 현재 대기열과 알려진 신호 계획을 사용합니다. 회귀 모델은 실행 단위로 분리한 평가 자료와 비교합니다.
- FMS는 기록된 실험을 재생합니다. 실제 차량 명령, 교차로 허가 및 배차 ETA에는 기존 경로를 사용합니다.

## 확인 명령

```sh
uv run --locked --project experiments/deepfleet python -m unittest discover -s experiments/deepfleet/tests
uv run --locked --project experiments/deepfleet ruff check experiments/deepfleet
uv run --locked --project experiments/deepfleet ruff format --check experiments/deepfleet
uv run --locked --project experiments/deepfleet mypy --strict experiments/deepfleet/src experiments/deepfleet/tests
python3 tests/integration/check_source_lines.py
```
