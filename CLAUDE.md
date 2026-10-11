@AGENTS.md

# 채널 운영 구조 — 아빠모해TV (단일 채널, 2개 콘텐츠 트랙)

이 레포는 **하나의 유튜브 채널(아빠모해TV)**을 운영한다. 그 안에 톤과 제작 방식이
서로 다른 두 콘텐츠 트랙이 있고, 아래 어떤 트랙에 대한 작업인지에 따라 적용되는
규칙(특히 톤)이 달라진다 — 두 트랙의 규칙을 섞어 쓰지 않는다.

| | **트랙 A: 세계 핫뉴스 쇼츠** | **트랙 B: 경제 뉴스 해설** |
|---|---|---|
| 제작 방식 | 완전 자동화 — `scripts/video_generator.py` + 매일 아침 자동 루틴(트리거) | Claude가 대본·기획 초안을 쓰고 사람이 검수/녹음해서 마무리 |
| 소재 | 전쟁·재난·국제 이슈 등 세계 뉴스 중 조회수 잠재력 높은 것 | 경제 뉴스가 내 지갑/생활에 미치는 영향 |
| 톤 | 차분한 뉴스 앵커체. 사실/미확인 주장 엄격 분리. 제목은 사실 기반 안에서 임팩트 있게(공포·충격 등 감정 반응도 선택 기준에 포함) | 친근한 설명형. **과장·공포 마케팅 금지**. 속보 경쟁 안 함 |
| 파일 규칙 | `scripts/episode_<YYYY-MM-DD>_<슬러그>.json` (video_generator.py가 바로 읽는 실제 렌더링 입력) | `economy/scripts/<YYYY-MM-DD>_쇼츠_주제.md` / `_롱폼_주제.md` (사람이 다듬을 초안 — 자동 렌더링 안 됨). 기획은 `economy/plans/`, 성과 기록은 `economy/tracking.csv` |
| 상세 규칙 | 이 파일 아래 "AI 협업 파이프라인 가이드" + `scripts/README.md` | `@youtube-guide.md` (아래 임포트) |

**판단 기준**: 요청이 "오늘 세계 뉴스 영상 만들어줘"류면 트랙 A 규칙(이 파일 + scripts/README.md)을,
"경제 채널 대본/기획/성과 분석"류면 트랙 B 규칙(`youtube-guide.md`)을 따른다. 모호하면
사용자에게 어느 트랙인지 먼저 확인한다. `youtube-guide.md`의 "항상 마지막에 '이번 주
당장 할 일' 제시" 같은 출력 규칙은 트랙 B 관련 답변에만 적용하고, 트랙 A 작업(일일
자동 루틴 보고, GitHub/코드 작업 등)에는 적용하지 않는다.

# 콘텐츠 작성 규칙 (트랙 A 에피소드 전원 항상 적용, 2026-10-11~)

이 섹션은 **소재를 고른 뒤 실제로 글을 쓰는 단계**의 규칙이다. "어떤 소재를 고를지"
걸러내는 선정 단계 규칙(`scripts/README.md`의 "뉴스 선정 — 제외 기준", 매일 자동
루틴의 [2단계] A/B/C 기준)과는 별개이며 서로 대체하지 않는다 — 선정 기준을 통과한
소재라도 이 작성 규칙을 통과하지 못하면(자기검증에서 "검수 필요"가 하나라도 남으면)
사람 확인 전까지 제목/설명/자막/내레이션에 반영하지 않는다. 위 "글로벌 톱 벤치마킹
기준 3. '팩트 기반'과 '실전 효용성' 중심의 검증"이 선언한 원칙("AI가 그럴듯하게
지어내지 않는다")을 트랙 A 에피소드 작성에 구체적으로 적용한 버전이다.

## 작업 순서

1. 웹 검색으로 서로 독립된 신뢰 출처 3곳 이상을 찾는다 (통신사·주요 언론·공식 성명
   우선). 사건 발생일과 오늘 날짜를 확인한다.
