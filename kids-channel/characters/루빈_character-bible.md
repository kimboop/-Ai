# 캐릭터 바이블 — 루빈 (Rubin)

- **성별**: 여자아이
- **종**: 유니콘
- **참고 이미지**: `references/루빈_reference.webp` (사용자 제공)

## 설정 (초안 — 성격·세계관은 스토리 작업 시 더 다듬을 것)
- 우아하고 반짝이는 분위기의 유니콘. 티노(아기 티라노사우루스, 남자아이)와
  단짝 친구
- 참고 이미지의 분위기(반짝이는 무지개 빛 효과, 따뜻한 숲속 배경)로 보아
  "마법·신비로움" 쪽 캐릭터로 설정하기 좋음 — 다정하고 상냥한 성격으로
  제안

## 외형 (참고 이미지 기준)
- 전체적으로 하얀색/아주 옅은 라벤더색 털
- 길고 풍성한 웨이브 긴 갈기(라벤더~연보라 톤, 그러데이션), 일부 가닥은
  작게 땋아 구슬 장식을 함
- 이마에서 뻗어나온 나선형의 반짝이는(투명하게 빛나는) 뿔, 뿔 주변으로
  무지개색 반짝이 입자/빛줄기 효과
- 크고 따뜻한 갈색 눈, 부드러운 속눈썹, 다정하고 친근한 미소(이빨이 살짝
  보임)
- 목에 작은 보석 펜던트와 나뭇잎 모양 장식이 달린 목걸이
  (은은한 금속/보석 느낌)
- 몸 전체·갈기에 은은한 반짝이(스파클) 입자 효과
- 날씬하고 우아한 체형, 네 다리로 서 있는 자세
- 분위기: 완전한 플랫 애니메이션이 아니라, 사실적인 털 질감 + 신비로운
  반짝임이 섞인 "하이엔드 패밀리 판타지 영화" 느낌 (포토리얼과 스타일라이즈
  사이)

## Higgsfield 캐릭터 시트 프롬프트 (커스텀 렌더 모듈, split-screen)

참고 이미지가 표준 "3d-stylized(픽사풍)"보다 더 사실적인 털 질감과 반짝이
효과가 강해서, 포토리얼과 스타일라이즈드를 섞은 커스텀 렌더 모듈로
작성했다. 실제 생성 전 사용자 확인 필요(계정 크레딧 부족 — README 참고).
확인되면 아래 프롬프트로 `generate_image` 실행 (16:9):

```
Split-screen character sheet composition, left side a full-body shot of the character standing upright in a neutral pose facing the camera with all four legs on the ground, full head-to-toe framing with the whole body and all legs visible, right side a tight close-up chest-up portrait of the same character, identical original character on both sides, single subject only exactly one character in frame, pure white seamless studio background, professional character sheet presentation, a graceful young unicorn mascot character for a preschool kids show, female character, soft pale lavender-white fur coat with fine realistic fur texture, long flowing wavy mane in a lavender-to-soft-purple gradient with a few small braided strands and tiny bead accents, a spiraled translucent glowing horn with a faint rainbow sparkle trail curling above the head, large warm brown eyes with soft natural catchlights, no oversized specular glare, soft friendly eyelashes, gentle warm smile with a hint of teeth, a delicate necklace with a small gem pendant and leaf-shaped charms, fine shimmering sparkle particles scattered across the coat and mane, semi-realistic 3D animated film render blending natural fur detail with warm stylized family-film appeal, elegant slender proportions, soft global illumination, warm natural forest-toned studio lighting, gentle rim light, high-end 3D animation studio quality, cinematic family-fantasy-film render, clean neutral background, 4K, single subject only, exactly one character, no other characters, no duplicate figures, no props, no furniture, no background objects, left panel standing full-body head-to-toe not cropped, right panel tight close-up not full body, no text, no watermark, no logos, no frame borders, wholesome warm friendly expression suitable for toddlers, no scary or sharp features
```

- 이후 에피소드에서도 위 외형 설명(색·갈기·뿔·목걸이)을 그대로 유지하고
  포즈·표정만 바꿔서 재사용한다(일관성 유지 원칙).
