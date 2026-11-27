# fms_repo_1

자율주행 시스템 통합 프로젝트 1팀

## 누가 어떤 일을 하나요?

기본 앱은 **FMS(PyQt)**, **Admin(PyQt)**, **사용자 앱(Android)**입니다. **Admin(Web)**은 비공식 보조 앱입니다. Admin(PyQt) 기능을 추가하거나 변경할 때 Admin(Web)에도 같은 동작을 반영하고 두 앱에서 각각 검증합니다.

- **AMO FMS(PyQt)**는 관제 서버에서 차량·호출·이벤트의 최신 기록을 IF-03 TCP로 읽습니다. **AMO Admin(PyQt)**은 별도 프로세스에서 Web 게이트웨이의 HTTP API로 운영 이력과 관리 화면을 엽니다. [PyQt 안내](GUI/MainControllerPC/AMOAdmin/README.md)
- **사용자 앱(Android)**은 승객이 한국어·영어·중국어로 로그인하고, 편도 호출을 요청하고, 본인 이력을 보는 앱입니다. SW 도면의 승객 접점은 Web Browser로 표시되며, Android의 운영 연결 계약은 팀에서 정합니다. [Android 안내](GUI/UserMobile/AndroidApp/README.md)
- **관제 서버**는 회원·권한, 호출 접수, 운영 조회를 처리합니다. 이 서버에서만 PostgreSQL에 접근합니다. Flyway는 번호가 붙은 SQL을 순서대로 실행해 DB 구조를 준비합니다. [관제 서버](Server/AMOMainServer/AmoMainControlService) · [DB 변경 파일](Server/AMOMainServer/AmoDB/migrations)
- **Web 게이트웨이**는 HTTP 요청을 받아 IF-02를 통해 관제 서버에 전달합니다. **Admin(Web)**은 Vue로 구현한 관리자 화면이며 운영 상태, 운행 이력, 시험 결과를 보여 줍니다. [Web 게이트웨이](Server/WebServer/AmoWebService/backend) · [Admin(Web)](Server/WebServer/AmoWebService/frontend/admin)
- **공용 지도**에는 확정 도로 배치, v0.2 이력·재생용 지도와 로고가 있습니다. **통합 모의 시험**은 편도 운행부터 취소·경로 변경, 렌트·Cargo·분실물까지 확인합니다. [공용 지도](maps) · [모의 시험](tests/integration/README.md)

## 개발 환경에서 실행하기

서버 두 개를 빌드하려면 JDK 21과 Maven이 필요합니다. 데모를 시작하기 전에 비어 있는 **개발용 PostgreSQL**을 준비하세요. 아래 예제는 각 단계에서 별도 터미널을 열고 저장소 루트에서 시작하는 방식입니다.

### 1. 관제 서버

개발용 DB에 맞춰 `AMO_DB_URL`에 JDBC 주소를 넣고, `AMO_DB_USER`와 `AMO_DB_PASSWORD`를 설정합니다.

```sh
cd Server/AMOMainServer/AmoMainControlService
mvn spotless:check verify
SPRING_PROFILES_ACTIVE=demo java -jar target/amo-main-control-0.1.0-SNAPSHOT.jar
```

### 2. Web 게이트웨이

```sh
cd Server/WebServer/AmoWebService/backend
mvn spotless:check verify
java -jar target/amo-web-service-0.1.0-SNAPSHOT.jar
```

### 3. 기존 관리자 Web과 브라우저 로그인

```sh
cd Server/WebServer/AmoWebService/frontend/admin
npm ci
npm run check && npm test && npm run build
npm run dev -- --port 5175
```

게이트웨이의 기본 HTTP 포트는 `18085`입니다. 관제 서버의 개발용 IF-02와 IF-03은 `demo` 설정에서 각각 `18086`, `18087`로 열립니다. 가상 계정은 `DemoAccounts.java`에 있습니다. Google 로그인과 계정 연결에는 서버 설정과 OAuth 등록이 필요합니다. [PyQt 실행 방법](GUI/MainControllerPC/AMOAdmin/README.md) · [Android 실행 방법](GUI/UserMobile/AndroidApp/README.md)

## Ubuntu에서 Docker Compose로 실행하기