2. 출처에서 확인된 사실만 "사실 목록"으로 먼저 정리하고, 항목마다 출처 URL을 붙인다.
3. 제목·설명·자막·내레이션은 사실 목록에 있는 내용만으로 쓴다. 목록에 없는 문장은
   넣지 않는다.
4. 작성 후 자막/내레이션/설명문의 모든 문장을 자기검증한다 (아래 "자기검증" 참고).

## 작성 규칙

- 한쪽 당사자의 발표·주장은 사실로 쓰지 않고 "OO는 ~라고 주장/발표했다"로 쓴다.
  독립 확인이 안 되면 "독립적으로 확인되지 않았다"를 덧붙인다.
- 따옴표 인용은 출처 원문에서 확인된 것만 쓴다. 확인 안 되면 인용부호 없이 요약하거나
  뺀다.
- 숫자(사망·부상·인원·금액)는 출처가 엇갈리면 쓰지 않거나 "보도마다 다르다"로 쓰고,
  누가 발표한 수치인지 밝힌다.
- 인명·직함·지명은 영문 표기와 한국 주요 언론 표기를 모두 확인하고, 현재 직함인지
  전직인지 구분한다.
- 다른 날짜·다른 사건의 정보를 섞지 않는다. 비슷한 과거 사건이 있으면 사건일로
  구분한다.
- 사건 후 1일 이상 지났으면 [속보]를 쓰지 않는다.
- 기관·국가에 대한 비난·평가 표현은 쓰지 않는다. 입장은 주체별로 나눠 전달한다.
- 해시태그는 출처에서 확인된 고유명사만 쓴다.
- 설명문 끝에 근거 링크 1~2개를 넣는다.
- 기사 본문을 열 수 없어 확인하지 못한 내용은 쓰지 않고 "사람이 확인할 항목"으로
  분류한다. (scripts/README.md의 egress 프록시 차단 안내와 같은 맥락 — 막히면
  WebSearch 스니펫으로 대체하되, 스니펫만으로 확인 못 한 디테일은 쓰지 않는다.)

## 자기검증 (필수, 출력물에 포함)

| 구분(제목/설명/자막/내레이션) | 문장 | 근거 출처 URL | 사실/주장 | 확인 상태(확인됨/불확실) |
|---|---|---|---|---|

- 불확실한 문장은 삭제하거나 고쳐 쓴 뒤 다시 검증한다.
- 불확실이 하나라도 남으면 "검수 필요"로 표시하고 이유를 쓴다.
- 절대 스스로 "Pass"나 "승인"이라고 표시하지 않는다. 최종 승인은 사람이 한다.

## 에피소드마다 만들 산출물

1. `output/episode_날짜_주제.mp4` (자막·내레이션이 사실 목록 범위 안에 있어야 함)
2. `output/thumbnails/episode_날짜_주제.png`
3. `output/thumbnails/episode_날짜_주제.upload.txt` (제목 / 설명 / 해시태그 / 근거 링크)
4. `output/thumbnails/episode_날짜_주제.factcheck.md` (사실 목록 + 출처 + 자기검증표 +
   사람이 확인할 항목)

# 작업 지시 처리 규칙 (Claude Code, 2026-10-11~)

에피소드 수정·제작 지시를 받을 때 이 흐름을 따른다.

- 지시를 받으면 되묻지 말고 바로 실행한다. 되묻는 것은 아래 두 경우뿐이다.
  (a) 지시문이 "아래 내용"이라고 했는데 실제 내용이 메시지에 없을 때: 한 줄로
      "교체 내용이 없습니다. 다시 보내주세요"라고만 하고 멈춘다.
  (b) 파일 삭제·덮어쓰기처럼 되돌릴 수 없는 작업일 때.
- 의도가 짐작되면 짐작대로 진행하고, 가정한 내용을 결과 맨 위에 한 줄로 적는다.
  사용자가 확인해 주기를 기다리며 멈추지 않는다.
- 기존 파일은 덮어쓰지 않는다. 영상·이미지는 `_v2`처럼 새 파일로 저장한다
  (render-shorts.yml의 `output_file` 입력으로 경로 지정 가능 — 2026-10-11 추가).
  upload.txt처럼 교체 지시가 명확한 텍스트 파일만 교체하되, 교체 전 원본을
  `.bak`으로 남긴다.
