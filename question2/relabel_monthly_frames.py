"""Put a large bold month + year label in the top-right of each monthly frame and rebuild the GIF."""
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


def label_frame(src: Path, month_idx: int) -> Image.Image:
    im = Image.open(src).convert("RGBA")
    canvas = Image.new("RGBA", im.size, (7, 13, 20, 255))
    canvas.alpha_composite(im)

    month = MONTHS[month_idx]
    year = "2020"
    mean_txt = f"{MEANS[month_idx]:.6f}"
    sub = "mean NO2 (mol/m2)"

    font_month = get_font(max(56, im.width // 5))
    font_year = get_font(max(34, im.width // 9))
    font_sub = get_font(max(15, im.width // 24))

    # Build a tight badge image first, then paste it.
    probe = Image.new("RGBA", (800, 400), (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(probe)
    lines = [
        (month, font_month, (240, 199, 94, 255)),
        (year, font_year, (255, 255, 255, 255)),
        (mean_txt, font_sub, (61, 187, 154, 255)),
        (sub, font_sub, (210, 218, 228, 255)),
    ]

    pad_x, pad_y, gap = 12, 8, 2
    widths, heights = [], []
    for text, font, _ in lines:
        bbox = pdraw.textbbox((0, 0), text, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])

    block_w = max(widths) + pad_x * 2
    block_h = sum(heights) + gap * (len(lines) - 1) + pad_y * 2

    badge = Image.new("RGBA", (block_w, block_h), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(badge)
    bdraw.rounded_rectangle(
        [0, 0, block_w - 1, block_h - 1],
        radius=10,
        fill=(7, 13, 20, 220),
        outline=(240, 199, 94, 220),
        width=2,
    )

    y = pad_y
    for (text, font, color), w, h in zip(lines, widths, heights):
        x = block_w - pad_x - w
        bdraw.text((x, y), text, font=font, fill=color)
        y += h + gap

    x0 = im.width - block_w - 10
    y0 = 10
    canvas.alpha_composite(badge, (x0, y0))
    return canvas.convert("RGB")


def main():
    frame_paths = []
    for i in range(1, 13):
        src = FRAMES / f"no2_2020_{i:02d}.png"
        labeled = label_frame(src, i - 1)
        out = FRAMES / f"labeled_{i:02d}.png"
        labeled.save(out)
        frame_paths.append(out)
        print("Labeled", out.name, f"{MEANS[i-1]:.6f}")

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
