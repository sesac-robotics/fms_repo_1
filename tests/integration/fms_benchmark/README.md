# AMO FMS 관리자 조회 비교

별도 PyQt FMS를 실행하고, 관리자 조회를 함께 실행하는 조건에서는 Admin(PyQt)
또는 Admin(Web)을 사용합니다. 같은 가상 차량 입력, PostgreSQL 데이터,
읽기 전용 IF-03으로 비교합니다.

## 준비

- 팀 저장소 루트에서 시작합니다. Python 3.12.8과 uv, JDK 21, Maven,
  PostgreSQL 17, Node와 로컬 Chrome을 준비합니다.
- 저장소 밖 비공개 디렉터리에 독립 PostgreSQL 인스턴스를 실행하고
  `amo_bench` 데이터베이스를 준비합니다. 클라이언트와 서버는 루프백을 사용합니다.
- 팀 README의 Main Control과 Web 게이트웨이 명령으로 두 서버를 빌드·실행합니다.
  Main Control의 JDBC 주소는 이 인스턴스를 가리키고 `demo` 프로필을 씁니다.
  개발 IF-02·IF-03 포트를 기존 실행과 겹치지 않게 지정합니다.
  Main의 비공개 HTTP 포트는 `--server.port=0`으로 고정해 Web의
  `SERVER_PORT` 환경 변수가 Main의 포트로 전달되는 충돌을 피합니다.
- 관리자 Web 폴더에서 `npm ci`를 실행한 뒤
  `AMO_API_URL=http://127.0.0.1:<gateway> npm run dev`로 실행합니다.
- 별도 경로에 Playwright Core를 설치하고 `AMO_BENCH_PLAYWRIGHT`에
  해당 패키지의 `index.mjs` 절대 경로, `AMO_BENCH_CHROME`에 Chrome 실행
  파일 경로를 설정합니다. 벤치마크에서는 로컬 Chrome 창을 실제로 엽니다.

## 합성 데이터

아래 `psql`은 격리 인스턴스의 소켓 또는 호스트, 포트, 사용자를 명시해
실행합니다. SQL 파일은 `amo_bench` 데이터베이스 이름을 확인합니다.
Main Control이 Flyway를 적용한 뒤 빈 데이터의 DB 크기를 먼저 기록합니다.

```sh
psql -X -d amo_bench -c 'SELECT pg_database_size(current_database())'
psql -X -d amo_bench -v first=1 -v last=100000 -f tests/integration/fms_benchmark/passengers.sql
psql -X -d amo_bench -v first=100001 -v last=1000000 -f tests/integration/fms_benchmark/passengers.sql
psql -X -d amo_bench -f tests/integration/fms_benchmark/history.sql
```

승객 적재는 지정 범위의 ID를 새로 만들기 때문에 같은 범위를 다시 적재하려면
새 시험 DB를 만듭니다. 100만 명 결과는 10만 명에 90만 명을 추가한 결과입니다.
운행 요청 10만 건, 관련 운영 이벤트 30만 건, 시험 결과 이력 1만 건은
회원 적재와 구분합니다. 원시 로그와 DB 디렉터리는 저장소 밖에 보관합니다.

## 비교 실행

`AMO_FMS_API`는 Web 게이트웨이, `AMO_FMS_TCP_PORT`는 IF-03,
`AMO_ADMIN_WEB_URL`은 Vue 주소입니다. `AMO_BENCH_SERVER_PIDS`에
Main, 게이트웨이, PostgreSQL 부모 PID를 이 순서대로 쉼표로 나열합니다.
`AMO_BENCH_DEMO_PASSWORD`는 격리 DB에 설치된 가상 관리자 암호입니다.
`psql` 접속 옵션과 출력 경로는 실제 격리 환경의 값으로 교체합니다.

```sh
python3 tests/integration/fms_benchmark/run.py --repeats 3 --duration 45 \
  /path/to/evidence -- psql -h /path/to/socket -p 15432 -U amo_bench -d amo_bench
python3 tests/integration/fms_benchmark/summarize.py /path/to/evidence > /path/to/summary.json
```

각 반복에서 다음 세 조건의 실행 순서를 회전합니다.

| 조건 | 관제 | 관리자 |
| --- | --- | --- |
| baseline | 기존 PyQt FMS | 검색 없음 |
| web | 기존 PyQt FMS | 별도 관리자 Web |
| standalone | 기존 PyQt FMS | 별도 관리자 PyQt |

독립 관리자 PyQt의 HTTP 응답은 `admin.jsonl`에 따로 기록합니다.
이전 통합 모드의 측정값을 포함한 보고서는 당시 실측 기록으로 보존합니다.
새 실행에는 별도 출력 경로를 사용합니다.
차량 4대의 1초 간격 표본과 기존 7.5초 폴링을 사용합니다.
관리자 부하 조건은 45초 동안 회원·운행·시험 검색을 각각 2회, 페이지당 50건,
동시 검색 1건으로 실행합니다. 실제 Web 메뉴 이동은 메뉴별 자동 조회를
동반할 수 있으며 Web 기록에는 검색 요청과 자동 조회가 모두 남습니다.
검색 비교에는 같은 입력의 명시적 검색만 포함합니다.
서버 인증과 활성 세션은 계속 적용되며, Qt 자동 드라이버는 개발용 직접
로그인을 사용합니다.

아래 명령을 저장소 루트에서 실행하면 FMS와 Admin의 브라우저 로그인과 첫
화면을 격리된 시험 환경의 별도 프로세스에서 검증합니다.

```sh
uv run --locked --project GUI/MainControllerPC/AMOAdmin \
  python tests/integration/fms_benchmark/desktop_smoke.py /path/to/evidence
```

`--client fms` 또는 `--client admin`을 지정하면 한 앱만 검증합니다.

## 지표

- 지연은 PostgreSQL에 입력된 수신 시각부터 Qt 지도 페인트 처리 완료까지입니다.
  클라이언트와 DB가 같은 호스트에서 실행되며 갱신 공백은 단조 시계로 잽니다.
  창 시스템이 화면에 픽셀을 내보낸 물리적 시각은 측정하지 않습니다.
- 표시 누락은 조회 응답에 있었으나 해당 실행 중 지도에 그려지지 않은 순번입니다.
  조회 사이에 덮인 표본은 별도 지표에 들어갑니다. 관제 상태 API는 최신값 폴링입니다.
- 원시 디렉터리에는 표본별 수신·조회·페인트, 관리자 HTTP 응답, 프로세스 CPU·RSS
  표본과 PostgreSQL 누적 통계의 전후 값이 들어갑니다. RSS 합계에는 공유 메모리가
  중복 포함될 수 있습니다. 예비 시험과 정식 시험은 독립 출력 디렉터리를 씁니다.
- 결과는 단일 맥의 개발용 루프백 조건입니다. 운영 허용 지연·갱신 누락 기준은
  팀에서 결정합니다.
