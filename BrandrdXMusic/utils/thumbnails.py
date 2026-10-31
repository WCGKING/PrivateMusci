import os
import urllib.request
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

WIDTH, HEIGHT = 1280, 720
OUTPUT_DIR = "downloads"


def _font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _load_cover(cover):
    """Accept an HTTP(S) URL or a local image path."""
    if not cover:
        return None
    try:
        if str(cover).startswith(("http://", "https://")):
            request = urllib.request.Request(
                str(cover), headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read()
            return Image.open(BytesIO(data)).convert("RGB")
        if os.path.isfile(str(cover)):
            return Image.open(str(cover)).convert("RGB")
    except Exception:
        return None
    return None


def _fit_cover(image, size):
    image = image.copy()
    target_w, target_h = size
    scale = max(target_w / image.width, target_h / image.height)
    image = image.resize(
        (int(image.width * scale), int(image.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = (image.width - target_w) // 2
    top = (image.height - target_h) // 2
    return image.crop((left, top, left + target_w, top + target_h))


def _time_label(seconds):
    seconds = max(0, int(seconds or 0))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def generate_thumbnail(
    title,
    artist="Unknown Artist",
    album="",
    duration=0,
    current_time=0,
    thumbnail_url=None,
    output_path=None,
):
    """
    Create a light lavender/white music-player thumbnail.

    thumbnail_url can be an image URL or a local image path.
    duration and current_time are seconds.
    Returns the generated image path.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    title = str(title or "Unknown Track").strip()
    artist = str(artist or "Unknown Artist").strip()
    album = str(album or "").strip()

    duration = max(0, int(duration or 0))
    current_time = max(0, min(int(current_time or 0), duration)) if duration else 0
    progress = (current_time / duration) if duration else 0

    cover = _load_cover(thumbnail_url)

    # Soft, blurred background based on the actual song artwork.
    if cover:
        background = _fit_cover(cover, (WIDTH, HEIGHT)).filter(
            ImageFilter.GaussianBlur(42)
        )
        background = ImageEnhance.Brightness(background).enhance(1.65)
        background = Image.blend(
            background,
            Image.new("RGB", (WIDTH, HEIGHT), (248, 242, 255)),
            0.76,
        )
    else:
        background = Image.new("RGB", (WIDTH, HEIGHT), (247, 242, 255))

    canvas = background.convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Soft pastel glow accents.
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-180, -180, 390, 390), fill=(203, 151, 255, 95))
    gd.ellipse((900, 390, 1450, 920), fill=(255, 174, 225, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(65))
    canvas = Image.alpha_composite(canvas, glow)
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Main glass panel.
    draw.rounded_rectangle(
        (28, 28, WIDTH - 28, HEIGHT - 28),
        radius=42,
        fill=(255, 255, 255, 190),
        outline=(255, 255, 255, 235),
        width=3,
    )

    # Artwork shadow and cover.
    art_x, art_y, art_size = 72, 125, 500
    shadow = Image.new("RGBA", (art_size + 50, art_size + 50), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        (18, 18, art_size + 30, art_size + 30),
        radius=38,
        fill=(102, 48, 160, 75),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    canvas.alpha_composite(shadow, (art_x - 25, art_y - 25))

    if cover:
        artwork = _fit_cover(cover, (art_size, art_size))
    else:
        artwork = Image.new("RGB", (art_size, art_size), (229, 211, 250))
        ad = ImageDraw.Draw(artwork)
        ad.text((art_size // 2, art_size // 2), "♫", anchor="mm",
                font=_font(180, True), fill=(112, 48, 190))

    mask = Image.new("L", (art_size, art_size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, art_size, art_size), radius=34, fill=255
    )
    artwork_rgba = artwork.convert("RGBA")
    artwork_rgba.putalpha(mask)
    canvas.alpha_composite(artwork_rgba, (art_x, art_y))

    draw = ImageDraw.Draw(canvas, "RGBA")

    # Header and song details.
    draw.rounded_rectangle(
        (650, 100, 1040, 165), radius=30,
        fill=(111, 42, 190, 235)
    )
    draw.text((845, 132), "NOW PLAYING", anchor="mm",
              font=_font(27, True), fill=(255, 255, 255, 255))

    # Keep title within the available width.
    title_font = _font(57, True)
    while draw.textbbox((0, 0), title, font=title_font)[2] > 540 and len(title) > 8:
        title = title[:-4].rstrip() + "..."

    draw.text((650, 205), title, font=title_font,
              fill=(38, 24, 54, 255))

    draw.text((650, 300), "ARTIST", font=_font(17, True),
              fill=(132, 92, 165, 255))
    draw.text((650, 328), artist[:42], font=_font(29, True),
              fill=(65, 43, 85, 255))

    if album:
        draw.text((650, 385), "ALBUM", font=_font(17, True),
                  fill=(132, 92, 165, 255))
        draw.text((650, 412), album[:42], font=_font(25),
                  fill=(83, 62, 103, 255))

    # Progress bar and elapsed / total time.
    bar_x, bar_y, bar_w, bar_h = 650, 500, 535, 15
    draw.rounded_rectangle(
        (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h),
        radius=8, fill=(210, 193, 229, 255)
    )
    if duration:
        filled = max(0, min(bar_w, int(bar_w * progress)))
        if filled:
            draw.rounded_rectangle(
                (bar_x, bar_y, bar_x + filled, bar_y + bar_h),
                radius=8, fill=(145, 54, 220, 255)
            )
        knob_x = bar_x + filled
        draw.ellipse(
            (knob_x - 13, bar_y - 10, knob_x + 13, bar_y + 25),
            fill=(255, 255, 255, 255),
            outline=(145, 54, 220, 255),
            width=4,
        )

    draw.text((650, 530), _time_label(current_time), font=_font(22, True),
              fill=(75, 55, 95, 255))
    draw.text((1185, 530), _time_label(duration), anchor="ra",
              font=_font(22, True), fill=(75, 55, 95, 255))

    # Decorative playback controls (visual only; Telegram buttons remain functional).
    centers = [760, 900, 1040, 1180]
    cy = 625
    for cx in centers:
        draw.ellipse(
            (cx - 37, cy - 37, cx + 37, cy + 37),
            fill=(255, 255, 255, 225),
            outline=(164, 104, 220, 255),
            width=3,
        )

    # Previous icon.
    draw.polygon([(774, 607), (774, 643), (751, 625)], fill=(115, 50, 180, 255))
    draw.rectangle((744, 607, 750, 643), fill=(115, 50, 180, 255))

    # Large pause icon.
    draw.ellipse(
        (850, 570, 950, 670),
        fill=(112, 39, 184, 255),
        outline=(255, 255, 255, 255),
        width=4,
    )
    draw.rounded_rectangle((887, 598, 900, 642), radius=4, fill="white")
    draw.rounded_rectangle((907, 598, 920, 642), radius=4, fill="white")

    # Next icon.
    draw.polygon([(1026, 607), (1026, 643), (1049, 625)], fill=(115, 50, 180, 255))
    draw.rectangle((1050, 607, 1056, 643), fill=(115, 50, 180, 255))

    # Subtle music-note decoration and footer.
    draw.text((95, 650), "♫", font=_font(42, True),
              fill=(137, 75, 205, 220))
    draw.rounded_rectangle(
        (250, 650, 690, 690), radius=20,
        fill=(255, 255, 255, 205),
        outline=(196, 159, 226, 220),
        width=2,
    )
    draw.text((470, 670), "Powered by BrandrdXMusic",
              anchor="mm", font=_font(19, True),
              fill=(105, 48, 160, 255))

    if not output_path:
        output_path = os.path.join(OUTPUT_DIR, "brandrd_music_thumbnail.png")

    canvas.convert("RGB").save(output_path, "PNG", optimize=True)
    return output_path
