# 🐹 장꾸 AI — 플로팅 버블 AI 펫

바탕화면 위를 떠다니는 안드로이드 AI 펫 앱입니다. 장꾸는:

- **플로팅 버블 펫** — 홈 화면 위 어디든 드래그해서 옮길 수 있고, 손을 떼면 화면 가장자리에 착 붙어요. 상태에 따라 표정도 바뀝니다 (🐹 대기 / 🤔 생각 중 / 😆 대화 중).
- **AI 챗봇** — 버블을 탭하면 채팅창이 열리고, Google Gemini API로 대화합니다.
- **스마트폰 제어** — 대화 중에 AI가 직접 폰을 조작합니다 (tool use).
  예: "손전등 켜줘", "볼륨 30으로 줄여줘", "유튜브 실행해 줘", "무음으로 바꿔 줘"
- **일정 리마인더** — "내일 아침 9시에 회의 알려줘"라고 말하면 리마인더를 등록하고 시간이 되면 알림을 보내줍니다. 재부팅해도 유지됩니다.
- **알림 읽기** — "요즘 온 알림 뭐 있어?"라고 물으면 다른 앱의 최근 알림을 요약해 줍니다 (알림 읽기 권한 필요).

## 스크린 구성

| 구성 요소 | 설명 |
|---|---|
| 설정 화면 (`MainActivity`) | API 키 입력, 권한 안내, 장꾸 시작/중지 |
| 플로팅 버블 (`PetOverlayService`) | 포그라운드 서비스 + `WindowManager` 오버레이 |
| 채팅 패널 | 버블 탭 시 열리는 대화 창 |

## AI가 사용할 수 있는 도구

| 도구 | 기능 |
|---|---|
| `toggle_flashlight` | 손전등 켜기/끄기 |
| `set_brightness` | 화면 밝기 조절 (0~100%) |
| `set_volume` | 미디어/벨소리 볼륨 조절 |
| `set_ring_mode` | 소리/진동/무음 전환 |
| `launch_app` | 앱 이름으로 검색해서 실행 |
| `open_url` | 브라우저로 URL/검색 열기 |
| `open_settings` | 와이파이·블루투스 등 설정 화면 열기 |
| `get_device_status` | 배터리·볼륨·밝기 등 상태 조회 |
| `create_reminder` / `list_reminders` / `delete_reminder` | 리마인더 관리 |
| `get_recent_notifications` | 최근 알림 요약 |

## 빌드 방법

요구 사항: Android Studio (또는 JDK 17+ 및 Android SDK 34)

```bash
./gradlew assembleDebug
# APK 위치: app/build/outputs/apk/debug/app-debug.apk
```

단위 테스트:

```bash
./gradlew testDebugUnitTest
```

## 사용 방법

1. **Gemini API 키 발급** — [Google AI Studio](https://aistudio.google.com/apikey)에서 무료로 API 키를 만듭니다 (`AIza...` 형식, 무료 티어 제공).
2. 앱을 설치하고 실행 → API 키를 입력하고 **키 저장**을 누릅니다.
   (키는 기기 내 `EncryptedSharedPreferences`에 암호화 저장되며 외부로 전송되지 않습니다 — Gemini API 호출에만 사용)
3. 권한을 켭니다:
   - **다른 앱 위에 표시** (필수) — 플로팅 버블 표시
   - **알림 표시** / **정확한 알람** — 리마인더 기능
   - **알림 읽기** (선택) — 다른 앱 알림 요약
   - **시스템 설정 변경** (선택) — 화면 밝기 제어
4. **🐹 장꾸 시작!** 버튼을 누르면 버블이 나타납니다.

### 실기기 테스트 체크리스트

- [ ] 버블이 표시되고 드래그 → 가장자리 스냅이 동작하는가
- [ ] 버블 탭 → 채팅 패널이 열리는가
- [ ] "안녕!" → 장꾸 페르소나로 답하는가
- [ ] "손전등 켜줘" → 플래시가 켜지는가
- [ ] "내일 9시에 회의 알려줘" → 리마인더 등록 → 시간에 알림 수신
- [ ] "요즘 온 알림 알려줘" → 알림 요약 (권한 허용 시)
- [ ] 재부팅 후 리마인더 알람이 유지되는가

## 기술 스택

- Kotlin, minSdk 26 (Android 8.0) / targetSdk 34
- [Gemini API](https://ai.google.dev/gemini-api/docs) (`gemini-2.5-flash`) — REST `generateContent` + function calling 에이전트 루프 (OkHttp)
- Room + AlarmManager — 리마인더 저장/알람
- `WindowManager` 오버레이 + Foreground Service — 플로팅 버블
- `NotificationListenerService` — 알림 읽기

## 주의 사항

- API 키를 앱에 직접 저장하는 BYO-key 방식은 **개인용 프로젝트** 전제입니다. 스토어 배포용이라면 서버 프록시를 두세요.
- Gemini 무료 티어 한도를 넘으면 요금이 발생할 수 있습니다. 짧은 대화 위주로 설계되어 있습니다 (`maxOutputTokens=2048`, 히스토리 자동 정리).
- 와이파이/블루투스는 최신 안드로이드에서 앱이 직접 토글할 수 없어, 해당 설정 화면을 열어주는 방식으로 동작합니다.
