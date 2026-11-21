# fms_repo_1

자율주행 시스템 통합 프로젝트 1팀

AMO 개발용 화면은 PyQt FMS, Vue 3 관리자 Web, Android 승객 앱으로 구성합니다. 세 화면에서 한국어, 영어, 중국어 간체와 라이트·다크 모드를 선택할 수 있습니다. 설정에서 처음 사용 안내를 끄거나 다시 볼 수 있습니다.

| 화면 | 폴더 | 맡는 일 |
| --- | --- | --- |
| PyQt FMS | `apps/admin` | 차량·배차·이벤트 모니터링과 관제 상태 확인 |
| 관리자 Web | `services/web_service/frontend` | 관리자 가입 요청·승인, 회원과 권한, 운영 이력, 시험 결과, 메뉴 관리 |
| Android | `apps/mobile` | 승객 회원가입, 편도 호출, 진행 상태·이력 확인 |
| Spring Boot | `services/web_service/backend` | JWT 발급·검증, Google 계정 연동, 화면 API |
| PostgreSQL | `database/migrations` | AMoDE 업무 모델과 화면 지원 데이터 |

## 개발 환경에서 시작하기

1. 별도로 만든 로컬 PostgreSQL 개발 DB의 JDBC 주소, 역할, 비밀번호를 `AMO_DB_URL`, `AMO_DB_USER`, `AMO_DB_PASSWORD`에 지정합니다. 환경 변수 값은 소스에 저장하지 않습니다.
2. JDK 21로 Spring Boot를 실행합니다. `demo` 프로필은 업무·지원 테이블을 마이그레이션하고 예시 기록과 개발용 로그인 계정을 추가합니다.

   ```sh
   cd services/web_service/backend
   SPRING_PROFILES_ACTIVE=demo SERVER_ADDRESS=127.0.0.1 SERVER_PORT=18085 mvn spring-boot:run
   ```

3. 관리자 Web을 별도 터미널에서 실행합니다.

   ```sh
   cd services/web_service/frontend
   npm ci
   AMO_API_URL=http://127.0.0.1:18085 npm run dev
   ```

4. FMS는 `apps/admin`에서 Python 3.12와 `uv`로 실행합니다. Android는 `apps/mobile`을 Android Studio에서 열고 개발 API 주소를 지정한 후 debug 빌드를 실행합니다. 플랫폼별 실행 옵션은 각 화면의 README를 확인합니다.

개발 계정은 `admin@amo.test`, `operator@amo.test`, `passenger@amo.test`입니다. 공용 개발 비밀번호는 `AmoDemo!2026`입니다. 관리자 Web에는 관리자·관제 계정으로, Android에는 승객 계정으로 로그인합니다.

## 설계 기준

- [User Requirements](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/2883600)
- [System Requirements](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/557330)
- [System Architecture](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/360590)
- [State Architecture](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8192050)
- [단계별 통합 구현 가이드](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8127144)
- [개발 표준](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/4358173)
- [AMO Figma 화면 설계](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8127728/AMO+Figma+v0.2)
- [맵 예시안 v0.2](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8192349/v0.2+2440x2225)
- [AMoDE DB ERD](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8127076)

## 관리자 Web과 PyQt FMS 로그인 공유

1. 관리자 Web과 PyQt FMS에 같은 Web 주소를 사용합니다. PyQt의 기본 Web 주소는 `http://127.0.0.1:5175`입니다. 주소를 바꾸면 `AMO_ADMIN_WEB_URL`을 지정합니다.
2. PyQt에서 **브라우저로 로그인**을 누릅니다. 이전에 관리자 Web에 로그인한 브라우저와 같은 프로필이 열리면 로그인 정보를 다시 입력할 필요가 없습니다.
3. 브라우저에서 계정 이름을 확인하고 **PyQt FMS에 연결**을 선택합니다. PyQt에서 로그인을 시작한 경우 이미 열어 둔 관리자 Web 탭도 로그인 상태를 갱신합니다.

Google로 로그인할 때도 같은 브라우저 흐름을 사용합니다. Spring Boot의 `AMO_GOOGLE_CLIENT_ID`에 Web OAuth 클라이언트 ID를 지정하고, Google Cloud의 승인된 JavaScript 원본에 실제 관리자 Web 주소를 등록합니다. 승인받은 기존 관리자·운영자 계정은 Web 설정에서 같은 이메일의 Google 계정을 먼저 연결합니다.

## 운행 이력 화면 확인

관리자 Web의 **운행 이력**에서 개발 기록 `#2` S2 → S4를 선택하면 해당 운행에 저장된 차량 위치가 지도에 표시됩니다. `#1` S1 → S2를 선택하면 경로 데이터가 없다는 안내가 표시됩니다.

운행 상세는 지원되는 v0.2 지도 좌표계의 위치 기록을 사용합니다. 수신 공백으로 나뉜 구간은 지도에서도 따로 표시합니다. 차량 위치와 시험 결과는 개발 DB의 화면 확인용 예시입니다.

운행 제어, 차량 위치 보정, Main Control 실차 TCP 연결은 별도의 통합 검증이 필요합니다. Google 로그인 설정은 [Spring Boot README](services/web_service/backend/README.md)에서 확인할 수 있습니다.
