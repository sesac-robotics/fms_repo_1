# AMO Android 사용자 앱

AMoDE 시험장 v0.2의 S1~S4 정류장에서 편도 호출을 요청하는 Android 앱입니다. 앱에서 호출을 접수하고, 서버가 확인한 배차·운행 상태와 이용 이력을 봅니다.

## 실행 준비

- JDK 21, Android SDK Platform 36, Android SDK Build Tools 36.0.0을 설치합니다. 앱은 Android 8.0(API 26) 이상을 지원합니다.
- Gradle Wrapper 9.6.1과 Android Gradle Plugin 9.3.1을 사용합니다. `JAVA_HOME`과 `ANDROID_HOME`은 설치 위치에 맞춥니다.
- Spring Boot API를 먼저 실행합니다. 에뮬레이터에서 기본 API 주소는 `http://10.0.2.2:8080`입니다. API가 다른 포트라면 빌드할 때 지정합니다.
- 다른 기기에서는 기기에서 접근할 수 있는 HTTPS 주소를 지정합니다. HTTP는 debug 빌드의 에뮬레이터와 루프백 주소에서만 허용합니다.

```sh
cd apps/mobile
AMO_API_URL=http://10.0.2.2:18085 ./gradlew :app:installDebug
./gradlew :app:ktlintCheck :app:lintDebug :app:testDebugUnitTest
```

Android Studio에서는 `apps/mobile`을 열어 SDK와 에뮬레이터를 지정합니다. 소스 포매팅은 `./gradlew :app:ktlintFormat`을 사용합니다.

## 화면과 계정

1. 이메일로 가입하거나 로그인합니다. 운영자 계정은 관리자 도구에서 사용합니다.
2. 첫 이용 안내에서 출발지·목적지 선택과 호출 확인 방법을 볼 수 있습니다. 설정에서 안내를 끄거나 다시 시작할 수 있습니다.
3. 호출 화면에서 출발지와 목적지를 고르고 호출합니다. 지도에서 정류장 위치를 확인할 수 있습니다. 현재 호출 상태와 새로고침은 지도 위에 표시됩니다. 진행 중인 호출과 이용 이력 화면은 열어 둔 동안 5초 간격으로 서버를 조회합니다.
4. 프로필에서 본인의 이름·이메일·회원 ID를 확인하고 로그아웃합니다. 언어는 한국어·English·简体中文, 테마는 시스템·라이트·다크 중에서 고릅니다.

맵과 로고는 저장소의 `maps/`에서 Android용 파일만 빌드에 포함합니다. 앱은 Android 메모리의 JWT를 API의 Bearer 헤더로 보내며, 세션이 만료되거나 앱 프로세스를 다시 시작하면 다시 로그인합니다.

## Google 로그인

Google Cloud에서 Android OAuth 클라이언트에 `com.amo.passenger`와 사용 중인 서명 인증서의 SHA-1을 등록합니다. Web OAuth 클라이언트 ID는 Spring Boot의 Google 설정에 지정합니다. 앱은 서버가 반환한 Web 클라이언트 ID를 Android Credential Manager에 넘기고, 받은 ID 토큰을 Spring Boot에서 검증합니다.

이메일로 이미 가입했다면 해당 계정으로 로그인한 뒤 프로필의 **Google 계정 연결**을 사용합니다. Google 설정이 없는 서버는 Google 기능을 사용할 수 없다는 메시지를 표시합니다.

[플랫폼별 단계와 화면](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8357019) · [Android/Kotlin 표준](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/4554759) · [맵 예시안 v0.2](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8192349)
