# AMO PyQt FMS

관제 운영자가 차량, 호출·배차, 운영 이벤트를 확인하는 데스크톱 앱입니다.
한국어·영어·중국어 간체와 라이트·다크 테마를 제공합니다. 첫 로그인 안내는 설정에서 끄거나 다시 볼 수 있습니다.

## 개발 환경에서 실행

Python 3.12와 `uv`가 필요합니다. Spring Boot 백엔드와 Vue 관리자 Web을 먼저 실행하세요.

```sh
cd GUI/MainControllerPC/AMOAdmin
uv sync --locked
AMO_FMS_API=http://127.0.0.1:18085 uv run --locked amo-fms
```

- `AMO_FMS_API` 기본값은 `http://127.0.0.1:18085`이고, `AMO_ADMIN_WEB_URL` 기본값은 `http://127.0.0.1:5175`입니다. 두 앱이 같은 백엔드에 연결되게 설정하세요. 다른 호스트의 주소에는 HTTPS를 사용하세요.
- 개발용 예시 데이터가 활성화된 백엔드에는 `operator@amo.test` / `AmoDemo!2026`으로 로그인할 수 있습니다.
- 지도와 로고는 저장소의 `maps/`를 읽습니다. 별도 경로가 필요하면 `AMO_MAP_DIR`을 지정하세요.
- **로그인** Web 게이트웨이에 접속합니다. 로그인 뒤 받은 접속 증표(JWT)는 앱이 실행되는 동안 메모리에만 보관합니다.
- **차량 상태 새로고침** Main Control에 개발용 IF-03 연결(TCP)로 접속합니다. 기본 포트는 18087입니다. 필요하면 AMO_FMS_TCP_PORT로 바꿉니다.

## 브라우저 로그인

1. FMS에서 **브라우저로 로그인**을 누릅니다.
2. 기본 브라우저에 열린 관리자 Web에서 AMO 계정으로 로그인합니다. 기존 브라우저 세션이 있으면 그 계정으로 연결을 확인합니다. 관리자 Web에 Google 로그인이 설정돼 있으면 해당 방식으로도 로그인할 수 있습니다.
3. 관리자 Web에서 **PyQt FMS에 연결**을 누른 뒤 FMS로 돌아옵니다. 승인된 `OPERATOR` 또는 `ADMIN` 계정으로 연결할 수 있습니다.

기존 로그인을 이어서 사용하려면 관리자 Web에 로그인한 것과 같은 브라우저 프로필에서 같은 주소를 사용하세요. FMS에서 브라우저 연결 대기를 취소하면 다시 시작할 수 있습니다.

## 개발 미리보기

- **운행 화면**은 Main Control이 IF-03으로 보낸 차량과 운영 기록을 보여 줍니다. PostgreSQL은 Main Control이 읽습니다.
- **지도 v0.2**에는 시설 배치와 개발용 차량 위치가 보입니다. 지도 아래 설명에서 정지선과 교차로 경계를 구분할 수 있습니다.
- 최신 조회에 실패하면 이전 조회 결과와 갱신 실패를 함께 표시합니다.
- 호출 접수와 차량에서 관측한 운행 상태를 구분합니다. 조작 미리보기는 네트워크로 전송되지 않습니다.
- 개발 IF-03은 읽기 전용입니다. 실제 관제 명령과 이벤트 전달 계약은 팀 회의에서 정합니다.

## 검증

```sh
uv run --locked ruff check
uv run --locked ruff format --check
uv run --locked python -m compileall -q src
uv run --locked python -m unittest discover -s tests
```

[관제 GUI](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/2621446) · [플랫폼별 구현 가이드](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8357019) · [맵 구성안 v0.2](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8192349)
