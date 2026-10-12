"""Add a clear top banner with bold month/year on one line and rebuild the GIF."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "web" / "q2" / "outputs"
FRAMES = OUT / "monthly_frames"
MONTHS = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
]
MEANS = [
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
    """Place glyph box top-left at (x, y)."""
    _, _, bbox = text_size(draw, text, font)
    draw.text((x - bbox[0], y - bbox[1]), text, font=font, fill=fill)


def label_frame(src: Path, month_idx: int) -> Image.Image:
    im = Image.open(src).convert("RGBA")

    # Tall banner ABOVE the map — labels never sit on the city outline.
    banner_h = 96
    canvas = Image.new("RGB", (im.width, im.height + banner_h), (7, 13, 20))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, im.width, banner_h], fill=(10, 18, 28))

    month = MONTHS[month_idx]
    year = "2020"
    title = f"{month}  {year}"  # one line — cannot overlap each other
    mean_txt = f"{MEANS[month_idx]:.6f}"

    font_title = get_font(44)
    font_mean = get_font(18)
    font_unit = get_font(15)

    # Left: mean value + unit
    draw_text_topleft(draw, 14, 18, mean_txt, font_mean, (61, 187, 154))
    draw_text_topleft(draw, 14, 48, "mean NO2 (mol/m2)", font_unit, (200, 210, 220))

    # Right: MONTH  YEAR as one bold line
    tw, th, _ = text_size(draw, title, font_title)
    title_x = im.width - 16 - tw
    title_y = (banner_h - 6 - th) // 2
    draw_text_topleft(draw, title_x, title_y, title, font_title, (240, 199, 94))

    # Gold rule under banner, clear of text
    draw.line([(0, banner_h - 3), (im.width, banner_h - 3)], fill=(240, 199, 94), width=3)

    # Map below banner on dark background
    map_bg = Image.new("RGBA", im.size, (7, 13, 20, 255))
    map_bg.alpha_composite(im)
    canvas.paste(map_bg.convert("RGB"), (0, banner_h))
    return canvas


def main():
    frame_paths = []
    for i in range(1, 13):
        src = FRAMES / f"no2_2020_{i:02d}.png"
        labeled = label_frame(src, i - 1)
        out = FRAMES / f"labeled_{i:02d}.png"
        labeled.save(out)
        frame_paths.append(out)
        print("Labeled", out.name)

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