- 사용자가 따로 말하지 않는 한 구글 드라이브·시트는 건드리지 않는다.
- 스스로 "Pass"나 "승인"이라고 표시하지 않는다. 최종 승인은 사람이 한다.
- 결과 보고는 5줄 이내로 쓴다: ① 한 일 ② 가정한 것 ③ 확인 못 한 것(출처 없음·접근
  불가) ④ 만든/바꾼 파일 이름 ⑤ 사람이 확인할 것.
- 위 "콘텐츠 작성 규칙"(사실 목록 → 출처 3곳 이상 → 자기검증표, 주장은 "~라고
  주장"으로 표기, 인용·수치는 확인된 것만, [속보]는 1일 지나면 삭제)은 모든
  에피소드에 항상 적용한다 — 이 섹션은 그 작업을 어떤 태도·형식으로 수행할지에
  대한 절차이고, "콘텐츠 작성 규칙"은 내용 자체의 기준이라 서로 대체하지 않는다.

# Claude Code notes

Everything shared between agents lives in `AGENTS.md` (imported above).
This file is only for notes specific to Claude Code.

- Designated development branch for this repo's automated tasks:
  `claude/gemini-collaboration-setup-by3aea` (see repo task instructions).
- MCP servers available to Claude Code in this environment are managed at
  the platform/session level, not via a local `.claude/settings.json` — if
  you add a project-scoped MCP server here, mirror it in
  `.gemini/settings.json` so Gemini CLI has the same access.

# 글로벌 톱 벤치마킹 기준 (Global Top Benchmarking Standards)

이 프로젝트의 코드와 파이프라인을 설계·수정할 때는 아래 4가지를 항상 기준으로 삼는다.
새 기능을 추가하거나 리뷰할 때 이 기준에 어긋나면 "동작은 한다"만으로 통과시키지 않는다.

## 1. 프로덕션 레벨의 아키텍처 기준

- **지양**: 스크립트가 중간에 멈추거나 API 에러 하나로 그냥 꺼져버리는 아마추어식 구조.
- **기준**: 상태 유지형(Stateful) 파이프라인, 강력한 예외 처리(Error Recovery), 일시적
  오류(429/503 등) 자동 재시도(Retry) 로직을 설계 단계부터 포함한다.
- **적용 사례**: `orchestrator/ai_collaboration.py`의 `post()`는 429/503을 지수
  백오프(10s → 20s → 40s → 80s)로 최대 4회 재시도한다. Gemini 무료 티어 키가 트래픽이
  몰릴 때 503을 자주 반환하는 걸 실제로 겪고 나서 넣은 방어 로직이다.

## 2. 에이전틱 파이프라인과 역할 분담 (Agentic Workflow)

- **지양**: 하나의 AI(예: ChatGPT 하나)에게 전부 맡기는 단일 모델 의존.
- **기준**: 방대한 웹 검색·데이터 수집은 광범위한 컨텍스트와 탐색 능력이 검증된 모델
  (Gemini)이 맡고, 논리적 검증·구조화·최종 패키징은 정교한 추론에 특화된 모델(Claude)이
  이어받는 분업형 에이전트 체계를 고수한다. 자세한 구조는 아래 "AI 협업 파이프라인 가이드"
  참고.

## 3. '팩트 기반'과 '실전 효용성' 중심의 검증 (Fact-Based & Real-World Utility)

- **지양**: AI가 그럴듯하게 지어내거나(Hallucination) 대충 요약하고 넘어가는 것.
- **기준**: 리서치 단계부터 최신 뉴스, 공신력 있는 데이터, 실물 지표 등 검증 가능한 사실만
  수집하도록 강제하고, 그 위에서 실무에 바로 쓸 수 있는 구체적 산출물(리포트/코드/패키지)을
  만든다. `orchestrator/ai_collaboration.py`의 프롬프트가 FACT / FORECAST / TARGET /
  INTERPRETATION을 명시적으로 분리하도록 요구하는 것도 이 때문이다.

## 4. 지속적인 최신 트렌드 이식 (Fast-Following Top Standards)

- AI 생태계는 변화가 매우 빠르다. "지금 전 세계 개발자들이 가장 선호하는 방식이 무엇인가"를
  끊임없이 탐색하고, 새 프레임워크나 더 효율적인 기법이 나오면 파이프라인에 즉시 반영한다.
- **적용 사례**: 모델 ID를 코드에 하드코딩하지 않고 `GEMINI_MODEL` / `CLAUDE_MODEL` 저장소
  변수로 오버라이드할 수 있게 설계했다. 모델이 폐기되거나(`gemini-2.5-flash`,
  `claude-sonnet-4-20250514`가 실제로 이렇게 폐기됐다) 더 나은 버전이 나와도 코드를 건드릴
  필요 없이 변수 값만 바꾸면 된다.

## 섹터별 벤치마킹 지침 (Sector-Specific Benchmarking)

- **2차 전지·로봇 섹터 분석 시**: 해당 분야의 글로벌 톱티어 기업(예: Tesla, Boston
  Dynamics 등)의 최신 뉴스도 반드시 함께 벤치마킹할 것. 국내/특정 기업 자료만으로
  분석을 끝내지 말고, 그 섹터를 이끄는 글로벌 선두 기업들의 동향(기술 발표, 실적,
  파트너십, 리콜/사고 등 리스크 이슈 포함)을 리서치 단계(Gemini)에서 함께 수집해
  비교 기준으로 삼는다.

# AI 협업 파이프라인 가이드 (Claude 메인 → Gemini 서포트, 인스타그램 릴스)

파이프라인의 산출물은 **인스타그램 릴스**(세로 9:16, 90초 이하 권장) 전용이다.
유튜브 롱폼용으로 되돌리려면 `input.md`의 Task와
`orchestrator/ai_collaboration.py`의 프롬프트를 함께 바꿔야 한다.

## 구성 파일

| 파일 | 역할 |
|---|---|
| `.github/workflows/three-ai-collaboration.yml` | 파이프라인을 실행하는 GitHub Actions 워크플로 |
| `orchestrator/ai_collaboration.py` | 실제 Claude → Gemini 호출 로직 |
| `input.md` | 파이프라인에 넣을 소스 자료 (기본 입력 파일) |
| `artifacts/01-claude-lead-draft.md` | Claude가 만든 릴스 제작 초안 (자동 생성) |
| `artifacts/02-final-reels-package.md` | Gemini가 갭을 채운 최종 산출물 (자동 생성) |

## 흐름

1. **Claude(메인)** — 리드 프로듀서 겸 1차 저작자 역할. 소스 자료를 바탕으로 릴스
   제작 패키지 전체(훅, 타임스탬프 대본, 샷 리스트, 자막/온스크린 텍스트, 캡션 초안,
   해시태그, 트렌딩 오디오 방향, 커버 프레임, CTA, QC 체크리스트)를 직접 작성한다.
   스스로 검증할 수 없는 항목(실시간 트렌딩 오디오명, 최신 해시태그 성과, 최신
   수치/사실 등)은 지어내지 않고 `[VERIFY-GEMINI: ...]` 마커로 명시적으로 표시한다.
2. **Gemini(서포트)** — Claude의 창작·구조적 선택은 그대로 두고, 문서 안의
   `[VERIFY-GEMINI: ...]` 마커만 리서치로 채운 뒤 최종 QC(팩트 라벨링 일관성,
   저작권/음원 라이선스 리스크, 커뮤니티 가이드라인 리스크, 해시태그·캡션 정합성)를
   수행해 최종 산출물을 완성한다.

OpenAI(GPT) 3단계는 원래 있었지만 결제 문제로 제거했다. 필요해지면
`orchestrator/ai_collaboration.py`에 `openai()` 함수를 다시 추가하고, 워크플로에
`OPENAI_API_KEY` 시크릿과 가드 체크(`test -n "$OPENAI_API_KEY" || ...`)를 복원하면 된다.

## 실행 방법

- **수동 실행**: Actions 탭 → "AI Collaboration" → Run workflow → `input_file` 지정
  (기본값 `input.md`)
- **자동 실행**: `input.md`, `inputs/**`, `orchestrator/**`,
  `.github/workflows/three-ai-collaboration.yml` 중 하나가 바뀌는 push 시 자동 트리거

## 필요한 저장소 설정

**Secrets** (Settings → Secrets and variables → Actions → **Secrets** 탭 — 반드시 이
탭이어야 한다. Variables 탭에 넣으면 평문으로 로그에 노출된다):

- `GEMINI_API_KEY` — https://aistudio.google.com 의 "Get API key"에서 발급 (Vertex AI
  콘솔에서 발급한 키는 이 REST 호출 방식과 호환되지 않아 404가 난다)
