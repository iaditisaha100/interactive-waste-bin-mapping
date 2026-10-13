"""Build wide GIF frames: centered map + clear month label + readable NO2 units."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "web" / "q2" / "outputs"
FRAMES = OUT / "monthly_frames"
MONTHS = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
]
# mol/m2 -> display as umol/m2 (* 1e6)
MEANS_MOL = [
    0.00012122771002100347,
    0.0001344614113413094,
    6.880824049356434e-05,
    3.1167083747727884e-05,
    2.528248632513494e-05,
    3.3787137553019465e-05,
    2.6177846744314662e-05,
    3.2956713088002256e-05,
    5.6979418709488174e-05,
    9.034704234676807e-05,
    0.00010548495940183935,
    0.0001679684995766481,
]

CANVAS_W = 920
CANVAS_H = 620
BG = (7, 13, 20)


def get_font(size):
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\calibrib.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1], bbox


def draw_text_topleft(draw, x, y, text, font, fill):
    _, _, bbox = text_size(draw, text, font)
    draw.text((x - bbox[0], y - bbox[1]), text, font=font, fill=fill)


def label_frame(src: Path, month_idx: int) -> Image.Image:
    im = Image.open(src).convert("RGBA")
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), BG)
    draw = ImageDraw.Draw(canvas)

    bar_h = 88
    draw.rectangle([0, 0, CANVAS_W, bar_h], fill=(10, 18, 28))
    draw.line([(0, bar_h - 3), (CANVAS_W, bar_h - 3)], fill=(240, 199, 94), width=3)

    month = MONTHS[month_idx]
    title = f"{month}  2020"
    mean_umol = MEANS_MOL[month_idx] * 1e6
    mean_txt = f"{mean_umol:.1f}"

    font_title = get_font(48)
    font_mean = get_font(28)
    font_unit = get_font(15)

    # Left: readable mean in umol/m2
    draw_text_topleft(draw, 20, 14, mean_txt, font_mean, (61, 187, 154))
    draw_text_topleft(draw, 20, 50, "mean NO2 (umol/m2)", font_unit, (200, 210, 220))

    # Top-right month/year
    tw, th, _ = text_size(draw, title, font_title)
    draw_text_topleft(
        draw,
        CANVAS_W - 20 - tw,
        (bar_h - 6 - th) // 2,
        title,
        font_title,
        (240, 199, 94),
    )

    # Centered map below the bar
    map_area_h = CANVAS_H - bar_h - 12
    map_area_w = CANVAS_W - 40
    scale = min(map_area_w / im.width, map_area_h / im.height)
    new_w = max(1, int(im.width * scale))
    new_h = max(1, int(im.height * scale))
    resized = im.resize((new_w, new_h), Image.Resampling.LANCZOS)

    map_bg = Image.new("RGBA", (new_w, new_h), (*BG, 255))
    map_bg.alpha_composite(resized)

    paste_x = (CANVAS_W - new_w) // 2
    paste_y = bar_h + (map_area_h - new_h) // 2
    canvas.paste(map_bg.convert("RGB"), (paste_x, paste_y))
    return canvas


def main():
    frame_paths = []
    for i in range(1, 13):
        src = FRAMES / f"no2_2020_{i:02d}.png"
        labeled = label_frame(src, i - 1)
        out = FRAMES / f"labeled_{i:02d}.png"
        labeled.save(out)
        frame_paths.append(out)
        print("Labeled", out.name, f"{MEANS_MOL[i-1]*1e6:.1f} umol/m2")

    frames = [Image.open(p).convert("RGB") for p in frame_paths]
    gif = OUT / "mumbai_2020_monthly_no2.gif"
    frames[0].save(
        gif,
        save_all=True,
        append_images=frames[1:],
        duration=800,
        loop=0,
    )
    print("Saved", gif)


if __name__ == "__main__":
    main()
