# 아빠모해TV 쇼츠 자동화 (Project AutoShorts)

`video_generator.py`는 대본 JSON을 받아 [Pixabay](https://pixabay.com/api/docs/)
세로형 B-roll + [Edge-TTS](https://github.com/rany2/edge-tts) 내레이션 +
`moviepy`로 9:16 프리미엄 뉴스 쇼츠(제목 배지 + 자막 카드)를 렌더링하는
스크립트다. `orchestrator/ai_collaboration.py`가 만드는 최종 프로덕션
패키지(대본·장면 지시)를 구조화한 JSON을 입력으로 받는다고 가정한다.

> **왜 Pexels가 아니라 Pixabay인가**: 원래 Pexels을 썼는데, 대시보드에 보이는
> 키 값과 바이트 단위로 완전히 일치하는 키를 등록해도 Pexels API가 계속
> `401 Invalid API key`로 거부했다(계정 승인/활성화 쪽 문제로 추정 — 코드나
> 시크릿 등록 문제가 아님을 GitHub Actions 러너에서 직접 curl로 재확인함).
> Pixabay는 가입 즉시 키가 바로 활성화되는 경우가 대부분이라 이 대기 없이
> 바로 쓸 수 있어서 교체했다.

## 아키텍처 메모

- **상태 유지(Stateful)**: 내레이션 오디오(`voice.mp3`)와 씬별 Pixabay
  다운로드를 `output/.cache/<episode>/`에 캐싱한다. 대본 텍스트가 안 바뀌면
  재실행해도 내레이션을 다시 합성하지 않고, 같은 검색어의 B-roll도 다시
  받지 않는다 — Pixabay/Edge-TTS 쿼터를 불필요하게 태우지 않기 위함이다.
- **재시도**: Pixabay 검색·다운로드는 `orchestrator/ai_collaboration.py`의
  `post()`와 같은 429/503 지수 백오프(최대 4회)를 쓴다. Edge-TTS 합성도
  일시적 오류에 3회까지 재시도한다.
- **빠른 실패**: 폰트나 `PIXABAY_API_KEY`가 없으면 렌더링을 시작하기 전에
  명확한 에러로 막는다. 폰트를 못 찾았다고 조용히 기본 비트맵 폰트로
  대체하지 않는다 — "프리미엄 뉴스 쇼츠"에 깨진 자막을 그대로 내보내는
  건 렌더링이 아예 안 되는 것보다 나쁘다.
- Pixabay 한 곳에서 못 찾은 씬은 남색 단색(`ColorClip`) 배경으로 폴백하고
  경고 로그를 남긴 뒤 계속 진행한다 — 씬 하나 때문에 전체 쇼츠 제작이
  중단되지는 않는다.

## 의존성 (Dependencies)

### 시스템 의존성

- **ffmpeg** — 별도 설치 불필요. `pip install -r scripts/requirements.txt`가
  설치하는 `imageio-ffmpeg`(moviepy의 의존성)가 정적 빌드된 ffmpeg를
  자동으로 받아서 쓴다. 네트워크가 막힌 환경에서만 시스템 ffmpeg를 설치하고
  `FFMPEG_BINARY` 환경변수로 경로를 지정한다.
  ```bash
  # Debian/Ubuntu
  sudo apt-get install -y ffmpeg
  export FFMPEG_BINARY=$(which ffmpeg)
  ```

### Python 의존성

```bash
pip install -r scripts/requirements.txt
```

| 패키지 | 용도 |
|---|---|
| `moviepy` (2.x) | 클립 합성, 크롭/루프, 자막·타이틀 오버레이, 최종 인코딩 |
| `Pillow` | 자막 카드/타이틀 배지를 그리는 이미지 렌더링 |
| `numpy` | moviepy ↔ Pillow 프레임 배열 변환 |
| `edge-tts` | 마이크로소프트 Edge 브라우저 TTS 엔진으로 내레이션 합성 |

Pixabay 호출은 별도 SDK 없이 표준 라이브러리(`urllib`)로 직접 구현했다 —
`orchestrator/ai_collaboration.py`와 같은 재시도 로직을 공유하기 위해서다.

**ImageMagick은 필요 없다.** 자막/타이틀은 `PIL.ImageDraw`로 직접 렌더링한
이미지를 `ImageClip`으로 합성하는 방식이라 moviepy `TextClip`/ImageMagick
경로를 아예 타지 않는다.

### 폰트 (Fonts)

`create_subtitle_image`/`create_title_image`는 폰트 파일 경로를 **명시적으로**
요구한다. 못 찾으면 렌더링 전에 에러로 막는다(비트맵 폰트로 조용히 대체하지
않음).

- 기본으로 찾는 순서: `SHORTS_FONT_BOLD`/`SHORTS_FONT_EXTRABOLD` 환경변수 →
  `assets/fonts/NanumGothicBold.ttf` / `NanumGothicExtraBold.ttf` →
  시스템 경로 `/usr/share/fonts/truetype/nanum/...` (Debian/Ubuntu 패키지가
  설치하는 위치).
- 로컬/CI에 나눔고딕을 설치하려면:
  ```bash
  # Debian/Ubuntu — /usr/share/fonts/truetype/nanum/에 바로 설치됨.
  # NanumGothicBold.ttf는 fonts-nanum에 있지만 NanumGothicExtraBold.ttf(타이틀용)는
  # 별도 패키지인 fonts-nanum-extra에 들어있다 — 하나만 설치하면 타이틀 카드
  # 렌더링에서 "Font not found"가 난다. 둘 다 설치할 것.
  sudo apt-get install -y fonts-nanum fonts-nanum-extra
  # 또는 프로젝트에 직접 배치
  # https://github.com/naver/nanumfont 에서 받아 assets/fonts/에 복사
  ```
- 나눔고딕은 SIL Open Font License로 재배포·임베드가 허용된다. 폰트 파일
  자체는 이 저장소에 커밋하지 않는다 — 각 환경에서 위 방법으로 설치/배치한다.
- 다른 폰트로 바꾸려면 `SHORTS_FONT_BOLD`(자막용) / `SHORTS_FONT_EXTRABOLD`
  (타이틀용) 환경변수로 경로를 지정한다. 한글을 쓸 거라면 한글 글리프를
  지원하는 폰트여야 한다.

## 필요한 환경변수

- `PIXABAY_API_KEY` — https://pixabay.com/api/docs/ 에서 발급 (가입 후
  계정 페이지에 바로 표시됨). **절대 코드나 대화에 붙여넣지 말고** 로컬
  환경변수 또는 CI 시크릿으로만 전달한다 (`GEMINI_API_KEY`/
  `ANTHROPIC_API_KEY`와 동일한 취급 — 루트 `CLAUDE.md` 참고).

선택 환경변수:
- `SHORTS_TTS_VOICE` — Edge-TTS 보이스 (기본 `ko-KR-SunHiNeural`). 사용 가능한
  보이스 목록: `edge-tts --list-voices`
- `SHORTS_FONT_BOLD` / `SHORTS_FONT_EXTRABOLD` — 폰트 경로 오버라이드
- `VIDEO_FPS` (기본 30), `VIDEO_PRESET` (기본 `medium`), `VIDEO_RENDER_THREADS`
  (기본 CPU 코어 수), `FFMPEG_BINARY`

## 대본 JSON 스키마

```json
{
  "title": "글로벌 핵심 이슈 리포트",
  "scenes": [
    {
      "script": "오늘의 첫 번째 소식입니다.",
      "broll_query": "news studio vertical"
    },
    {
      "script": "두 번째 소식으로 넘어가겠습니다.",
      "broll_query": "city skyline night vertical"
    }
  ]
}
```

- `script`: 필수. 해당 씬에서 읽을 대사 — 전체 씬의 `script`를 이어붙여
  Edge-TTS로 한 번에 합성하고, 합성된 오디오 길이를 씬 개수로 나눠 씬별
  길이를 정한다(원본 프로토타입과 동일한 방식).
- `broll_query`: 선택. 해당 씬의 B-roll을 찾을 Pixabay 검색어. 생략 시
  `"news background vertical"`.

## 사용법

```bash
# 샘플 대본 생성
python scripts/video_generator.py scripts/episode.json --init

# 스키마만 검증 (렌더링 없음, moviepy/edge-tts 없어도 동작)
python scripts/video_generator.py scripts/episode.json --validate-only

# 렌더링
export PIXABAY_API_KEY=...
python scripts/video_generator.py scripts/episode.json

# 캐시 무시하고 내레이션·B-roll 처음부터 다시 받기
python scripts/video_generator.py scripts/episode.json --no-resume
```

### 썸네일

`scripts/make_thumbnail.py`는 video_generator.py와 같은 팔레트/폰트로 9:16
브랜드 썸네일을 만든다. Pixabay 등 외부 이미지가 전혀 필요 없어서(순수
타이포그래피 + PIL 도형) 네트워크가 막힌 환경에서도 바로 쓸 수 있다.

```bash
python scripts/make_thumbnail.py \
  --title "헤드라인 첫 줄\n헤드라인 둘째 줄" \
  --kicker "테크 이슈" \
  --subtitle "부제목" \
  --output output/thumbnails/episode-name.png
```

주요 옵션:

| 옵션 | 설명 |
|---|---|
| `--output` | 출력 MP4 경로 (기본: `output/<episode-stem>.mp4`) |
| `--work-dir` | 내레이션/B-roll 캐시 위치 커스터마이즈 |
| `--voice` | Edge-TTS 보이스 오버라이드 |
| `--fps` / `--preset` / `--threads` | 인코딩 옵션 |

## 테스트

용도가 다른 테스트 스크립트가 두 개 있다.

| | `scripts/test_mock.py` | `scripts/test_run.py` |
|---|---|---|
| 검증 대상 | 자막/타이틀 카드, 크롭, 캐싱, 합성 구조 (Pixabay/Edge-TTS는 모킹) | Pixabay + Edge-TTS까지 포함한 실제 렌더링 1회 |
| 네트워크 | 불필요 | 필요 (Pixabay REST + Edge-TTS 웹소켓) |
| API 키 | 불필요 | `PIXABAY_API_KEY` 필요 |
| 언제 쓰나 | 로직을 고칠 때마다, 방화벽/프록시 뒤에서도 | 배포 전 마지막 확인, 새 환경 셋업 직후 |

```bash
# 로직 검증 — 네트워크/키 없이 어디서나
python scripts/test_mock.py -v

# 실가동 검증 — 아래 "실가동 검증 가이드" 환경에서만 의미가 있다
export PIXABAY_API_KEY=...
python scripts/test_run.py
```

`test_run.py`가 `speech.platform.bing.com` SSL/연결 에러나 `pixabay.com`
401/403으로 실패한다면 보통 코드 문제가 아니라 지금 실행 중인 환경(방화벽·사내
프록시·제한된 아웃바운드 정책, 또는 키 자체가 아직 비활성 상태)이 웹소켓이나
해당 호스트를 막고 있다는 뜻이다.

## 실가동 검증 가이드 (로컬 PC / GitHub Actions)

이 파이프라인을 개발한 샌드박스 세션은 외부 API 호스트가 아웃바운드 정책으로
차단돼 있고, Edge-TTS가 쓰는 웹소켓 업그레이드 자체를 프록시가 지원하지 않아서
`test_run.py`의 라이브 렌더링을 끝까지 돌릴 수 없었다 — 둘 다 그 세션 고유의
네트워크 정책 때문이지 코드 문제가 아니며, `scripts/test_mock.py`로 로직 자체는
이미 검증했다. 아래 두 환경에는 이런 제약이 없다.

### 로컬 PC

```bash
pip install -r scripts/requirements.txt
sudo apt-get install -y fonts-nanum fonts-nanum-extra   # macOS는 위 "폰트" 절 참고
export PIXABAY_API_KEY=발급받은_키
python scripts/test_run.py                              # 스모크 테스트
python scripts/video_generator.py scripts/episode.json   # 실제 대본으로 렌더링
```

### GitHub Actions

1. Settings → Secrets and variables → Actions → **Secrets** 탭(Variables 탭
   아님 — 평문 노출 사고 사례가 루트 `CLAUDE.md`에 있다)에 `PIXABAY_API_KEY` 등록.
2. 워크플로:
   ```yaml
   - uses: actions/setup-python@v5
     with:
       python-version: '3.12'
   - run: pip install -r scripts/requirements.txt
   - run: sudo apt-get install -y fonts-nanum fonts-nanum-extra
   - run: python scripts/test_mock.py            # 항상 실행 — 네트워크 불필요
   - env:
       PIXABAY_API_KEY: ${{ secrets.PIXABAY_API_KEY }}
     run: python scripts/video_generator.py scripts/episode.json
   ```
   `ubuntu-latest` 러너는 아웃바운드 네트워크 제한이 없어서 Pixabay REST 호출과
   Edge-TTS 웹소켓이 둘 다 정상 동작한다.

## 트러블슈팅

- **`Missing PIXABAY_API_KEY`**: 위 "필요한 환경변수" 참고. 시크릿을 코드에
  하드코딩하지 말 것.
- **`Font not found`**: 위 "폰트" 절 참고 — `fonts-nanum`과 `fonts-nanum-extra`를
  둘 다 설치했는지 확인(ExtraBold는 별도 패키지) 또는
  `SHORTS_FONT_BOLD`/`SHORTS_FONT_EXTRABOLD` 지정.
- **`moviepy could not locate an ffmpeg binary`**: `pip install -r
  scripts/requirements.txt`를 다시 실행(imageio-ffmpeg가 바이너리를 다시
  받음). 네트워크가 막힌 환경이면 `FFMPEG_BINARY` 폴백 사용.
- **Pixabay가 특정 씬에서 결과를 못 찾음**: 로그에 경고가 남고 해당 씬은
  남색 단색 배경으로 자동 대체된다 — `broll_query`를 더 구체적으로
  바꾸면 보통 해결된다.
- **Pixabay가 401/403을 반환함**: 키 값 자체가 틀렸거나(복사 버튼으로
  다시 복사해볼 것) Pixabay 계정이 아직 승인/활성화되지 않은 상태일 수
  있다 — 이건 코드로 고칠 수 없으니 Pixabay 계정 상태를 확인할 것.
- **Edge-TTS가 SSL/네트워크 에러를 낸다**: 방화벽·프록시 환경에서 흔하다.
  사내 프록시를 쓰는 경우 해당 프록시의 CA 인증서를 시스템 신뢰 저장소에
  등록해야 `edge-tts`(aiohttp 기반)가 접속할 수 있다. 단, 프록시가 **웹소켓
  업그레이드 자체를 지원하지 않는** 경우(정책 기반 아웃바운드 프록시에서
  흔함)는 인증서를 맞춰도 소용없다 — Edge-TTS는 REST가 아니라 웹소켓으로
  통신한다. 이럴 땐 우회하려 하지 말고 위 "실가동 검증 가이드"의 환경에서
  돌릴 것.
- **렌더링이 중간에 죽었다**: 같은 명령을 다시 실행하면 된다. 내레이션과
  이미 받은 B-roll은 `output/.cache/<episode>/`에서 재사용된다.

## 업로드 자동화 절충안 (트랙 A, 2026-10-07~)

YouTube Data API(`videos.insert`)를 직접 붙이지 않은 상태라, **영상 파일 자체를
YouTube에 올리는 "업로드" 버튼은 아직 사용자가 직접 눌러야 한다.** 대신 vidIQ
MCP 연결(`mcp__vidIQ__*`)로 업로드 이후 번거로운 작업(제목/설명/태그/썸네일
입력, 공개 전환)은 자동화했다.

**채널**: 아빠모해TV, channelId `UCiiNvTZMmWZHB90FwQQ9dpQ` (vidIQ에 연결돼
있어야 함 — 연결 안 돼 있으면 `vidiq_user_channels`가 빈 배열을 반환한다).

### 매일 자동 루틴이 하는 일
1. 영상 렌더링 완료 후, 업로드용 제목/설명/태그/썸네일을
   `scripts/upload_meta/<YYYY-MM-DD>_<슬러그>.json`에 저장한다
   (`{"title", "description", "tags": [5개], "thumbnail_path", "episode_file", "run_url"}`).
2. 사용자에게 "영상 파일을 비공개/미등록으로만 업로드하고 알려달라"고 안내한다
   (제목·설명·썸네일은 입력할 필요 없음 — 파일만 올리면 됨).

### "업로드했어" 같은 말이 들어오면 (후속 처리 — Claude가 직접 실행)
1. `scripts/upload_meta/`에서 가장 최근 메타데이터 파일을 읽는다.
2. `vidiq_user_videos`(channelId 위 참고, `privacyStatus: ["private","unlisted"]`,
   `order: "newest"`)로 방금 올라온 원본 영상을 찾는다. 여러 개가 애매하면
   제목/업로드 시각으로 사용자에게 확인 후 진행한다.
3. `vidiq_update_video`로 title/description/tags/`privacyStatus: "public"`을
   한 번에 반영한다.
4. 썸네일 PNG를 읽어서 base64 data URI(`data:image/png;base64,...`)로 변환한
   뒤 `vidiq_update_video_thumbnail`의 `thumbnail` 파라미터로 전달한다
   (`thumbnailFile`은 OpenAI 첨부파일 전용이라 여기선 못 쓴다 — 로컬 파일은
   `thumbnail`에 data URI로 넣는 방식만 가능, PNG 2MiB 이하).
5. 완료되면 최종 영상 링크를 사용자에게 보고한다.

완전 자동 업로드(사람이 파일을 올리는 과정까지 없애는 것)를 원하면 별도로
Google OAuth 앱 + `videos.insert` 연동이 필요하다 — 아직 안 만들었다.
