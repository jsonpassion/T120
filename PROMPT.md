# LLM 콘텐츠 생성 프롬프트 모음

아무 LLM에나 그대로 복붙해서 쓰는 프롬프트 2종입니다.
**순서**: ① 커리큘럼 설계 → (사람이 검토·확정) → ② 유닛 파일 생성 (권당 1회 반복).
생성 후에는 반드시 `python3 tools/validate_content.py`로 검증하세요 (0 errors 필수).

---

## 프롬프트 ① — 커리큘럼 설계 (난이도별 · 도메인별 권 제목)

> 아래 전체를 복사해 붙여넣으세요. 결과 표를 검토·수정한 뒤 확정본을 프롬프트 ②에 사용합니다.

```
당신은 TOEFL 어휘 교재 커리큘럼 설계자입니다. 점수대(밴드) 4개 × 권(unit) 10개 = 총 40권의
단어책 커리큘럼을 설계하세요. 각 권은 100단어이며, 앱의 책장에 도메인 제목으로 표시됩니다.

[밴드 정의]
- score-000-060 (level 1, beginner):      목표 ~60점. 기초 학술 어휘와 캠퍼스 생활 필수 어휘.
- score-061-080 (level 2, intermediate):  목표 61-80점. 리딩/리스닝 빈출 중급 학술 어휘.
- score-081-100 (level 3, upper-intermediate): 목표 81-100점. 강의·지문의 분야별 핵심 학술 어휘.
- score-101-120 (level 4, advanced):      목표 101-120점. 고난도 학술 어휘, 뉘앙스 동사, 라이팅 고급 표현.

[설계 규칙]
1. 각 권에는 unit_title(영문 도메인명, 1-3단어)과 한국어 부제(테마 설명)를 붙입니다.
   예: "Biology" / "생물학 — 세포·생태·진화".
2. 도메인은 실제 TOEFL 지문·강의 출제 분야에서 고릅니다:
   자연과학(Biology, Astronomy, Geology, Chemistry, Physics), 사회과학(Psychology,
   Economics, Sociology, Anthropology), 인문(History, Art, Archaeology, Literature,
   Linguistics), 캠퍼스 생활(Campus Life, Lectures & Labs), 학술 기능어(Academic Verbs,
   Research & Data, Argument & Logic, Transitions) 등.
3. 낮은 밴드일수록 캠퍼스 생활·기능어 비중을 높이고, 높은 밴드일수록 전문 분야 비중을
   높이세요. 같은 도메인이 여러 밴드에 등장해도 됩니다 (예: Biology I → Biology II처럼
   심화되는 구조 권장. 이 경우 unit_title은 "Biology"와 "Biology II"처럼 구분).
4. 밴드 내 10권의 도메인은 서로 겹치지 않게 하세요.
5. 각 권의 100단어가 무엇으로 채워질지 예상 가능하도록 부제를 구체적으로 쓰세요.

[출력 형식] — 아래 마크다운 표만 출력하세요. 다른 설명 금지.
| band_id | unit | unit_title | 한국어 부제 |
|---|---|---|---|
| score-000-060 | 001 | Campus Life | 캠퍼스 생활 — 수강신청·기숙사·도서관 |
| ... | ... | ... | ... |
(총 40행: 밴드 4개 × unit 001~010)
```

---

## 프롬프트 ② — 유닛 파일 생성 (권당 1회)

> `{{ }}` 자리표시자 4곳을 채운 뒤 전체를 복사해 붙여넣으세요.
> `{{EXISTING_WORDS}}`에는 **같은 밴드**에 이미 존재하는 단어 전체를 콤마로 나열합니다
> (`grep -h '^- ' content/voca/{{BAND_ID}}/*.md | cut -d'|' -f1 | sed 's/^- //;s/ *$//'` 로 추출).

