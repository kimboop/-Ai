# Video Generator

`video_generator.py`는 JSON 씬 매니페스트(이미지/B-roll + 내레이션 + 배경음악 +
SRT 자막)를 받아 `moviepy`로 최종 MP4를 렌더링하는 스크립트다. Gemini로
작업했던 유튜브 영상 자동화 시스템을 이식한 것으로, `orchestrator/ai_collaboration.py`가
만드는 최종 프로덕션 패키지(대본 · 장면별 지시 · SRT 초안)를 구조화한
`scenes.json`을 입력으로 받는다고 가정한다.

## 아키텍처 메모

- **상태 유지(Stateful)**: 씬마다 렌더링 결과를 `output/.cache/<manifest>/scene_N.mp4`에
  캐싱하고 `state.json`에 체크포인트를 남긴다. 중간에 죽거나 Ctrl-C로 멈춰도
  다시 실행하면 이미 렌더링된 씬은 건너뛴다(`--no-resume`으로 끌 수 있음).
- **재시도**: 매니페스트에 원격 URL(예: 스톡/AI 생성 이미지 다운로드 링크)이
  들어오면 `orchestrator/ai_collaboration.py`의 `post()`와 같은 방식으로
  지수 백오프 재시도를 한다.
- **빠른 실패**: 폰트 미설정, ffmpeg 없음, 매니페스트 스키마 오류는 렌더링을
  시작하기 전에 검증해서 즉시 에러 메시지로 알려준다 (`--validate-only`로
  렌더링 없이 검증만 가능).

## 의존성 (Dependencies)

### 시스템 의존성

- **ffmpeg** — moviepy가 인코딩/디코딩에 사용하는 필수 바이너리. **별도
  설치가 필요 없다**: `pip install -r scripts/requirements.txt`가 함께
  설치하는 `imageio-ffmpeg`가 정적 빌드된 ffmpeg 바이너리를 자동으로
  받아서 쓴다. 스크립트는 시작 시 moviepy가 실제로 ffmpeg를 찾았는지
  확인하고, 못 찾으면 렌더링 전에 에러로 알려준다.
  - 방화벽/오프라인 환경 등 `imageio-ffmpeg`의 바이너리 다운로드가 막힌
    경우에만 시스템 ffmpeg를 직접 설치하고 `FFMPEG_BINARY` 환경변수로
    경로를 지정한다:
    ```bash
    # Debian/Ubuntu
    sudo apt-get install -y ffmpeg
    # macOS (Homebrew)
    brew install ffmpeg
    export FFMPEG_BINARY=$(which ffmpeg)
    ```

- **ImageMagick은 필요 없음** — moviepy 1.x의 `TextClip`은 ImageMagick을
  요구했지만, `requirements.txt`에 고정한 moviepy 2.x는 `TextClip`에 폰트
  파일 경로를 직접 넘기는 방식으로 바뀌면서 ImageMagick 의존성이 사라졌다.
  1.x로 낮춰서 쓰지 말 것 — 이 스크립트의 `TextClip(font=...)` 호출은 2.x
  API 기준이다.

### Python 의존성

```bash
pip install -r scripts/requirements.txt
```

| 패키지 | 용도 |
|---|---|
| `moviepy` (2.x) | 클립 합성, Ken Burns 확대/축소, 자막 오버레이, 최종 인코딩 |
| `Pillow` | moviepy의 이미지/텍스트 렌더링 백엔드 |
| `numpy` | moviepy 내부 프레임 배열 연산 |

SRT 파싱은 별도 라이브러리 없이 스크립트 안에 20줄짜리 파서로 직접
구현했다 — 포맷이 단순해서 의존성을 하나 더 추가할 이유가 없었다.

### 폰트 (Fonts)

`TextClip`은 폰트 파일 경로를 **명시적으로** 요구한다(시스템 폰트를 이름으로
찾지 않는다). 폰트를 지정하지 않으면 스크립트가 렌더링 전에 명확한 에러를
낸다.

- 폰트 파일은 `assets/fonts/`에 넣는다 (`.ttf` / `.otf`).
- 매니페스트의 `"font"` 필드에 경로를 쓰거나, `VIDEO_FONT_PATH` 환경변수로
  전역 기본값을 지정한다. 매니페스트 쪽이 우선한다.