- `ANTHROPIC_API_KEY` — https://console.anthropic.com/settings/keys

**Variables** (같은 페이지의 Variables 탭 — 평문, 민감정보 아님):

- `GEMINI_MODEL` — 권장값 `gemini-flash-latest` (특정 버전 대신 별칭을 쓰면 모델이
  세대교체돼도 코드/설정을 안 건드려도 됨)
- `CLAUDE_MODEL` — 권장값 `claude-sonnet-5`

## 겪었던 함정들 (읽고 반복하지 말 것)

- **Secrets vs Variables 탭 착각**: 시크릿을 Variables 탭에 잘못 등록하면 값이
  암호화되지 않고 CI 로그에 그대로 찍힌다. 실제로 OpenAI 키가 이렇게 노출된 적이 있어서
  즉시 폐기·재발급했다. 시크릿은 반드시 Secrets 탭에.
- **시크릿 이름 불일치**: 워크플로가 읽는 이름(`GEMINI_API_KEY` 등)과 저장소에 등록한
  이름이 정확히 일치해야 한다. `GAMINI_MODEL`처럼 오타가 나거나 `_MODEL`/`_API_KEY`를
  헷갈리면 "Missing ... secret" 에러로 즉시 드러난다.
- **모델 폐기**: `gemini-2.5-flash`와 `claude-sonnet-4-20250514`는 둘 다 API가
  404/`not_found_error`를 반환하며 폐기됐다. 404가 나면 키 문제가 아니라 모델 ID
  문제일 가능성부터 의심할 것 — 실제로 잘못된 키는 400을 반환하지 404를 반환하지 않는다.