```
당신은 TOEFL 어휘 교재 저자입니다. 아래 규격을 정확히 지켜 단어책 1권(마크다운 파일 1개)을
통째로 작성하세요. 출력은 파일 내용 그 자체만 — 코드펜스나 설명 없이.

[이번 권 정보]
- band_id: {{BAND_ID}}            (예: score-081-100)
- unit 번호: {{UNIT_NUMBER}}       (예: 003 → 파일명 unit-003.md, id 접미사 u003)
- unit_title: {{UNIT_TITLE}}       (예: Astronomy)
- 테마: {{THEME_KO}}               (예: 천문학 — 행성·항성·우주 탐사)

[파일 규격 — 그대로 따를 것]
1. 파일은 YAML frontmatter로 시작:
---
id: voca-{밴드 숫자부}-u{unit 3자리}     (예: voca-081-100-u003)
type: voca
level: {1|2|3|4}                        (밴드 순서: 000-060=1, 061-080=2, 081-100=3, 101-120=4)
difficulty: {beginner|intermediate|upper-intermediate|advanced}
tags: [toefl, vocabulary, unit-{번호}, {도메인 소문자}]
source: t120
version: 1
updated_at: {오늘 날짜}T00:00:00Z
score_band_id: {band_id}
score_min: {밴드 최소 점수}
score_max: {밴드 최대 점수}
unit_title: {{UNIT_TITLE}}
---
2. frontmatter 다음: 빈 줄 + 제목 한 줄
   `# {레벨 한국어명} {권번호}권 — {{UNIT_TITLE}} ({테마 요약}) 100`
3. 이어서 단어 줄 **정확히 100줄**. 각 줄은 6필드, 구분자는 ` | `:
   `- word | 한국어 뜻 | /IPA/ | 암기 힌트 | English example | 예문 번역`

[단어 줄 세부 규칙]
- word: 소문자 단어 또는 짧은 구(콜로케이션). TOEFL 리딩·리스닝·라이팅 실제 빈출 어휘만.
- 한국어 뜻: 간결하게. 필요 시 괄호로 문맥 표시. 예: "가설", "(생물) 개체군".
- IPA: 미국식 발음기호를 / / 안에.
- 암기 힌트: 한국어 학습자용 — 어원 분해(photo(빛)+synthesis(합성)), 연상, 한글 발음
  연결 중 하나. 15자 내외로 짧게.
- example: 학술 지문·강의·캠퍼스 대화 톤의 자연스러운 한 문장 (8-12단어).
- 번역: 예문의 자연스러운 한국어 번역.
- 어떤 필드에도 파이프 문자(|)를 추가로 쓰지 말 것 (구분자 전용).

[중복 금지 — 가장 중요]
- 아래 [기존 단어 목록]에 있는 단어와 word 필드가 한 글자라도 같으면 절대 사용 금지.
- 이번 권 100단어 안에서도 중복 금지.
- 표제어의 단순 변형(파생어)은 허용되지만 남용 금지 (기존에 analyze가 있으면 analysis는
  가능하나, 되도록 새 어휘를 선택).

[기존 단어 목록 — 같은 밴드에 이미 있는 단어들]
{{EXISTING_WORDS}}

[자체 검증 후 출력]
출력 직전에 스스로 확인: ① 단어 줄이 정확히 100줄인가 ② 모든 줄이 6필드인가
③ 기존 목록·권 내 중복이 없는가 ④ frontmatter 필드가 규격과 일치하는가.
확인이 끝나면 파일 내용만 출력하세요.
```

---

## 생성 후 체크리스트

```bash
python3 tools/validate_content.py   # 0 errors 필수 (100단어, 6필드, 밴드 내 중복)
python3 tools/build_manifest.py     # manifest.json 재생성
git add content/ manifest.json && git commit && git push
```

- 검증기가 중복·수량 오류를 잡으면 해당 줄만 교체 후 재검증.
- 밴드 간 중복은 경고(허용)이지만, 새 유닛이 경고를 새로 만들지 않게 하는 것을 권장.
