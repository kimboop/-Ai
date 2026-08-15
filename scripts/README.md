# 아빠모해TV 쇼츠 자동화 (Project AutoShorts)

`video_generator.py`는 대본 JSON을 받아 [Pexels](https://www.pexels.com/api/)
세로형 B-roll + [Edge-TTS](https://github.com/rany2/edge-tts) 내레이션 +
`moviepy`로 9:16 프리미엄 뉴스 쇼츠(제목 배지 + 자막 카드)를 렌더링하는
스크립트다. `orchestrator/ai_collaboration.py`가 만드는 최종 프로덕션
패키지(대본·장면 지시)를 구조화한 JSON을 입력으로 받는다고 가정한다.

## 아키텍처 메모

- **상태 유지(Stateful)**: 내레이션 오디오(`voice.mp3`)와 씬별 Pexels
  다운로드를 `output/.cache/<episode>/`에 캐싱한다. 대본 텍스트가 안 바뀌면
  재실행해도 내레이션을 다시 합성하지 않고, 같은 검색어의 B-roll도 다시
  받지 않는다 — Pexels/Edge-TTS 쿼터를 불필요하게 태우지 않기 위함이다.
- **재시도**: Pexels 검색·다운로드는 `orchestrator/ai_collaboration.py`의
  `post()`와 같은 429/503 지수 백오프(최대 4회)를 쓴다. Edge-TTS 합성도
  일시적 오류에 3회까지 재시도한다.
- **빠른 실패**: 폰트나 `PEXELS_API_KEY`가 없으면 렌더링을 시작하기 전에
  명확한 에러로 막는다. 폰트를 못 찾았다고 조용히 기본 비트맵 폰트로
  대체하지 않는다 — "프리미엄 뉴스 쇼츠"에 깨진 자막을 그대로 내보내는
  건 렌더링이 아예 안 되는 것보다 나쁘다.
- Pexels 한 곳에서 못 찾은 씬은 남색 단색(`ColorClip`) 배경으로 폴백하고
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

Pexels 호출은 별도 SDK 없이 표준 라이브러리(`urllib`)로 직접 구현했다 —
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

- `PEXELS_API_KEY` — https://www.pexels.com/api/ 에서 발급. **절대 코드나
  대화에 붙여넣지 말고** 로컬 환경변수 또는 CI 시크릿으로만 전달한다
  (`GEMINI_API_KEY`/`ANTHROPIC_API_KEY`와 동일한 취급 — 루트 `CLAUDE.md`
  참고).

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
      "pexels_query": "news studio vertical"
    },
    {
      "script": "두 번째 소식으로 넘어가겠습니다.",
      "pexels_query": "city skyline night vertical"
    }
  ]
}
```

- `script`: 필수. 해당 씬에서 읽을 대사 — 전체 씬의 `script`를 이어붙여
  Edge-TTS로 한 번에 합성하고, 합성된 오디오 길이를 씬 개수로 나눠 씬별
  길이를 정한다(원본 프로토타입과 동일한 방식).
- `pexels_query`: 선택. 해당 씬의 B-roll을 찾을 Pexels 검색어. 생략 시
  `"news background vertical"`.

## 사용법

```bash
# 샘플 대본 생성
python scripts/video_generator.py scripts/episode.json --init

# 스키마만 검증 (렌더링 없음, moviepy/edge-tts 없어도 동작)
python scripts/video_generator.py scripts/episode.json --validate-only

# 렌더링
export PEXELS_API_KEY=...
python scripts/video_generator.py scripts/episode.json

# 캐시 무시하고 내레이션·B-roll 처음부터 다시 받기
python scripts/video_generator.py scripts/episode.json --no-resume
```

주요 옵션:

| 옵션 | 설명 |
|---|---|
| `--output` | 출력 MP4 경로 (기본: `output/<episode-stem>.mp4`) |
| `--work-dir` | 내레이션/B-roll 캐시 위치 커스터마이즈 |
| `--voice` | Edge-TTS 보이스 오버라이드 |
| `--fps` / `--preset` / `--threads` | 인코딩 옵션 |

## 트러블슈팅

- **`Missing PEXELS_API_KEY`**: 위 "필요한 환경변수" 참고. 시크릿을 코드에
  하드코딩하지 말 것.
- **`Font not found`**: 위 "폰트" 절 참고 — `fonts-nanum`과 `fonts-nanum-extra`를
  둘 다 설치했는지 확인(ExtraBold는 별도 패키지) 또는
  `SHORTS_FONT_BOLD`/`SHORTS_FONT_EXTRABOLD` 지정.
- **`moviepy could not locate an ffmpeg binary`**: `pip install -r
  scripts/requirements.txt`를 다시 실행(imageio-ffmpeg가 바이너리를 다시
  받음). 네트워크가 막힌 환경이면 `FFMPEG_BINARY` 폴백 사용.
- **Pexels가 특정 씬에서 결과를 못 찾음**: 로그에 경고가 남고 해당 씬은
  남색 단색 배경으로 자동 대체된다 — `pexels_query`를 더 구체적으로
  바꾸면 보통 해결된다.
- **Edge-TTS가 SSL/네트워크 에러를 낸다**: 방화벽·프록시 환경에서 흔하다.
  사내 프록시를 쓰는 경우 해당 프록시의 CA 인증서를 시스템 신뢰 저장소에
  등록해야 `edge-tts`(aiohttp 기반)가 접속할 수 있다.
- **렌더링이 중간에 죽었다**: 같은 명령을 다시 실행하면 된다. 내레이션과
  이미 받은 B-roll은 `output/.cache/<episode>/`에서 재사용된다.
