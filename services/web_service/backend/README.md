# AMO Spring Boot 백엔드

Android 승객 요청과 관리자 Web의 운영 조회·계정·메뉴를 처리합니다. PyQt 개발 화면은 동일 API를 통해 시험 데이터를 읽습니다. Main Control 업무 처리와 PostgreSQL 접근은 `dev.amo.maincontrol`에 두었습니다.

## 로컬 시연

Java 21, Maven, 격리된 PostgreSQL 17 빈 DB를 사용합니다. Spring Boot가 시작될 때 Flyway가 업무 스키마와 인증·메뉴를 생성합니다. `demo` 프로필을 사용할 때만 가짜 기록을 추가합니다.

```sh
cd services/web_service/backend
export AMO_DB_URL='jdbc:postgresql://127.0.0.1:5432/amo_dev'
export AMO_DB_USER='amo_demo'
export AMO_DB_PASSWORD='<격리된 DB 비밀번호>'
SPRING_PROFILES_ACTIVE=demo SERVER_ADDRESS=127.0.0.1 SERVER_PORT=18085 mvn spring-boot:run
```

시연 계정은 `admin@amo.test`, `operator@amo.test`, `passenger@amo.test`입니다. 비밀번호는 모두 `AmoDemo!2026`입니다. 회원·메뉴 변경이나 승객 호출은 시연 DB에 실제로 저장됩니다.

## 관리자 SSO와 Google 로그인

PyQt FMS는 관리자 Web을 브라우저로 열어 기존 세션을 사용합니다. 승인된 관리자·운영자가 연결을 확인하면 Web이 60초짜리 일회용 코드를 전달합니다. PyQt는 시작 시 만든 PKCE verifier로 코드를 교환해 자체 세션을 받습니다.

Google 로그인을 켜려면 Google Auth Platform에서 관리자 Web의 실제 원본을 등록하고 Web OAuth 클라이언트 ID를 `AMO_GOOGLE_CLIENT_ID`에 설정합니다. Android는 같은 Google Cloud 프로젝트에 앱 패키지와 APK 서명 SHA-1을 등록하고, 서버에서 받은 Web 클라이언트 ID를 사용합니다. PyQt는 Web의 Google 로그인 흐름을 사용합니다.

승인된 관리자·운영자와 이메일로 가입한 승객은 기존 AMO 계정으로 로그인한 뒤 같은 이메일의 Google 계정을 연결합니다. Google로 처음 접속한 새 계정에는 승객 권한이 부여됩니다. 개발용 테스트 모드에서는 Google Auth Platform의 테스트 사용자 설정도 적용합니다.

## 검증

```sh
mvn spotless:check verify
```

`GET /api/health`로 PostgreSQL 연결을 확인합니다. 업무·DB 인터페이스는 팀 Confluence 문서에 연결됩니다.

- [AMoDE DB ERD](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8127076/AMoDE+DB+ERD)
- [통합 업무·DB 가이드](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8127144)
- [FMS·관리자 Web·Android 단계별 구현 가이드](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8127144)

## 현재 연동 범위

Web과 Main Control의 서비스는 동일 프로세스에서 연결됩니다. PyQt의 HTTP 연결은 시연용이며, 팀 인터페이스인 IF-02·IF-03 TCP 전송과 실차 명령은 추후 통합 대상입니다. v0.2 정류장 위치는 도면에서 읽은 화면용 값입니다. 배차 가능 차량은 시연 데이터에서 모두 비활성화되어 있습니다. 호출·대기 상태와 사유는 팀 가이드의 입력값을 따르며, 클라이언트에서 사용하는 영문 코드명은 시연용으로 정했습니다.

시연 프로필을 제외한 환경에서는 `AMO_JWT_KEY`에 32바이트 이상 키를 Base64로 설정하고 HTTPS를 사용합니다. 초기 관리자 발급과 토큰 갱신 방식은 운영 배포 전에 팀에서 결정합니다.

## 운행 기록의 경로

관리자와 운영자는 `GET /api/operations/requests/{requestId}/route`로 선택한 호출의 차량 위치 기록을 조회합니다. 출발이 확인된 최신 운행에서 해당 차량과 배정에 연결된 관측값만 가져옵니다. 지도 v0.2의 왼쪽 아래가 원점이며 좌표 단위는 m입니다.

응답의 `segments`는 순서대로 관측한 좌표 묶음입니다. 출처나 일련번호가 끊기면 별도 선으로 표시합니다. 경로가 없으면 `segments`는 빈 배열이며, 존재하지 않는 호출 번호에는 404를 반환합니다. 최근 관측값 2,000개를 초과하면 `truncated`가 true입니다. 개발 DB에는 완료된 예시 호출의 위치 기록이 들어 있습니다.

## 관리자 Web 계정으로 PyQt 로그인

PyQt는 시스템 브라우저에서 관리자 Web을 엽니다. 브라우저에서 로그인한 관리자나 운영자가 연결을 승인하면, Web은 쿠키와 CSRF 토큰으로 `POST /api/auth/desktop/authorize`를 호출합니다. 요청에는 PyQt가 지정한 loopback 포트와 PKCE S256 challenge가 들어갑니다.

발급 코드는 최대 60초 동안 유효하며 한 번만 교환할 수 있습니다. DB에는 원본 코드 대신 SHA-256 해시를 저장합니다. PyQt는 `POST /api/auth/desktop/token`에 코드, 포트와 PKCE verifier를 보내 같은 계정의 별도 접근 토큰을 받습니다. 교환 전에 브라우저 세션이 만료되거나 폐기되면 코드를 사용할 수 없습니다.
