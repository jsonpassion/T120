# T120 Content — TOEFL® 어휘 콘텐츠 리포

> **T120은 작업용 코드네임입니다** (만점 120에서 따옴; 앱 브랜드 확정 시 리포 이름과 함께 변경 가능).
> [NINE90](https://github.com/jsonpassion/NINE90)(TOEIC 트랙)과 동일한 콘텐츠 파이프라인을 쓰는
> TOEFL 트랙 리포지토리 — 앱은 manifest URL 하나로 이 리포의 콘텐츠를 통째로 동기화합니다.

**현재 상태: 규격 + 도구 + 샘플만 존재.** 실제 단어 콘텐츠는 아직 생성 전이며,
생성 방법은 [PROMPT.md](PROMPT.md)의 복붙용 LLM 프롬프트를 따릅니다.

## 구조

```
content/voca/{band}/unit-NNN.md   ← 1파일 = 1권 = 정확히 100단어 (10단어 = 1챕터)
tools/build_manifest.py           ← manifest.json 생성 (sha256, version = c-{hash12})
tools/validate_content.py         ← 형식·수량·중복 검증 (0 errors 필수)
manifest.json                     ← 앱이 읽는 콘텐츠 인덱스 (도구로만 생성, 손편집 금지)
PROMPT.md                         ← LLM으로 커리큘럼·유닛을 생성하는 복붙 프롬프트
```

## 점수 밴드 (TOEFL iBT 0–120)

| band_id | 레벨 | 라벨 | 성격 |
|---|---|---|---|
| `score-000-060` | 1 · beginner | ~60 | 기초 학술 어휘 · 캠퍼스 생활 |
| `score-061-080` | 2 · intermediate | 61–80 | 리딩/리스닝 빈출 중급 어휘 |
| `score-081-100` | 3 · upper-intermediate | 81–100 | 분야별 핵심 학술 어휘 |
| `score-101-120` | 4 · advanced | 101–120 | 고난도 어휘 · 라이팅 고급 표현 |

## NINE90 형식과의 차이 — `unit_title`

TOEIC 트랙은 권을 번호("N권")로 부르지만, TOEFL 트랙은 **도메인 제목의 책장**을 씁니다.
frontmatter에 `unit_title`(영문 도메인명, 예: `Biology`, `Campus Life`)이 **필수**이며,
앱 책장의 책 커버에 이 제목이 표시됩니다. manifest에도 `unit_title`로 포함됩니다.
그 외 단어 줄 형식은 NINE90 v2와 동일합니다:

```
- word | 한국어 뜻 | /IPA/ | 암기 힌트 | English example | 예문 번역
```

샘플: [content/voca/score-101-120/unit-001.md](content/voca/score-101-120/unit-001.md)
(형식 시연용 10단어 — 실제 유닛은 100단어).

## 콘텐츠 규칙

- 유닛당 **정확히 100단어**, 10단어 = 1챕터 (앱의 회독 단위)
- **밴드 내 중복 = 오류**, 밴드 간 중복 = 경고(허용 — 레벨이 올라가면 재등장 가능)
- 필드 안에 파이프(`|`) 금지 (구분자 전용)
- 카드 ID = `{파일 id}-{줄 번호}` — **출시 후 기존 줄의 순서 변경·삭제 금지**
  (사용자 학습 진도가 카드 ID에 매여 있음). 추가는 새 유닛 파일로.
- `manifest.json`의 `profile.free_chapters`(기본 3) = 권마다 무료로 열리는 챕터 수
  (앱이 원격 설정으로 읽음)

## 워크플로

```bash
# 1) 커리큘럼 설계 → PROMPT.md의 프롬프트 ① 사용, 표를 검토·확정
# 2) 권 생성     → PROMPT.md의 프롬프트 ② 사용 (기존 단어 목록 주입 필수)
# 3) 검증·배포
python3 tools/validate_content.py    # 0 errors 필수
python3 tools/build_manifest.py
git add content/ manifest.json && git commit -m "Add <band> unit-NNN" && git push
```

앱은 raw.githubusercontent.com의 manifest.json 버전 변경을 감지해 바뀐 파일만 내려받습니다
(sha256 검증 포함). raw CDN 캐시 특성상 push 후 매니페스트 반영까지 ~5분 걸릴 수 있습니다.

## 상표 고지

TOEFL®은 ETS(Educational Testing Service)의 등록 상표입니다. 이 리포지토리와 관련 앱은
ETS와 무관하며, ETS의 제휴·보증·승인을 받지 않았습니다. 모든 콘텐츠는 자체 제작이며
실제 기출문제를 포함하지 않습니다.

© 2026 ForgeLab
