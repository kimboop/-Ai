@AGENTS.md

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
- **API 키를 채팅/커밋에 붙여넣지 않기**: 디버깅 중 키가 필요하면 GitHub Actions
  워크플로 안에서 길이/앞뒤 몇 글자만 출력하거나, 실제 호출 결과(상태 코드 + 응답
  본문)만 출력하는 임시 디버그 스텝을 추가했다가 원인을 찾으면 바로 되돌리는 방식을
  썼다 — 키 값 자체는 로그에도, 대화에도 남기지 않는다.