강의 01~05의 이미지 빌드, 컨테이너 실행·점검, 네트워크 연결을 Main Control, Web 게이트웨이, 브라우저 로그인용 Web에 적용했습니다. Docker Engine과 Compose가 설치된 Ubuntu에서 실행합니다.

1. 호스트나 별도 서버에 빈 개발용 PostgreSQL을 준비합니다. Main Control이 이 DB에 Flyway 마이그레이션을 적용합니다.
2. Git에서 제외되는 `.env`에 `AMO_DB_URL`(JDBC URL), `AMO_DB_USER`, `AMO_DB_PASSWORD`, `AMO_JWT_KEY`(Base64로 인코딩한 32바이트 이상 키)를 설정합니다. 비밀번호와 키는 Compose 시크릿으로 마운트합니다.
3. 저장소 루트에서 실행합니다.

```sh
docker compose config -q
docker compose up --build -d
docker compose ps
curl -fsS http://127.0.0.1:18085/api/health
docker compose logs main-control gateway
docker compose exec gateway java -version
docker compose down
```

기본 프로필은 `demo`입니다. IF-02 18086과 IF-03 18087의 기존 루프백 연결을 유지하기 위해 Linux 호스트 네트워크를 사용합니다. 게이트웨이는 18085, Web은 5175에서 호스트의 루프백으로 열립니다. 기존 직접 실행과 병행할 때는 `AMO_GATEWAY_PORT`, `AMO_WEB_TCP_PORT`, `AMO_FMS_TCP_PORT`, `AMO_ADMIN_WEB_PORT`로 빈 포트를 지정하고 클라이언트 접속 주소도 맞춥니다. PostgreSQL 데이터는 외부 DB에 남습니다.

FMS와 Admin PyQt는 호스트에서, Android는 기기 또는 에뮬레이터에서 실행합니다. 강의의 X11 권한 변경, 이미지 레지스트리 푸시, 실차 ROS 2 통신은 이 실행 구성의 범위 밖입니다. [PyQt 실행 안내](GUI/MainControllerPC/AMOAdmin/README.md) · [Android 실행 안내](GUI/UserMobile/AndroidApp/README.md)

Google 로그인을 쓰려면 Git에서 제외되는 `.env`에 Google Cloud의 Web 클라이언트 ID를 `AMO_GOOGLE_CLIENT_ID`로 넣습니다. Android도 검수한다면 등록된 Android 클라이언트 ID를 `AMO_GOOGLE_ALLOWED_AUDIENCES`에 넣습니다. 여러 서명은 등록한 ID를 쉼표로 구분합니다. Google Cloud의 Web 클라이언트에 실제 Vue 접속 주소를 JavaScript 원본으로 등록하고, 변경 후 `docker compose up -d main-control`을 실행합니다. 브라우저 기반 로그인을 쓰는 PyQt와 관리자 Web은 승인된 AMO 운영 계정에 같은 이메일의 Google 계정이 연결되어 있어야 합니다.

Android에서 Google로 로그인한 승객에게 운영자 권한도 부여하려면 관리자가 **회원·권한**에서 승객의 이메일을 검색한 뒤 **Google 운영자 추가**를 선택합니다. 승객 계정과 운행 이력은 유지됩니다. 같은 Google 계정으로 Android에 로그인하면 승객 세션이, 관리자 Web이나 PyQt의 브라우저 로그인으로 접속하면 별도로 승인된 운영자 세션이 발급됩니다.

강의실 `demo` 세션은 로그인 또는 PyQt 연결 시점부터 12시간 유지됩니다. 일반·Google 로그인에 같은 기준을 적용하며, 데모 브라우저 쿠키는 세션 쿠키입니다. 브라우저의 세션 복원 설정에 따라 쿠키가 복원될 수 있습니다. 데모 이외의 세션은 20분입니다.

## 같은 Wi-Fi에서 공용 서버에 직접 연결하기

진행자 노트북에서 기존 AMO 서버와 PostgreSQL을 실행하고, 강의실 접속용 HTTPS 및 IF-03 TLS 포트를 엽니다. 팀원은 각 노트북의 FMS·Admin과 Android 앱에서 공용 서버에 연결합니다. [진행자 설정, 팀원 실행 및 Google 로그인 DB 저장 항목](docker/classroom-lan.md)

