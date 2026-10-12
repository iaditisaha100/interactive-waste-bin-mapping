"""Draw a white Greater Mumbai boundary on exported map PNGs and rebuild the GIF."""
from pathlib import Path

import geopandas as gpd
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_PATH = ROOT / "dataset" / "Mumbai_boundary.geojson"
OUT_DIR = ROOT / "web" / "q2" / "outputs"
BG = (7, 13, 20, 255)
WHITE = (255, 255, 255, 255)
LINE_WIDTH = 3


def lonlat_to_px(lon, lat, bounds, width, height):
    minx, miny, maxx, maxy = bounds
    x = (lon - minx) / (maxx - minx) * (width - 1)
    y = (maxy - lat) / (maxy - miny) * (height - 1)
    return x, y


def draw_outline(im, gdf, bounds, width=LINE_WIDTH):
    canvas = Image.new("RGBA", im.size, BG)
    canvas.alpha_composite(im.convert("RGBA"))
    draw = ImageDraw.Draw(canvas)

    for geom in gdf.geometry:
        polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for poly in polys:
            rings = [poly.exterior, *poly.interiors]
            for ring in rings:
                pts = [
                    lonlat_to_px(lon, lat, bounds, canvas.width, canvas.height)
                    for lon, lat in ring.coords
                ]
                if len(pts) >= 2:
                    draw.line(pts, fill=WHITE, width=width, joint="curve")
    return canvas


def process_file(path, gdf, bounds):
    im = Image.open(path)
    out = draw_outline(im, gdf, bounds)
    out.save(path)
    print("Outlined", path.name)


def main():
    gdf = gpd.read_file(BOUNDARY_PATH)
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    bounds = tuple(gdf.total_bounds)

    targets = [
        OUT_DIR / "mumbai_2020_mean_no2.png",
        OUT_DIR / "mumbai_2020_no2_65plus_exposure.png",
        *sorted((OUT_DIR / "monthly_frames").glob("no2_2020_*.png")),
    ]

    for path in targets:
        if path.exists():
            process_file(path, gdf, bounds)
        else:
            print("Missing", path)

    frames_dir = OUT_DIR / "monthly_frames"
    frame_paths = []
    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    for i, raw_path in enumerate(sorted(frames_dir.glob("no2_2020_*.png")), start=1):
        im = Image.open(raw_path).convert("RGBA")
        bar = Image.new("RGBA", (im.width, 36), (7, 13, 20, 235))
        labeled = Image.new("RGBA", (im.width, im.height + 36), BG)
        labeled.paste(bar, (0, 0))
        labeled.paste(im, (0, 36))
        draw = ImageDraw.Draw(labeled)
        draw.text(
            (12, 8),
            f"Greater Mumbai — {month_names[i - 1]} 2020 tropospheric NO2",
            fill=(243, 247, 251, 255),
        )
        labeled_path = frames_dir / f"labeled_{i:02d}.png"
        labeled.convert("RGB").save(labeled_path)
        frame_paths.append(labeled_path)

    if frame_paths:
        frames = [Image.open(p).convert("RGB") for p in frame_paths]
        gif_path = OUT_DIR / "mumbai_2020_monthly_no2.gif"
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=700,
            loop=0,
        )
        print("Saved", gif_path)

    print("Done — white boundary outlines added.")


if __name__ == "__main__":
    main()
