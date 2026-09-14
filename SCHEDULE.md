# schedule.json — 공식 시험 일정

앱의 **시험 일정** 시트(대시보드 D-day 칩 · 설정 › 학습 설정 › 시험일)가 읽는 파일이다.
리포 루트의 `schedule.json`을 앱이 `manifest` 옆 raw URL에서 받는다
(`https://raw.githubusercontent.com/jsonpassion/<Repo>/main/schedule.json`). **main 에 push = 배포**.

- 앱 리더: `NINE90/Models/ExamSchedule.swift` (+ `ExamScheduleStore.swift`, `ExamScheduleView.swift`)
- 검사기: `python3 tools/validate_schedule.py` — **에러 0 이어야 push**. 검사 뒤에 **앱 화면 그대로의 목록(app view)** 을 찍는다
- 앱은 6시간마다(시트를 열면 5분마다) 다시 받고, 실패하면 마지막으로 받은 파일을 쓴다.

## 앱이 날짜를 다루는 규칙

기준은 **사용자 기기의 오늘 날짜(달력 날짜, 시각 무시)**다.

| 상황 | 앱 동작 |
|---|---|
| `examDate` 가 오늘 이후 | 목록에 표시, 선택 가능, D-day 계산 |
| `examDate` 가 **오늘(시험 당일)** 이거나 지난 날 | **무시** — 목록에서 빠지고 선택 불가 |
| 사용자가 고른 시험의 날이 됨 | D-day 칩 사라짐, 선택 해제, 예약된 알림 모두 취소 (자정·포그라운드 복귀 때 다시 판정) |
| 공식 날짜가 바뀜 (같은 `id`, 다른 `examDate`) | 사용자가 고른 시험의 날짜·제목이 새 값으로 따라감, 알림도 다시 예약 |
| 세션 한 줄의 날짜가 잘못됨 | 그 세션만 조용히 빠짐 (나머지는 정상) → 그래서 검사기가 필수 |
| `schema` 가 앱이 아는 것보다 큼 | 파일 전체 무시 (캐시 유지) |

그래서 지난 회차는 파일에 남아 있어도 앱에 해가 없지만, 검사기가 경고하니 갱신 때 지운다.

## 데이터 확인 = 앱과 같은 로직

`validate_schedule.py` 는 두 가지를 한다.
1. **규격 검사** (ERROR/WARN) — 앱보다 엄격하다. 앱이 조용히 버릴 줄(잘못된 날짜·타입)을 전부 에러로 드러낸다.
2. **app view** — 앱의 `ExamSchedule.swift` 와 **같은 읽기 규칙**으로, 그날 앱이 보여 줄 내용을 한 줄씩 찍는다.

```
TODAY 2026-09-14
SCHEDULE exam=TOPIK selfScheduled=0 updatedAt=2026-09-14
REGION KR default=1 countries=KR sessions=3
  SHOW 2026-106 2026-10-18 D-34 reg=open:2 windows=1 levels=all result=2026-11-27   ← 목록에 보임
  HIDE 2026-105 2026-09-14                                                          ← 시험 당일/지난 회차: 앱이 무시
DEVICE KR -> KR
DEVICE other -> KR                                                                  ← 목록에 없는 나라의 기본 지역
```
- `reg=` : `opens:N`(N일 후 접수 시작) · `open:N`(접수 중, N일 후 마감) · `closed` · `none`(접수 정보 없음)
- 읽을 수 없는 파일은 `UNREADABLE`, 앱보다 새 schema 는 `IGNORED` (둘 다 앱은 이전 캐시 유지)
- 특정 날로 보고 싶으면 `--today 2026-10-18` (예: 시험 당일에 목록에서 빠지는지), 목록만 보려면 `--app-view`
- 같은 로직임을 보증하는 장치: 앱 리포 `Tools/content-kit/parity/run.sh` 가 앱의 Swift 모델과 이 스크립트의 출력을 픽스처 × 여러 날짜로 diff 한다 (규칙을 한쪽만 바꾸면 실패). **앱이나 검사기의 읽기 규칙을 바꾸면 반드시 이걸 돌리고, 검사기를 6개 콘텐츠 리포에 다시 복사한다.**