## 데모로 어디까지 확인할 수 있나요?

별도 AMO Admin의 **시나리오 검수** 탭에서 Taxi의 선결제, 경로 적용, 연결 복구를 단계별로 재생합니다. FMS는 확정 지도에서 현재 검수 차량을 표시하며, 호출·운행·결제 기록은 같은 DB의 검수 전용 스키마에 저장됩니다. [시나리오 검수 실행](GUI/MainControllerPC/AMOAdmin/README.md#단계별-시나리오-검수)

- 편도 호출에서 모의 견적과 선결제를 확인할 수 있습니다. 모의 탑승·주행·하차를 순서대로 넣으면 최종 요금과 영수증이 한 번 기록됩니다. 차량·설비에 명령을 보내는 기능은 비활성입니다.
- `demo` 설정에서만 가상 차량·상태·이력·시험 점수를 넣습니다. `PINKY-01`~`PINKY-04`는 화면에 각 차량의 위치·방향·속도를 표시할 때 쓰는 시험 ID입니다. 네 대 모두 배차를 꺼 둡니다. `DEMO-REPLAY-01`은 모의 운행과 충전 증빙을 따로 검증하는 가상 차량입니다.
- 변경 견적을 수락하고 필요한 모의 차액 결제에 성공하면 모의 IF-04 명령 기록을 만들 수 있습니다. 일치하는 적용 보고 뒤에만 FMS와 Android에 적용 목적지가 표시됩니다. 충전칸 점유·충전 시작·70% 도달·시설 이탈과 운영 이력은 각각 확인합니다. [수정 시나리오 로컬 검증](tests/integration/README.md#개정-시나리오-로컬-검증)
- 운행 이력 #2에는 저장한 경로가 있습니다. 대기 중인 이력 #1에는 경로가 없습니다.
- 실제 LiDAR·Vision 위치 추정, 자동 배차·안전 정지, 실물 연결과 운행 이력 수집은 별도 시험이 필요합니다.

## 교차로 혼잡 예측 실험

확정 도면의 교차로 한 곳에서 모의 차량 4대의 로그를 생성해 10초·30초 뒤 대기열과 대기시간을 평가합니다. 생성한 결과 파일을 FMS에서 재생할 수 있습니다. [실험 실행과 FMS 확인](experiments/deepfleet/README.md)

## 회의 안건별 적용 기준과 다시 확인할 일

[회의 반영표](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/9142410)의 순서입니다. 아래 Python 파일은 모두 `tests/integration/`에 있고, Java 클래스는 Main Control에 있습니다.

| 회의 안건 | 현재 적용한 개발·모의 기준과 위치 | 결정 뒤 재검증 |
| --- | --- | --- |
| **1. 정지·재접속·개별 회수** | PyQt의 조작 버튼은 화면에서 미리보기만 합니다.<br>`one_way_operations.py`는 차량 ID와 접속이 새로 열릴 때마다 바뀌는 연결 세대를 기준으로 모의 결과를 확인합니다.<br>실제 IF-04·05 연결은 미구현입니다. | 지정한 차량만 정지하는지, 다시 연결한 뒤 이전 명령이 무효인지, 탑승을 확인한 뒤 지정 차량만 회수하는지 확인합니다. |
| **2. 탑승 확인과 출발 승인 A-02** | `one_way_trip.py`에서 같은 운행·배정·차량으로 만든 시험용 확인 신호를 사용합니다.<br>운영에서 쓰는 신호는 미구현입니다. | 확인이 없거나 오래됐거나 다른 배정의 것이면 출발을 막는지 확인합니다.<br>명령을 받았다는 응답과 차량이 실제로 출발했다는 보고도 구분합니다. |
| **3. 교차로·신호·위치** | `one_way_operations.py`는 시험용 교차로 신호를 씁니다.<br>`OperationsRepository`는 차량 네 대의 저장된 위치를 읽습니다.<br>실제 위치 추정과 IF-06은 미구현입니다. | 녹색 신호이고 교차로가 비었으며 출구에 여유가 있을 때만 진입을 허가하는지 확인합니다.<br>앞차가 완전히 나가기 전에는 다음 차가 대기해야 합니다.<br>네 대의 위치와 방향도 동시에 확인합니다. |
| **4. 메시지·인증·운영 연결 A-01·05** | IF-02·03은 메시지 앞에 데이터 길이를 붙인 개발용 JSON을 쓰고, Android는 개발용 HTTP로 접속합니다.<br>JWT는 로그인 뒤 발급받는 접속 증표입니다.<br>직원 브라우저 SSO는 한 번 쓰는 코드와 PKCE 확인 절차를 거칩니다.<br><br>`RideService`는 앱이 보낸 호출 시각과 DB가 기록한 접수 시각을 분리합니다.<br>이전 앱이 호출 시각을 보내지 않으면 빈 값으로 둡니다.<br>ESP32 입력은 모의 시험용입니다. | 운영 연결 경로, 권한과 로그아웃 범위, 시각 출처, 중복·재연결·재시도를 확인합니다.<br>암호화 연결(TLS), 메시지 전달 설정(QoS), 실제 Google 계정 로그인도 검증합니다. |
| **5. 배차·시설·충전 A-04** | `one_way_intake.py`와 `one_way_depot.py`에서 예상 도착 시간과 시설 상태를 모의로 확인합니다.<br>격리 데모는 모의 복귀·충전 증빙을 저장합니다. 실제 배차와 IF-10 전송은 팀 계약에 따릅니다. | 예상 시간이 같을 때의 순서, 배터리 잔량, 칸 점유와 이탈을 확인합니다.<br>충전 70%에 대기 상태로 바뀌는 일과 배차 자격 판정을 구분합니다.<br>기존 작업을 끝낸 복귀 차량은 새 운행으로 안전하게 전환할 수 있을 때 배차 적격인지 모의로 확인합니다. |
| **6. 관제 영상 가림과 열람** | `AMOAIInterface/`와 `Vision/`은 기본 구조가 있습니다.<br>IF-07·08·09 영상 전달은 미구현입니다. | 누가 영상을 볼 수 있는지, 얼굴 가림이 실패하면 표시를 막는지, 원본을 어떻게 보관하고 누가 열람하는지 확인합니다. |
| **7. 모의 요금·결제** | 격리 데모는 편도 요청에 최초 견적과 모의 선결제를 연결하고 하차 후 영수증을 한 번 발행합니다. 원래의 메모리 검증은 회귀 시험으로 남습니다. | 서비스별 요율과 결제 상태, 값이나 수단이 없을 때의 보류, 실패 후 재시도를 확인합니다. |
| **8. 호출 취소·미탑승** | `stage_two_cancellation.py`는 픽업 장소에 정차한 뒤 시험용 만료를 넣습니다.<br>같은 배정에서 정차와 작업 해제가 일어나는지 확인합니다. | 승객이 누른 취소와 미탑승 만료가 겹칠 때의 순서를 확인합니다.<br>기존 작업을 해제한 뒤 배정이 한 번만 끝나야 합니다. |
| **9. 운행 중 목적지 변경** | `stage_two_route.py`와 `stage_two_planning.py`는 시험용 배터리 한계와 경로 새 버전을 다룹니다.<br>IF-04로 새 경로가 실제 적용됐다는 보고가 오기 전에는 기존 경로를 유지합니다. | 가장 최근에 유효한 경로만 반영하는지 확인합니다.<br>IF-05로 정차와 재출발을 각각 확인합니다. |
| **10. 렌트 목적지·시간·반납 A-03** | `stage_three_rental.py`는 SR-002에 맞춰 처음에 목적지를 받지 않습니다.<br>같은 배정의 모의 차량 인수 확인 시점부터 이용 시간을 잽니다. | 시작·만료 시점, 정차·하차, 필요한 경우 주차칸 이탈을 각각 확인합니다. |
| **11. Cargo 인계·분리·회수 A-04** | `stage_three_cargo.py`는 지정 위치에서 같은 카트를 분리했는지, 차량이 일반 주행 설정으로 돌아왔는지 따로 확인합니다.<br>IF-13은 연결 제안입니다. | 분리 실패 또는 미확인 상태에서 정상 종료와 재사용을 막는지, 어떤 조건에서 차고지로 바로 갈 수 있는지 확인합니다. |
| **12. 분실물 사진·알림·정정** | `stage_three_lost.py`는 시험용 사진 참조와 판정을 씁니다.<br>대상마다 모의 알림을 기록하고 같은 건을 두 번 보내지 않는지 확인합니다. | 같은 운행의 사진과 열람 권한을 확인합니다.<br>알림이 실패한 대상에게만 다시 보내고, 판정 정정 뒤에는 아직 보내지 않은 알림을 보류하는지 확인합니다. |

기준 문서와 연계 자료는 아래에서 확인할 수 있습니다. [사용자 요구사항 UR](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/2883600) · [시스템 요구사항 SR](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/557330) · [시스템 아키텍처 SA](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/360590) · [상태 아키텍처](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8192050) · [시스템 시나리오](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8028678) · [인터페이스 명세](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8028663)

## 개발 표준 검사

포매터가 만든 줄바꿈을 기준으로 직접 쓴 구현·시험 소스의 물리적 줄을 셉니다. 빈 줄과 주석을 포함해 파일당 200줄까지 허용합니다. 승인된 예외는 없습니다. 단, 외부에서 받은 Gradle Wrapper와 도구가 만든 잠금 파일·빌드 결과, 지도 이미지 같은 정적 자산은 직접 작성한 소스가 아닙니다. [모듈화와 200줄 기준](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/4653058) · [공통 개발 표준 및 기술별 기준](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/4358173)

각 기술의 포맷을 검사한 뒤 저장소 루트에서 줄 수를 확인합니다.

```sh
python3 tests/integration/check_source_lines.py
```

- **Python** Python 3.12.8에서 잠긴 Ruff 0.14.4로 포맷과 린트를 검사합니다. PyQt 시험은 앱 폴더에서 실행합니다. 통합 모의 시험은 저장소 루트에서 실행합니다.
- **Java** 두 서버 모듈에서 JDK 21과 Maven으로 `mvn spotless:check verify`를 실행합니다.
- **Android** Android 앱 폴더에서 JDK 21과 SDK 36으로 `./gradlew :app:ktlintCheck :app:lintDebug :app:testDebugUnitTest :app:assembleDebug`를 실행합니다.
- **Vue** 관리자 Web 폴더에서 `npm ci` 후 `npm run check && npm test && npm run build`를 실행합니다. 공통 개발 표준과 저장소의 Prettier 설정을 사용합니다.

<details>
<summary>기존 기본 파일 24개 (46043e4 기준)</summary>

```text
Device/AMODepot/ChargingStationKit/ChargingController/README.md
Device/AMODepot/DepotServer/DepotService/amode_depot/config/README.md
Device/AMODepot/DepotServer/DepotService/amode_depot/launch/README.md
Device/AMODepot/DepotServer/DepotService/amode_depot/package.xml
Device/AMODepot/ParkingStationKit/ParkingController/README.md
Device/AMOVehicle/AmoControlBoard/CameraStreamer/README.md
Device/AMOVehicle/AmoControlBoard/DrivingController/amode_driving/config/README.md
Device/AMOVehicle/AmoControlBoard/DrivingController/amode_driving/launch/README.md
Device/AMOVehicle/AmoControlBoard/DrivingController/amode_driving/package.xml
Device/SignalKit/SignalController/LEDController/README.md
GUI/MainControllerPC/AMOAdmin/pyproject.toml
GUI/MainControllerPC/AMOAdmin/src/amo_fms/README.md
GUI/UserMobile/AndroidApp/app/src/README.md
GUI/UserMobile/AndroidApp/settings.gradle.kts
Server/AMOAIServer/AMOAIInterface/README.md
Server/AMOAIServer/Vision/README.md
Server/AMOMainServer/AmoDB/migrations/README.md
Server/AMOMainServer/AmoMainControlService/pom.xml
Server/AMOMainServer/AmoMainControlService/src/README.md
Server/WebServer/AmoWebService/backend/pom.xml
Server/WebServer/AmoWebService/backend/src/README.md
Server/WebServer/AmoWebService/frontend/admin/README.md
maps/README.md
tests/integration/README.md
```

</details>