- **Gemini 무료 티어 503**: 특히 `-latest` 별칭은 트래픽이 몰릴 때 일시적으로 503을
  반환하는 일이 흔하다. `post()`의 재시도 로직이 이걸 흡수하도록 설계돼 있다.
- **읽기 타임아웃은 `HTTPError`가 아니다**: 2026-10-07 실제 라이브 실행에서
  `TimeoutError`("The read operation timed out")가 발생했는데, 당시 `post()`가
  `except urllib.error.HTTPError`만 잡고 있어서 재시도 한 번도 없이 1차 시도에서
  그대로 올라왔다 — 심지어 `run()`의 Gemini 실패 폴백(except 블록)도 똑같이
  `HTTPError`만 잡고 있어서 폴백 파일조차 안 쓰이고 그냥 죽었다. `post()`와
  `run()` 양쪽 다 `except (urllib.error.HTTPError, TimeoutError,
  urllib.error.URLError)`로 넓혀서 고쳤다 (`HTTPError`가 `URLError`의 서브클래스라
  순서상 먼저 잡아야 함에 주의). 네트워크 호출에 예외 처리를 추가할 때는 상태코드
  기반 에러만 생각하지 말고 타임아웃/연결 끊김도 항상 같이 챙길 것.
- **API 키를 채팅/커밋에 붙여넣지 않기**: 디버깅 중 키가 필요하면 GitHub Actions
  워크플로 안에서 길이/앞뒤 몇 글자만 출력하거나, 실제 호출 결과(상태 코드 + 응답
  본문)만 출력하는 임시 디버그 스텝을 추가했다가 원인을 찾으면 바로 되돌리는 방식을
  썼다 — 키 값 자체는 로그에도, 대화에도 남기지 않는다.

@youtube-guide.md