접수 상태 태그(오늘 기준): 창 시작 전 `N일 후 접수 시작` · 창 안 `접수 중 · N일 후 마감`(마지막 날은 `오늘 마감`) · 모든 창 종료 `접수 마감`.
알림(사용자가 켠 경우, 오전 9시): 각 접수 창 시작일, 마감 전날, 시험 전날.

## 형식

```json
{
  "schema": 1,
  "exam": "TOPIK",
  "updatedAt": "2026-09-14",
  "officialURL": "https://www.topik.go.kr",
  "selfScheduled": false,
  "regions": [
    {
      "id": "KR",
      "name": {"ko": "한국", "en": "Korea", "ja": "韓国", "zh": "韩国", "vi": "Hàn Quốc"},
      "countries": ["KR"],
      "default": true,
      "officialURL": "https://www.topik.go.kr",
      "sessions": [
        {
          "id": "2026-106",
          "title": {"ko": "제106회", "en": "106th TOPIK"},
          "examDate": "2026-10-18",
          "registration": [
            {"start": "2026-08-26", "end": "2026-09-01"},
            {"label": {"ko": "추가 접수", "en": "Late registration"}, "start": "2026-09-08", "end": "2026-09-09"}
          ],
          "resultDate": "2026-11-27",
          "levels": ["topik-3", "topik-4", "topik-5", "topik-6"],
          "note": {"ko": "TOPIK II만 시행", "en": "TOPIK II only"},
          "url": "https://www.topik.go.kr/..."
        }
      ]
    }
  ]
}
```
(위 날짜·회차는 **형식 예시일 뿐 실제 일정이 아니다**.)

| 필드 | 필수 | 설명 |
|---|---|---|
| `schema` | ✅ | 항상 `1` |
| `exam` | ✅ | 시험 이름 (표시엔 앱의 `brand.examMark` 사용, 이 값은 사람이 읽는 용도) |
| `updatedAt` | ✅ | 이 파일을 공식 사이트와 대조한 날 `yyyy-MM-dd` — 시트 하단 "업데이트" |
| `officialURL` | 권장 | 지역에 `officialURL` 이 없을 때 쓰는 공식 일정 페이지 (https) |
| `selfScheduled` | – | `true` = 정해진 회차 없이 원하는 날 예약하는 시험(TOEFL iBT). `sessions` 는 비워 두고, 앱은 공식 링크 + 날짜 직접 입력만 보여 준다 |
| `note` | – | 시험 전체 안내 (현재 앱 미표시, 예약 필드) |
| `regions[].id` | ✅ | 지역 키 (`KR`, `VN`, `US`, `GLOBAL` …) — 사용자가 고른 지역으로 저장되므로 바꾸지 말 것 |
| `regions[].name` | ✅ | 지역 이름 (지역이 2개 이상이면 시트에 지역 메뉴가 뜬다) |
| `regions[].countries` | 권장 | ISO 3166 2글자. 기기 지역이 여기에 있으면 그 지역이 기본 선택 |
| `regions[].default` | – | 기기 지역이 어느 곳에도 없을 때 기본 (최대 1개, 없으면 첫 지역) |
| `regions[].officialURL` | 권장 | 그 지역 접수 사이트 — **날짜 고르는 곳 바로 위의 "공식 사이트에서 일정 확인" 버튼**이 연다 |
| `sessions[].id` | ✅ | 회차 키. **한 번 정하면 바꾸지 말 것** (사용자 선택이 이 id 로 연결되어 날짜 변경을 따라감). 권장: `YYYY-회차` 또는 `YYYY-MM-DD` |
| `sessions[].title` | ✅ | `"제106회"` 또는 `{lang: text}` |
| `sessions[].examDate` | ✅ | 시험일 (여러 날이면 첫날) |
| `sessions[].registration` | – | 접수 창 목록 `{start, end, label?}`, `end` 는 시험일 이전. 정기/특별추가 접수처럼 여러 개 가능 |
| `sessions[].resultDate` | – | 성적 발표일 (시험일 이후) |
| `sessions[].levels` | – | 이 회차가 다루는 밴드 id (`content/…/voca/<band>` 폴더명). 생략 = 전 급수. 사용자 급수와 안 맞으면 흐리게 표시 |
| `sessions[].note` · `url` | – | 짧은 안내 · 회차 공지 링크 (https) |

