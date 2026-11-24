"""Build Nuvio folder tile images and hero title logos.

Reads tiles.json, downloads each backdrop, and writes:
  tiles/<slug>.jpg  - 16:9 tile, black bottom gradient, bold title
  logos/<slug>.png  - transparent title logo for the hero area
"""
import io
import json
import os
import urllib.request

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 960, 540
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf"


def load_font_bytes():
    with urllib.request.urlopen(FONT_URL, timeout=60) as r:
        return r.read()


FONT_BYTES = load_font_bytes()


def font(size, weight=800):
    f = ImageFont.truetype(io.BytesIO(FONT_BYTES), size)
    try:
        axes = f.get_variation_axes()
        vals = []
        for a in axes:
            name = a.get("name", b"")
            name = name.decode() if isinstance(name, bytes) else str(name)
            if "eight" in name:  # Weight
                vals.append(weight)
            elif "ptical" in name:  # Optical size
                vals.append(min(max(size / 2, a["minimum"]), a["maximum"]))
            else:
                vals.append(a["default"])
        f.set_variation_by_axes(vals)
    except Exception:
        pass
    return f


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGB")


def cover(img, w, h):
    s = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def bottom_gradient(w, h, start=0.35, max_alpha=235):
    g = Image.new("L", (1, h), 0)
    for y in range(h):
        t = (y / h - start) / (1 - start)
        g.putpixel((0, y), int(max_alpha * max(0.0, min(1.0, t)) ** 1.4))
    return g.resize((w, h))


def spaced(draw, xy, text, fnt, spacing, fill, anchor_center=True):
    widths = [draw.textlength(c, font=fnt) for c in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x, y = xy
    if anchor_center:
        x -= total / 2
    for c, cw in zip(text, widths):
        draw.text((x, y), c, font=fnt, fill=fill, anchor="lm")
        x += cw + spacing


def genre_tile(bg_url, label):
    img = cover(fetch(bg_url), W, H)
    black = Image.new("RGB", (W, H), (0, 0, 0))
    img = Image.composite(black, img, bottom_gradient(W, H))
    d = ImageDraw.Draw(img)
    size = 96
    f = font(size)
    while d.textlength(label, font=f) > W - 110 and size > 40:
        size -= 4
        f = font(size)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((52, H - 48), label, font=f, fill=(0, 0, 0, 170), anchor="ls")
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    img = Image.alpha_composite(img.convert("RGBA"), shadow)
    ImageDraw.Draw(img).text((48, H - 52), label, font=f, fill="white", anchor="ls")
    return img.convert("RGB")


def dark_tile(bg_url, label):
    # Charcoal tile with a faint, heavily darkened backdrop and spaced caps
    base = Image.new("RGB", (W, H), (28, 28, 34))
    if bg_url:
        art = cover(fetch(bg_url), W, H).filter(ImageFilter.GaussianBlur(18))
        base = Image.blend(base, art, 0.18)
    shade = Image.new("RGB", (W, H), (0, 0, 0))
    base = Image.composite(shade, base, bottom_gradient(W, H, start=0.0, max_alpha=150))
    d = ImageDraw.Draw(base)
    text = label.upper()
    size = 64
    f = font(size, weight=500)
    while sum(d.textlength(c, font=f) for c in text) + 14 * len(text) > W - 120 and size > 30:
        size -= 2
        f = font(size, weight=500)
    spaced(d, (W / 2, H / 2), text, f, spacing=size * 0.22, fill=(240, 240, 245))
    return base


def logo(label):
    text = label.upper()
    f = font(150, weight=900)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    w = int(tmp.textlength(text, font=f)) + 60
    img = Image.new("RGBA", (w, 220), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((30, 110), text, font=f, fill="white", anchor="lm")
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


def main():
    cfg = json.load(open("tiles.json"))
    os.makedirs("tiles", exist_ok=True)
    os.makedirs("logos", exist_ok=True)
    for t in cfg:
        slug, label, style, bg = t["slug"], t["label"], t["style"], t.get("backdrop")
        try:
            img = genre_tile(bg, label) if style == "genre" else dark_tile(bg, label)
            img.save(f"tiles/{slug}.jpg", quality=88, optimize=True, progressive=True)
            logo(label).save(f"logos/{slug}.png", optimize=True)
            print("ok", slug)
        except Exception as e:
            print("FAILED", slug, e)


if __name__ == "__main__":
    main()
