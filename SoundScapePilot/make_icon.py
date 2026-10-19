"""Extract the pasted logo from opencode's db and build the app icon set.

Outputs:
  logo.ico                        (project root - PyInstaller EXE + WiX shortcuts)
  static/logo.ico                 (favicon)
  static/logo.png                 (sidebar <img>, emblem only)
  logo.png                        (named master preview, 512)
  assets/soundscape_pilot_logo_src.png (raw extracted source)
"""
import base64
import io
import json
import math
import os
import sqlite3

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = r"C:\Users\flana\.local\share\opencode\opencode.db"
SRC = os.path.join(ROOT, "assets", "soundscape_pilot_logo_src.png")
FONT_PATH = r"C:\Windows\Fonts\ariblk.ttf"
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
SMALL_SIZES = {16, 24, 32, 48}  # emblem only, no text


def extract_source():
    if os.path.exists(SRC):
        return SRC
    con = sqlite3.connect(f"file:{DB.replace(chr(92), '/')}?mode=ro", uri=True)
    con.execute("pragma busy_timeout=3000")
    rows = con.execute(
        "select data from part where data like '%soundscape_pilot_logo%' "
        "order by rowid desc limit 20"
    ).fetchall()
    con.close()
    for (raw,) in rows:
        payload = json.loads(raw)
        if payload.get("type") == "file" and "url" in payload:
            break
    else:
        raise SystemExit("pasted logo not found in opencode db")
    b64 = payload["url"].split("base64,", 1)[1]
    os.makedirs(os.path.dirname(SRC), exist_ok=True)
    with open(SRC, "wb") as f:
        f.write(base64.b64decode(b64))
    return SRC


def sample_palette(img):
    """(magenta_bg, navy, teal) sampled from the artwork."""
    px = img.convert("RGB")
    w, h = px.size
    corners = [px.getpixel((2, 2)), px.getpixel((w - 3, 2)),
               px.getpixel((2, h - 3)), px.getpixel((w - 3, h - 3))]
    bg = max(set(corners), key=corners.count)

    navy_votes, teal_votes = [], []
    for y in range(0, h, 7):
        for x in range(0, w, 7):
            r, g, b = px.getpixel((x, y))
            if abs(r - bg[0]) < 40 and abs(g - bg[1]) < 40 and abs(b - bg[2]) < 40:
                continue
            if g > 80 and b > 80 and r < g + 40 and abs(g - b) < 70:
                teal_votes.append((r, g, b))
            elif r + g + b < 330:
                navy_votes.append((r, g, b))

    def avg(votes, fallback):
        if not votes:
            return fallback
        n = len(votes)
        return tuple(sum(c[i] for c in votes) // n for i in range(3))

    return bg, avg(navy_votes, (16, 54, 79)), avg(teal_votes, (14, 143, 143))


def emblem_crop(img):
    """Crop the circular emblem (non-background artwork) from the source."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    bg = rgb.getpixel((2, 2))
    mask = Image.new("L", (w, h), 0)
    mp = mask.load()
    rp = rgb.load()
    for y in range(h):
        for x in range(w):
            r, g, b = rp[x, y]
            if abs(r - bg[0]) > 30 or abs(g - bg[1]) > 30 or abs(b - bg[2]) > 30:
                mp[x, y] = 255
    bbox = mask.getbbox()
    if not bbox:
        raise SystemExit("no emblem found in source")
    pad = 6
    bbox = (max(0, bbox[0] - pad), max(0, bbox[1] - pad),
            min(w, bbox[2] + pad), min(h, bbox[3] + pad))
    return img.crop(bbox), bg


def letter_spaced(draw, xy, text, font, fill, target_w):
    """Draw text at xy with tracking so total width == target_w."""
    widths = [draw.textlength(ch, font=font) for ch in text]
    natural = sum(widths)
    gaps = len(text) - 1
    extra = (target_w - natural) / gaps if gaps else 0
    x, y = xy
    for ch, cw in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += cw + extra
    return x


def font_fit(draw, text, max_w, start_px):
    size = start_px
    font = ImageFont.truetype(FONT_PATH, size)
    while draw.textlength(text, font=font) > max_w and size > 10:
        size -= 2
        font = ImageFont.truetype(FONT_PATH, size)
    return font


def build_masters(emblem, bg, navy):
    pad = 8

    # emblem-only master (square, artwork centered like the original)
    e = emblem.convert("RGBA")
    m = Image.new("RGB", (512, 512), bg)
    scale = (512 - 2 * pad) / max(e.size)
    e2 = e.resize((max(1, int(e.width * scale)), max(1, int(e.height * scale))), Image.LANCZOS)
    m.paste(e2, ((512 - e2.width) // 2, (512 - e2.height) // 2), e2)

    # named master: emblem on top, SOUNDSCAPE / PILOT stacked below
    W = H = 1024
    n = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(n)

    eb = emblem.convert("RGBA")
    box_w, box_h = int(W * 0.60), int(H * 0.50)
    s = min(box_w / eb.width, box_h / eb.height)
    ew, eh = int(eb.width * s), int(eb.height * s)
    eb = eb.resize((ew, eh), Image.LANCZOS)
    ex = (W - ew) // 2
    ey = int(H * 0.055)
    n.paste(eb, (ex, ey), eb)

    text_top = ey + eh + int(H * 0.045)
    target_w = int(W * 0.88)
    x0 = (W - target_w) // 2

    font1 = font_fit(d, "SOUNDSCAPE", target_w, int(H * 0.135))
    letter_spaced(d, (x0, text_top), "SOUNDSCAPE", font1, navy, target_w)

    line2_top = text_top + int(font1.size * 1.18)
    font2 = font_fit(d, "PILOT", target_w, int(H * 0.175))
    letter_spaced(d, (x0, line2_top), "PILOT", font2, navy, target_w)

    bottom = line2_top + int(font2.size * 1.1)
    overflow = bottom - (H - int(H * 0.045))
    if overflow > 0:  # compress vertically if it ran past the edge
        n = n.resize((W, H), Image.LANCZOS)
    return m, n


def main():
    src = extract_source()
    img = Image.open(src).convert("RGB")
    bg, navy, teal = sample_palette(img)
    emblem, _ = emblem_crop(img)
    print(f"source {img.size} bg={bg} navy={navy} teal={teal} emblem={emblem.size}")

    emblem_master, named_master = build_masters(emblem, bg, navy)

    # small sizes: emblem only; large: named
    ico_images = []
    for sz in ICO_SIZES:
        master = emblem_master if sz in SMALL_SIZES else named_master
        ico_images.append(master.resize((sz, sz), Image.LANCZOS))

    ico_root = os.path.join(ROOT, "logo.ico")
    for target in (ico_root, os.path.join(ROOT, "static", "logo.ico")):
        os.makedirs(os.path.dirname(target), exist_ok=True)
        ico_images[-1].save(target, format="ICO", sizes=[(s, s) for s in ICO_SIZES],
                            append_images=ico_images[:-1])

    emblem_master.resize((128, 128), Image.LANCZOS).save(
        os.path.join(ROOT, "static", "logo.png"))
    named_master.resize((512, 512), Image.LANCZOS).save(
        os.path.join(ROOT, "logo.png"))

    print("wrote logo.ico, static/logo.ico, static/logo.png, logo.png")


if __name__ == "__main__":
    main()