텍스트 필드는 문자열 하나 또는 `{"ko": …, "en": …, "ja": …, "zh": …, "vi": …}`. 없는 언어는 en → ko 순으로 대체.

## 갱신 절차 (예약 작업이 할 일)

1. 이 리포의 `schedule.json` 과 `regions[].officialURL`(없으면 `officialURL`)의 **공식 페이지만** 대조한다. 블로그·학원 요약은 쓰지 않는다.
2. 오늘 이후 회차를 추가·수정한다. 공식 발표가 아직 없으면 **추측해서 넣지 않는다** (비워 두면 앱은 공식 링크 + 직접 입력을 보여 준다).
3. 시험일이 오늘이거나 지난 회차는 지운다.
4. 기존 회차의 날짜가 바뀌었으면 `id` 는 그대로 두고 날짜만 고친다.
5. `updatedAt` 을 오늘로.
6. `python3 tools/validate_schedule.py` → 에러 0 확인 (경고는 읽고 판단).
7. 변경이 있을 때만 `git commit -m "Schedule: <요약>" && git push`.

### 예약 작업용 붙여넣기 프롬프트

```
이 리포(현재 디렉토리)의 schedule.json 을 공식 시험 일정과 맞춰 갱신하라. 규격과 규칙은 SCHEDULE.md.
- 오늘 날짜를 확인하고, 각 region 의 officialURL(없으면 최상위 officialURL) 공식 페이지에서만 일정을 읽는다. 공식 발표가 없는 회차는 넣지 않는다.
- 오늘 이후 회차의 시험일·접수 기간(추가 접수 포함)·성적 발표일을 반영하고, 시험일이 오늘이거나 지난 회차는 지운다.
- 이미 있는 회차는 id 를 바꾸지 말고 날짜만 고친다. 새 회차 id 는 SCHEDULE.md 권장 형식.
- 제목·지역 이름은 ko/en/ja/zh(+HSK 리포는 vi) 로 쓴다.
- updatedAt 을 오늘로 바꾸고 python3 tools/validate_schedule.py 가 에러 0 인지 확인한다.
- 실제로 바뀐 내용이 있을 때만 커밋하고 main 에 push 한다. 무엇을 바꿨는지(회차·날짜·출처 URL) 요약해 보고한다.
```

## 시험별 메모

| 리포 | 시험 | 지역 | 비고 |
|---|---|---|---|
| NINE90 | TOEIC (정기시험) | KR | 접수 창을 정기 접수 / 특별추가 접수로 나눠 `label` |
| T120 | TOEFL iBT | GLOBAL | `selfScheduled: true`, 세션 없음 |
| T600 | TEPS (정기시험) | KR | |
| J180 | JLPT | KR (+필요 시 JP 등) | 급수 전체 동시 시행이면 `levels` 생략 |
| K300 | TOPIK (PBT/IBT) | KR + 응시자 많은 해외 국가 | 해외는 국가마다 시행 회차·접수일이 다르므로 국가별 region. TOPIK I/II 분리 시행이면 `levels` |
| C300 | HSK | VN(기본) + KR | 지역마다 시행일·방식(PBT/IBT)이 달라 `note` 로 구분, 급수 제한 회차는 `levels` |