- 한글 자막/그래픽을 쓸 경우 한글을 지원하는 폰트가 필요하다. 무료·상업적
  이용 가능한 후보:
  - [Pretendard](https://github.com/orioncactus/pretendard) (SIL OFL 1.1)
  - [Noto Sans KR](https://fonts.google.com/noto/specimen/Noto+Sans+KR) (SIL OFL 1.1)
  - [Black Han Sans](https://fonts.google.com/specimen/Black+Han+Sans) (제목/썸네일용, SIL OFL 1.1) — 굵은 타이틀 카드용
- 라이선스 확인: 위 폰트는 모두 SIL Open Font License로 재배포·임베드가
  허용되지만, 다른 폰트를 추가할 때는 영상에 렌더링(임베드)해서 배포하는
  용도가 라이선스에서 허용되는지 반드시 확인할 것. 폰트 파일 자체는 이
  저장소에 커밋하지 않는 걸 권장 — 라이선스별 재배포 조건이 다르므로 각
  환경에서 다운로드해 `assets/fonts/`에 배치한다.

## 디렉터리 레이아웃

```
assets/
  fonts/        # .ttf/.otf — 커밋하지 않음, 각자 다운로드해서 배치
  images/       # 씬 배경/B-roll 정지 이미지
  video/        # 씬 배경/B-roll 영상 클립
  audio/        # 내레이션, 배경음악
  subtitles/    # SRT 초안 (artifacts/02-final-package.md의 SRT 섹션에서 추출)
scripts/
  video_generator.py
  scenes.json   # 씬 매니페스트 (--init으로 샘플 생성 가능)
output/
  <manifest>.mp4
  .cache/<manifest>/   # 씬별 렌더 캐시 + state.json (재실행 시 재사용)
```

## 씬 매니페스트 스키마

```json
{
  "resolution": [1920, 1080],
  "fps": 30,
  "font": "assets/fonts/Pretendard-Bold.ttf",
  "narration_audio": "assets/audio/narration.mp3",
  "background_music": "assets/audio/bgm.mp3",
  "bgm_volume": 0.15,
  "subtitles_srt": "assets/subtitles/final.srt",
  "scenes": [
    {
      "id": 1,
      "duration": 5.0,
      "visual": {
        "type": "image",
        "path": "assets/images/scene01.jpg",
        "ken_burns": true,
        "zoom_ratio": 1.08
      },
      "graphic": {
        "text": "출처: 예시 통계청 2026",
        "position": "bottom_left"
      }
    },
    {
      "id": 2,
      "duration": 4.0,
      "visual": { "type": "video", "path": "assets/video/broll01.mp4" }
    }
  ]
}
```

- `visual.type`: `image` (Ken Burns 팬/줌 지원) / `video` / `color` (플레이스홀더용
  단색 배경).
- `visual.path`: 로컬 경로(매니페스트 파일 기준 상대 경로) 또는 `http(s)://` URL
  (URL이면 자동으로 재시도 로직과 함께 다운로드해 캐싱).
- `graphic`: 하단 3분의1(lower-third) 스타일 텍스트 오버레이 — 그래픽 스펙의
  출처 표기 등에 사용.
- `subtitles_srt`: `artifacts/02-final-package.md`의 "SRT 초안" 섹션을 `.srt`
  파일로 뽑아 넣는다.

## 사용법

```bash
# 샘플 매니페스트 생성
python scripts/video_generator.py --init --manifest scripts/scenes.json

# 매니페스트 스키마만 검증 (렌더링 없음, moviepy/ffmpeg 없어도 동작)
python scripts/video_generator.py --manifest scripts/scenes.json --validate-only

# 렌더링
python scripts/video_generator.py --manifest scripts/scenes.json

# 캐시 무시하고 처음부터 다시 렌더링
python scripts/video_generator.py --manifest scripts/scenes.json --no-resume
```

주요 옵션:

| 옵션 | 설명 |
|---|---|
| `--output` | 출력 MP4 경로 (기본: `output/<manifest-stem>.mp4`) |
| `--preset` | ffmpeg x264 preset (`ultrafast`~`veryslow`, 기본 `medium`) |
| `--threads` | 인코딩 스레드 수 (기본: CPU 코어 수) |
| `--cache-dir` | 씬 렌더 캐시/상태 파일 위치 커스터마이즈 |

환경변수: `VIDEO_FONT_PATH`, `VIDEO_PRESET`, `VIDEO_RENDER_THREADS`.

## 트러블슈팅

- **`moviepy could not locate an ffmpeg binary`**: 보통은 `pip install -r
  scripts/requirements.txt`를 다시 실행하면 해결된다(imageio-ffmpeg가
  바이너리를 다시 받는다). 네트워크가 막힌 환경이면 위 "시스템 의존성"의
  `FFMPEG_BINARY` 폴백을 사용한다.
- **`No font configured`**: 매니페스트에 `"font"`를 추가하거나 `VIDEO_FONT_PATH`를
  설정. 폰트를 안 넣고 렌더링을 진행시켜 자막이 깨진 채로 인코딩되는 것보다
  렌더링 전에 막는 게 낫다고 판단해 의도적으로 하드 에러로 처리했다.
  (인코딩까지 다 끝난 뒤 자막이 비어있는 걸 발견하는 것보다 훨씬 싸다.)
  - 여러 픽스처(2.x 이전 버전) 문서에서 `TextClip(txt=...)` 예제를 볼 수 있는데,
  이 저장소는 moviepy 2.x 기준 `text=` 파라미터를 쓴다. 오래된 예제 코드를
  그대로 붙여넣지 말 것.
- **렌더링이 중간에 죽었다**: 그냥 같은 명령을 다시 실행하면 된다. 이미 완료된
  씬은 `output/.cache/<manifest>/`에서 재사용되고, 실패한 씬부터 다시
  렌더링한다.
- **배경음악이 씬 길이보다 짧다**: 자동으로 루프 처리된다(`bgm_volume`으로
  볼륨만 조절).
