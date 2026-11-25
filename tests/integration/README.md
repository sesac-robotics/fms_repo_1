# 1단계 편도 모의 검증

[시스템 시나리오 v10](https://k8c1.atlassian.net/wiki/pages/viewpage.action?pageId=8028678&pageVersion=10)의 SD-01~07과 [인터페이스 명세 v10](https://k8c1.atlassian.net/wiki/pages/viewpage.action?pageId=8028663&pageVersion=10)에 맞춰 가입, 호출, 배차, 운행, 정차, 복귀와 충전을 메모리에서 검증합니다. 기준은 [UR v24](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/2883600), [SR v53](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/557330), [SA v42](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/360590), [State Architecture v17](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8192050)입니다.

## 실행

`fms_repo_1` 루트에서 Python 3.12로 실행합니다. 표준 라이브러리만 사용합니다.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/integration -p 'test_one_way*.py' -v
```

상위 주행 검증 환경에 설치된 Ruff 0.14.4로 포맷과 린트를 확인합니다.

```sh
../.venv/bin/ruff format --check --config ../pyproject.toml tests/integration/*.py
../.venv/bin/ruff check --config ../pyproject.toml tests/integration/*.py
```

## 적용 기준

| 시나리오 | 확인할 동작 | 근거 |
| --- | --- | --- |
| **SD-01·02 · 가입, 호출과 배차** | • 등록된 모의 사용자인지 확인하고 출발지와 목적지를 받습니다.<br>• 앱에서 호출한 시각과 관제가 처음 접수한 시각을 따로 확인합니다. 같은 호출을 다시 보내도 한 번만 처리합니다.<br>• 배차할 수 있는 차량과 픽업 보고를 확인합니다. | UR-01·02·12·15<br>SR-001·002·006~008·025·033<br>IF-01~05 |
| **SD-03 · 탑승 확인과 출발** | • 현재 배정에 대한 시험용 탑승 확인 뒤 목적지 이동을 승인합니다.<br>• 명령을 받았다는 응답과 실제 출발에 해당하는 모의 보고를 구분합니다. | UR-13<br>SR-003·009·031<br>택시 상태도<br>IF-04·05 |
| **SD-04 · 운행과 교차로** | • 길을 막고 다시 열었을 때를 각각 확인합니다. 차량 네 대의 시험용 위치를 입력합니다.<br>• 녹색 신호, 비어 있는 교차로, 출구 여유를 확인합니다. 먼저 온 차가 들어가며, 차체가 완전히 빠져나가야 다음 차가 들어갈 수 있습니다. | SR-013·014·016·017·023·024<br>IF-05·06·09·11 |
| **SD-05 · 목적지 도착과 차고지 복귀** | • 목적지 정차, 하차, 운행 종료를 순서대로 확인합니다.<br>• 요금 안내와 모의 결제를 구분합니다. 차고지 도착과 주차칸을 실제로 차지했다는 보고도 구분합니다. | SR-003·025·035·037<br>택시 상태도<br>IF-05·10·12 |
| **SD-06 · 지정 차량 조작과 통신 끊김** | • 지정한 차량만 조작하고, 명령 결과와 실제 차량 상태 보고를 구분합니다.<br>• 연결이 끊겼을 때와 다시 연결한 뒤 이전 연결의 결과가 들어올 때를 확인합니다.<br>• 개인을 알아볼 수 없도록 처리됐다는 표시가 있는 시험용 영상만 고릅니다. | SR-030~032·035<br>IF-03~05·07·09 |
| **SD-07 · 충전과 배차 자격** | • 충전칸에 도착한 시점과 충전을 시작한 시점을 구분합니다.<br>• 70%에서 충전 상태가 대기로 바뀌는지 확인합니다.<br>• 다음 운행은 충전칸을 벗어났는지, 통신이 연결됐는지, 필요한 배터리가 남았는지 따로 확인합니다. | SR-025·033~035<br>택시 상태도<br>IF-05·10·12 |

## 임시 적용 · 팀 승인 전

- 시간, 차량·회원 ID, 위치, 배터리와 차고지 이벤트는 합성 입력입니다. 배차 후보는 시험용 ETA 순으로 정렬하고, 동률일 때 차량 ID를 비교합니다. 교차로 정지선 도착 시각이 같은 모의 입력에도 차량 ID로 일관된 순서를 재생합니다. 요금의 거리·시간 계산값은 시험용이며 팀 요금표에 적용하지 않습니다.
- 1단계 탑승 확인은 현재 운행에 해당하는 모의 입력을 사용합니다. 2단계 얼굴 인식, 미탑승 자동 취소, 주행 중 목적지 변경은 별도 단계입니다.
- 주차와 충전은 배정의 목적에 따라 나눕니다. 차량의 도착 보고와 차고 장치의 점유·충전 시작 보고를 따로 처리합니다. 충전 70%는 대기 전이 조건이며, 시설 이탈과 다음 운행의 배차 적격은 별도로 검사합니다.

## 실행 결과

2026-11-22에 Python 3.12.8로 15개 시험을 실행해 모두 통과했습니다. 편도 호출부터 충전 대기까지 같은 차량·배정·운행으로 이어 가는 재생 1개와 SD별 정상·오류 확인 14개입니다. Ruff 0.14.4 포맷·린트, Python 파일 7개의 mypy 1.18.2 엄격 검사와 200줄 기준도 통과했습니다.

## 팀 회의에서 정할 사항

- Android·ESP32 운영 호출 경계, 실제 탑승 확인의 담당과 증거, 호출·접수 시각 원천과 인터페이스의 메시지·인증·QoS
- 차량 선정·ETA·요금 기준, 관제 영상의 비식별 처리 담당과 전달 경로, 위치·신호 관측의 유효 조건
- 차고지 도착 뒤 주차·충전 분기, Main의 충전 상태 반환 경로, 시설 점유·이탈 증거와 복귀 중 재배차 조건

시험은 실제 앱·서버·DB·ROS 2 전송, 센서 위치 추정, 영상 인식·블러 처리, 차량 동작을 실행하지 않습니다. 도면 정정과 이번 실행 결과는 [시스템 시나리오](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8028678)에서 함께 확인할 수 있습니다.

# 2단계 호출 취소·목적지 변경 모의 검증

[시스템 시나리오 v11](https://k8c1.atlassian.net/wiki/pages/viewpage.action?pageId=8028678&pageVersion=11)의 SD-08·09와 [인터페이스 명세 v10](https://k8c1.atlassian.net/wiki/pages/viewpage.action?pageId=8028663&pageVersion=10)을 사용합니다. 확정 근거는 [UR v24](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/2883600), [SR v53](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/557330), [SA v42](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/360590), [State Architecture v17](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8192050)입니다.

## 실행

`fms_repo_1` 루트에서 Python 3.12로 실행합니다. 첫 명령은 SD-08·09만, 두 번째 명령은 1단계 회귀 확인까지 실행합니다.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/integration -p 'test_stage_two*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/integration -p 'test_*.py' -v
```

```sh
../.venv/bin/ruff format --check --no-cache --config ../pyproject.toml tests/integration/*.py
../.venv/bin/ruff check --no-cache --config ../pyproject.toml tests/integration/*.py
PYTHONDONTWRITEBYTECODE=1 ../.venv/bin/mypy --strict --cache-dir=/dev/null tests/integration/*.py
```

## 확정 근거

| 시나리오 | 판정 기준 | 근거 |
| --- | --- | --- |
| **SD-08 · 호출 취소와 미탑승** | • 승객이 탑승 전에 직접 취소한 경우와 미탑승으로 자동 취소된 경우를 구분하고 배정을 종료합니다.<br>• 차량이 이미 배정됐다면 실제 정지, 기존 작업 해제, 복귀 도착을 각각 확인합니다. 명령 접수 응답은 따로 기록합니다.<br>• 택시·통합 상태도는 차량이 호출 장소로 이동 중이거나 탑승을 기다리는 중에 호출이 취소되면 차고지로 이동하는 흐름을 보여 줍니다. | UR-18<br>SR-010·031·033·035<br>IF-01~05·09 |
| **SD-09 · 목적지와 경유지 변경** | • 진행 중인 본인 운행에서 요청을 받습니다. 지도·차단 구간·배터리를 고려해 경로를 다시 계산합니다.<br>• 처음 호출한 장소와 변경 이력을 남깁니다. 새 경로가 실제로 적용됐는지는 IF-04로 확인합니다.<br>• 정차한 뒤 목적지를 추가하는 일은 별도 흐름입니다. 실제 재출발은 IF-05로 확인합니다. | UR-19<br>SR-011·014·034·035<br>IF-01·02·04·05<br>택시·통합 상태도 |

## 임시 적용 기준 · 팀 승인 전

- 미탑승은 픽업 도착 후 시험용 시간 초과 사건을 주입합니다. 실제 제한 시간 없이 취소가 먼저 도착한 경우와 탑승 확인이 먼저 도착한 경우를 각각 재생합니다. 탑승 확인은 해당 운행의 합성 판정을 사용합니다.
- 배정이 끝난 뒤 모의 복귀 도착과 연결·차량 정상 상태를 확인하고, 다음 운행의 시험용 필요 잔량 25%를 판정합니다. 복귀 중 자동 재배차는 보류합니다.
- SD-09의 합성 지도에서 열린 구간 하나를 100m·2모의 틱·배터리 4%p로 계산합니다. 예비 잔량은 10%p, 경유지 상한은 `max(0, (현재 잔량 − 10) // 10)`개입니다. 전체 경로의 에너지와 예비 잔량도 확인합니다. 이 값들은 모의 시험용입니다.
- 주행 중에는 같은 배정·차량·명령·연결에서 새 개정을 실제 적용했다는 보고가 올 때까지 기존 경로를 유지합니다. 제안 경로 거절과 기존 경로가 막혀 우회 없이 안전 대기하는 경우를 구분합니다. 정차 중 추가 목적지는 별도 재출발 확인을 사용합니다.

## 실제 시험 결과

2026-11-22에 Python 3.12.8로 SD-08 개별 시험 7개, SD-09 개별 시험 7개, 같은 호출·배정·차량의 출발부터 경로 개정 적용까지 연계 재생 1개를 실행했습니다. 2단계 15개와 1단계를 포함한 회귀 시험 30개가 모두 통과했습니다. Ruff 0.14.4 포맷·린트와 mypy 1.18.2 엄격 검사도 통과했습니다. 신규 Python 파일 7개는 최대 191줄이었습니다.

- **SD-08** 배정 전 본인 취소, 픽업 이동·탑승 대기의 취소, 미탑승, 탑승 확인과 취소의 양쪽 처리 순서, 중복·다른 배정·이전 연결 및 정리 실패를 확인했습니다. 명령 접수만으로는 배정을 종료하지 않고 같은 배정의 정차와 기존 작업 해제 보고가 모두 있어야 종료했습니다. 올바른 복귀 보고와 차량 적격도 별도로 확인했습니다.
- **SD-09** 지도 차단을 피한 경로 계산, 배터리·경유지 제한, 잘못된 요청과 적용 실패, 오래되거나 다른 연결의 응답을 확인했습니다. 명령이 접수됐을 때는 200m·4모의 틱이 유지됐고, 제어의 같은 개정 적용 보고 후 300m·6모의 틱으로 갱신됐습니다. 최초 호출의 장소는 보존했고, 정차 후 추가 목적지는 일치하는 실제 재출발의 모의 보고가 와야 이동 상태로 전이했습니다.

시험 범위는 메모리 모의 모델입니다. 실제 앱·서버·DB·ROS 2 통신과 얼굴 인식, 경로의 실차 적용, 실제 차량 움직임은 미검증입니다.

## 팀 회의에서 정할 사항

- **SD-08** 미탑승 시간의 시작점과 실제 제한 시간, 취소와 탑승이 동시에 들어왔을 때의 우선순위·사용자 표시, 정리 실패 복구, A-04의 복귀 중 재배차와 고장 회수 조건
- **SD-09** 배터리·예비 잔량·경유지 운영값, 요청을 받는 상태와 제어가 적용할 안전한 시점, 중첩 요청·지연·재접속 시 개정 처리, 택시 상태도의 정차 후 추가 목적지와 주행 중 변경 표기
- **공통** IF-02의 재시도·인증 계약, IF-04·05의 보고 형식·QoS, 화면과 이력 저장 시점

[시스템 시나리오](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8028678)에서 실행 결과와 2단계 시퀀스 검토본을 확인할 수 있습니다.

# 3단계 렌트·Cargo·분실물 모의 검증

[시스템 시나리오 v12](https://k8c1.atlassian.net/wiki/pages/viewpage.action?pageId=8028678&pageVersion=12)의 SD-10~12와 [인터페이스 명세 v10](https://k8c1.atlassian.net/wiki/pages/viewpage.action?pageId=8028663&pageVersion=10)을 사용합니다. 확정 근거는 [UR v24](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/2883600), [SR v53](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/557330), [SA v42](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/360590), [State Architecture v17](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8192050)입니다.

## 실행

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/integration -p 'test_stage_three*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/integration -p 'test_*.py' -q
../.venv/bin/ruff format --check --no-cache --config ../pyproject.toml tests/integration/*.py
../.venv/bin/ruff check --no-cache --config ../pyproject.toml tests/integration/*.py
PYTHONDONTWRITEBYTECODE=1 ../.venv/bin/mypy --strict --cache-dir=/dev/null tests/integration/*.py
```

## 임시 적용 기준 · 팀 승인 전

- **SD-10** 최초 요청은 SR-002에 맞춰 출발지와 양수 이용 시간만 받습니다. 같은 배정의 모의 실제 출발부터 합성 초를 세고, 시작 전 미정과 만료 0초를 구분합니다. 이동 중 만료는 반납 대기로 보냅니다. 정차·하차 및 주차칸을 사용했다면 이탈 확인 뒤 복귀합니다. 모의 요금은 시험용 거리와 이용 시간의 합으로 산정하며 만료 이후 시간은 추가하지 않습니다. 차량 재사용에 쓴 모의 필요 잔량 40%도 시험값입니다. IF-01·02·04·05·10·12를 대조했습니다.
- **SD-11** 지정 위치의 상차와 결착, 장착 주행 설정 적용을 별도 사건으로 입력합니다. 합성 인수 확인 뒤 화물차고지로 복귀하고, 지정 위치의 같은 카트 분리 확인 뒤 일반 주행 설정 복귀를 확인합니다. 분리 실패나 결착 전후 취소는 자동 복귀·재사용 대신 보류합니다. 차량 재사용에 쓴 모의 필요 잔량은 25%입니다. IF-04·05와 제안 상태인 IF-13을 대조했습니다.
- **SD-12** 하차를 기준으로 전·후 순서가 맞는 같은 운행·차량의 사진 ID와 합성 판정만 사용합니다. `운행 + 감지 키`를 기준으로 중복을 확인하며 대상별 성공 시각을 보존합니다. 모의 정정이 승인되면 남은 전송을 보류하고 기존 성공과 정정 이력을 보존합니다. IF-07·09·01~03·12를 대조했습니다.

## 실제 시험 결과

2026-11-22에 Python 3.12.8로 SD-10 6개, SD-11 7개, SD-12 6개를 실행해 **19개 모두 통과**했습니다. 1~3단계 회귀 시험 49개도 모두 통과했고, Python 파일 20개에서 Ruff와 mypy 엄격 검사를 통과했습니다. 신규 6개 파일은 최장 194줄이었습니다.

- **SD-10** 출발 전 남은 시간 미정, 30초 경계의 만료, 주차 도착·점유·이탈, 재출발, 정차·하차·복귀, 모의 결제 보류·실패·재시도와 차량 재사용 판정을 확인했습니다.
- **SD-11** 장소·차량·운행·카트·작업이 일치하는 결착과 분리, 인수 전 정차, 장착·일반 주행 설정의 별도 적용, 현재 배정의 모의 남은 거리, 카트·차량 재사용의 분리와 실패 시 보류를 확인했습니다.
- **SD-12** 촬영 누락·순서 오류·다른 운행의 사진은 비교 불가로 처리했습니다. 합성 후보만 사용자·관리자에게 각각 전달했고, 관리자만 실패한 시험에서는 관리자만 재시도했습니다. 최초 성공 시각, 중복 감지, 오검출 정정 이력을 확인했습니다.

검증 범위는 오프라인 모의 모델입니다. 실제 차량·카트·주차 센서·카메라, 사진 비교 정확도와 얼굴 가림, 실결제, 앱 알림과 TCP·UDP·HTTP·ROS 2·DB 연동은 미검증입니다.

## 팀 회의에서 정할 사항

- **SD-10** SR-002와 렌터카 상태도의 첫 목적지 표기, 이용 시간 시작 기준, 만료·직접 반납의 안전 정차·하차 증거, 자동 주차와 점유·이탈의 운영 기준 및 요금 정책
- **SD-11** Cargo·통합 상태도의 탑승자 확인과 차고지 직행을 화물 인계·분리에 적용할 조건, 결착 전후 취소·분리 실패 회수, 인수 증거·분리 위치·카트 재사용 승인, IF-13 전송 계약
- **SD-12** 촬영 기준과 비교 불가 처리, 오검출 정정 책임과 이미 보낸 알림의 후속 안내, 대상별 재시도 정책, 사진 접근 권한·보존 기간·비식별 처리

[시스템 시나리오](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8028678)에서 3단계 시퀀스 검토본을 확인할 수 있습니다.

## 개정 시나리오 로컬 검증

[시스템 시나리오](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8028678), [인터페이스 명세](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8028663), [State Architecture v17](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8192050), [시나리오별 DB 처리](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8356422)를 적용합니다. 위의 기존 실행 기록은 당시 모의 검증 결과입니다.

### 서버·DB 통합 실행

비어 있는 별도 개발 PostgreSQL에 [루트 실행 절차](../../README.md#개발-환경에서-실행하기)로 Main Control의 `demo` 프로필과 Web 게이트웨이를 엽니다. 시험은 가상 승객과 관리자만 사용하며 가상 운행과 영수증을 DB에 저장합니다. 포트는 실제 실행 값에 맞춥니다.

```sh
AMO_DEMO_HTTP=http://127.0.0.1:18085 AMO_DEMO_IF03_PORT=18087 \
  python3 -m unittest discover -s tests/integration -p test_revised_demo_http.py -v
```

| 순서 | 검증할 증거 |
| --- | --- |
| 초기 충전과 호출 | `DEMO-REPLAY-01`의 점유 → 충전 시작 → 70% 도달과 대기 → 실제 이탈에 해당하는 모의 보고를 저장합니다. 호출 견적에는 거리·시간과 시험 요율 버전을 남깁니다. 같은 결제 시도 키를 동시에 보내 결과와 시각이 일치하는지 확인합니다. |
| 배차부터 확정까지 | 선결제 없이 배차를 시도해 거절되는지 확인합니다. 같은 배정의 픽업 정차·승차·출발·목적지 정차·하차를 순서대로 기록합니다. 재전송한 하차는 기존 확정 요금과 영수증을 반환합니다. |
| 경로 변경과 재출발 | 승객 재수락과 필요한 모의 차액 결제 뒤 명령을 발행합니다. 접수 확인, 다른 연결의 적용 보고 거절, 실제 적용에 해당하는 보고, 정차 후 실제 재출발에 해당하는 보고를 각각 확인합니다. 적용 실패 시험에서는 결제 이력과 기존 목적지·요금을 함께 보존합니다. |
| 복귀·충전과 화면 | 복귀 지시와 차량 도착, 시설 점유, 충전 시작, 배터리 임계치와 시설 이탈을 따로 확인합니다. FMS는 IF-03으로 원래 목적지와 적용 개정을 받고, Admin은 Web API를 통해 견적·결제·요금과 운영 이력을 읽습니다. |

### 2026-11-24 실행 결과

격리 PostgreSQL 16.15와 Web 게이트웨이에서 편도·변경·복귀 통합 4개와 오프라인 회귀 50개가 통과했습니다. Android API 36 에뮬레이터에서 모의 선결제, 변경 견적 수락, 적용 목적지 갱신과 영수증을 확인했습니다. 가상 운행 5만 건으로 별도 PyQt Admin 조회를 실행하는 동안 대조 실행과 병행 실행의 IF-03 응답은 각각 3건 모두 정상입니다. 차량·차고 설비 연동과 운영 규모 성능 검수는 별도 대상입니다.

### 모의 관측 API

아래 경로는 `demo` 프로필에서만 로컬 검증에 사용합니다. 승객이 소유한 요청의 견적·결제 API와 관리자 모의 입력은 각각 인증이 필요합니다.

| 메서드·경로 | 입력 |
| --- | --- |
| `POST /api/rides/{id}/mock-quote` | 빈 JSON 객체 |
| `POST /api/rides/{id}/mock-prepayment` · `POST /api/rides/{id}/mock-change-accept` | `quoteId`, `key` |
| `GET /api/rides/{id}/fare` · `GET /api/rides/{id}/route-change` | 없음 |
| `POST /api/rides/{id}/mock-change-propose` | `destination` |
| `POST /api/admin/demo/rides/{id}/observe` | `step`, 목적지 정차에서는 `distanceMeters`와 `elapsedSeconds` |
| `POST /api/admin/demo/rides/{id}/route/{propose\|issue\|report}` | `destination`, `revisionId`, 또는 같은 명령의 응답 식별자와 `report` |
| `POST /api/admin/demo/depot/observe` | `requestId`(초기 충전 생략), `step`, `key`, 배터리 보고 시 `batteryPercent` |

시험 요율은 지도상의 모의 거리·시간을 사용합니다. 운영 요율·결제 실패 재시도와 환불, 차액 결제 뒤 적용 실패 정산, 별도 관리자 권한·운영 범위, 대여·Cargo의 실제 증거와 IF-04·05·10·13 전송 계약은 팀에서 결정합니다. 대여·Cargo 개정 분기는 메모리 검증에서 실행합니다.


## 클릭형 시나리오 검수 시험

위와 같은 격리 서버에서 다음 명령을 실행합니다. 검수는 공용 시연 차량과 충전칸을 재사용합니다. 테스트가 저장한 검수별 단계와 호출 기록은 검수용 DB에서 확인할 수 있습니다.

```sh
AMO_DEMO_HTTP=http://127.0.0.1:18085 AMO_DEMO_IF03_PORT=18087 \
  python3 -m unittest discover -s tests/integration -p test_scenario_review_http.py -v

cd GUI/MainControllerPC/AMOAdmin
QT_QPA_PLATFORM=offscreen AMO_DEMO_HTTP=http://127.0.0.1:18085 \
  uv run --locked python -m unittest discover -s tests -p test_scenario_review_panel.py -v
```

서버 시험은 접수와 적용의 구분, 결제 뒤 적용 실패, 중복 단계 실행, 차량 재사용, 호출과 검수 기록 보존, 이전 지도 위치 제거, 관리자 권한과 Android 입력 확인을 검증합니다. PyQt 시험은 실제 검수 탭에서 선행 단계 재생, 실패 보고 클릭, 완료 단계 다시 보기와 원래 운행 이력 조회를 검증합니다.
