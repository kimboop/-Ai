"""Draw the six 9:16 scene images for the 10/12 gym deduction short.

Flat navy + gold graphics, no words (captions carry the text), drawn at 2x
and downscaled for smooth edges. Artwork stays in the upper ~65% of the
frame because the captions sit in the lower third.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

S = 2
W, H = 1080 * S, 1920 * S
BG_TOP, BG_BOT = (15, 26, 48), (10, 18, 34)        # #0F1A30 -> darker
GOLD, GOLD_D = (232, 181, 74), (176, 132, 44)
CREAM, MUTED, PANEL = (244, 241, 234), (96, 112, 142), (27, 42, 74)
RED = (214, 104, 92)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def canvas():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOT)))
    # soft gold glow behind the artwork
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    cx, cy = W // 2, int(H * 0.36)
    for r in range(900 * S // 2, 0, -12 * S):
        a = int(26 * (1 - r / (900 * S / 2)))
        g.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*GOLD, a))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    return img, ImageDraw.Draw(img)


def save(img, name):
    img.convert("RGB").resize((W // S, H // S), Image.LANCZOS).save(OUT / name, optimize=True)


def p(v):
    return int(v * S)


def dumbbell(d, cx, cy, k=1.0, col=GOLD):
    bar_w, bar_h = p(360 * k), p(34 * k)
    d.rounded_rectangle([cx - bar_w // 2, cy - bar_h // 2, cx + bar_w // 2, cy + bar_h // 2], p(14 * k), fill=CREAM)
    for side in (-1, 1):
        for i, (w, h) in enumerate([(p(54 * k), p(230 * k)), (p(44 * k), p(170 * k))]):
            x = cx + side * (bar_w // 2 - p(40 * k) - i * p(62 * k))
            d.rounded_rectangle([x - w // 2, cy - h // 2, x + w // 2, cy + h // 2], p(16 * k), fill=col)


def card(d, x, y, w, h, tilt_col=GOLD):
    d.rounded_rectangle([x, y, x + w, y + h], p(36), fill=PANEL, outline=tilt_col, width=p(8))
    d.rectangle([x, y + int(h * 0.22), x + w, y + int(h * 0.36)], fill=(12, 20, 38))
    d.rounded_rectangle([x + p(46), y + int(h * 0.52), x + p(46) + p(110), y + int(h * 0.52) + p(80)], p(14), fill=GOLD)
    for i in range(3):
        d.rounded_rectangle([x + p(46) + i * p(120), y + int(h * 0.80), x + p(46) + i * p(120) + p(90), y + int(h * 0.80) + p(18)], p(9), fill=MUTED)


def check(d, cx, cy, r, col=GOLD):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    d.line([(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.38), (cx + r * 0.5, cy - r * 0.35)], fill=(12, 20, 38), width=int(r * 0.22), joint="curve")


def cross(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED)
    o = r * 0.4
    for a, b in [((cx - o, cy - o), (cx + o, cy + o)), ((cx - o, cy + o), (cx + o, cy - o))]:
        d.line([a, b], fill=(12, 20, 38), width=int(r * 0.22))


# scene01 — dumbbell + card (hook)
img, d = canvas()
dumbbell(d, W // 2, p(560), 1.25)
card(d, p(300), p(800), p(480), p(300))
check(d, p(760), p(820), p(70))
save(img, "scene01.png")

# scene02 — gym + pool + calendar page "7"
img, d = canvas()
dumbbell(d, p(330), p(470), 0.75)
for i in range(3):  # pool waves
    y = p(420) + i * p(70)
    pts = [(p(620) + x * p(10), y + int(p(18) * ((-1) ** (x // 6)))) for x in range(0, 33, 6)]
    d.line(pts, fill=(110, 170, 220), width=p(18), joint="curve")
d.rounded_rectangle([p(360), p(700), p(720), p(1100)], p(30), fill=CREAM)
d.rounded_rectangle([p(360), p(700), p(720), p(800)], p(30), fill=GOLD)
d.rectangle([p(360), p(760), p(720), p(800)], fill=GOLD)
for x in (p(450), p(630)):
    d.rounded_rectangle([x - p(14), p(670), x + p(14), p(740)], p(10), fill=MUTED)
f = ImageFont.truetype(FONT, p(230))
d.text((W // 2, p(950)), "7", font=f, fill=(15, 26, 48), anchor="mm")
save(img, "scene02.png")

# scene03 — 300 badge + card
img, d = canvas()
cx, cy, r = W // 2, p(560), p(270)
d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD)
d.ellipse([cx - r + p(26), cy - r + p(26), cx + r - p(26), cy + r - p(26)], outline=GOLD_D, width=p(10))
f = ImageFont.truetype(FONT, p(190))
d.text((cx, cy), "300", font=f, fill=(15, 26, 48), anchor="mm")
card(d, p(330), p(900), p(420), p(260))
save(img, "scene03.png")

# scene04 — O/X comparison: ticket (counts) vs bottle + shoe (excluded)
img, d = canvas()
for x0 in (p(90), p(560)):
    d.rounded_rectangle([x0, p(320), x0 + p(430), p(1080)], p(40), fill=PANEL)
# ticket
tx, ty = p(140), p(560)
d.rounded_rectangle([tx, ty, tx + p(330), ty + p(200)], p(24), fill=GOLD)
for cy_ in (ty + p(100),):
    d.ellipse([tx - p(30), cy_ - p(30), tx + p(30), cy_ + p(30)], fill=PANEL)
    d.ellipse([tx + p(300), cy_ - p(30), tx + p(360), cy_ + p(30)], fill=PANEL)
for i in range(4):
    d.ellipse([tx + p(165) - p(8), ty + p(30) + i * p(42), tx + p(165) + p(8), ty + p(46) + i * p(42)], fill=GOLD_D)
check(d, p(305), p(910), p(80))
# bottle
bx = p(690)
d.rounded_rectangle([bx, p(520), bx + p(80), p(800)], p(26), fill=(120, 170, 210))
d.rounded_rectangle([bx + p(18), p(480), bx + p(62), p(525)], p(8), fill=CREAM)
# shoe
d.rounded_rectangle([p(800), p(700), p(950), p(790)], p(30), fill=CREAM)
d.rounded_rectangle([p(800), p(640), p(870), p(740)], p(28), fill=CREAM)
d.rectangle([p(800), p(775), p(955), p(800)], fill=MUTED)
cross(d, p(775), p(910), p(80))
save(img, "scene04.png")

# scene05 — receipt checklist + card (to-do)
img, d = canvas()
rx, ry, rw, rh = p(300), p(300), p(480), p(760)
d.rectangle([rx, ry, rx + rw, ry + rh], fill=CREAM)
for i in range(12):  # zigzag bottom edge
    x = rx + i * rw // 12
    d.polygon([(x, ry + rh), (x + rw // 24, ry + rh + p(30)), (x + rw // 12, ry + rh)], fill=CREAM)
for i in range(3):
    y = ry + p(150) + i * p(190)
    check(d, rx + p(90), y, p(44))
    d.rounded_rectangle([rx + p(160), y - p(16), rx + rw - p(60), y + p(16)], p(12), fill=MUTED)
card(d, p(560), p(860), p(380), p(240))
save(img, "scene05.png")

# scene06 — bell + week strip with Sunday highlighted (CTA)
img, d = canvas()
cx, cy = W // 2, p(520)
d.pieslice([cx - p(200), cy - p(230), cx + p(200), cy + p(170)], 180, 360, fill=GOLD)
d.rectangle([cx - p(200), cy - p(30), cx + p(200), cy + p(150)], fill=GOLD)
d.polygon([(cx - p(200), cy + p(150)), (cx - p(250), cy + p(210)), (cx + p(250), cy + p(210)), (cx + p(200), cy + p(150))], fill=GOLD)
d.ellipse([cx - p(50), cy + p(200), cx + p(50), cy + p(290)], fill=GOLD_D)
d.ellipse([cx - p(30), cy - p(290), cx + p(30), cy - p(230)], fill=GOLD_D)
for i in range(7):
    x = p(130) + i * p(120)
    fill = GOLD if i == 6 else PANEL
    d.rounded_rectangle([x, p(930), x + p(100), p(1050)], p(22), fill=fill)
save(img, "scene06.png")
print("ok")
