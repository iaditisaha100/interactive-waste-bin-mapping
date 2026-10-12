"""Re-export Q2 map PNGs/GIF with a white Greater Mumbai boundary outline."""
from pathlib import Path

import ee
import geemap
import geopandas as gpd
import requests
from PIL import Image, ImageDraw

PROJECT_ID = "solar-grail-510708-p8"
ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_PATH = ROOT / "dataset" / "Mumbai_boundary.geojson"
OUT_DIR = ROOT / "web" / "q2" / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

NO2_BAND = "tropospheric_NO2_column_number_density"
CLOUD_BAND = "cloud_fraction"
HIGH_NO2_COLOR = "#ff6b6b"
no2_vis = {
    "min": 0,
    "max": 0.0002,
    "palette": [
        "#071820",
        "#0b3d4a",
        "#147a7f",
        "#3dbb9a",
        "#f0c75e",
        "#f4a261",
        "#e76f51",
        "#c1121f",
    ],
}
month_names = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def mask_clouds(img):
    return img.updateMask(img.select(CLOUD_BAND).lte(0.2))


def add_boundary_outline(rgb, mumbai_ee, width=3):
    """Dark fill outside the city + white ULB outline (like the Pune reference)."""
    bg = (
        ee.Image.constant([7, 13, 20])
        .toByte()
        .rename(["vis-red", "vis-green", "vis-blue"])
    )
    base = bg.blend(rgb)
    outline = (
        ee.Image()
        .byte()
        .paint(mumbai_ee, 1, width)
        .selfMask()
        .visualize(palette=["ffffff"])
    )
    return base.blend(outline)


def thumb_bytes(image, region, dimensions=800):
    url = image.getThumbURL(
        {
            "region": region,
            "dimensions": dimensions,
            "format": "png",
        }
    )
    return requests.get(url, timeout=180).content


def main():
    ee.Initialize(project=PROJECT_ID)
    print("EE OK")

    mumbai_gdf = gpd.read_file(BOUNDARY_PATH)
    if mumbai_gdf.crs is None or mumbai_gdf.crs.to_epsg() != 4326:
        mumbai_gdf = mumbai_gdf.to_crs(epsg=4326)
    mumbai_ee = geemap.geopandas_to_ee(mumbai_gdf)
    region = mumbai_ee.geometry().bounds()

    no2_2020 = (
        ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_NO2")
        .filterBounds(mumbai_ee.geometry())
        .filterDate("2020-01-01", "2021-01-01")
    )
    annual_no2 = (
        no2_2020.map(mask_clouds).select(NO2_BAND).mean().clip(mumbai_ee.geometry())
    )

    annual_rgb = add_boundary_outline(annual_no2.visualize(**no2_vis), mumbai_ee)
    annual_path = OUT_DIR / "mumbai_2020_mean_no2.png"
    annual_path.write_bytes(thumb_bytes(annual_rgb, region, 800))
    print("Saved", annual_path)

    p75 = annual_no2.reduceRegion(
        reducer=ee.Reducer.percentile([75]),
        geometry=mumbai_ee.geometry(),
        scale=1000,
        maxPixels=1e13,
        bestEffort=True,
    )
    threshold = ee.Number(p75.get(NO2_BAND))
    high_no2 = annual_no2.gte(threshold).selfMask()

    exposure_rgb = annual_no2.visualize(**no2_vis)
    high_vis = high_no2.visualize(min=0, max=1, palette=[HIGH_NO2_COLOR])
    exposure_map = add_boundary_outline(
        ee.ImageCollection([exposure_rgb, high_vis]).mosaic(),
        mumbai_ee,
    )
    exposure_path = OUT_DIR / "mumbai_2020_no2_65plus_exposure.png"
    exposure_path.write_bytes(thumb_bytes(exposure_map, region, 800))
    print("Saved", exposure_path)

    frames_dir = OUT_DIR / "monthly_frames"
    frames_dir.mkdir(exist_ok=True)
    frame_paths = []

    for m in range(1, 13):
        start = ee.Date.fromYMD(2020, m, 1)
        end = start.advance(1, "month")
        month_img = (
            no2_2020.filterDate(start, end)
            .map(mask_clouds)
            .select(NO2_BAND)
            .mean()
            .clip(mumbai_ee.geometry())
        )
        month_rgb = add_boundary_outline(month_img.visualize(**no2_vis), mumbai_ee)
        raw_path = frames_dir / f"no2_2020_{m:02d}.png"
        raw_path.write_bytes(thumb_bytes(month_rgb, region, 700))

        im = Image.open(raw_path).convert("RGBA")
        bar = Image.new("RGBA", (im.width, 36), (7, 13, 20, 235))
        labeled = Image.new("RGBA", (im.width, im.height + 36), (7, 13, 20, 255))
        labeled.paste(bar, (0, 0))
        labeled.paste(im, (0, 36))
        draw = ImageDraw.Draw(labeled)
        draw.text(
            (12, 8),
            f"Greater Mumbai — {month_names[m - 1]} 2020 tropospheric NO2",
            fill=(243, 247, 251),
        )
        labeled_path = frames_dir / f"labeled_{m:02d}.png"
        labeled.convert("RGB").save(labeled_path)
        frame_paths.append(labeled_path)
        print("Frame", m)

    gif_path = OUT_DIR / "mumbai_2020_monthly_no2.gif"
    frames = [Image.open(p).convert("RGB") for p in frame_paths]
    frames[0].save(
        gif_path, save_all=True, append_images=frames[1:], duration=700, loop=0
    )
    print("Saved", gif_path)
    print("Done with white boundary outlines.")


if __name__ == "__main__":
    main()
